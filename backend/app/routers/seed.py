from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HealthCheck, HistoricalIncident, MetricSnapshot, RecentDeploy
from app.schemas import DeploySeedRequest, MemorySeedRequest


router = APIRouter(prefix="/api/seed", tags=["seed"])


@router.post("/deploys")
def seed_deploys(payload: DeploySeedRequest, db: Session = Depends(get_db)) -> dict:
    for deploy in payload.deploys:
        db.add(RecentDeploy(**deploy.model_dump()))
    db.commit()
    return {"status": "seeded", "count": len(payload.deploys)}


@router.post("/memory")
def seed_memory(payload: MemorySeedRequest, db: Session = Depends(get_db)) -> dict:
    for incident in payload.incidents:
        db.add(HistoricalIncident(**incident.model_dump()))
    db.commit()
    return {"status": "seeded", "count": len(payload.incidents)}


@router.post("/demo")
def seed_demo(db: Session = Depends(get_db)) -> dict:
    for service in ["database", "redis", "message-queue"]:
        db.add(HealthCheck(service=service, status="healthy", latency_ms=12.0))

    for service in ["payments", "auth", "api-gateway"]:
        db.add(MetricSnapshot(service=service, metric_type="error_rate", value=0.2, baseline=0.2))
        db.add(MetricSnapshot(service=service, metric_type="latency_ms", value=145.0, baseline=150.0))

    db.commit()
    return {"status": "seeded", "health_checks": 3, "metric_snapshots": 6}
