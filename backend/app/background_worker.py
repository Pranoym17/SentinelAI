import math
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

from app.agents.incident_orchestrator import IncidentOrchestrator
from app.database import SessionLocal
from app.models import Config, Incident, MetricSnapshot
from app.schemas import SignalIn
from app.time_utils import utc_now


class BackgroundWorker:
    def __init__(self, poll_seconds: int = 5, window_size: int = 20, z_threshold: float = 3.0):
        self.poll_seconds = poll_seconds
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.windows = defaultdict(lambda: deque(maxlen=window_size))
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._payment_spike_at: datetime | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="sentinel-background-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def schedule_payment_spike(self, delay_seconds: int = 30) -> dict:
        with self._lock:
            self._payment_spike_at = utc_now() + timedelta(seconds=delay_seconds)
            spike_at = self._payment_spike_at.isoformat()
        return {"status": "scheduled", "service": "payments", "spike_at": spike_at}

    def state(self) -> dict:
        with self._lock:
            spike_at = self._payment_spike_at.isoformat() if self._payment_spike_at else None
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "poll_seconds": self.poll_seconds,
            "window_size": self.window_size,
            "z_threshold": self.z_threshold,
            "payment_spike_at": spike_at,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            self.tick()
            self._stop.wait(self.poll_seconds)

    def tick(self) -> None:
        db = SessionLocal()
        try:
            config = db.query(Config).order_by(Config.id.desc()).first()
            if not config:
                return

            for service in config.services or ["payments", "auth", "api-gateway"]:
                value = self._next_error_rate(service)
                snapshot = MetricSnapshot(service=service, metric_type="error_rate", value=value, baseline=0.2)
                db.add(snapshot)
                db.commit()

                key = (service, "error_rate")
                window = self.windows[key]
                z_score = compute_z_score(value, list(window))
                window.append(value)

                if z_score > self.z_threshold and not self._has_open_incident(db, service, "error_spike"):
                    signal = SignalIn(
                        service=service,
                        type="error_spike",
                        value=value,
                        baseline=0.2,
                        unit="percent",
                    )
                    IncidentOrchestrator(db).handle_signal(signal, config)
        finally:
            db.close()

    def _next_error_rate(self, service: str) -> float:
        with self._lock:
            should_spike = service == "payments" and self._payment_spike_at and utc_now() >= self._payment_spike_at
            if should_spike:
                self._payment_spike_at = None
                return 18.0
        return 0.2

    def _has_open_incident(self, db, service: str, signal_type: str) -> bool:
        return (
            db.query(Incident)
            .filter(
                Incident.status == "open",
                Incident.service == service,
                Incident.signal_type == signal_type,
            )
            .first()
            is not None
        )


def compute_z_score(value: float, previous_values: list[float]) -> float:
    if len(previous_values) < 2:
        return 0.0
    mean = sum(previous_values) / len(previous_values)
    variance = sum((item - mean) ** 2 for item in previous_values) / len(previous_values)
    std_dev = math.sqrt(variance)
    if std_dev < 0.001:
        return abs(value - mean) / 0.001
    return abs(value - mean) / std_dev


worker = BackgroundWorker(
    poll_seconds=int(os.getenv("SENTINEL_WORKER_POLL_SECONDS", "5")),
    window_size=int(os.getenv("SENTINEL_WORKER_WINDOW_SIZE", "20")),
    z_threshold=float(os.getenv("SENTINEL_WORKER_Z_THRESHOLD", "3.0")),
)
