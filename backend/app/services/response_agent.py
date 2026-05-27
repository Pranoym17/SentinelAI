from sqlalchemy.orm import Session

from app.models import Config, Incident
from app.services.jira_service import JiraService
from app.services.slack_service import SlackService
from app.services.timeline_service import TimelineService


class ResponseAgent:
    def __init__(self, db: Session, config: Config):
        self.db = db
        self.config = config
        self.jira = JiraService()
        self.slack = SlackService()
        self.timeline = TimelineService(db)

    def route(self, incident: Incident) -> list[str]:
        actions_taken = []
        configured_actions = self.config.actions or []

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
                else:
                    self.timeline.append(incident.id, "jira_skipped", result.get("reason", "Jira skipped"))

            if "slack" in configured_actions:
                result = self.slack.post_incident_alert(incident)
                if result.get("posted"):
                    incident.slack_message_ts = result.get("ts")
                    self.timeline.append(incident.id, "slack_sent", "Slack incident alert sent")
                    actions_taken.append("slack_sent")
                else:
                    self.timeline.append(incident.id, "slack_skipped", result.get("reason", "Slack skipped"))

        elif incident.confidence >= 50:
            if "slack" in configured_actions:
                result = self.slack.post_review_request(incident)
                if result.get("posted"):
                    self.timeline.append(incident.id, "slack_review_requested", "Slack review request sent")
                    actions_taken.append("slack_review_requested")
                else:
                    self.timeline.append(incident.id, "slack_skipped", result.get("reason", "Slack skipped"))
        else:
            self.timeline.append(incident.id, "human_review", "Low-confidence incident flagged for human review")
            actions_taken.append("flagged_for_review")

        self.db.commit()
        return actions_taken
