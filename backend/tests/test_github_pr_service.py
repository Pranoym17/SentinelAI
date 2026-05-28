import base64

from app.models import Incident, TimelineEvent
from app.services.github_pr_service import GitHubPRService


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
            "content": base64.b64encode(b"def authorize(response):\n    return response\n").decode("ascii"),
            "encoding": "base64",
        }

    def update_file(self, repo, path, branch, message, content_base64, sha):
        decoded = base64.b64decode(content_base64).decode("utf-8")
        assert "SentinelAI suggested fix preview" in decoded
        return {"committed": True, "commit_sha": "commit-sha", "content_url": "https://github.com/file"}

    def open_pull_request(self, repo, title, head, base, body):
        assert "SentinelAI incident fix" in body
        return {"opened": True, "number": 7, "url": "https://github.com/pull/7", "title": title, "branch": head}


def add_incident(db, confidence=95, with_preview=True):
    incident = Incident(
        service="payments",
        signal_type="error_spike",
        signal_value=18.0,
        severity="SEV-1",
        hypothesis="Deploy regression in payment SDK response handling",
        confidence=confidence,
        reasoning_chain=[{"step": "CHECKING COMMITS", "detail": "Commit changed sdk_client.py"}],
        recommended_actions=["Audit SDK response parsing"],
        jira_ticket_url="https://example.atlassian.net/browse/SCRUM-10",
    )
    if with_preview:
        incident.fix_preview = {
            "title": "Guard missing authorization_id in payment SDK response",
            "summary": "Add a guard for partial provider responses.",
            "repo": "Pranoym17/payments-api-demo",
            "files": [{"path": "app/services/sdk_client.py"}],
            "diff": "diff --git a/app/services/sdk_client.py b/app/services/sdk_client.py",
            "confidence": 95,
        }
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def event_types(db, incident_id):
    return [
        event.event_type
        for event in db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident_id).all()
    ]


def test_github_pr_creation_guarded_by_env(client, monkeypatch):
    from app.database import SessionLocal

    monkeypatch.setenv("GITHUB_PR_ENABLED", "false")
    db = SessionLocal()
    try:
        incident = add_incident(db)
        result = GitHubPRService(db, github=FakeGitHub()).create_pr(incident)
        assert result["status"] == "disabled"
    finally:
        db.close()


def test_github_pr_creation_success(client, monkeypatch):
    from app.database import SessionLocal

    monkeypatch.setenv("GITHUB_PR_ENABLED", "true")
    monkeypatch.setenv("GITHUB_PR_BASE_BRANCH", "main")
    monkeypatch.setenv("GITHUB_PR_BRANCH_PREFIX", "sentinel")
    db = SessionLocal()
    try:
        incident = add_incident(db)
        result = GitHubPRService(db, github=FakeGitHub()).create_pr(incident)

        assert result["status"] == "created"
        assert result["github_pr"]["number"] == 7
        assert result["github_pr"]["branch"] == "sentinel/fix-incident-1-payments"
        assert "github_branch_created" in event_types(db, incident.id)
        assert "github_commit_created" in event_types(db, incident.id)
        assert "github_pr_created" in event_types(db, incident.id)
        assert db.get(Incident, incident.id).github_pr["url"] == "https://github.com/pull/7"
    finally:
        db.close()


def test_github_pr_blocks_low_confidence(client, monkeypatch):
    from app.database import SessionLocal

    monkeypatch.setenv("GITHUB_PR_ENABLED", "true")
    db = SessionLocal()
    try:
        incident = add_incident(db, confidence=55)
        result = GitHubPRService(db, github=FakeGitHub()).create_pr(incident)
        assert result["status"] == "blocked"
        assert "high-confidence" in result["reason"]
    finally:
        db.close()


def test_github_pr_endpoint_returns_existing_pr(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db)
        incident.github_pr = {"url": "https://github.com/pull/8", "number": 8}
        db.commit()
        response = client.post(f"/api/incidents/{incident.id}/github-pr")
        assert response.status_code == 200
        assert response.json()["status"] == "existing"
        assert response.json()["github_pr"]["number"] == 8
    finally:
        db.close()
