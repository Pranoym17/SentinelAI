import time

from sqlalchemy.orm import Session

from app.models import Incident, MetricSnapshot
from app.services.timeline_service import TimelineService


ROLLBACK_LOGS = [
    "Checking current payments-api deployment version",
    "Selected previous stable release v2.4.0",
    "Draining traffic from unhealthy payments-api tasks",
    "Deploying rollback release to production",
    "Warming containers and reattaching health checks",
    "Validating checkout success rate and payment authorization flow",
    "Rollback complete; payments error rate normalized",
]


class RollbackService:
    def __init__(self, db: Session):
        self.db = db
        self.timeline = TimelineService(db)

    def execute(self, incident: Incident, delay_seconds: float = 0.0) -> dict:
        logs = []
        self.timeline.append(
            incident.id,
            "rollback_started",
            f"Rollback started for {incident.service}",
            {"target_version": "v2.4.0"},
        )

        for index, line in enumerate(ROLLBACK_LOGS, start=1):
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            logs.append(line)
            self.timeline.append(
                incident.id,
                "rollback_log",
                line,
                {"line": index, "total": len(ROLLBACK_LOGS)},
            )

        self.db.add(
            MetricSnapshot(
                service=incident.service,
                metric_type="error_rate",
                value=0.2,
                baseline=0.2,
            )
        )
        self.timeline.append(
            incident.id,
            "metrics_normalized",
            f"{incident.service} error_rate returned to 0.2%",
            {"metric_type": "error_rate", "value": 0.2},
        )
        self.timeline.append(
            incident.id,
            "rollback_completed",
            f"Rollback completed for {incident.service}",
        )
        self.db.commit()

        return {
            "status": "completed",
            "incident_id": incident.id,
            "logs": logs,
            "metric": {"service": incident.service, "metric_type": "error_rate", "value": 0.2},
        }
