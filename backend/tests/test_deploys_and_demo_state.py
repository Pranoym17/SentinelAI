from datetime import datetime, timezone

from tests.test_api_flow import save_config, seed_context


def test_create_and_list_deploys(client):
    now = datetime.now(timezone.utc).isoformat()

    created = client.post(
        "/api/deploys",
        json={
            "service": "payments-api",
            "version": "v9.9.9",
            "author": "tester",
            "deployed_at": now,
            "changes_summary": "Test deploy",
        },
    ).json()

    assert created["service"] == "payments-api"
    assert created["version"] == "v9.9.9"
    assert created["suspected_cause"] is False

    deploys = client.get("/api/deploys").json()["deploys"]
    assert deploys[0]["version"] == "v9.9.9"


def test_deploy_correlation_marks_suspected_cause(client):
    save_config(client)
    seed_context(client)
    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    deploys = client.get("/api/deploys").json()["deploys"]
    correlated = [deploy for deploy in deploys if deploy["suspected_cause"]]

    assert correlated
    assert correlated[0]["correlated_incident_id"] == incident["incident_id"]


def test_demo_state_combines_dashboard_data(client):
    save_config(client)
    seed_context(client)
    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    state = client.get("/api/demo/state").json()

    assert state["worker"]["running"] in [True, False]
    assert state["metrics"]
    assert state["active_incident"]["incident_id"] == incident["incident_id"]
    assert state["recent_deploys"]
    assert "jira" in state["integrations"]
    assert state["timeline"]


def test_demo_state_without_incident(client):
    client.post("/api/demo/full-seed")

    state = client.get("/api/demo/state").json()

    assert state["active_incident"] is None
    assert state["metrics"]
    assert state["recent_deploys"]
