from app.models import Incident, TimelineEvent
from app.services.openai_service import OpenAIService


class PostMortemAgent:
    def __init__(self):
        self.openai = OpenAIService()

    def generate(self, incident: Incident, timeline: list[TimelineEvent]) -> str:
        context = self._context(incident, timeline)
        if self.openai.configured:
            try:
                return self.openai.generate_post_mortem(context)
            except Exception:
                pass
        return self._fallback(incident, timeline)

    def _context(self, incident: Incident, timeline: list[TimelineEvent]) -> dict:
        return {
            "incident": {
                "service": incident.service,
                "severity": incident.severity,
                "status": incident.status,
                "signal_type": incident.signal_type,
                "signal_value": incident.signal_value,
                "hypothesis": incident.hypothesis,
                "confidence": incident.confidence,
                "reasoning_chain": incident.reasoning_chain or [],
                "affected_teams": incident.affected_teams or [],
                "resolution_text": incident.resolution_text,
                "detected_at": incident.detected_at.isoformat(),
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "duration_minutes": incident.duration_minutes,
                "jira_ticket_id": incident.jira_ticket_id,
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

    def _fallback(self, incident: Incident, timeline: list[TimelineEvent]) -> str:
        timeline_lines = "\n".join(
            f"- {event.occurred_at.isoformat()} - {event.description}" for event in timeline
        )
        action_items = "\n".join(
            [
                "- Add automated regression checks for the affected service.",
                "- Tighten deployment monitoring around error-rate changes.",
                "- Document rollback ownership and expected response times.",
            ]
        )
        return (
            f"# INCIDENT POST-MORTEM - {incident.jira_ticket_id or incident.service.upper()}\n\n"
            f"## Summary\n{incident.service} experienced a {incident.signal_type} incident "
            f"with peak signal value {incident.signal_value}. The agent classified it as "
            f"{incident.severity} with {incident.confidence}% confidence.\n\n"
            f"## What happened\n{incident.hypothesis}\n\n"
            f"## Root cause\nThe likely root cause was: {incident.hypothesis}\n\n"
            f"## How it was detected\nSentinelAI detected the anomalous {incident.signal_type} signal automatically.\n\n"
            f"## Resolution\n{incident.resolution_text}\n\n"
            f"## Timeline\n{timeline_lines}\n\n"
            f"## Action items\n{action_items}\n\n"
            "## Lessons learned\nCapturing timeline events during the incident made the post-mortem more complete and immediate.\n"
        )
