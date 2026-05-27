import os

import requests

from app.models import Incident


class JiraService:
    def __init__(self):
        self.base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        self.email = os.getenv("JIRA_EMAIL", "")
        self.api_token = os.getenv("JIRA_API_TOKEN", "")
        self.project_key = os.getenv("JIRA_PROJECT_KEY", "INC")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.email and self.api_token and self.project_key)

    def create_ticket(self, incident: Incident) -> dict:
        if not self.configured:
            return {"created": False, "reason": "Jira is not configured"}

        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"{incident.severity}: {incident.service} {incident.signal_type}",
                "issuetype": {"name": "Bug"},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": incident.hypothesis or ""}],
                        }
                    ],
                },
                "labels": [incident.service, "sentinel-ai"],
            }
        }
        response = requests.post(
            f"{self.base_url}/rest/api/3/issue",
            auth=(self.email, self.api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        ticket_id = data["key"]
        return {
            "created": True,
            "ticket_id": ticket_id,
            "url": f"{self.base_url}/browse/{ticket_id}",
        }
