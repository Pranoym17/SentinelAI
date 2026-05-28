from fastapi import APIRouter, Depends, HTTPException
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
def trigger(delay_seconds: int = 30, service: str = "payments", signal_type: str | None = None) -> dict:
    try:
        return worker.schedule_demo_signal(service=service, signal_type=signal_type, delay_seconds=delay_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/worker")
def state() -> dict:
    return worker.state()


@router.get("/state")
def demo_state(db: Session = Depends(get_db)) -> dict:
    return DemoService(db).state()
