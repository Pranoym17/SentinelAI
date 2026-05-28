from sqlalchemy.orm import Session

from app.models import Config, Incident
from app.services.integration_config_resolver import IntegrationConfigResolver
from app.services.jira_service import JiraService
from app.services.oncall_service import OnCallService
from app.services.slack_service import SlackService
from app.services.timeline_service import TimelineService


class ResponseAgent:
    def __init__(self, db: Session, config: Config):
        self.db = db
        self.config = config
        integration_configs = IntegrationConfigResolver(db)
        self.jira = JiraService(integration_configs.config_for("jira"))
        self.slack = SlackService(integration_configs.config_for("slack"))
        self.timeline = TimelineService(db)
        self.oncall = OnCallService(db)

    def route(self, incident: Incident, recommended_actions: list[str] | None = None) -> list[str]:
        actions_taken = []
        configured_actions = self.config.actions or []
        recommended_actions = recommended_actions or []

        if incident.confidence is None:
            return actions_taken

        if incident.confidence >= 80:
            current_oncall = self._identify_oncall(incident)
            if "jira" in configured_actions:
                result = self.jira.create_ticket(incident)
                if result.get("created"):
                    incident.jira_ticket_id = result["ticket_id"]
                    incident.jira_ticket_url = result["url"]
                    self.timeline.append(
                        incident.id,
                        "jira_created",
                        f"Jira ticket {result['ticket_id']} created",
                        {"url": result["url"]},
                    )
                    actions_taken.append("jira_created")
                    self._enhance_jira_incident(incident, recommended_actions, current_oncall, actions_taken)
                elif result.get("failed"):
                    self.timeline.append(incident.id, "jira_failed", result.get("reason", "Jira failed"))
                else:
                    self.timeline.append(incident.id, "jira_skipped", result.get("reason", "Jira skipped"))

            if "slack" in configured_actions:
                result = self.slack.post_incident_alert(incident, self._slack_actions(incident, recommended_actions))
                if result.get("posted"):
                    incident.slack_message_ts = result.get("ts")
                    self.timeline.append(incident.id, "slack_sent", "Slack incident alert sent")
                    actions_taken.append("slack_sent")
                    self._post_slack_update(
                        incident,
                        "Jira ticket is ready. Response ownership and recommended actions have been attached.",
                        "jira_context",
                    )
                elif result.get("failed"):
                    self.timeline.append(incident.id, "slack_failed", result.get("reason", "Slack post failed"))
                else:
                    self.timeline.append(incident.id, "slack_skipped", result.get("reason", "Slack skipped"))

        elif incident.confidence >= 50:
            if "slack" in configured_actions:
                current_oncall = self._identify_oncall(incident)
                result = self.slack.post_review_request(incident, self._slack_actions(incident, recommended_actions), current_oncall)
                if result.get("posted"):
                    incident.slack_message_ts = result.get("ts")
                    self.timeline.append(incident.id, "slack_review_requested", "Slack review request sent")
                    actions_taken.append("slack_review_requested")
                elif result.get("failed"):
                    self.timeline.append(incident.id, "slack_failed", result.get("reason", "Slack post failed"))
                else:
                    self.timeline.append(incident.id, "slack_skipped", result.get("reason", "Slack skipped"))
        else:
            current_oncall = self._identify_oncall(incident)
            if "slack" in configured_actions:
                result = self.slack.post_low_confidence_alert(incident, current_oncall)
                if result.get("posted"):
                    incident.slack_message_ts = result.get("ts")
                    self.timeline.append(incident.id, "slack_low_confidence_sent", "Slack low-confidence alert sent")
                    actions_taken.append("slack_low_confidence_sent")
                elif result.get("failed"):
                    self.timeline.append(incident.id, "slack_failed", result.get("reason", "Slack post failed"))
                else:
                    self.timeline.append(incident.id, "slack_skipped", result.get("reason", "Slack skipped"))
            self.timeline.append(incident.id, "human_review", "Low-confidence incident flagged for human review")
            actions_taken.append("flagged_for_review")

        self.db.commit()
        return actions_taken

    def post_timeline_update(self, incident: Incident, event_type: str, description: str) -> None:
        if incident.jira_ticket_id:
            result = self.jira.add_comment(
                incident.jira_ticket_id,
                f"SentinelAI update:\n{description}\n\nEvent: {event_type}",
            )
            if result.get("commented"):
                self.timeline.append(incident.id, "jira_comment_added", f"Jira updated for {event_type}", result)
        if incident.slack_message_ts:
            self._post_slack_update(incident, description, event_type)

    def finalize_resolution(self, incident: Incident) -> list[str]:
        actions_taken = []
        if incident.jira_ticket_id:
            comment = self.jira.add_comment(
                incident.jira_ticket_id,
                self._post_mortem_comment(incident),
            )
            if comment.get("commented"):
                self.timeline.append(incident.id, "jira_post_mortem_added", "Post-mortem added to Jira", comment)
                actions_taken.append("jira_post_mortem_added")

            transition = self.jira.transition_issue(incident.jira_ticket_id, ["done", "resolved", "closed"])
            if transition.get("transitioned"):
                self.timeline.append(
                    incident.id,
                    "jira_resolved",
                    f"Jira ticket moved to {transition['transition']}",
                    transition,
                )
                actions_taken.append("jira_resolved")

        if incident.slack_message_ts:
            message = (
                f"Incident resolved in {incident.duration_minutes or 0} minute(s). "
                f"Resolution: {incident.resolution_text or 'Resolution text not provided'}. "
                "Post-mortem generated."
            )
            result = self._post_slack_update(incident, message, "resolved")
            if result.get("posted"):
                actions_taken.append("slack_resolution_update")
        self.db.commit()
        return actions_taken

    def _identify_oncall(self, incident: Incident) -> dict | None:
        team = (incident.affected_teams or [None])[0]
        schedule = self.oncall.current_schedule(team=team)
        if not schedule:
            return None
        data = self.oncall.serialize(schedule)
        self.timeline.append(
            incident.id,
            "oncall_identified",
            f"On-call identified: {data['name']} ({data.get('team') or 'unknown team'})",
            data,
        )
        return data

    def _enhance_jira_incident(
        self,
        incident: Incident,
        recommended_actions: list[str],
        current_oncall: dict | None,
        actions_taken: list[str],
    ) -> None:
        assign = self.jira.assign_issue(incident.jira_ticket_id, current_oncall)
        if assign.get("assigned"):
            self.timeline.append(
                incident.id,
                "jira_assigned",
                f"Jira ticket assigned to {current_oncall.get('name') if current_oncall else 'configured default assignee'}",
                assign,
            )
            actions_taken.append("jira_assigned")

        subtasks = self.jira.create_subtasks(incident, self._subtask_actions(recommended_actions))
        created_subtasks = [item for item in subtasks.get("subtasks", []) if item.get("created")]
        if created_subtasks:
            self.timeline.append(
                incident.id,
                "jira_subtasks_created",
                f"Created {len(created_subtasks)} Jira response subtask(s)",
                {"subtasks": created_subtasks},
            )
            actions_taken.append("jira_subtasks_created")

        comment = self.jira.add_comment(incident.jira_ticket_id, self._initial_jira_comment(incident, current_oncall))
        if comment.get("commented"):
            self.timeline.append(incident.id, "jira_comment_added", "Initial incident context added to Jira", comment)

        transition = self.jira.transition_issue(incident.jira_ticket_id, ["in progress", "investigating", "start progress"])
        if transition.get("transitioned"):
            self.timeline.append(
                incident.id,
                "jira_in_progress",
                f"Jira ticket moved to {transition['transition']}",
                transition,
            )

    def _post_slack_update(self, incident: Incident, description: str, event_type: str) -> dict:
        result = self.slack.post_thread_update(
            incident,
            description,
            thread_ts=incident.slack_message_ts,
            event_type=event_type,
        )
        if result.get("posted"):
            self.timeline.append(
                incident.id,
                "slack_thread_updated",
                f"Slack thread updated: {event_type}",
                {"event_type": event_type, "ts": result.get("ts")},
            )
        elif result.get("failed"):
            self.timeline.append(incident.id, "slack_thread_failed", result.get("reason", "Slack thread update failed"))
        return result

    def _subtask_actions(self, recommended_actions: list[str]) -> list[str]:
        defaults = [
            "Verify customer-facing error rate is back below threshold",
            "Confirm checkout success rate recovered",
            "Update the incident runbook with confirmed resolution",
        ]
        actions = [action for action in recommended_actions if action and not action.lower().startswith("sla warning")]
        for action in defaults:
            if action not in actions:
                actions.append(action)
        return actions[:6]

    def _slack_actions(self, incident: Incident, recommended_actions: list[str]) -> list[str]:
        summary = self._communication_summary(incident)
        return [summary["engineer_summary"], summary["manager_summary"], *recommended_actions]

    def _communication_summary(self, incident: Incident) -> dict:
        return {
            "engineer_summary": (
                f"Engineer summary: {incident.hypothesis or 'Root cause is still being investigated'} "
                f"Confidence {incident.confidence}%."
            ),
            "manager_summary": (
                f"Manager summary: {incident.service} is in {incident.severity or 'incident'} state. "
                "Response actions are being coordinated."
            ),
        }

    def _initial_jira_comment(self, incident: Incident, current_oncall: dict | None) -> str:
        oncall = current_oncall.get("name") if current_oncall else "No on-call engineer matched"
        actions = "\n".join(f"- {action}" for action in (incident.recommended_actions or [])) or "- No recommended actions captured"
        return (
            "SentinelAI update:\n"
            f"Owner: {oncall}\n"
            f"Confidence: {incident.confidence}%\n"
            f"Hypothesis: {incident.hypothesis or 'No hypothesis captured'}\n\n"
            f"Recommended actions:\n{actions}"
        )

    def _post_mortem_comment(self, incident: Incident) -> str:
        return (
            "SentinelAI generated post-mortem:\n\n"
            f"{incident.post_mortem or 'Post-mortem was not available.'}"
        )
