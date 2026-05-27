from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Config, Incident, MetricSnapshot, TimelineEvent
from app.schemas import ResolveIncidentIn, SignalIn, StatusQueryIn


router = APIRouter(tags=["incidents"])


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


def severity_for_signal(payload: SignalIn) -> str:
    if payload.type == "error_spike" and payload.value >= 10:
        return "SEV-1"
    if payload.type == "latency_spike" and payload.value >= 2000:
        return "SEV-2"
    return "SEV-3"


@router.post("/api/signal")
def receive_signal(payload: SignalIn, db: Session = Depends(get_db)) -> dict:
    config = db.query(Config).order_by(Config.id.desc()).first()
    if not config:
        raise HTTPException(status_code=400, detail="No config found. Please run setup first.")

    metric_type = "error_rate" if payload.type == "error_spike" else payload.type
    db.add(
        MetricSnapshot(
            service=payload.service,
            metric_type=metric_type,
            value=payload.value,
            baseline=payload.baseline,
        )
    )

    confidence = 80 if payload.value > payload.baseline else 35
    severity = severity_for_signal(payload)
    reasoning_chain = [
        {
            "step": "SIGNAL DETECTED",
            "detail": f"{payload.service} {payload.type} at {payload.value} vs baseline {payload.baseline}",
            "confidence": 30,
        },
        {
            "step": "API FOUNDATION",
            "detail": "Phase 1 recorded the incident. OpenAI investigation will replace this placeholder in Phase 3.",
            "confidence": confidence,
        },
    ]
    incident = Incident(
        service=payload.service,
        signal_type=payload.type,
        signal_value=payload.value,
        severity=severity,
        hypothesis=f"{payload.service} is showing an anomalous {payload.type}. Investigation pending.",
        confidence=confidence,
        reasoning_chain=reasoning_chain,
        affected_teams=[payload.service, "platform"],
    )
    db.add(incident)
    db.flush()

    event = TimelineEvent(
        incident_id=incident.id,
        event_type="detection",
        description=f"{payload.type} detected for {payload.service}: {payload.value}",
        event_metadata={"baseline": payload.baseline, "unit": payload.unit},
    )
    db.add(event)
    db.commit()
    db.refresh(incident)

    return {
        **serialize_incident(incident, [event]),
        "triggered": True,
        "actions_taken": [],
    }


@router.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)) -> dict:
    incidents = db.query(Incident).order_by(Incident.detected_at.desc()).all()
    active = [serialize_incident(incident) for incident in incidents if incident.status == "open"]
    resolved = [serialize_incident(incident) for incident in incidents if incident.status == "resolved"]
    return {"active": active, "resolved": resolved}


@router.get("/api/incidents/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> dict:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    timeline = (
        db.query(TimelineEvent)
        .filter(TimelineEvent.incident_id == incident_id)
        .order_by(TimelineEvent.occurred_at)
        .all()
    )
    return serialize_incident(incident, timeline)


@router.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(
    incident_id: int,
    payload: ResolveIncidentIn,
    db: Session = Depends(get_db),
) -> dict:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    incident.resolution_text = payload.resolution_text
    incident.duration_minutes = max(
        0,
        int((incident.resolved_at - incident.detected_at).total_seconds() / 60),
    )
    incident.post_mortem = (
        f"# INCIDENT POST-MORTEM - {incident.service.upper()}\n\n"
        f"## Summary\n{incident.hypothesis}\n\n"
        f"## Resolution\n{payload.resolution_text}\n\n"
        "## Note\nAI-generated post-mortem will be implemented in a later phase.\n"
    )
    db.add(
        TimelineEvent(
            incident_id=incident.id,
            event_type="resolved",
            description=f"Incident resolved: {payload.resolution_text}",
        )
    )
    db.commit()
    db.refresh(incident)

    return {
        "status": "resolved",
        "duration_minutes": incident.duration_minutes,
        "post_mortem": incident.post_mortem,
    }


@router.post("/api/status")
def query_status(payload: StatusQueryIn, db: Session = Depends(get_db)) -> dict:
    incident = None
    if payload.incident_id:
        incident = db.get(Incident, payload.incident_id)
    if incident is None:
        incident = (
            db.query(Incident)
            .filter(Incident.status == "open")
            .order_by(Incident.detected_at.desc())
            .first()
        )
    if incident is None:
        return {"response": "No active incidents. All monitored systems are currently normal."}

    duration = int((datetime.utcnow() - incident.detected_at).total_seconds() / 60)
    response = (
        f"{incident.service} incident is {incident.status} at {incident.severity}. "
        f"It has been open for {duration} minutes. "
        f"Current hypothesis: {incident.hypothesis} "
        f"Confidence is {incident.confidence}%."
    )
    return {"response": response}
