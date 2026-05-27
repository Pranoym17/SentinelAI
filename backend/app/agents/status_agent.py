from app.models import Incident, TimelineEvent
from app.services.openai_service import OpenAIService
from app.time_utils import utc_now


class StatusAgent:
    def __init__(self):
        self.openai = OpenAIService()

    def answer(self, query: str, incident: Incident, timeline: list[TimelineEvent]) -> str:
        context = self._context(query, incident, timeline)
        if self.openai.configured:
            try:
                return self.openai.generate_status(context)
            except Exception:
                pass
        return self._fallback(incident)

    def _context(self, query: str, incident: Incident, timeline: list[TimelineEvent]) -> dict:
        duration = int((utc_now() - incident.detected_at).total_seconds() / 60)
        return {
            "query": query,
            "incident": {
                "service": incident.service,
                "severity": incident.severity,
                "status": incident.status,
                "duration_minutes": duration,
                "hypothesis": incident.hypothesis,
                "confidence": incident.confidence,
                "jira_ticket_id": incident.jira_ticket_id,
                "jira_ticket_url": incident.jira_ticket_url,
            },
            "timeline": [
                {
                    "event_type": event.event_type,
                    "description": event.description,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in timeline
            ],
        }

    def _fallback(self, incident: Incident) -> str:
        duration = int((utc_now() - incident.detected_at).total_seconds() / 60)
        return (
            f"{incident.service} incident is {incident.status} at {incident.severity}. "
            f"It has been open for {duration} minutes. "
            f"Current hypothesis: {incident.hypothesis} "
            f"Confidence is {incident.confidence}%. "
            "Next expected update is after the response action or rollback step completes."
        )
