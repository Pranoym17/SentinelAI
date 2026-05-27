import os
import json

from openai import OpenAI

from app.agents.types import INVESTIGATION_JSON_SCHEMA, InvestigationResult


class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    @property
    def configured(self) -> bool:
        return self.client is not None

    def unavailable_response(self) -> dict:
        return {
            "configured": False,
            "model": self.model,
            "reason": "OPENAI_API_KEY is not configured",
        }

    def investigate(self, signal: dict, context: dict) -> InvestigationResult:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an autonomous incident response investigator. "
                        "Use only the provided signal and context. Return valid JSON matching the schema. "
                        "Confidence should increase when memory, recent deploys, and healthy dependencies corroborate a cause."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "signal": signal,
                            "context": context,
                            "severity_rules": {
                                "SEV-1": "User-facing service is down or severely degraded.",
                                "SEV-2": "Partial degradation or non-critical service affected.",
                                "SEV-3": "Minor issue with low user impact.",
                            },
                        },
                        indent=2,
                        default=str,
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": INVESTIGATION_JSON_SCHEMA,
            },
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return InvestigationResult.model_validate_json(content)
