import os

import requests

from app.models import Incident


class SlackService:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.channel = os.getenv("SLACK_CHANNEL", "#incidents")

    @property
    def configured(self) -> bool:
        return bool(self.webhook_url)

    def post_incident_alert(self, incident: Incident) -> dict:
        if not self.configured:
            return {"posted": False, "reason": "Slack webhook is not configured"}

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{incident.severity}: {incident.service} incident",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Hypothesis:* {incident.hypothesis}\n*Confidence:* {incident.confidence}%",
                },
            },
        ]
        response = requests.post(self.webhook_url, json={"blocks": blocks}, timeout=15)
        response.raise_for_status()
        return {"posted": True, "ts": None, "channel": self.channel}

    def post_review_request(self, incident: Incident) -> dict:
        if not self.configured:
            return {"posted": False, "reason": "Slack webhook is not configured"}

        response = requests.post(
            self.webhook_url,
            json={
                "text": (
                    f"Human review requested for {incident.service}. "
                    f"Confidence: {incident.confidence}%. {incident.hypothesis}"
                )
            },
            timeout=15,
        )
        response.raise_for_status()
        return {"posted": True, "ts": None, "channel": self.channel}
