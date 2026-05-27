from datetime import timedelta

from app.database import SessionLocal
from app.models import Incident, SLARecord, TimelineEvent
from app.time_utils import utc_now


def save_config(client):
    return client.post(
        "/api/config",
        json={
            "services": ["payments", "auth", "api-gateway"],
            "signals": ["error_spike", "latency_spike"],
            "actions": ["jira", "slack"],
            "thresholds": {"error_rate": 5, "latency_ms": 2000},
            "slack_channel": "#incidents",
            "jira_project_key": "INC",
        },
    )


def seed_context(client):
    client.post("/api/seed/demo")
    now = utc_now().isoformat()
    client.post(
        "/api/seed/deploys",
        json={
            "deploys": [
                {
                    "service": "payments-api",
                    "version": "v2.4.1",
                    "author": "devops",
                    "deployed_at": now,
                    "changes_summary": "Updated payments SDK",
                }
            ]
        },
    )
    client.post(
        "/api/seed/memory",
        json={
            "incidents": [
                {
                    "service": "payments",
                    "signal_type": "error_spike",
                    "root_cause": "Previous payments deploy regression",
                    "resolution": "Rollback",
                    "duration_minutes": 34,
                    "occurred_at": now,
                }
            ]
        },
    )


def test_resolving_incident_records_sla_downtime(client):
    assert save_config(client).status_code == 200
    client.post("/api/services", json={"name": "payments", "sla_target": 99.9})
    seed_context(client)
    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    with SessionLocal() as db:
        db_incident = db.get(Incident, incident["incident_id"])
        db_incident.detected_at = utc_now() - timedelta(minutes=17)
        db.commit()

    resolved = client.post(
        f"/api/incidents/{incident['incident_id']}/resolve",
        json={"resolution_text": "Rolled back payments-api"},
    ).json()

    assert resolved["status"] == "resolved"
    assert resolved["duration_minutes"] == 17

    with SessionLocal() as db:
        record = db.query(SLARecord).filter(SLARecord.service == "payments").one()
        events = (
            db.query(TimelineEvent)
            .filter(TimelineEvent.incident_id == incident["incident_id"])
            .order_by(TimelineEvent.occurred_at)
            .all()
        )

    assert record.total_downtime_minutes == 17
    assert record.incident_count == 1
    assert record.actual_uptime < 100
    assert "sla_downtime_recorded" in [event.event_type for event in events]


def test_sla_prediction_escalates_incident_before_response_routing(client):
    assert save_config(client).status_code == 200
    client.post("/api/services", json={"name": "payments", "sla_target": 99.99999})

    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "latency_spike", "value": 3500.0, "baseline": 150.0},
    ).json()

    event_types = [event["event_type"] for event in incident["timeline"]]

    assert incident["severity"] == "SEV-1"
    assert incident["sla_prediction"]["will_breach"] is True
    assert incident["sla_prediction"]["breach_in_minutes"] < 30
    assert "sla_warning" in event_types
    assert "severity_escalated" in event_types
    assert incident["recommended_actions"][0].startswith("SLA warning:")
