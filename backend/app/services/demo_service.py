from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Config, HealthCheck, HistoricalIncident, Incident, MetricSnapshot, RecentDeploy, TimelineEvent
from app.time_utils import utc_now


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    def reset(self, keep_config: bool = True) -> dict:
        for model in [TimelineEvent, Incident, MetricSnapshot, HealthCheck, HistoricalIncident, RecentDeploy]:
            self.db.query(model).delete()
        if not keep_config:
            self.db.query(Config).delete()
        self.db.commit()
        return {"status": "reset", "keep_config": keep_config}

    def seed_basics(self) -> dict:
        for service in ["database", "redis", "message-queue"]:
            self.db.add(HealthCheck(service=service, status="healthy", latency_ms=12.0))

        for service in ["payments", "auth", "api-gateway"]:
            self.db.add(MetricSnapshot(service=service, metric_type="error_rate", value=0.2, baseline=0.2))
            self.db.add(MetricSnapshot(service=service, metric_type="latency_ms", value=145.0, baseline=150.0))

        self.db.commit()
        return {"status": "seeded", "health_checks": 3, "metric_snapshots": 6}

    def full_seed(self) -> dict:
        self.reset(keep_config=False)
        config = Config(
            services=["payments", "auth", "api-gateway"],
            signals=["error_spike", "latency_spike"],
            actions=["jira", "slack"],
            thresholds={"error_rate": 5, "latency_ms": 2000, "deployment_window_minutes": 60},
            slack_channel="#incidents",
            jira_project_key="INC",
        )
        self.db.add(config)
        self.seed_basics()

        self.db.add(
            RecentDeploy(
                service="payments-api",
                version="v2.4.1",
                author="devops",
                deployed_at=utc_now() - timedelta(minutes=14),
                changes_summary="Updated payments SDK to v3.2.0",
            )
        )
        self.db.add(
            HistoricalIncident(
                service="payments",
                signal_type="error_spike",
                root_cause="Failed deploy introduced null pointer in payments module",
                resolution="Rollback to previous version",
                duration_minutes=34,
                occurred_at=datetime(2026, 3, 3, 14, 0, 0),
            )
        )
        self.db.commit()
        return {"status": "seeded", "config_id": config.id}
