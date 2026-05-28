from datetime import timedelta

from sqlalchemy.orm import Session

from app.agents.types import InvestigationResult, ReasoningStep
from app.models import HealthCheck, HistoricalIncident, RecentDeploy
from app.schemas import SignalIn
from app.services.github_service import GitHubService
from app.services.openai_service import OpenAIService
from app.services.runbook_service import RunbookService
from app.time_utils import utc_now


class InvestigatorAgent:
    def __init__(self, db: Session):
        self.db = db
        self.openai = OpenAIService()

    def investigate(self, signal: SignalIn) -> tuple[InvestigationResult, int | None]:
        context, matched_incident_id = self._build_context(signal)
        if self.openai.configured:
            try:
                investigation = self.openai.investigate(signal.model_dump(), context)
                return self._calibrate_investigation(signal, investigation, context), matched_incident_id
            except Exception:
                investigation = self._fallback_investigation(signal, context)
                return self._calibrate_investigation(signal, investigation, context), matched_incident_id
        investigation = self._fallback_investigation(signal, context)
        return self._calibrate_investigation(signal, investigation, context), matched_incident_id

    def _build_context(self, signal: SignalIn) -> tuple[dict, int | None]:
        cutoff = utc_now() - timedelta(minutes=60)
        recent_deploys = (
            self.db.query(RecentDeploy)
            .filter(
                RecentDeploy.service.contains(signal.service),
                RecentDeploy.deployed_at >= cutoff,
            )
            .order_by(RecentDeploy.deployed_at.desc())
            .limit(5)
            .all()
        )
        past_incidents = (
            self.db.query(HistoricalIncident)
            .filter(
                HistoricalIncident.service == signal.service,
                HistoricalIncident.signal_type == signal.type,
            )
            .order_by(HistoricalIncident.occurred_at.desc())
            .limit(3)
            .all()
        )
        health_checks = (
            self.db.query(HealthCheck)
            .order_by(HealthCheck.checked_at.desc())
            .limit(10)
            .all()
        )
        matching_runbooks = RunbookService(self.db).matching(signal.service, signal.type, mark_used=True)
        recent_commits = GitHubService(self.db).recent_commits_for_service(signal.service, since_minutes=60)
        matched_incident_id = past_incidents[0].id if past_incidents else None

        context = {
            "recent_deploys": [
                {
                    "service": deploy.service,
                    "version": deploy.version,
                    "author": deploy.author,
                    "minutes_ago": int((utc_now() - deploy.deployed_at).total_seconds() / 60),
                    "changes_summary": deploy.changes_summary,
                }
                for deploy in recent_deploys
            ],
            "past_incidents": [
                {
                    "id": incident.id,
                    "root_cause": incident.root_cause,
                    "resolution": incident.resolution,
                    "duration_minutes": incident.duration_minutes,
                }
                for incident in past_incidents
            ],
            "health_checks": [
                {
                    "service": check.service,
                    "status": check.status,
                    "latency_ms": check.latency_ms,
                }
                for check in health_checks
            ],
            "runbooks": [
                {
                    "id": runbook.id,
                    "title": runbook.title,
                    "steps": runbook.steps or [],
                    "times_used": runbook.times_used,
                    "times_successful": runbook.times_successful,
                }
                for runbook in matching_runbooks
            ],
            "recent_commits": recent_commits,
        }
        return context, matched_incident_id

    def _fallback_investigation(self, signal: SignalIn, context: dict) -> InvestigationResult:
        confidence = 30
        reasoning_chain = [
            {
                "step": "SIGNAL DETECTED",
                "detail": f"{signal.service} {signal.type} is {signal.value} vs baseline {signal.baseline}.",
                "confidence": confidence,
            }
        ]

        if context["past_incidents"]:
            confidence += 25
            match = context["past_incidents"][0]
            reasoning_chain.append(
                {
                    "step": "CHECKING MEMORY",
                    "detail": f"Found matching incident #{match['id']}: {match['root_cause']}",
                    "confidence": confidence,
                }
            )
        else:
            reasoning_chain.append(
                {
                    "step": "CHECKING MEMORY",
                    "detail": "No matching historical incident found.",
                    "confidence": confidence,
                }
            )

        if context["recent_deploys"]:
            confidence += 25
            deploy = context["recent_deploys"][0]
            reasoning_chain.append(
                {
                    "step": "CHECKING DEPLOYS",
                    "detail": (
                        f"{deploy['service']} {deploy['version']} was deployed "
                        f"{deploy['minutes_ago']} minutes ago: {deploy['changes_summary']}"
                    ),
                    "confidence": confidence,
                }
            )
        else:
            reasoning_chain.append(
                {
                    "step": "CHECKING DEPLOYS",
                    "detail": "No recent deploy found in the last 60 minutes.",
                    "confidence": confidence,
                }
            )

        if context.get("recent_commits"):
            commit = context["recent_commits"][0]
            changed = ", ".join(commit.get("files_changed") or []) or "files unavailable"
            reasoning_chain.append(
                {
                    "step": "CHECKING COMMITS",
                    "detail": f"Recent commit {commit['sha']} by {commit.get('author')}: {commit['message']} ({changed})",
                    "confidence": confidence,
                }
            )

        if context.get("runbooks"):
            runbook = context["runbooks"][0]
            reasoning_chain.append(
                {
                    "step": "CHECKING RUNBOOKS",
                    "detail": f"Found runbook '{runbook['title']}' with steps: {', '.join(runbook['steps'][:3])}",
                    "confidence": confidence,
                }
            )

        healthy_dependencies = all(check["status"] == "healthy" for check in context["health_checks"])
        if healthy_dependencies and context["health_checks"]:
            confidence += 15
            health_detail = "Dependencies are healthy, making an app-layer regression more likely."
        else:
            health_detail = "Dependency health is degraded or unknown."

        confidence = min(confidence, 95)
        severity = "SEV-1" if signal.type == "error_spike" and signal.value >= 10 else "SEV-2"
        reasoning_chain.append(
            {
                "step": "CHECKING HEALTH",
                "detail": health_detail,
                "confidence": confidence,
            }
        )
        reasoning_chain.append(
            {
                "step": "HYPOTHESIS",
                "detail": f"Likely regression affecting {signal.service}. Confidence: {confidence}%.",
                "confidence": confidence,
            }
        )

        return InvestigationResult(
            reasoning_chain=reasoning_chain,
            hypothesis=f"Likely regression affecting {signal.service}, correlated with recent deploy or known pattern.",
            confidence=confidence,
            severity=severity,
            affected_teams=[signal.service, "platform"],
            recommended_actions=[
                *([f"Follow runbook: {context['runbooks'][0]['title']}"] if context.get("runbooks") else []),
                f"Review recent {signal.service} deploys",
                "Check exception logs",
                "Prepare rollback if errors remain elevated",
            ],
        )

    def _calibrate_investigation(
        self,
        signal: SignalIn,
        investigation: InvestigationResult,
        context: dict,
    ) -> InvestigationResult:
        evidence_score = 30
        if context.get("past_incidents"):
            evidence_score += 25
        if context.get("recent_deploys"):
            evidence_score += 25
        if context.get("health_checks") and all(check["status"] == "healthy" for check in context["health_checks"]):
            evidence_score += 10
        if context.get("runbooks"):
            evidence_score += 5
        if context.get("recent_commits"):
            evidence_score += 5

        calibrated = min(95, evidence_score)
        if calibrated > investigation.confidence:
            investigation.confidence = calibrated
            investigation.reasoning_chain.append(
                ReasoningStep(
                    step="EVIDENCE CALIBRATION",
                    detail=(
                        "Seeded incident memory, recent deploy evidence, runbook context, "
                        f"and dependency health support high confidence for {signal.service}."
                    ),
                    confidence=calibrated,
                )
            )

        if signal.type == "error_spike" and signal.value >= 10:
            investigation.severity = "SEV-1"
        elif signal.type == "latency_spike" and signal.value >= 2000 and investigation.severity not in ["SEV-1", "SEV-2"]:
            investigation.severity = "SEV-2"

        if signal.service not in investigation.affected_teams:
            investigation.affected_teams.insert(0, signal.service)

        return investigation
