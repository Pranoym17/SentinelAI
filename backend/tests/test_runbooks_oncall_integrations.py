from datetime import timedelta
from unittest.mock import Mock, patch

from app.database import SessionLocal
from app.models import Config, Incident, RunbookLibrary, TimelineEvent
from app.services.response_agent import ResponseAgent
from app.time_utils import utc_now


def save_config(client):
    return client.post(
        "/api/config",
        json={
            "services": ["payments"],
            "signals": ["error_spike"],
            "actions": [],
            "thresholds": {"error_rate": 5, "latency_ms": 2000},
            "slack_channel": "#incidents",
            "jira_project_key": "INC",
        },
    )


def test_matching_runbook_is_used_during_investigation_and_marked_successful_on_resolution(client):
    assert save_config(client).status_code == 200
    runbook = client.post(
        "/api/runbooks",
        json={
            "service": "payments",
            "signal_type": "error_spike",
            "title": "Payments rollback",
            "steps": ["Check deploy", "Rollback payments-api", "Verify checkout"],
        },
    ).json()["runbook"]

    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    assert "Follow runbook: Payments rollback" in incident["recommended_actions"]
    assert "CHECKING RUNBOOKS" in [step["step"] for step in incident["reasoning_chain"]]

    with SessionLocal() as db:
        db_runbook = db.get(RunbookLibrary, runbook["id"])
        assert db_runbook.times_used == 1
        assert db_runbook.last_used_at is not None

    client.post(
        f"/api/incidents/{incident['incident_id']}/resolve",
        json={"resolution_text": "Used runbook and rolled back payments-api"},
    )

    with SessionLocal() as db:
        db_runbook = db.get(RunbookLibrary, runbook["id"])
        events = db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident["incident_id"]).all()

    assert db_runbook.times_successful == 1
    assert "runbook_success_recorded" in [event.event_type for event in events]


def test_medium_confidence_response_identifies_oncall_and_sends_to_slack():
    with SessionLocal() as db:
        oncall = {
            "engineer_name": "Sarah",
            "engineer_email": "sarah@example.com",
            "slack_handle": "@sarah",
            "team": "payments-team",
            "start_time": utc_now() - timedelta(hours=1),
            "end_time": utc_now() + timedelta(hours=1),
            "is_active": True,
        }
        client_payload = {**oncall, "start_time": oncall["start_time"].isoformat(), "end_time": oncall["end_time"].isoformat()}
        from app.schemas import OnCallScheduleIn
        from app.services.oncall_service import OnCallService

        OnCallService(db).create(OnCallScheduleIn(**client_payload))
        incident = Incident(
            service="payments",
            signal_type="error_spike",
            signal_value=6.0,
            severity="SEV-2",
            hypothesis="Needs human review",
            confidence=65,
            affected_teams=["payments-team"],
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        agent = ResponseAgent(db, Config(actions=["slack"]))
        agent.slack.post_review_request = Mock(return_value={"posted": True})

        actions = agent.route(incident, ["Review manually"])
        events = db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident.id).all()

    assert actions == ["slack_review_requested"]
    assert "oncall_identified" in [event.event_type for event in events]
    agent.slack.post_review_request.assert_called_once()
    assert agent.slack.post_review_request.call_args.args[2]["slack_handle"] == "@sarah"


def test_integration_config_can_supply_slack_webhook(client):
    client.post(
        "/api/integrations",
        json={
            "type": "slack",
            "enabled": True,
            "config": {"webhook_url": "https://hooks.slack.test/from-db", "channel": "#db-incidents"},
        },
    )
    response = Mock()
    response.headers = {"content-type": "text/plain"}
    response.content = b"ok"
    response.raise_for_status = Mock()

    with patch("app.services.slack_service.requests.post", return_value=response) as post:
        result = client.post("/api/integrations/slack/test").json()

    assert result["posted"] is True
    assert result["channel"] == "#db-incidents"
    assert post.call_args.kwargs["json"]["channel"] == "#db-incidents"


def test_integration_config_can_supply_jira_credentials(client):
    client.post(
        "/api/integrations",
        json={
            "type": "jira",
            "enabled": True,
            "config": {
                "base_url": "https://jira-db.example.atlassian.net",
                "email": "db@example.com",
                "api_token": "db-token",
                "project_key": "SCRUM",
                "issue_type": "Bug",
            },
        },
    )
    response = Mock()
    response.json.return_value = {"key": "SCRUM-99"}
    response.raise_for_status = Mock()

    with patch("app.services.jira_service.requests.post", return_value=response) as post:
        result = client.post("/api/integrations/jira/test").json()

    assert result["created"] is True
    assert result["ticket_id"] == "SCRUM-99"
    assert post.call_args.args[0] == "https://jira-db.example.atlassian.net/rest/api/3/issue"
    assert post.call_args.kwargs["auth"] == ("db@example.com", "db-token")
    assert post.call_args.kwargs["json"]["fields"]["project"]["key"] == "SCRUM"
