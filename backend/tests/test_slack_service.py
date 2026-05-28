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


def test_slack_bot_token_posts_thread_update(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    monkeypatch.setenv("SLACK_CHANNEL", "C123")

    response = Mock()
    response.content = b'{"ok":true,"ts":"456.789"}'
    response.headers = {"content-type": "application/json"}
    response.raise_for_status.return_value = None
    response.json.return_value = {"ok": True, "ts": "456.789"}

    with patch("app.services.slack_service.requests.post", return_value=response) as post:
        result = SlackService().post_thread_update(
            make_incident(),
            "Rollback started",
            thread_ts="123.456",
            event_type="rollback_started",
        )

    assert result["posted"] is True
    assert result["ts"] == "456.789"
    assert post.call_args.args[0] == "https://slack.com/api/chat.postMessage"
    payload = post.call_args.kwargs["json"]
    assert payload["thread_ts"] == "123.456"
    assert payload["channel"] == "C123"


def test_slack_payload_includes_link_buttons(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/example")
    response = Mock()
    response.content = b""
    response.headers = {}
    response.raise_for_status.return_value = None

    with patch("app.services.slack_service.requests.post", return_value=response) as post:
        SlackService({"dashboard_url": "https://sentinel.example/dashboard"}).post_incident_alert(make_incident())

    blocks = post.call_args.kwargs["json"]["blocks"]
    actions = [block for block in blocks if block["type"] == "actions"]
    assert actions
    assert actions[0]["elements"][0]["url"] == "https://example.atlassian.net/browse/INC-123"
    assert actions[0]["elements"][1]["url"] == "https://sentinel.example/dashboard"
