from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ResolveIncidentIn, RollbackIn, SignalIn, StatusQueryIn
from app.services.incident_service import IncidentService
from app.services.rollback_service import RollbackService


router = APIRouter(tags=["incidents"])


@router.post("/api/signal")
def receive_signal(payload: SignalIn, db: Session = Depends(get_db)) -> dict:
    service = IncidentService(db)
    if not service.latest_config():
        raise HTTPException(status_code=400, detail="No config found. Please run setup first.")
    return service.create_from_signal(payload)


@router.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)) -> dict:
    return IncidentService(db).list()


@router.get("/api/incidents/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> dict:
    service = IncidentService(db)
    incident = service.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return service.detail(incident)


@router.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(
    incident_id: int,
    payload: ResolveIncidentIn,
    db: Session = Depends(get_db),
) -> dict:
    service = IncidentService(db)
    incident = service.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return service.resolve(incident, payload)


@router.post("/api/incidents/{incident_id}/rollback")
def rollback_incident(
    incident_id: int,
    payload: RollbackIn | None = None,
    db: Session = Depends(get_db),
) -> dict:
    service = IncidentService(db)
    incident = service.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status != "open":
        raise HTTPException(status_code=400, detail="Only open incidents can be rolled back")
    rollback_payload = payload or RollbackIn()
    return RollbackService(db).execute(incident, delay_seconds=rollback_payload.delay_seconds)


@router.post("/api/status")
def query_status(payload: StatusQueryIn, db: Session = Depends(get_db)) -> dict:
    return IncidentService(db).status_response(payload)
