from sqlalchemy.orm import Session

from app.models import Incident
from app.services.commander_service import CommanderService
from app.services.jira_service import JiraService
from app.services.openai_service import OpenAIService
from app.services.timeline_service import TimelineService


class PostMortemFollowupService:
    def __init__(self, db: Session, jira: JiraService | None = None):
        self.db = db
        self.openai = OpenAIService()
        self.timeline = TimelineService(db)
        self.commander = CommanderService(db)
        self.jira = jira or JiraService()

    def create_followups(self, incident: Incident) -> dict:
        self.commander.started(
            incident.id,
            "PostMortemAgent",
            "Extracting prevention follow-up tasks",
        )
        items = self._extract_items(incident)
        if not items:
            self.timeline.append(
                incident.id,
                "jira_followups_skipped",
                "No post-mortem follow-up tasks were generated",
            )
            self.commander.completed(
                incident.id,
                "PostMortemAgent",
                "No prevention tasks generated",
            )
            return {"created": False, "items": [], "reason": "No follow-up items generated"}

        actions = [item["title"] for item in items]
        result = self.jira.create_subtasks(incident, actions)
        created = [item for item in result.get("subtasks", []) if item.get("created")]
        if created:
            self.timeline.append(
                incident.id,
                "jira_followups_created",
                f"Created {len(created)} Jira post-mortem follow-up task(s)",
                {"items": items, "subtasks": created},
            )
            self.commander.completed(
                incident.id,
                "PostMortemAgent",
                f"Created {len(created)} prevention follow-up task(s)",
                {"items": items},
            )
        else:
            self.timeline.append(
                incident.id,
                "jira_followups_failed",
                result.get("reason", "Jira follow-up task creation failed"),
                {"items": items, "subtasks": result.get("subtasks", [])},
            )
            self.commander.failed(
                incident.id,
                "PostMortemAgent",
                "Could not create Jira prevention follow-up tasks",
                {"items": items},
            )
        self.db.flush()
        return {"created": bool(created), "items": items, "jira": result}

    def _extract_items(self, incident: Incident) -> list[dict]:
        context = {
            "incident": {
                "service": incident.service,
                "severity": incident.severity,
                "hypothesis": incident.hypothesis,
                "resolution_text": incident.resolution_text,
                "recommended_actions": incident.recommended_actions or [],
                "reasoning_chain": incident.reasoning_chain or [],
            },
            "post_mortem": incident.post_mortem,
        }
        if self.openai.configured:
            try:
                items = self.openai.generate_post_mortem_followups(context)
                if items:
                    return self._normalize(items)
            except Exception:
                pass
        return self._fallback_items(incident)

    def _normalize(self, items: list[dict]) -> list[dict]:
        normalized = []
        for item in items[:5]:
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            normalized.append(
                {
                    "title": title[:90],
                    "reason": str(item.get("reason") or "Prevents recurrence of this incident.").strip(),
                    "priority": str(item.get("priority") or "High").strip(),
                }
            )
        return normalized

    def _fallback_items(self, incident: Incident) -> list[dict]:
        service = incident.service
        return [
            {
                "title": f"Add regression test for {service} incident path",
                "reason": "Prevents the same failure mode from shipping again.",
                "priority": "High",
            },
            {
                "title": f"Add alert for {service} SDK response parsing failures",
                "reason": "Detects this class of failure before customer impact grows.",
                "priority": "High",
            },
            {
                "title": f"Update {service} rollback runbook with verified resolution",
                "reason": "Captures the mitigation used during this incident.",
                "priority": "Medium",
            },
        ]
