from pydantic import BaseModel, Field


class ReasoningStep(BaseModel):
    step: str
    detail: str
    confidence: int = Field(ge=0, le=100)


class InvestigationResult(BaseModel):
    reasoning_chain: list[ReasoningStep]
    hypothesis: str
    confidence: int = Field(ge=0, le=100)
    severity: str
    affected_teams: list[str]
    recommended_actions: list[str]


class StatusResult(BaseModel):
    response: str


STATUS_JSON_SCHEMA = {
    "name": "incident_status",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "response": {"type": "string"},
        },
        "required": ["response"],
    },
    "strict": True,
}


INVESTIGATION_JSON_SCHEMA = {
    "name": "incident_investigation",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "reasoning_chain": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "step": {"type": "string"},
                        "detail": {"type": "string"},
                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                    },
                    "required": ["step", "detail", "confidence"],
                },
            },
            "hypothesis": {"type": "string"},
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "severity": {"type": "string", "enum": ["SEV-1", "SEV-2", "SEV-3"]},
            "affected_teams": {"type": "array", "items": {"type": "string"}},
            "recommended_actions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "reasoning_chain",
            "hypothesis",
            "confidence",
            "severity",
            "affected_teams",
            "recommended_actions",
        ],
    },
    "strict": True,
}
