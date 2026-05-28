from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ResolveIncidentIn, RollbackIn, SignalIn, StatusQueryIn
from app.services.incident_service import IncidentService
from app.services.blast_radius_service import BlastRadiusService
from app.services.fix_preview_service import FixPreviewService
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


@router.get("/api/incidents/{incident_id}/post-mortem.md")
def download_post_mortem(incident_id: int, db: Session = Depends(get_db)) -> Response:
    service = IncidentService(db)
    incident = service.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not incident.post_mortem:
        raise HTTPException(status_code=404, detail="Post-mortem not found")
    filename = f"sentinelai-incident-{incident_id}-post-mortem.md"
    return Response(
        content=incident.post_mortem,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


@router.post("/api/incidents/{incident_id}/blast-radius")
def analyze_blast_radius(incident_id: int, db: Session = Depends(get_db)) -> dict:
    service = IncidentService(db)
    incident = service.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    result = BlastRadiusService(db).analyze_incident(incident)
    service.timeline.append(
        incident.id,
        "blast_radius_analyzed",
        result["warning"] or f"No connected services found for {incident.service}.",
        {
            "affected_services": result["affected_services"],
            "risk_level": result["risk_level"],
        },
    )
    db.commit()
    return result


@router.post("/api/incidents/{incident_id}/fix-preview")
def generate_fix_preview(incident_id: int, db: Session = Depends(get_db)) -> dict:
    service = IncidentService(db)
    incident = service.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return FixPreviewService(db).generate(incident)


@router.post("/api/status")
def query_status(payload: StatusQueryIn, db: Session = Depends(get_db)) -> dict:
    return IncidentService(db).status_response(payload)
