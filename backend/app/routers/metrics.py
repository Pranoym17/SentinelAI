from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import MetricUpdateIn
from app.services.metrics_service import MetricsService


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
def get_metrics(db: Session = Depends(get_db)) -> dict:
    return MetricsService(db).latest()


@router.get("/history")
def get_metric_history(db: Session = Depends(get_db), limit: int = 60) -> dict:
    return MetricsService(db).history(limit)


@router.post("/update")
def update_metric(payload: MetricUpdateIn, db: Session = Depends(get_db)) -> dict:
    snapshot = MetricsService(db).record(payload)
    db.commit()
    db.refresh(snapshot)
    return {"status": "updated", "id": snapshot.id}
