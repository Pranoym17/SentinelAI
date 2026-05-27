from unittest.mock import Mock, patch

import requests

from app.models import Incident
from app.services.jira_service import JiraService


def make_incident():
    return Incident(
        service="payments",
        severity="SEV-1",
        signal_type="error_spike",
        signal_value=18.0,
        hypothesis="Deploy regression in payments-api",
        confidence=95,
        reasoning_chain=[
            {"step": "SIGNAL DETECTED", "detail": "Error rate reached 18%"},
            {"step": "CHECKING DEPLOYS", "detail": "payments-api v2.4.1 deployed 14 minutes ago"},
        ],
        affected_teams=["payments", "platform"],
    )


def test_missing_jira_config_skips(monkeypatch):
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

    result = JiraService().create_ticket(make_incident())

    assert result == {"created": False, "reason": "Jira is not configured"}


def test_jira_payload_contains_incident_context(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "INC")
    monkeypatch.setenv("JIRA_ISSUE_TYPE", "Task")

    payload = JiraService().build_payload(make_incident())

    fields = payload["fields"]
    assert fields["project"]["key"] == "INC"
    assert fields["issuetype"]["name"] == "Task"
    assert fields["priority"]["name"] == "Highest"
    assert "payments" in fields["labels"]
    assert "sev-1" in fields["labels"]
    assert "Deploy regression in payments-api" in str(fields["description"])
    assert "payments-api v2.4.1" in str(fields["description"])


def test_jira_success_returns_ticket(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "INC")

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"key": "INC-123"}

    with patch("app.services.jira_service.requests.post", return_value=response) as post:
        result = JiraService().create_ticket(make_incident())

    assert result["created"] is True
    assert result["ticket_id"] == "INC-123"
    assert result["url"] == "https://example.atlassian.net/browse/INC-123"
    assert post.call_args.kwargs["json"]["fields"]["project"]["key"] == "INC"


def test_jira_failure_returns_structured_reason(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "INC")

    response = Mock()
    response.status_code = 400
    response.json.return_value = {"errors": {"project": "No permission"}}
    error = requests.HTTPError("bad request", response=response)

    with patch("app.services.jira_service.requests.post") as post:
        post.return_value.raise_for_status.side_effect = error
        result = JiraService().create_ticket(make_incident())

    assert result["created"] is False
    assert result["failed"] is True
    assert "No permission" in result["reason"]
