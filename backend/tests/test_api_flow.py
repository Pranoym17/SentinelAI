from datetime import datetime, timezone


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
    now = datetime.now(timezone.utc).isoformat()
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


def test_config_metrics_and_signal_flow(client):
    assert save_config(client).status_code == 200
    seed_context(client)

    metrics = client.get("/api/metrics").json()["metrics"]
    assert any(item["service"] == "payments" for item in metrics)

    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    assert incident["triggered"] is True
    assert incident["severity"] == "SEV-1"
    assert incident["confidence"] == 95
    assert [step["step"] for step in incident["reasoning_chain"]] == [
        "SIGNAL DETECTED",
        "CHECKING MEMORY",
        "CHECKING DEPLOYS",
        "CHECKING HEALTH",
        "HYPOTHESIS",
    ]


def test_below_threshold_signal_does_not_create_incident(client):
    assert save_config(client).status_code == 200

    result = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 1.0, "baseline": 0.2},
    ).json()

    assert result["triggered"] is False
    assert client.get("/api/incidents").json()["active"] == []


def test_status_and_resolution_generate_post_mortem(client):
    assert save_config(client).status_code == 200
    seed_context(client)
    incident = client.post(
        "/api/signal",
        json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
    ).json()

    status = client.post(
        "/api/status",
        json={"query": "What's the status?", "incident_id": incident["incident_id"]},
    ).json()
    assert "payments incident is open" in status["response"]

    resolved = client.post(
        f"/api/incidents/{incident['incident_id']}/resolve",
        json={"resolution_text": "Rolled back payments-api"},
    ).json()
    assert resolved["status"] == "resolved"
    assert "INCIDENT POST-MORTEM" in resolved["post_mortem"]


def test_demo_reset_and_full_seed(client):
    seeded = client.post("/api/demo/full-seed").json()
    assert seeded["status"] == "seeded"
    assert client.get("/api/config").status_code == 200

    reset = client.post("/api/demo/reset?keep_config=false").json()
    assert reset["status"] == "reset"
    assert client.get("/api/config").status_code == 404
