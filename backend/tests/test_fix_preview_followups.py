from unittest.mock import Mock

from app.models import Incident, TimelineEvent
from app.services.fix_preview_service import FixPreviewService
from app.services.post_mortem_followup_service import PostMortemFollowupService


def add_incident(db, resolved=False):
    incident = Incident(
        service="payments",
        signal_type="error_spike",
        signal_value=18.0,
        severity="SEV-1",
        hypothesis="Deploy regression in payment SDK response handling",
        confidence=95,
        reasoning_chain=[{"step": "CHECKING COMMITS", "detail": "Commit 5fd5308 changed sdk_client.py"}],
        recommended_actions=["Rollback payments-api", "Audit payment SDK response parsing"],
        affected_teams=["payments"],
        jira_ticket_id="SCRUM-10",
        jira_ticket_url="https://example.atlassian.net/browse/SCRUM-10",
        post_mortem="# INCIDENT POST-MORTEM\n\n## Action items\n- Add contract test",
        resolution_text="Rolled back payments-api",
    )
    if resolved:
        incident.status = "resolved"
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def event_types(db, incident_id):
    return [
        event.event_type
        for event in db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident_id).all()
    ]


def test_fix_preview_service_generates_and_stores_preview(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db)
        service = FixPreviewService(db)
        service.github.repo_for_service = Mock(return_value="Pranoym17/payments-api-demo")
        service.github.recent_commits_for_service = Mock(
            return_value=[
                {
                    "sha": "5fd5308",
                    "message": "Update payments SDK response handling",
                    "files_changed": ["app/services/sdk_client.py"],
                }
            ]
        )
        service.openai.client = None

        result = service.generate(incident)

        assert result["status"] == "generated"
        assert "authorization_id" in result["fix_preview"]["diff"]
        assert result["fix_preview"]["repo"] == "Pranoym17/payments-api-demo"
        assert "github_fix_preview_generated" in event_types(db, incident.id)
        assert db.get(Incident, incident.id).fix_preview["title"]
    finally:
        db.close()


def test_fix_preview_endpoint_returns_existing_preview(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db)
        incident.fix_preview = {"title": "Existing preview", "diff": "diff --git a/x b/x"}
        db.commit()

        response = client.post(f"/api/incidents/{incident.id}/fix-preview")

        assert response.status_code == 200
        assert response.json()["status"] == "existing"
        assert response.json()["fix_preview"]["title"] == "Existing preview"
    finally:
        db.close()


def test_post_mortem_followups_create_jira_tasks(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db, resolved=True)
        jira = Mock()
        jira.create_subtasks.return_value = {
            "created": True,
            "subtasks": [{"created": True, "ticket_id": "SCRUM-21", "summary": "Add contract test"}],
        }
        service = PostMortemFollowupService(db, jira=jira)
        service.openai.client = None

        result = service.create_followups(incident)

        assert result["created"] is True
        assert len(result["items"]) == 3
        assert "jira_followups_created" in event_types(db, incident.id)
        jira.create_subtasks.assert_called_once()
    finally:
        db.close()
