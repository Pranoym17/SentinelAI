from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import MetricSnapshot
from app.schemas import MetricUpdateIn


DEFAULT_SERVICES = ["payments", "auth", "api-gateway"]
DEFAULT_METRICS = {
    "error_rate": {"value": 0.2, "baseline": 0.2},
    "latency_ms": {"value": 145.0, "baseline": 150.0},
}


def signal_to_metric_type(signal_type: str) -> str:
    if signal_type == "error_spike":
        return "error_rate"
    if signal_type == "latency_spike":
        return "latency_ms"
    return signal_type


class MetricsService:
    def __init__(self, db: Session):
        self.db = db

    def status(self, value: float, baseline: float) -> str:
        diff_pct = abs(value - baseline) / max(abs(baseline), 0.001) * 100
        if diff_pct > 50:
            return "critical"
        if diff_pct > 20:
            return "warning"
        return "normal"

    def latest(self) -> dict:
        snapshots = (
            self.db.query(MetricSnapshot)
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
                    "status": self.status(value, baseline),
                }
            result.append(service_data)

        return {"metrics": result}

    def history(self, limit: int = 60) -> dict:
        snapshots = (
            self.db.query(MetricSnapshot)
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

    def record(self, payload: MetricUpdateIn) -> MetricSnapshot:
        snapshot = MetricSnapshot(
            service=payload.service,
            metric_type=payload.metric_type,
            value=payload.value,
            baseline=payload.baseline if payload.baseline is not None else payload.value,
        )
        self.db.add(snapshot)
        return snapshot

    def record_signal(self, service: str, signal_type: str, value: float, baseline: float) -> MetricSnapshot:
        snapshot = MetricSnapshot(
            service=service,
            metric_type=signal_to_metric_type(signal_type),
            value=value,
            baseline=baseline,
        )
        self.db.add(snapshot)
        return snapshot
