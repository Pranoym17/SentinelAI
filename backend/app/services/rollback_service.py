import time

from sqlalchemy.orm import Session

from app.models import Config, Incident, MetricSnapshot, RecentDeploy
from app.services.commander_service import CommanderService
from app.services.response_agent import ResponseAgent
from app.services.timeline_service import TimelineService


ROLLBACK_PROFILES = {
    "payments": {
        "stable_version": "v2.4.0",
        "validation": "checkout success rate and payment authorization flow",
        "metric_type": "error_rate",
        "normalized_value": 0.2,
    },
    "auth": {
        "stable_version": "v1.17.4",
        "validation": "login p95 latency and token validation cache hit rate",
        "metric_type": "latency_ms",
        "normalized_value": 150.0,
    },
    "api-gateway": {
        "stable_version": "v3.9.1",
        "validation": "gateway 5xx rate, route matching, and upstream retry behavior",
        "metric_type": "error_rate",
        "normalized_value": 0.2,
    },
}


class RollbackService:
    def __init__(self, db: Session):
        self.db = db
        self.timeline = TimelineService(db)
        self.commander = CommanderService(db)

    def execute(self, incident: Incident, delay_seconds: float = 0.0) -> dict:
        logs = []
        deploy = self._recent_deploy(incident)
        profile = ROLLBACK_PROFILES.get(incident.service, ROLLBACK_PROFILES["payments"])
        deploy_name = deploy.service if deploy else incident.service
        current_version = deploy.version if deploy else "current release"
        target_version = profile["stable_version"]
        metric_type = profile["metric_type"]
        normalized_value = profile["normalized_value"]
        logs_template = [
            f"Checking current {deploy_name} deployment version ({current_version})",
            f"Selected previous stable release {target_version}",
            f"Draining traffic from unhealthy {deploy_name} tasks",
            f"Deploying rollback release to {incident.service}",
            "Warming containers and reattaching health checks",
            f"Validating {profile['validation']}",
            f"Rollback complete; {incident.service} {metric_type} normalized",
        ]
        self.timeline.append(
            incident.id,
            "rollback_started",
            f"Rollback started for {incident.service}",
            {"target_version": target_version, "deploy_service": deploy_name, "current_version": current_version},
        )
        self.commander.started(
            incident.id,
            "RollbackAgent",
            f"Executing rollback for {incident.service}",
            {"target_version": target_version, "deploy_service": deploy_name, "current_version": current_version},
        )
        self._sync_update(incident, "rollback_started", f"Rollback started for {incident.service}")

        for index, line in enumerate(logs_template, start=1):
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            logs.append(line)
            self.timeline.append(
                incident.id,
                "rollback_log",
                line,
                {"line": index, "total": len(logs_template)},
            )

        self.db.add(
            MetricSnapshot(
                service=incident.service,
                metric_type=metric_type,
                value=normalized_value,
                baseline=0.2 if metric_type == "error_rate" else 150.0,
            )
        )
        self.timeline.append(
            incident.id,
            "metrics_normalized",
            f"{incident.service} {metric_type} returned to baseline",
            {"metric_type": metric_type, "value": normalized_value},
        )
        self.timeline.append(
            incident.id,
            "rollback_completed",
            f"Rollback completed for {incident.service}",
        )
        self.commander.completed(
            incident.id,
            "RollbackAgent",
            f"Rollback completed for {incident.service}",
            {"metric_type": metric_type, "value": normalized_value},
        )
        self._sync_update(incident, "rollback_completed", f"Rollback completed for {incident.service}")
        self.db.commit()

        return {
            "status": "completed",
            "incident_id": incident.id,
            "logs": logs,
            "metric": {"service": incident.service, "metric_type": metric_type, "value": normalized_value},
        }

    def _sync_update(self, incident: Incident, event_type: str, description: str) -> None:
        config = self.db.query(Config).order_by(Config.id.desc()).first()
        if not config:
            return
        ResponseAgent(self.db, config).post_timeline_update(incident, event_type, description)

    def _recent_deploy(self, incident: Incident) -> RecentDeploy | None:
        return (
            self.db.query(RecentDeploy)
            .filter(RecentDeploy.service.contains(incident.service))
            .order_by(RecentDeploy.deployed_at.desc())
            .first()
        )
