from app.models import Config, Incident, TimelineEvent


def serialize_config(config: Config) -> dict:
    return {
        "id": config.id,
        "services": config.services or [],
        "signals": config.signals or [],
        "actions": config.actions or [],
        "thresholds": config.thresholds or {},
        "slack_channel": config.slack_channel or "#incidents",
        "jira_project_key": config.jira_project_key or "INC",
    }


def serialize_timeline(event: TimelineEvent) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "description": event.description,
        "metadata": event.event_metadata or {},
        "occurred_at": event.occurred_at.isoformat(),
    }


def serialize_incident(incident: Incident, timeline: list[TimelineEvent] | None = None) -> dict:
    data = {
        "id": incident.id,
        "incident_id": incident.id,
        "status": incident.status,
        "severity": incident.severity,
        "service": incident.service,
        "signal_type": incident.signal_type,
        "signal_value": incident.signal_value,
        "hypothesis": incident.hypothesis,
        "confidence": incident.confidence,
        "reasoning_chain": incident.reasoning_chain or [],
        "recommended_actions": incident.recommended_actions or [],
        "fix_preview": incident.fix_preview,
        "github_pr": incident.github_pr,
        "raw_model_response": incident.raw_model_response,
        "affected_teams": incident.affected_teams or [],
        "jira_ticket_id": incident.jira_ticket_id,
        "jira_ticket_url": incident.jira_ticket_url,
        "slack_message_ts": incident.slack_message_ts,
        "resolution_text": incident.resolution_text,
        "post_mortem": incident.post_mortem,
        "detected_at": incident.detected_at.isoformat(),
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "duration_minutes": incident.duration_minutes,
    }
    if timeline is not None:
        data["timeline"] = [serialize_timeline(event) for event in timeline]
    return data
