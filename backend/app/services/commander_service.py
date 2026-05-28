from sqlalchemy.orm import Session

from app.models import Incident
from app.services.openai_service import OpenAIService
from app.services.timeline_service import TimelineService


class CommanderService:
    def __init__(self, db: Session):
        self.db = db
        self.timeline = TimelineService(db)
        self.openai = OpenAIService()

    def started(self, incident_id: int, agent: str, message: str, metadata: dict | None = None) -> None:
        self.timeline.append(
            incident_id,
            "agent_started",
            f"{agent}: {message}",
            {"agent": agent, "status": "running", **(metadata or {})},
        )

    def completed(self, incident_id: int, agent: str, message: str, metadata: dict | None = None) -> None:
        self.timeline.append(
            incident_id,
            "agent_completed",
            f"{agent}: {message}",
            {"agent": agent, "status": "completed", **(metadata or {})},
        )

    def failed(self, incident_id: int, agent: str, message: str, metadata: dict | None = None) -> None:
        self.timeline.append(
            incident_id,
            "agent_failed",
            f"{agent}: {message}",
            {"agent": agent, "status": "failed", **(metadata or {})},
        )

    def communication_briefs(self, incident: Incident, timeline: list | None = None) -> dict:
        context = {
            "incident": {
                "service": incident.service,
                "severity": incident.severity,
                "confidence": incident.confidence,
                "hypothesis": incident.hypothesis,
                "affected_teams": incident.affected_teams or [],
                "recommended_actions": incident.recommended_actions or [],
                "jira_ticket_id": incident.jira_ticket_id,
                "jira_ticket_url": incident.jira_ticket_url,
            },
            "reasoning_chain": incident.reasoning_chain or [],
            "timeline": [
                {
                    "event_type": event.event_type,
                    "description": event.description,
                    "metadata": event.event_metadata or {},
                }
                for event in (timeline or [])
            ],
        }
        if self.openai.configured:
            try:
                return self.openai.generate_communication_briefs(context)
            except Exception:
                pass
        return self._fallback_briefs(incident)

    def append_briefs(self, incident: Incident, briefs: dict) -> None:
        self.timeline.append(
            incident.id,
            "communication_briefs_generated",
            "Generated engineer and manager incident briefs",
            {
                "agent": "CommanderAgent",
                "engineer_brief": briefs.get("engineer_brief"),
                "manager_brief": briefs.get("manager_brief"),
            },
        )

    def _fallback_briefs(self, incident: Incident) -> dict:
        confidence = f"{incident.confidence}%" if incident.confidence is not None else "unknown confidence"
        return {
            "engineer_brief": (
                f"{incident.service} is in {incident.severity or 'incident'} state. "
                f"{incident.hypothesis or 'Root cause is still under investigation'} "
                f"Confidence: {confidence}."
            ),
            "manager_brief": (
                f"{incident.service} is degraded. SentinelAI has coordinated response actions "
                f"and is tracking the incident in Jira and Slack where configured."
            ),
        }
