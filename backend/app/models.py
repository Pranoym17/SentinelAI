from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base
from app.time_utils import utc_now


class Config(Base):
    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    services: Mapped[list[str]] = mapped_column(JSON, default=list)
    signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict)
    slack_channel: Mapped[str | None] = mapped_column(String, nullable=True)
    jira_project_key: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String, default="open")
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    service: Mapped[str] = mapped_column(String, index=True)
    signal_type: Mapped[str] = mapped_column(String)
    signal_value: Mapped[float] = mapped_column(Float)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_chain: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    recommended_actions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    raw_model_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_teams: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    jira_ticket_id: Mapped[str | None] = mapped_column(String, nullable=True)
    jira_ticket_url: Mapped[str | None] = mapped_column(String, nullable=True)
    slack_message_ts: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_mortem: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_past_incident_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    event_type: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class HistoricalIncident(Base):
    __tablename__ = "historical_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service: Mapped[str] = mapped_column(String, index=True)
    signal_type: Mapped[str] = mapped_column(String)
    root_cause: Mapped[str] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)


class RecentDeploy(Base):
    __tablename__ = "recent_deploys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    changes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service: Mapped[str] = mapped_column(String, index=True)
    metric_type: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[float] = mapped_column(Float)
    baseline: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[float] = mapped_column(Float)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    team: Mapped[str | None] = mapped_column(String, nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    sla_target: Mapped[float] = mapped_column(Float, default=99.9)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class SLARecord(Base):
    __tablename__ = "sla_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service: Mapped[str] = mapped_column(String, nullable=False, index=True)
    month: Mapped[str] = mapped_column(String, index=True)
    target_uptime: Mapped[float] = mapped_column(Float, default=99.9)
    actual_uptime: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_downtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    incident_count: Mapped[int] = mapped_column(Integer, default=0)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class OnCallSchedule(Base):
    __tablename__ = "on_call_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    engineer_name: Mapped[str] = mapped_column(String, nullable=False)
    engineer_email: Mapped[str | None] = mapped_column(String, nullable=True)
    slack_handle: Mapped[str | None] = mapped_column(String, nullable=True)
    team: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RunbookLibrary(Base):
    __tablename__ = "runbook_library"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    signal_type: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    times_successful: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    integration_type: Mapped[str] = mapped_column(String, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
