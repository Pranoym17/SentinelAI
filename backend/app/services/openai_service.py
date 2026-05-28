import os
import json
import time

from openai import OpenAI
from pydantic import ValidationError

from app.agents.types import INVESTIGATION_JSON_SCHEMA, STATUS_JSON_SCHEMA, InvestigationResult, StatusResult


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

        content = self._completion_json(
            messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an autonomous incident response investigator. "
                            "Use only the provided signal and context. Return valid JSON matching the schema. "
                            "Reference recent GitHub commit SHAs, changed files, runbooks, memory, deploys, and health when present."
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
            schema=INVESTIGATION_JSON_SCHEMA,
        )
        result = InvestigationResult.model_validate_json(content)
        result.raw_model_response = content
        return result

    def generate_status(self, context: dict) -> str:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured")

        content = self._completion_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer incident-status questions for engineering managers. "
                        "Use only the provided incident and timeline. Respond in 2-4 plain English sentences."
                    ),
                },
                {"role": "user", "content": json.dumps(context, indent=2, default=str)},
            ],
            schema=STATUS_JSON_SCHEMA,
        )
        return StatusResult.model_validate_json(content).response

    def generate_post_mortem(self, context: dict) -> str:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write concise professional incident post-mortems in markdown. "
                        "Use only the provided incident data, reasoning chain, and timeline. "
                        "Include Summary, What happened, Root cause, How it was detected, "
                        "Resolution, Timeline, Action items, and Lessons learned."
                    ),
                },
                {"role": "user", "content": json.dumps(context, indent=2, default=str)},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def generate_communication_briefs(self, context: dict) -> dict:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an incident commander. Return JSON only with engineer_brief and manager_brief. "
                        "Engineer brief is technical and mentions evidence. Manager brief is concise, impact/status oriented, "
                        "and avoids unnecessary implementation details. Use only provided context."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "context": context,
                            "schema": {
                                "engineer_brief": "technical summary for engineers, 1-2 sentences",
                                "manager_brief": "plain English status for managers, 1-2 sentences",
                            },
                        },
                        indent=2,
                        default=str,
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=20,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return {
            "engineer_brief": data.get("engineer_brief") or "Engineer brief unavailable.",
            "manager_brief": data.get("manager_brief") or "Manager brief unavailable.",
        }

    def generate_post_mortem_followups(self, context: dict) -> list[dict]:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract prevention follow-up tasks from an incident post-mortem. "
                        "Return JSON only with an items array. Each item has title, reason, and priority. "
                        "Keep titles actionable and under 90 characters."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "context": context,
                            "schema": {
                                "items": [
                                    {
                                        "title": "verb-first follow-up task",
                                        "reason": "why this prevents recurrence",
                                        "priority": "Highest | High | Medium | Low",
                                    }
                                ]
                            },
                        },
                        indent=2,
                        default=str,
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=20,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return data.get("items") or []

    def generate_fix_preview(self, context: dict) -> dict:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You propose a minimal code fix for an incident. Return JSON only. "
                        "Use unified diff format in the diff field. Do not claim the patch was applied. "
                        "Prefer files mentioned in recent commits."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "context": context,
                            "schema": {
                                "title": "short fix title",
                                "summary": "why this fix addresses the incident",
                                "files": [
                                    {
                                        "path": "file path",
                                        "before_risk": "risk in current code",
                                        "proposed_change": "specific change",
                                    }
                                ],
                                "diff": "unified diff preview",
                                "confidence": 0,
                            },
                        },
                        indent=2,
                        default=str,
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=25,
        )
        return json.loads(response.choices[0].message.content or "{}")

    def correlate_incidents(self, context: dict) -> dict:
        if not self.client:
            raise RuntimeError("OpenAI client is not configured")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Decide if incidents are likely correlated. Return compact JSON only.",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "context": context,
                            "schema": {
                                "correlated": "boolean",
                                "root_cause": "string",
                                "evidence": "string",
                            },
                        },
                        indent=2,
                        default=str,
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content or "{}")

    def _completion_json(self, messages: list[dict], schema: dict, attempts: int = 2) -> str:
        last_error = None
        for attempt in range(attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_schema", "json_schema": schema},
                    temperature=0.2,
                    timeout=20,
                )
                content = response.choices[0].message.content or "{}"
                if schema["name"] == "incident_investigation":
                    InvestigationResult.model_validate_json(content)
                elif schema["name"] == "incident_status":
                    StatusResult.model_validate_json(content)
                return content
            except (ValidationError, json.JSONDecodeError, Exception) as exc:
                last_error = exc
                if attempt == attempts - 1:
                    break
                messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": f"Your previous response failed validation: {exc}. Return valid JSON only.",
                    },
                ]
                time.sleep(0.2)
        raise RuntimeError(f"OpenAI JSON response failed after {attempts} attempt(s): {last_error}")
