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
        template = self._fallback_template(incident)
        target = next(
            (path for path in (files or []) if path == template["path"]),
            next((path for path in (files or []) if path.endswith(".py") and template["hint"] in path), template["path"]),
        )
        diff = template["diff"].format(target=target)
        return {
            "title": template["title"],
            "summary": template["summary"],
            "files": [
                {
                    "path": target,
                    "before_risk": template["before_risk"],
                    "proposed_change": template["proposed_change"],
                }
            ],
            "diff": diff,
            "confidence": incident.confidence or 70,
            "repo": context.get("repo"),
            "source": "fallback",
        }

    def _fallback_template(self, incident: Incident) -> dict:
        key = (incident.service, incident.signal_type)
        templates = {
            ("payments", "error_spike"): {
                "path": "app/services/payment_gateway.py",
                "hint": "payment",
                "title": "Guard missing authorization_id in payment SDK response",
                "summary": (
                    "The recent payment SDK response handling path may assume authorization_id is always present. "
                    "This preview adds a guard so partial provider responses fail cleanly."
                ),
                "before_risk": "Direct dictionary access can raise or mis-handle partial provider responses.",
                "proposed_change": "Use safe access and return a structured failed authorization response.",
                "diff": (
                    "diff --git a/{target} b/{target}\n"
                    "--- a/{target}\n"
                    "+++ b/{target}\n"
                    "@@\n"
                    "-authorization_id = response[\"authorization_id\"]\n"
                    "+authorization_id = response.get(\"authorization_id\")\n"
                    "+if not authorization_id:\n"
                    "+    return {{\"status\": \"failed\", \"reason\": \"missing authorization_id\"}}\n"
                ),
            },
            ("auth", "latency_spike"): {
                "path": "app/services/sdk_client.py",
                "hint": "sdk",
                "title": "Add timeout guard around token introspection cache misses",
                "summary": (
                    "The auth latency spike is consistent with token introspection calls escaping the session cache. "
                    "This preview adds timeout and fallback handling around cache misses."
                ),
                "before_risk": "Cache misses can wait on slow token introspection and amplify login latency.",
                "proposed_change": "Bound token introspection latency and return a retryable auth response when the cache path is saturated.",
                "diff": (
                    "diff --git a/{target} b/{target}\n"
                    "--- a/{target}\n"
                    "+++ b/{target}\n"
                    "@@\n"
                    "-token_state = introspection_client.validate(token)\n"
                    "+token_state = introspection_client.validate(token, timeout_ms=750)\n"
                    "+if token_state.timed_out:\n"
                    "+    return {{\"status\": \"retryable\", \"reason\": \"token_introspection_timeout\"}}\n"
                ),
            },
            ("api-gateway", "error_spike"): {
                "path": "app/routes/checkout.py",
                "hint": "route",
                "title": "Constrain gateway retries for upstream 5xx responses",
                "summary": (
                    "The gateway error spike is consistent with retry middleware amplifying upstream failures. "
                    "This preview adds a circuit-breaker style guard before retrying failing routes."
                ),
                "before_risk": "Aggressive retries can multiply upstream 500 responses and widen customer impact.",
                "proposed_change": "Limit retries for unhealthy upstreams and fail fast once the circuit is open.",
                "diff": (
                    "diff --git a/{target} b/{target}\n"
                    "--- a/{target}\n"
                    "+++ b/{target}\n"
                    "@@\n"
                    "-response = gateway.forward(request, retries=3)\n"
                    "+response = gateway.forward(request, retries=1, circuit_breaker=True)\n"
                    "+if response.circuit_open:\n"
                    "+    return {{\"status\": \"degraded\", \"reason\": \"upstream_circuit_open\"}}\n"
                ),
            },
        }
        return templates.get(
            key,
            {
                "path": "app/services/sdk_client.py",
                "hint": incident.service.split("-")[0],
                "title": f"Add guardrail for {incident.service} {incident.signal_type}",
                "summary": f"Proposed mitigation generated from {incident.service} incident context.",
                "before_risk": "The current path may not handle the incident failure mode explicitly.",
                "proposed_change": "Add bounded failure handling and structured telemetry for this incident class.",
                "diff": (
                    "diff --git a/{target} b/{target}\n"
                    "--- a/{target}\n"
                    "+++ b/{target}\n"
                    "@@\n"
                    "+# SentinelAI guardrail for incident-specific failure handling\n"
                ),
            },
        )
