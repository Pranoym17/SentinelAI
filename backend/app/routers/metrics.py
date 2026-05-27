from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MetricSnapshot
from app.schemas import MetricUpdateIn


router = APIRouter(prefix="/api/metrics", tags=["metrics"])

DEFAULT_SERVICES = ["payments", "auth", "api-gateway"]
DEFAULT_METRICS = {
    "error_rate": {"value": 0.2, "baseline": 0.2},
    "latency_ms": {"value": 145.0, "baseline": 150.0},
}


def metric_status(value: float, baseline: float) -> str:
    diff_pct = abs(value - baseline) / max(abs(baseline), 0.001) * 100
    if diff_pct > 50:
        return "critical"
    if diff_pct > 20:
        return "warning"
    return "normal"


@router.get("")
def get_metrics(db: Session = Depends(get_db)) -> dict:
    snapshots = (
        db.query(MetricSnapshot)
        .order_by(MetricSnapshot.recorded_at.desc())
        .limit(100)
        .all()
    )
    latest_by_key = {}
    for snapshot in snapshots:
        key = (snapshot.service, snapshot.metric_type)
        if key not in latest_by_key:
            latest_by_key[key] = snapshot

    services = sorted({svc for svc, _ in latest_by_key.keys()} | set(DEFAULT_SERVICES))
    result = []
    for service in services:
        service_data = {"service": service}
        for metric_type, defaults in DEFAULT_METRICS.items():
            snapshot = latest_by_key.get((service, metric_type))
            value = snapshot.value if snapshot else defaults["value"]
            baseline = snapshot.baseline if snapshot else defaults["baseline"]
            service_data[metric_type] = {
                "value": round(value, 2),
                "baseline": round(baseline, 2),
                "status": metric_status(value, baseline),
            }
        result.append(service_data)

    return {"metrics": result}


@router.get("/history")
def get_metric_history(db: Session = Depends(get_db), limit: int = 60) -> dict:
    snapshots = (
        db.query(MetricSnapshot)
        .order_by(MetricSnapshot.recorded_at.desc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    history = defaultdict(list)
    for snapshot in reversed(snapshots):
        history[snapshot.service].append(
            {
                "metric_type": snapshot.metric_type,
                "value": snapshot.value,
                "baseline": snapshot.baseline,
                "recorded_at": snapshot.recorded_at.isoformat(),
            }
        )
    return {"history": dict(history)}


@router.post("/update")
def update_metric(payload: MetricUpdateIn, db: Session = Depends(get_db)) -> dict:
    snapshot = MetricSnapshot(
        service=payload.service,
        metric_type=payload.metric_type,
        value=payload.value,
        baseline=payload.baseline if payload.baseline is not None else payload.value,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"status": "updated", "id": snapshot.id}
