from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConfigIn(BaseModel):
    services: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    slack_channel: str = "#incidents"
    jira_project_key: str = "INC"


class ConfigOut(ConfigIn):
    id: int


class MetricUpdateIn(BaseModel):
    service: str
    metric_type: str
    value: float
    baseline: float | None = None


class SignalIn(BaseModel):
    service: str
    type: str
    value: float
    baseline: float = 0.2
    unit: str | None = None


class DeploySeedIn(BaseModel):
    service: str
    version: str
    author: str
    deployed_at: datetime
    changes_summary: str = ""


class DeployIn(DeploySeedIn):
    pass


class DeploySeedRequest(BaseModel):
    deploys: list[DeploySeedIn]


class MemorySeedIn(BaseModel):
    service: str
    signal_type: str
    root_cause: str
    resolution: str
    duration_minutes: int
    occurred_at: datetime


class MemorySeedRequest(BaseModel):
    incidents: list[MemorySeedIn]


class ResolveIncidentIn(BaseModel):
    resolution_text: str = Field(min_length=1)


class RollbackIn(BaseModel):
    delay_seconds: float = Field(default=0.0, ge=0.0, le=2.0)


class StatusQueryIn(BaseModel):
    query: str = "What is the status?"
    incident_id: int | None = None


class ServiceIn(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    team: str | None = None
    repo_url: str | None = None
    sla_target: float = 99.9


class OnCallScheduleIn(BaseModel):
    engineer_name: str
    engineer_email: str | None = None
    slack_handle: str | None = None
    team: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool = True


class RunbookIn(BaseModel):
    service: str | None = None
    signal_type: str | None = None
    title: str
    steps: list[str] = Field(default_factory=list)


class IntegrationConfigIn(BaseModel):
    type: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
