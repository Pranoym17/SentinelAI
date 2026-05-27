import os

import requests

from app.models import Incident


class JiraService:
    def __init__(self, config: dict | None = None):
        config = config or {}
        self.base_url = (config.get("base_url") or config.get("JIRA_BASE_URL") or os.getenv("JIRA_BASE_URL", "")).rstrip("/")
        self.email = config.get("email") or config.get("JIRA_EMAIL") or os.getenv("JIRA_EMAIL", "")
        self.api_token = config.get("api_token") or config.get("JIRA_API_TOKEN") or os.getenv("JIRA_API_TOKEN", "")
        self.project_key = config.get("project_key") or config.get("JIRA_PROJECT_KEY") or os.getenv("JIRA_PROJECT_KEY", "INC")
        self.issue_type = config.get("issue_type") or config.get("JIRA_ISSUE_TYPE") or os.getenv("JIRA_ISSUE_TYPE", "Bug")
        self.priority_overrides = config.get("priority_overrides") or {}

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.email and self.api_token and self.project_key)

    def create_ticket(self, incident: Incident) -> dict:
        if not self.configured:
            return {"created": False, "reason": "Jira is not configured"}

        payload = self.build_payload(incident)
        try:
            response = requests.post(
                f"{self.base_url}/rest/api/3/issue",
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"created": False, "failed": True, "reason": self._failure_reason(exc)}

        data = response.json()
        ticket_id = data["key"]
        return {
            "created": True,
            "ticket_id": ticket_id,
            "url": f"{self.base_url}/browse/{ticket_id}",
        }

    def build_payload(self, incident: Incident) -> dict:
        labels = [
            self._label(incident.service),
            self._label(incident.severity or "severity-unknown"),
            "sentinel-ai",
        ]
        priority = self._priority_for_severity(incident.severity)
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"{incident.severity}: {incident.service} {incident.signal_type}",
                "issuetype": {"name": self.issue_type},
                "description": self._description(incident),
                "labels": labels,
            }
        }
        if priority:
            payload["fields"]["priority"] = {"name": priority}
        return payload

    def _description(self, incident: Incident) -> dict:
        reasoning_text = "\n".join(
            f"[{step.get('step', 'STEP')}] {step.get('detail', '')}"
            for step in (incident.reasoning_chain or [])
        )
        affected_teams = ", ".join(incident.affected_teams or []) or "not assigned"
        body = (
            f"Hypothesis: {incident.hypothesis or 'No hypothesis provided'}\n\n"
            f"Confidence: {incident.confidence}%\n"
            f"Service: {incident.service}\n"
            f"Signal: {incident.signal_type} = {incident.signal_value}\n"
            f"Affected teams: {affected_teams}\n\n"
            f"Reasoning chain:\n{reasoning_text or 'No reasoning chain captured.'}"
        )
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "SentinelAI Incident Investigation"}],
                },
                {
                    "type": "codeBlock",
                    "content": [{"type": "text", "text": body}],
                },
            ],
        }

    def _priority_for_severity(self, severity: str | None) -> str | None:
        defaults = {
            "SEV-1": "Highest",
            "SEV-2": "High",
            "SEV-3": "Medium",
        }
        env_key = f"JIRA_PRIORITY_{(severity or '').replace('-', '_')}"
        return self.priority_overrides.get(severity or "") or os.getenv(env_key, defaults.get(severity or ""))

    def _failure_reason(self, exc: requests.RequestException) -> str:
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            return f"Jira ticket creation failed ({response.status_code}): {detail}"
        return f"Jira ticket creation failed: {exc}"

    def _label(self, value: str) -> str:
        return value.lower().replace(" ", "-").replace("_", "-")
