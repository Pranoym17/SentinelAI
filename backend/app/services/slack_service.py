import os

import requests

from app.models import Incident


SEVERITY_EMOJI = {
    "SEV-1": ":red_circle:",
    "SEV-2": ":large_yellow_circle:",
    "SEV-3": ":large_green_circle:",
}


class SlackService:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.channel = os.getenv("SLACK_CHANNEL", "#incidents")

    @property
    def configured(self) -> bool:
        return bool(self.webhook_url)

    def post_incident_alert(self, incident: Incident, recommended_actions: list[str] | None = None) -> dict:
        if not self.configured:
            return {"posted": False, "reason": "Slack webhook is not configured"}

        payload = self._build_payload(
            incident=incident,
            title="Incident response started",
            mode="high_confidence",
            recommended_actions=recommended_actions or [],
            footer="High confidence: SentinelAI has started coordinated response actions.",
        )
        return self._post(payload)

    def post_review_request(self, incident: Incident, recommended_actions: list[str] | None = None) -> dict:
        if not self.configured:
            return {"posted": False, "reason": "Slack webhook is not configured"}

        payload = self._build_payload(
            incident=incident,
            title="Human review requested",
            mode="medium_confidence",
            recommended_actions=recommended_actions or [],
            footer="Medium confidence: SentinelAI is waiting for human confirmation.",
        )
        return self._post(payload)

    def post_low_confidence_alert(self, incident: Incident) -> dict:
        if not self.configured:
            return {"posted": False, "reason": "Slack webhook is not configured"}

        payload = self._build_payload(
            incident=incident,
            title="Low-confidence alert",
            mode="low_confidence",
            recommended_actions=["Review telemetry manually", "Check adjacent service health"],
            footer="Low confidence: SentinelAI did not take automated action.",
        )
        return self._post(payload)

    def _build_payload(
        self,
        incident: Incident,
        title: str,
        mode: str,
        recommended_actions: list[str],
        footer: str,
    ) -> dict:
        emoji = SEVERITY_EMOJI.get(incident.severity or "", ":white_circle:")
        teams = ", ".join(incident.affected_teams or []) or "not assigned"
        actions_text = "\n".join(f"- {action}" for action in recommended_actions) or "- No actions provided"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {incident.severity}: {incident.service} - {title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\n{incident.service}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{incident.severity}"},
                    {"type": "mrkdwn", "text": f"*Confidence:*\n{incident.confidence}%"},
                    {"type": "mrkdwn", "text": f"*Affected teams:*\n{teams}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Hypothesis:*\n{incident.hypothesis}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Recommended actions:*\n{actions_text}"},
            },
        ]

        if incident.jira_ticket_url:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Jira ticket:* <{incident.jira_ticket_url}|{incident.jira_ticket_id or 'View ticket'}>",
                    },
                }
            )

        blocks.extend(
            [
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": footer}],
                },
            ]
        )

        return {
            "channel": self.channel,
            "text": f"{incident.severity}: {incident.service} incident - {mode}",
            "blocks": blocks,
        }

    def _post(self, payload: dict) -> dict:
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"posted": False, "failed": True, "reason": f"Slack post failed: {exc}"}

        data = {}
        content_type = response.headers.get("content-type", "")
        if response.content and "application/json" in content_type:
            data = response.json()
        return {"posted": True, "ts": data.get("ts"), "channel": self.channel, "payload": payload}
