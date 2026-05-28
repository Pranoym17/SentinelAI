import math
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

from app.agents.incident_orchestrator import IncidentOrchestrator
from app.database import SessionLocal
from app.models import Config, MetricSnapshot
from app.schemas import SignalIn
from app.time_utils import utc_now


DEMO_SCENARIOS = {
    "payments": {
        "service": "payments",
        "type": "error_spike",
        "value": 18.0,
        "baseline": 0.2,
        "unit": "percent",
        "metric_type": "error_rate",
    },
    "auth": {
        "service": "auth",
        "type": "latency_spike",
        "value": 3200.0,
        "baseline": 150.0,
        "unit": "ms",
        "metric_type": "latency_ms",
    },
    "api-gateway": {
        "service": "api-gateway",
        "type": "error_spike",
        "value": 8.5,
        "baseline": 0.3,
        "unit": "percent",
        "metric_type": "error_rate",
    },
}


class BackgroundWorker:
    def __init__(self, poll_seconds: int = 5, window_size: int = 20, z_threshold: float = 3.0):
        self.poll_seconds = poll_seconds
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.windows = defaultdict(lambda: deque(maxlen=window_size))
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._scheduled_signal: dict | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="sentinel-background-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def schedule_payment_spike(self, delay_seconds: int = 30) -> dict:
        return self.schedule_demo_signal("payments", "error_spike", delay_seconds=delay_seconds)

    def schedule_demo_signal(
        self,
        service: str = "payments",
        signal_type: str | None = None,
        delay_seconds: int = 30,
    ) -> dict:
        scenario = DEMO_SCENARIOS.get(service)
        if not scenario:
            raise ValueError(f"Unknown demo service: {service}")
        if signal_type and scenario["type"] != signal_type:
            matches = [item for item in DEMO_SCENARIOS.values() if item["service"] == service and item["type"] == signal_type]
            if not matches:
                raise ValueError(f"Unknown demo scenario: {service}/{signal_type}")
            scenario = matches[0]
        with self._lock:
            spike_at = utc_now() + timedelta(seconds=delay_seconds)
            self._scheduled_signal = {**scenario, "spike_at": spike_at}
        return {
            "status": "scheduled",
            "service": scenario["service"],
            "signal_type": scenario["type"],
            "spike_at": spike_at.isoformat(),
        }

    def state(self) -> dict:
        with self._lock:
            scheduled = dict(self._scheduled_signal) if self._scheduled_signal else None
            if scheduled and scheduled.get("spike_at"):
                scheduled["spike_at"] = scheduled["spike_at"].isoformat()
            payment_spike_at = (
                scheduled["spike_at"]
                if scheduled and scheduled.get("service") == "payments" and scheduled.get("type") == "error_spike"
                else None
            )
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "poll_seconds": self.poll_seconds,
            "window_size": self.window_size,
            "z_threshold": self.z_threshold,
            "payment_spike_at": payment_spike_at,
            "scheduled_signal": scheduled,
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
                for metric_type, baseline in [("error_rate", 0.2), ("latency_ms", 150.0)]:
                    scenario = self._pop_due_signal(service, metric_type)
                    value = scenario["value"] if scenario else baseline
                    snapshot = MetricSnapshot(
                        service=service,
                        metric_type=metric_type,
                        value=value,
                        baseline=scenario["baseline"] if scenario else baseline,
                    )
                    db.add(snapshot)
                    db.commit()

                    key = (service, metric_type)
                    window = self.windows[key]
                    z_score = compute_z_score(value, list(window))
                    window.append(value)

                    if scenario or z_score > self.z_threshold:
                        signal = SignalIn(
                            service=service,
                            type=scenario["type"] if scenario else "error_spike",
                            value=value,
                            baseline=scenario["baseline"] if scenario else baseline,
                            unit=scenario["unit"] if scenario else ("percent" if metric_type == "error_rate" else "ms"),
                        )
                        IncidentOrchestrator(db).handle_signal(signal, config)
        finally:
            db.close()

    def _pop_due_signal(self, service: str, metric_type: str) -> dict | None:
        with self._lock:
            scheduled = self._scheduled_signal
            should_spike = (
                scheduled
                and scheduled["service"] == service
                and scheduled["metric_type"] == metric_type
                and utc_now() >= scheduled["spike_at"]
            )
            if should_spike:
                self._scheduled_signal = None
                return scheduled
        return None

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
