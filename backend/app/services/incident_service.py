from sqlalchemy.orm import Session

from app.models import Config, Incident
from app.schemas import ResolveIncidentIn, SignalIn, StatusQueryIn
from app.agents.incident_orchestrator import IncidentOrchestrator
from app.agents.post_mortem_agent import PostMortemAgent
from app.agents.status_agent import StatusAgent
from app.services.memory_service import MemoryService
from app.services.serializers import serialize_incident
from app.services.runbook_service import RunbookService
from app.services.sla_service import SLAService
from app.services.timeline_service import TimelineService
from app.time_utils import utc_now


def severity_for_signal(payload: SignalIn) -> str:
    if payload.type == "error_spike" and payload.value >= 10:
        return "SEV-1"
    if payload.type == "latency_spike" and payload.value >= 2000:
        return "SEV-2"
    return "SEV-3"


class IncidentService:
    def __init__(self, db: Session):
        self.db = db
        self.timeline = TimelineService(db)
        self.memory = MemoryService(db)
        self.runbooks = RunbookService(db)

    def latest_config(self) -> Config | None:
        return self.db.query(Config).order_by(Config.id.desc()).first()

    def create_from_signal(self, payload: SignalIn) -> dict:
        config = self.latest_config()
        return IncidentOrchestrator(self.db).handle_signal(payload, config)

    def list(self) -> dict:
        incidents = self.db.query(Incident).order_by(Incident.detected_at.desc()).all()
        active = [serialize_incident(incident) for incident in incidents if incident.status == "open"]
        resolved = [serialize_incident(incident) for incident in incidents if incident.status == "resolved"]
        return {"active": active, "resolved": resolved}

    def get(self, incident_id: int) -> Incident | None:
        return self.db.get(Incident, incident_id)

    def detail(self, incident: Incident) -> dict:
        return serialize_incident(incident, self.timeline.get(incident.id))

    def resolve(self, incident: Incident, payload: ResolveIncidentIn) -> dict:
        incident.status = "resolved"
        incident.resolved_at = utc_now()
        incident.resolution_text = payload.resolution_text
        incident.duration_minutes = max(
            0,
            int((incident.resolved_at - incident.detected_at).total_seconds() / 60),
        )
        self.timeline.append(
            incident.id,
            "resolved",
            f"Incident resolved: {payload.resolution_text}",
        )
        timeline = self.timeline.get(incident.id)
        incident.post_mortem = PostMortemAgent().generate(incident, timeline)
        self.memory.remember(
            service=incident.service,
            signal_type=incident.signal_type,
            root_cause=incident.hypothesis or "Unknown root cause",
            resolution=payload.resolution_text,
            duration_minutes=incident.duration_minutes or 0,
            occurred_at=incident.detected_at,
        )
        sla_record = SLAService(self.db).record_downtime(
            incident.service,
            incident.duration_minutes or 0,
            commit=False,
        )
        self.timeline.append(
            incident.id,
            "sla_downtime_recorded",
            f"Recorded {incident.duration_minutes or 0} minute(s) of downtime against {incident.service} SLA",
            {
                "service": incident.service,
                "month": sla_record.month,
                "total_downtime_minutes": sla_record.total_downtime_minutes,
                "incident_count": sla_record.incident_count,
                "sla_breached": sla_record.sla_breached,
            },
        )
        successful_runbooks = self.runbooks.mark_successful(incident.service, incident.signal_type)
        if successful_runbooks:
            self.timeline.append(
                incident.id,
                "runbook_success_recorded",
                f"Marked {len(successful_runbooks)} matching runbook(s) successful",
                {"runbook_ids": [runbook.id for runbook in successful_runbooks]},
            )
        self.db.commit()
        self.db.refresh(incident)

        return {
            "status": "resolved",
            "duration_minutes": incident.duration_minutes,
            "post_mortem": incident.post_mortem,
        }

    def status_response(self, payload: StatusQueryIn) -> dict:
        incident = self.db.get(Incident, payload.incident_id) if payload.incident_id else None
        if incident is None:
            incident = (
                self.db.query(Incident)
                .filter(Incident.status == "open")
                .order_by(Incident.detected_at.desc())
                .first()
            )
        if incident is None:
            return {"response": "No active incidents. All monitored systems are currently normal."}

        timeline = self.timeline.get(incident.id)
        return {"response": StatusAgent().answer(payload.query, incident, timeline)}
