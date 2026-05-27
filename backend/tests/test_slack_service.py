import os
from unittest.mock import Mock, patch

import requests

from app.models import Incident
from app.services.slack_service import SlackService


def make_incident(confidence=95):
    return Incident(
        id=7,
        service="payments",
        severity="SEV-1",
        signal_type="error_spike",
        signal_value=18.0,
        hypothesis="Deploy regression in payments-api",
        confidence=confidence,
        affected_teams=["payments", "platform"],
        jira_ticket_id="INC-123",
        jira_ticket_url="https://example.atlassian.net/browse/INC-123",
    )


def test_missing_webhook_skips(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    result = SlackService().post_incident_alert(make_incident())

    assert result == {"posted": False, "reason": "Slack webhook is not configured"}


def test_incident_alert_payload_contains_core_context(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/example")
    response = Mock()
    response.content = b""
    response.raise_for_status.return_value = None

    with patch("app.services.slack_service.requests.post", return_value=response) as post:
        result = SlackService().post_incident_alert(
            make_incident(),
            ["Rollback payments-api", "Check exception logs"],
        )

    assert result["posted"] is True
    payload = post.call_args.kwargs["json"]
    assert payload["channel"] == os.getenv("SLACK_CHANNEL", "#incidents")
    block_text = str(payload["blocks"])
    assert "payments" in block_text
    assert "95%" in block_text
    assert "Deploy regression in payments-api" in block_text
    assert "Rollback payments-api" in block_text
    assert "INC-123" in block_text


def test_webhook_failure_returns_structured_failure(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/example")

    with patch(
        "app.services.slack_service.requests.post",
        side_effect=requests.RequestException("network down"),
    ):
        result = SlackService().post_review_request(make_incident(confidence=65))

    assert result["posted"] is False
    assert result["failed"] is True
    assert "network down" in result["reason"]
