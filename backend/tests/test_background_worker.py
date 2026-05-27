from app.background_worker import BackgroundWorker, compute_z_score, worker


def test_compute_z_score_detects_spike():
    assert compute_z_score(18.0, [0.2] * 20) > 3.0


def test_compute_z_score_ignores_short_window():
    assert compute_z_score(18.0, [0.2]) == 0.0


def test_worker_trigger_state():
    worker = BackgroundWorker()
    result = worker.schedule_payment_spike(delay_seconds=5)
    assert result["status"] == "scheduled"
    assert worker.state()["payment_spike_at"] is not None


def test_global_worker_tick_detects_scheduled_spike(client):
    client.post("/api/demo/full-seed")
    worker.windows[("payments", "error_rate")].clear()
    worker.windows[("payments", "error_rate")].extend([0.2] * 20)
    worker.schedule_payment_spike(delay_seconds=0)

    worker.tick()

    active = client.get("/api/incidents").json()["active"]
    assert len(active) == 1
    assert active[0]["service"] == "payments"
    assert active[0]["signal_type"] == "error_spike"


def test_worker_reuses_existing_open_incident_on_second_spike(client):
    client.post("/api/demo/full-seed")
    worker.windows[("payments", "error_rate")].clear()
    worker.windows[("payments", "error_rate")].extend([0.2] * 20)
    worker.schedule_payment_spike(delay_seconds=0)
    worker.tick()

    worker.windows[("payments", "error_rate")].clear()
    worker.windows[("payments", "error_rate")].extend([0.2] * 20)
    worker.schedule_payment_spike(delay_seconds=0)
    worker.tick()

    active = client.get("/api/incidents").json()["active"]
    assert len(active) == 1
    detail = client.get(f"/api/incidents/{active[0]['incident_id']}").json()
    assert "duplicate_signal" in [event["event_type"] for event in detail["timeline"]]
