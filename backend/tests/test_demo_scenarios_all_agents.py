import base64

from app.models import Incident, Service, SLARecord
from app.services.fix_preview_service import FixPreviewService
from app.services.github_pr_service import GitHubPRService
from app.services.rollback_service import RollbackService


SCENARIOS = [
    ("payments", "error_spike", 18.0, 0.2, "payment"),
    ("auth", "latency_spike", 3200.0, 150.0, "token"),
    ("api-gateway", "error_spike", 8.5, 0.3, "gateway"),
]


class FakeGitHub:
    configured = True

    def repo_for_service(self, service):
        return "Pranoym17/payments-api-demo"

    def get_branch_sha(self, repo, branch):
        return "base-sha"

    def create_branch(self, repo, branch, base_sha):
        return {"created": True, "branch": branch}

    def get_file(self, repo, path, ref):
        return {
            "ok": True,
            "path": path,
            "sha": "file-sha",
            "content": base64.b64encode(b"def handler(response):\n    return response\n").decode("ascii"),
            "encoding": "base64",
        }

    def update_file(self, repo, path, branch, message, content_base64, sha):
        decoded = base64.b64decode(content_base64).decode("utf-8")
        assert "SentinelAI suggested fix preview" in decoded
        return {"committed": True, "commit_sha": "commit-sha", "content_url": "https://github.com/file"}

    def open_pull_request(self, repo, title, head, base, body):
        assert "SentinelAI incident fix" in body
        return {"opened": True, "number": 7, "url": "https://github.com/pull/7", "title": title, "branch": head}


def test_full_seed_creates_catalog_and_sla_for_all_demo_services(client):
    from app.database import SessionLocal

    client.post("/api/demo/full-seed")
    db = SessionLocal()
    try:
        for service_name, _, _, _, _ in SCENARIOS:
            service = db.query(Service).filter(Service.name == service_name).one()
            sla = db.query(SLARecord).filter(SLARecord.service == service_name).one()

            assert service.team
            assert service.dependencies
            assert service.repo_url
            assert sla.target_uptime == service.sla_target
    finally:
        db.close()


def test_all_seeded_scenarios_trigger_rich_incidents(client):
    for service, signal_type, value, baseline, expected_text in SCENARIOS:
        client.post("/api/demo/full-seed")
        incident = client.post(
            "/api/signal",
            json={"service": service, "type": signal_type, "value": value, "baseline": baseline},
        ).json()

        assert incident["triggered"] is True
        assert incident["service"] == service
        assert incident["confidence"] >= 80
        assert incident["matched_past_incident_id"]
        assert incident["recommended_actions"]
        assert expected_text in str(incident["reasoning_chain"]).lower()

        blast = client.post(f"/api/incidents/{incident['incident_id']}/blast-radius").json()
        assert blast["risk_level"] != "unknown"
        assert blast["affected_services"]


def test_fix_preview_and_rollback_are_service_specific_for_each_demo(client):
    from app.database import SessionLocal

    for service, signal_type, value, baseline, expected_text in SCENARIOS:
        client.post("/api/demo/full-seed")
        incident_data = client.post(
            "/api/signal",
            json={"service": service, "type": signal_type, "value": value, "baseline": baseline},
        ).json()

        db = SessionLocal()
        try:
            incident = db.get(Incident, incident_data["incident_id"])
            preview = FixPreviewService(db).generate(incident)["fix_preview"]
            rollback = RollbackService(db).execute(incident)

            assert expected_text in (preview["title"] + preview["summary"] + preview["diff"]).lower()
            assert service in " ".join(rollback["logs"])
            assert rollback["metric"]["service"] == service
            if signal_type == "latency_spike":
                assert rollback["metric"]["metric_type"] == "latency_ms"
            else:
                assert rollback["metric"]["metric_type"] == "error_rate"
        finally:
            db.close()


def test_github_pr_can_open_for_each_high_confidence_demo(client, monkeypatch):
    from app.database import SessionLocal

    monkeypatch.setenv("GITHUB_PR_ENABLED", "true")
    monkeypatch.setenv("GITHUB_PR_BASE_BRANCH", "main")
    monkeypatch.setenv("GITHUB_PR_BRANCH_PREFIX", "sentinel")

    for service, signal_type, value, baseline, _ in SCENARIOS:
        client.post("/api/demo/full-seed")
        incident_data = client.post(
            "/api/signal",
            json={"service": service, "type": signal_type, "value": value, "baseline": baseline},
        ).json()

        db = SessionLocal()
        try:
            incident = db.get(Incident, incident_data["incident_id"])
            assert incident.confidence >= 80
            FixPreviewService(db).generate(incident)

            result = GitHubPRService(db, github=FakeGitHub()).create_pr(incident)

            assert result["status"] == "created"
            assert service in result["github_pr"]["branch"]
        finally:
            db.close()


def test_demo_trigger_endpoint_accepts_all_scenarios(client):
    for service, signal_type, _, _, _ in SCENARIOS:
        response = client.post(f"/api/demo/trigger?delay_seconds=5&service={service}&signal_type={signal_type}")

        assert response.status_code == 200
        body = response.json()
        assert body["service"] == service
        assert body["signal_type"] == signal_type
