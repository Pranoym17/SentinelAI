from datetime import timedelta

from app.database import SessionLocal
from app.models import Incident
from app.time_utils import utc_now


def save_config(client):
    return client.post(
        "/api/config",
        json={
            "services": ["payments", "auth", "api-gateway"],
            "signals": ["error_spike", "latency_spike"],
            "actions": [],
            "thresholds": {"error_rate": 5, "latency_ms": 2000},
            "slack_channel": "#incidents",
            "jira_project_key": "INC",
        },
    )


def test_blast_radius_endpoint_reports_upstream_and_downstream_services(client):
    assert save_config(client).status_code == 200
    client.post(
        "/api/services",
        json={"name": "payments", "dependencies": ["database", "redis"], "team": "payments-team"},
    )
    client.post("/api/services", json={"name": "checkout", "dependencies": ["payments"]})
    client.post("/api/services", json={"name": "billing-worker", "dependencies": ["payments"]})

    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    blast_radius = client.post(f"/api/incidents/{incident['incident_id']}/blast-radius").json()
    detail = client.get(f"/api/incidents/{incident['incident_id']}").json()

    assert blast_radius["service"] == "payments"
    assert blast_radius["upstream_dependencies"] == ["database", "redis"]
    assert blast_radius["downstream_dependents"] == ["billing-worker", "checkout"]
    assert blast_radius["affected_services"] == ["billing-worker", "checkout", "database", "redis"]
    assert blast_radius["risk_level"] == "high"
    assert "blast_radius_analyzed" in [event["event_type"] for event in detail["timeline"]]


def test_blast_radius_endpoint_handles_missing_service_catalog_entry(client):
    assert save_config(client).status_code == 200
    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    blast_radius = client.post(f"/api/incidents/{incident['incident_id']}/blast-radius").json()

    assert blast_radius["risk_level"] == "unknown"
    assert blast_radius["affected_services"] == []
    assert "unknown" in blast_radius["warning"].lower()


def test_correlated_signal_reuses_primary_incident_and_records_timeline(client):
    assert save_config(client).status_code == 200
    client.post("/api/services", json={"name": "payments", "dependencies": ["database"]})
    client.post("/api/services", json={"name": "auth", "dependencies": ["database"]})

    first = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()
    second = client.post(
        "/api/signal",
        json={"service": "auth", "type": "error_spike", "value": 12.0, "baseline": 0.1},
    ).json()

    assert second["correlated"] is True
    assert second["incident_id"] == first["incident_id"]
    assert second["correlation"]["affected_services"] == ["auth", "payments"]
    assert "database" in second["correlation"]["root_cause"]
    assert "correlation_detected" in [event["event_type"] for event in second["timeline"]]
    assert len(client.get("/api/incidents").json()["active"]) == 1


def test_old_open_incident_does_not_correlate_after_window(client):
    assert save_config(client).status_code == 200
    client.post("/api/services", json={"name": "payments", "dependencies": ["database"]})
    client.post("/api/services", json={"name": "auth", "dependencies": ["database"]})

    first = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()
    with SessionLocal() as db:
        incident = db.get(Incident, first["incident_id"])
        incident.detected_at = utc_now() - timedelta(minutes=6)
        db.commit()

    second = client.post(
        "/api/signal",
        json={"service": "auth", "type": "error_spike", "value": 12.0, "baseline": 0.1},
    ).json()

    assert second.get("correlated") is not True
    assert second["incident_id"] != first["incident_id"]
    assert len(client.get("/api/incidents").json()["active"]) == 2
