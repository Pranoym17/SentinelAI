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
                elif result.get("failed"):
                    self.timeline.append(incident.id, "jira_failed", result.get("reason", "Jira failed"))
                else:
                    self.timeline.append(incident.id, "jira_skipped", result.get("reason", "Jira skipped"))

            if "slack" in configured_actions:
                result = self.slack.post_incident_alert(incident, recommended_actions)
                if result.get("posted"):
                    incident.slack_message_ts = result.get("ts")
                    self.timeline.append(incident.id, "slack_sent", "Slack incident alert sent")
                    actions_taken.append("slack_sent")
                elif result.get("failed"):
                    self.timeline.append(incident.id, "slack_failed", result.get("reason", "Slack post failed"))
                else:
                    self.timeline.append(incident.id, "slack_skipped", result.get("reason", "Slack skipped"))

        elif incident.confidence >= 50:
            if "slack" in configured_actions:
                current_oncall = self._identify_oncall(incident)
                result = self.slack.post_review_request(incident, recommended_actions, current_oncall)
                if result.get("posted"):
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
