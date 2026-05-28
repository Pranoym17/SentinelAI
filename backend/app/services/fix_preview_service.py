from sqlalchemy.orm import Session

from app.models import Incident
from app.services.commander_service import CommanderService
from app.services.github_service import GitHubService
from app.services.openai_service import OpenAIService
from app.services.timeline_service import TimelineService


class FixPreviewService:
    def __init__(self, db: Session):
        self.db = db
        self.github = GitHubService(db)
        self.openai = OpenAIService()
        self.timeline = TimelineService(db)
        self.commander = CommanderService(db)

    def generate(self, incident: Incident) -> dict:
        if incident.fix_preview:
            return {"status": "existing", "fix_preview": incident.fix_preview}

        self.commander.started(
            incident.id,
            "GitHubFixAgent",
            "Generating fix diff preview from incident context and recent commits",
        )
        context = self._context(incident)
        preview = self._generate_preview(incident, context)
        incident.fix_preview = preview
        self.timeline.append(
            incident.id,
            "github_fix_preview_generated",
            f"Generated fix preview: {preview.get('title')}",
            {"fix_preview": preview},
        )
        self.commander.completed(
            incident.id,
            "GitHubFixAgent",
            "Fix diff preview generated",
            {"title": preview.get("title"), "repo": preview.get("repo")},
        )
        self.db.commit()
        self.db.refresh(incident)
        return {"status": "generated", "fix_preview": preview}

    def _context(self, incident: Incident) -> dict:
        repo = self.github.repo_for_service(incident.service)
        recent_commits = self.github.recent_commits_for_service(incident.service, since_minutes=1440)
        return {
            "repo": repo,
            "incident": {
                "id": incident.id,
                "service": incident.service,
                "severity": incident.severity,
                "hypothesis": incident.hypothesis,
                "confidence": incident.confidence,
                "signal_type": incident.signal_type,
                "signal_value": incident.signal_value,
                "reasoning_chain": incident.reasoning_chain or [],
                "recommended_actions": incident.recommended_actions or [],
            },
            "recent_commits": recent_commits,
            "post_mortem": incident.post_mortem,
        }

    def _generate_preview(self, incident: Incident, context: dict) -> dict:
        if self.openai.configured:
            try:
                preview = self.openai.generate_fix_preview(context)
                if preview.get("title") and preview.get("diff"):
                    return self._normalize_preview(preview, context)
            except Exception:
                pass
        return self._fallback_preview(incident, context)

    def _normalize_preview(self, preview: dict, context: dict) -> dict:
        return {
            "title": preview.get("title") or "SentinelAI incident fix",
            "summary": preview.get("summary") or "Proposed fix generated from incident context.",
            "files": preview.get("files") or [],
            "diff": preview.get("diff") or "",
            "confidence": int(preview.get("confidence") or 70),
            "repo": context.get("repo"),
            "source": "openai",
        }

    def _fallback_preview(self, incident: Incident, context: dict) -> dict:
        commits = context.get("recent_commits") or []
        files = commits[0].get("files_changed") if commits else []
        target = next((path for path in (files or []) if path.endswith(".py")), "app/services/sdk_client.py")
        diff = (
            f"diff --git a/{target} b/{target}\n"
            f"--- a/{target}\n"
            f"+++ b/{target}\n"
            "@@\n"
            "-authorization_id = response[\"authorization_id\"]\n"
            "+authorization_id = response.get(\"authorization_id\")\n"
            "+if not authorization_id:\n"
            "+    return {\"status\": \"failed\", \"reason\": \"missing authorization_id\"}\n"
        )
        return {
            "title": "Guard missing authorization_id in payment SDK response",
            "summary": (
                "The recent payment SDK response handling path may assume authorization_id is always present. "
                "This preview adds a guard so partial provider responses fail cleanly."
            ),
            "files": [
                {
                    "path": target,
                    "before_risk": "Direct dictionary access can raise or mis-handle partial provider responses.",
                    "proposed_change": "Use safe access and return a structured failed authorization response.",
                }
            ],
            "diff": diff,
            "confidence": incident.confidence or 70,
            "repo": context.get("repo"),
            "source": "fallback",
        }
