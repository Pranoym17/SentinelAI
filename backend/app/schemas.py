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


class StatusQueryIn(BaseModel):
    query: str = "What is the status?"
    incident_id: int | None = None
