from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.background_worker import worker
from app.models import HistoricalIncident, RecentDeploy
from app.schemas import DeploySeedRequest, MemorySeedRequest
from app.services.demo_service import DemoService


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
    return DemoService(db).seed_basics()


@router.post("/full-demo")
def seed_full_demo(db: Session = Depends(get_db)) -> dict:
    return DemoService(db).full_seed()


@router.post("/reset")
def reset_demo(keep_config: bool = True, db: Session = Depends(get_db)) -> dict:
    return DemoService(db).reset(keep_config=keep_config)


@router.post("/trigger")
def trigger_demo(delay_seconds: int = 30) -> dict:
    return worker.schedule_payment_spike(delay_seconds=delay_seconds)


@router.get("/worker")
def worker_state() -> dict:
    return worker.state()
