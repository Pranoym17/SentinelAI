from unittest.mock import Mock

from app.models import Config, Incident, TimelineEvent
from app.services.response_agent import ResponseAgent


def add_incident(db, confidence=95):
    incident = Incident(
        service="payments",
        signal_type="error_spike",
        signal_value=18.0,
        severity="SEV-1",
        hypothesis="Deploy regression",
        confidence=confidence,
        affected_teams=["payments"],
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def event_types(db, incident_id):
    return [
        event.event_type
        for event in db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident_id).all()
    ]


def test_response_agent_records_jira_and_slack_success(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db, confidence=95)
        agent = ResponseAgent(db, Config(actions=["jira", "slack"]))
        agent.jira.create_ticket = Mock(
            return_value={"created": True, "ticket_id": "SCRUM-9", "url": "https://example/browse/SCRUM-9"}
        )
        agent.slack.post_incident_alert = Mock(return_value={"posted": True, "ts": "123.456"})

        actions = agent.route(incident, ["Rollback"])

        assert actions == ["jira_created", "slack_sent"]
        assert event_types(db, incident.id) == ["jira_created", "slack_sent"]
    finally:
        db.close()


def test_response_agent_records_failures(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db, confidence=95)
        agent = ResponseAgent(db, Config(actions=["jira", "slack"]))
        agent.jira.create_ticket = Mock(return_value={"created": False, "failed": True, "reason": "Jira failed"})
        agent.slack.post_incident_alert = Mock(return_value={"posted": False, "failed": True, "reason": "Slack failed"})

        actions = agent.route(incident, ["Rollback"])

        assert actions == []
        assert event_types(db, incident.id) == ["jira_failed", "slack_failed"]
    finally:
        db.close()


def test_response_agent_records_skips(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db, confidence=95)
        agent = ResponseAgent(db, Config(actions=["jira", "slack"]))
        agent.jira.create_ticket = Mock(return_value={"created": False, "reason": "Jira is not configured"})
        agent.slack.post_incident_alert = Mock(return_value={"posted": False, "reason": "Slack is not configured"})

        actions = agent.route(incident, ["Rollback"])

        assert actions == []
        assert event_types(db, incident.id) == ["jira_skipped", "slack_skipped"]
    finally:
        db.close()


def test_response_agent_low_confidence_slack_path(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        incident = add_incident(db, confidence=30)
        agent = ResponseAgent(db, Config(actions=["slack"]))
        agent.slack.post_low_confidence_alert = Mock(return_value={"posted": True})

        actions = agent.route(incident)

        assert actions == ["slack_low_confidence_sent", "flagged_for_review"]
        assert event_types(db, incident.id) == ["slack_low_confidence_sent", "human_review"]
    finally:
        db.close()
