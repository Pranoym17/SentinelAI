import os

from openai import OpenAI


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
