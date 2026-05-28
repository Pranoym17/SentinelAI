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
        self.subtask_issue_type = (
            config.get("subtask_issue_type")
            or config.get("JIRA_SUBTASK_ISSUE_TYPE")
            or os.getenv("JIRA_SUBTASK_ISSUE_TYPE", "Sub-task")
        )
        self.default_assignee_account_id = (
            config.get("default_assignee_account_id")
            or config.get("JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID")
            or os.getenv("JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID", "")
        )
        self.component_by_service = config.get("component_by_service") or {}
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

    def assign_issue(self, issue_key: str, oncall: dict | None = None) -> dict:
        if not self.configured:
            return {"assigned": False, "reason": "Jira is not configured"}
        account_id = self._account_id_for_oncall(oncall)
        if not account_id:
            return {"assigned": False, "reason": "No Jira assignee account ID found"}
        try:
            response = requests.put(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/assignee",
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json={"accountId": account_id},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"assigned": False, "failed": True, "reason": self._failure_reason(exc)}
        return {"assigned": True, "account_id": account_id, "assignee": (oncall or {}).get("name")}

    def create_subtasks(self, incident: Incident, actions: list[str]) -> dict:
        if not self.configured:
            return {"created": False, "reason": "Jira is not configured", "subtasks": []}
        if not incident.jira_ticket_id or not actions:
            return {"created": False, "reason": "No Jira parent or actions available", "subtasks": []}

        subtasks = []
        for index, action in enumerate(actions[:6], start=1):
            payload = {
                "fields": {
                    "project": {"key": self.project_key},
                    "parent": {"key": incident.jira_ticket_id},
                    "summary": self._subtask_summary(action, index),
                    "issuetype": {"name": self.subtask_issue_type},
                    "description": self._adf_doc(
                        f"Generated from SentinelAI incident {incident.jira_ticket_id}.\n\n"
                        f"Reason: {incident.hypothesis or 'No hypothesis captured'}\n"
                        f"Confidence: {incident.confidence}%\n"
                        f"Action: {action}"
                    ),
                    "labels": ["sentinel-ai", self._label(incident.service), "incident-action"],
                }
            }
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
                subtasks.append({"created": False, "summary": payload["fields"]["summary"], "reason": self._failure_reason(exc)})
                continue
            data = response.json()
            subtasks.append(
                {
                    "created": True,
                    "ticket_id": data["key"],
                    "summary": payload["fields"]["summary"],
                    "url": f"{self.base_url}/browse/{data['key']}",
                }
            )
        return {"created": any(item.get("created") for item in subtasks), "subtasks": subtasks}

    def add_comment(self, issue_key: str, message: str) -> dict:
        if not self.configured:
            return {"commented": False, "reason": "Jira is not configured"}
        if not issue_key:
            return {"commented": False, "reason": "No Jira issue key available"}
        try:
            response = requests.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json={"body": self._adf_doc(message)},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"commented": False, "failed": True, "reason": self._failure_reason(exc)}
        data = response.json() if response.content else {}
        return {"commented": True, "comment_id": data.get("id")}

    def transition_issue(self, issue_key: str, target_names: list[str]) -> dict:
        if not self.configured:
            return {"transitioned": False, "reason": "Jira is not configured"}
        if not issue_key:
            return {"transitioned": False, "reason": "No Jira issue key available"}
        try:
            transitions_response = requests.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json"},
                timeout=15,
            )
            transitions_response.raise_for_status()
            transitions = transitions_response.json().get("transitions", [])
            transition = self._match_transition(transitions, target_names)
            if not transition:
                return {"transitioned": False, "reason": f"No matching Jira transition for {', '.join(target_names)}"}
            response = requests.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json={"transition": {"id": transition["id"]}},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"transitioned": False, "failed": True, "reason": self._failure_reason(exc)}
        return {"transitioned": True, "transition": transition.get("name")}

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
        component = self._component_for_service(incident.service)
        if component:
            payload["fields"]["components"] = [{"name": component}]
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
        return self._adf_doc(body, heading="SentinelAI Incident Investigation")

    def _adf_doc(self, body: str, heading: str | None = None) -> dict:
        content = []
        if heading:
            content.append(
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": heading}],
                }
            )
        content.append(
            {
                "type": "codeBlock",
                "content": [{"type": "text", "text": body}],
            }
        )
        return {
            "type": "doc",
            "version": 1,
            "content": content,
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

    def _account_id_for_oncall(self, oncall: dict | None) -> str | None:
        if oncall and oncall.get("jira_account_id"):
            return oncall["jira_account_id"]
        email = (oncall or {}).get("email")
        if email:
            account_id = self.lookup_account_id(email)
            if account_id:
                return account_id
        return self.default_assignee_account_id or None

    def lookup_account_id(self, email: str) -> str | None:
        try:
            response = requests.get(
                f"{self.base_url}/rest/api/3/user/search",
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json"},
                params={"query": email, "maxResults": 5},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None
        for user in response.json():
            if user.get("emailAddress") == email or user.get("accountId"):
                return user.get("accountId")
        return None

    def _component_for_service(self, service: str) -> str | None:
        return self.component_by_service.get(service) or os.getenv(f"JIRA_COMPONENT_{service.upper().replace('-', '_')}")

    def _subtask_summary(self, action: str, index: int) -> str:
        clean = " ".join(action.split())
        if len(clean) > 86:
            clean = f"{clean[:83]}..."
        return f"[SentinelAI] {clean}" if clean else f"[SentinelAI] Follow-up action {index}"

    def _match_transition(self, transitions: list[dict], target_names: list[str]) -> dict | None:
        wanted = [name.lower() for name in target_names]
        for transition in transitions:
            name = transition.get("name", "").lower()
            if any(target in name for target in wanted):
                return transition
        return None
