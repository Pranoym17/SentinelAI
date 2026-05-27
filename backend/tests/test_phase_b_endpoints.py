from datetime import timedelta

from app.time_utils import utc_now


def test_services_endpoint_create_and_list(client):
    created = client.post(
        "/api/services",
        json={
            "name": "payments",
            "display_name": "Payments API",
            "description": "Handles checkout",
            "dependencies": ["database", "redis"],
            "team": "payments-team",
            "repo_url": "github.com/example/payments-api",
            "sla_target": 99.95,
        },
    ).json()

    assert created["status"] == "created"
    services = client.get("/api/services").json()["services"]
    assert services[0]["name"] == "payments"
    assert services[0]["dependencies"] == ["database", "redis"]


def test_sla_endpoint_reports_service_budget(client):
    client.post("/api/services", json={"name": "payments", "sla_target": 99.9})

    sla = client.get("/api/sla").json()["sla"]

    assert len(sla) == 1
    assert sla[0]["service"] == "payments"
    assert sla[0]["status"] == "healthy"
    assert sla[0]["remaining_budget_minutes"] > 0


def test_oncall_endpoint_create_and_current(client):
    now = utc_now()
    created = client.post(
        "/api/oncall",
        json={
            "engineer_name": "Sarah",
            "engineer_email": "sarah@example.com",
            "slack_handle": "@sarah",
            "team": "payments-team",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=8)).isoformat(),
            "is_active": True,
        },
    ).json()

    assert created["status"] == "created"
    current = client.get("/api/oncall/current").json()["oncall"]
    assert current["name"] == "Sarah"
    assert current["slack_handle"] == "@sarah"


def test_runbooks_endpoint_create_and_list(client):
    created = client.post(
        "/api/runbooks",
        json={
            "service": "payments",
            "signal_type": "error_spike",
            "title": "Payments rollback",
            "steps": ["Check deploy", "Rollback", "Verify metrics"],
        },
    ).json()

    assert created["status"] == "created"
    runbooks = client.get("/api/runbooks").json()["runbooks"]
    assert runbooks[0]["title"] == "Payments rollback"
    assert runbooks[0]["success_rate"] == 0


def test_analytics_endpoint_returns_summary(client):
    data = client.get("/api/analytics").json()

    assert data["mttd_seconds"] == 0
    assert data["mttr_minutes"] == 0
    assert data["total_incidents"] == 0
    assert data["sla_compliance"] == 100.0


def test_integration_config_endpoint_save_and_list(client):
    saved = client.post(
        "/api/integrations",
        json={"type": "github", "enabled": True, "config": {"repo": "example/payments-api"}},
    ).json()

    assert saved["status"] == "saved"
    integrations = client.get("/api/integrations").json()["integrations"]
    assert integrations[0]["type"] == "github"
    assert integrations[0]["enabled"] is True


def test_integration_config_endpoint_updates_existing(client):
    client.post("/api/integrations", json={"type": "github", "enabled": True, "config": {"repo": "a"}})
    client.post("/api/integrations", json={"type": "github", "enabled": False, "config": {"repo": "b"}})

    integrations = client.get("/api/integrations").json()["integrations"]

    assert len(integrations) == 1
    assert integrations[0]["enabled"] is False
