from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.background_worker import worker
from app.database import get_db
from app.services.demo_service import DemoService


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/full-seed")
def full_seed(db: Session = Depends(get_db)) -> dict:
    return DemoService(db).full_seed()


@router.post("/reset")
def reset(keep_config: bool = True, db: Session = Depends(get_db)) -> dict:
    return DemoService(db).reset(keep_config=keep_config)


@router.post("/trigger")
def trigger(delay_seconds: int = 30) -> dict:
    return worker.schedule_payment_spike(delay_seconds=delay_seconds)


@router.get("/worker")
def state() -> dict:
    return worker.state()


@router.get("/state")
def demo_state(db: Session = Depends(get_db)) -> dict:
    return DemoService(db).state()
