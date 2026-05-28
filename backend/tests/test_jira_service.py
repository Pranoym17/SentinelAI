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


def test_jira_assigns_oncall_by_email(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "INC")

    search_response = Mock()
    search_response.raise_for_status.return_value = None
    search_response.json.return_value = [{"accountId": "abc-123", "emailAddress": "sarah@example.com"}]
    assign_response = Mock()
    assign_response.raise_for_status.return_value = None

    with patch("app.services.jira_service.requests.get", return_value=search_response) as get:
        with patch("app.services.jira_service.requests.put", return_value=assign_response) as put:
            result = JiraService().assign_issue("INC-123", {"email": "sarah@example.com", "name": "Sarah"})

    assert result["assigned"] is True
    assert result["account_id"] == "abc-123"
    assert get.call_args.kwargs["params"]["query"] == "sarah@example.com"
    assert put.call_args.kwargs["json"] == {"accountId": "abc-123"}


def test_jira_creates_subtasks_from_actions(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "INC")

    incident = make_incident()
    incident.jira_ticket_id = "INC-123"

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = [{"key": "INC-124"}, {"key": "INC-125"}]

    with patch("app.services.jira_service.requests.post", return_value=response) as post:
        result = JiraService().create_subtasks(incident, ["Rollback payments-api", "Verify checkout"])

    assert result["created"] is True
    assert [item["ticket_id"] for item in result["subtasks"]] == ["INC-124", "INC-125"]
    payload = post.call_args_list[0].kwargs["json"]
    assert payload["fields"]["parent"]["key"] == "INC-123"
    assert payload["fields"]["issuetype"]["name"] == "Sub-task"


def test_jira_add_comment_and_transition(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "INC")

    comment_response = Mock(content=b"{}")
    comment_response.raise_for_status.return_value = None
    comment_response.json.return_value = {"id": "1001"}
    transitions_response = Mock()
    transitions_response.raise_for_status.return_value = None
    transitions_response.json.return_value = {"transitions": [{"id": "31", "name": "Done"}]}
    transition_response = Mock()
    transition_response.raise_for_status.return_value = None

    with patch("app.services.jira_service.requests.post", side_effect=[comment_response, transition_response]) as post:
        with patch("app.services.jira_service.requests.get", return_value=transitions_response):
            service = JiraService()
            comment = service.add_comment("INC-123", "Incident resolved")
            transition = service.transition_issue("INC-123", ["done"])

    assert comment == {"commented": True, "comment_id": "1001"}
    assert transition == {"transitioned": True, "transition": "Done"}
    assert post.call_args_list[1].kwargs["json"] == {"transition": {"id": "31"}}
