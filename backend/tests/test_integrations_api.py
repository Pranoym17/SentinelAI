from unittest.mock import patch


def test_integration_status_reports_config(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "jira-token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "SCRUM")
    monkeypatch.setenv("JIRA_ISSUE_TYPE", "Bug")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/example")
    monkeypatch.setenv("SLACK_CHANNEL", "#incidents")

    data = client.get("/api/integrations/status").json()

    assert data["openai"]["configured"] is True
    assert data["openai"]["model"] == "gpt-test"
    assert data["jira"]["configured"] is True
    assert data["jira"]["project_key"] == "SCRUM"
    assert data["slack"]["configured"] is True
    assert data["slack"]["channel"] == "#incidents"


def test_slack_test_endpoint_uses_service(client):
    with patch("app.services.integration_service.SlackService") as slack_cls:
        slack_cls.return_value.post_review_request.return_value = {"posted": True, "channel": "#incidents"}

        result = client.post("/api/integrations/slack/test").json()

    assert result == {"posted": True, "channel": "#incidents"}


def test_jira_test_endpoint_uses_service(client):
    with patch("app.services.integration_service.JiraService") as jira_cls:
        jira_cls.return_value.create_ticket.return_value = {
            "created": True,
            "ticket_id": "SCRUM-10",
            "url": "https://example/browse/SCRUM-10",
        }

        result = client.post("/api/integrations/jira/test").json()

    assert result["created"] is True
    assert result["ticket_id"] == "SCRUM-10"
