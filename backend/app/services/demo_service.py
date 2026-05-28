from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Config,
    HealthCheck,
    HistoricalIncident,
    Incident,
    MetricSnapshot,
    OnCallSchedule,
    RecentDeploy,
    RunbookLibrary,
    Service,
    SLARecord,
    TimelineEvent,
)
from app.services.deploy_service import DeployService
from app.services.integration_service import IntegrationService
from app.services.metrics_service import MetricsService
from app.services.serializers import serialize_incident, serialize_timeline
from app.time_utils import utc_now


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    def reset(self, keep_config: bool = True) -> dict:
        for model in [
            TimelineEvent,
            Incident,
            MetricSnapshot,
            HealthCheck,
            HistoricalIncident,
            RecentDeploy,
            SLARecord,
            RunbookLibrary,
            OnCallSchedule,
            Service,
        ]:
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
        self._seed_service_catalog()
        self._seed_oncall()
        self._seed_runbooks()

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
            RecentDeploy(
                service="auth-service",
                version="v1.18.0",
                author="identity-team",
                deployed_at=utc_now() - timedelta(minutes=22),
                changes_summary="Changed session validation cache and token introspection timeout",
            )
        )
        self.db.add(
            RecentDeploy(
                service="api-gateway",
                version="v3.9.2",
                author="platform",
                deployed_at=utc_now() - timedelta(minutes=36),
                changes_summary="Updated route matching middleware and upstream retry defaults",
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
        self.db.add(
            HistoricalIncident(
                service="auth",
                signal_type="latency_spike",
                root_cause="Token introspection calls saturated after cache policy change",
                resolution="Restored cache TTL and raised connection pool limits",
                duration_minutes=21,
                occurred_at=datetime(2026, 2, 18, 16, 30, 0),
            )
        )
        self.db.add(
            HistoricalIncident(
                service="api-gateway",
                signal_type="error_spike",
                root_cause="Gateway retry middleware amplified upstream 500 responses",
                resolution="Disabled aggressive retry policy and patched route matcher",
                duration_minutes=27,
                occurred_at=datetime(2026, 4, 9, 11, 15, 0),
            )
        )
        self.db.commit()
        return {"status": "seeded", "config_id": config.id}

    def _seed_service_catalog(self) -> None:
        services = [
            Service(
                name="payments",
                display_name="Payments API",
                description="Authorizes checkout payments and provider responses.",
                dependencies=["auth", "database", "redis", "message-queue"],
                team="payments-team",
                repo_url="Pranoym17/payments-api-demo",
                sla_target=99.99,
            ),
            Service(
                name="auth",
                display_name="Auth Service",
                description="Handles login, sessions, token validation, and identity cache.",
                dependencies=["database", "redis"],
                team="identity-team",
                repo_url="Pranoym17/payments-api-demo",
                sla_target=99.95,
            ),
            Service(
                name="api-gateway",
                display_name="API Gateway",
                description="Routes public API traffic to downstream platform services.",
                dependencies=["auth", "payments", "redis"],
                team="platform",
                repo_url="Pranoym17/payments-api-demo",
                sla_target=99.99,
            ),
            Service(
                name="checkout-web",
                display_name="Checkout Web",
                description="Customer checkout frontend that depends on payments and auth.",
                dependencies=["payments", "auth", "api-gateway"],
                team="web-platform",
                repo_url="Pranoym17/payments-api-demo",
                sla_target=99.9,
            ),
            Service(
                name="billing-worker",
                display_name="Billing Worker",
                description="Async billing jobs that consume payment events.",
                dependencies=["payments", "message-queue"],
                team="payments-team",
                repo_url="Pranoym17/payments-api-demo",
                sla_target=99.9,
            ),
        ]
        self.db.add_all(services)

        month = utc_now().strftime("%Y-%m")
        self.db.add_all(
            [
                SLARecord(
                    service="payments",
                    month=month,
                    target_uptime=99.99,
                    actual_uptime=99.995,
                    total_downtime_minutes=2,
                    incident_count=1,
                    sla_breached=False,
                ),
                SLARecord(
                    service="auth",
                    month=month,
                    target_uptime=99.95,
                    actual_uptime=99.98,
                    total_downtime_minutes=8,
                    incident_count=1,
                    sla_breached=False,
                ),
                SLARecord(
                    service="api-gateway",
                    month=month,
                    target_uptime=99.99,
                    actual_uptime=99.996,
                    total_downtime_minutes=1,
                    incident_count=1,
                    sla_breached=False,
                ),
            ]
        )

    def _seed_oncall(self) -> None:
        now = utc_now()
        self.db.add_all(
            [
                OnCallSchedule(
                    engineer_name="Maya Chen",
                    engineer_email="maya@example.com",
                    slack_handle="@maya",
                    team="payments",
                    start_time=now - timedelta(hours=2),
                    end_time=now + timedelta(hours=10),
                ),
                OnCallSchedule(
                    engineer_name="Noah Patel",
                    engineer_email="noah@example.com",
                    slack_handle="@noah",
                    team="auth",
                    start_time=now - timedelta(hours=2),
                    end_time=now + timedelta(hours=10),
                ),
                OnCallSchedule(
                    engineer_name="Avery Smith",
                    engineer_email="avery@example.com",
                    slack_handle="@avery",
                    team="api-gateway",
                    start_time=now - timedelta(hours=2),
                    end_time=now + timedelta(hours=10),
                ),
            ]
        )

    def _seed_runbooks(self) -> None:
        self.db.add_all(
            [
                RunbookLibrary(
                    service="payments",
                    signal_type="error_spike",
                    title="Payments checkout error response",
                    steps=[
                        "Inspect recent payments-api deploy and SDK response parsing changes",
                        "Verify provider authorization response shape",
                        "Rollback payments-api if checkout errors remain elevated",
                    ],
                    times_used=4,
                    times_successful=3,
                ),
                RunbookLibrary(
                    service="auth",
                    signal_type="latency_spike",
                    title="Auth latency and token cache response",
                    steps=[
                        "Check token introspection latency and identity cache hit rate",
                        "Restore previous session cache TTL if login latency remains high",
                        "Validate login p95 latency returns below threshold",
                    ],
                    times_used=3,
                    times_successful=3,
                ),
                RunbookLibrary(
                    service="api-gateway",
                    signal_type="error_spike",
                    title="Gateway routing error response",
                    steps=[
                        "Inspect recent route matcher and retry policy changes",
                        "Disable aggressive upstream retry rules if errors amplify",
                        "Confirm gateway 5xx rate and downstream health normalize",
                    ],
                    times_used=2,
                    times_successful=2,
                ),
            ]
        )

    def state(self) -> dict:
        from app.background_worker import worker

        active_incident = (
            self.db.query(Incident)
            .filter(Incident.status == "open")
            .order_by(Incident.detected_at.desc())
            .first()
        )
        timeline_events = []
        if active_incident:
            timeline_events = (
                self.db.query(TimelineEvent)
                .filter(TimelineEvent.incident_id == active_incident.id)
                .order_by(TimelineEvent.occurred_at)
                .all()
            )
        else:
            timeline_events = self.db.query(TimelineEvent).order_by(TimelineEvent.occurred_at.desc()).limit(10).all()
            timeline_events = list(reversed(timeline_events))

        return {
            "worker": worker.state(),
            "metrics": MetricsService(self.db).latest()["metrics"],
            "active_incident": serialize_incident(active_incident, timeline_events) if active_incident else None,
            "recent_deploys": DeployService(self.db).list(limit=10)["deploys"],
            "integrations": IntegrationService(self.db).status(),
            "timeline": [serialize_timeline(event) for event in timeline_events],
        }
