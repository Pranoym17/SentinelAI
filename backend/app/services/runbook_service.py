from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Incident, RunbookLibrary
from app.schemas import RunbookIn
from app.time_utils import utc_now


class RunbookService:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> dict:
        runbooks = self.db.query(RunbookLibrary).order_by(RunbookLibrary.times_used.desc()).all()
        return {"runbooks": [self.serialize(runbook) for runbook in runbooks]}

    def create(self, payload: RunbookIn) -> dict:
        runbook = RunbookLibrary(**payload.model_dump())
        self.db.add(runbook)
        self.db.commit()
        self.db.refresh(runbook)
        return {"status": "created", "runbook": self.serialize(runbook)}

    def matching(self, service: str, signal_type: str, mark_used: bool = False) -> list[RunbookLibrary]:
        runbooks = (
            self.db.query(RunbookLibrary)
            .filter(
                (RunbookLibrary.service == service) | (RunbookLibrary.service.is_(None)),
                (RunbookLibrary.signal_type == signal_type) | (RunbookLibrary.signal_type.is_(None)),
            )
            .order_by(RunbookLibrary.times_successful.desc(), RunbookLibrary.times_used.desc())
            .limit(3)
            .all()
        )
        if mark_used:
            for runbook in runbooks:
                runbook.times_used += 1
                runbook.last_used_at = utc_now()
        return runbooks

    def mark_successful(self, service: str, signal_type: str) -> list[RunbookLibrary]:
        runbooks = self.matching(service, signal_type, mark_used=False)
        for runbook in runbooks:
            runbook.times_successful += 1
        return runbooks

    def create_or_update_from_incident(self, incident: Incident) -> RunbookLibrary:
        runbook = (
            self.db.query(RunbookLibrary)
            .filter(RunbookLibrary.service == incident.service, RunbookLibrary.signal_type == incident.signal_type)
            .order_by(RunbookLibrary.created_at.desc())
            .first()
        )
        steps = self._steps_from_incident(incident)
        if runbook:
            existing_steps = runbook.steps or []
            runbook.steps = [*existing_steps, *[step for step in steps if step not in existing_steps]]
        else:
            runbook = RunbookLibrary(
                service=incident.service,
                signal_type=incident.signal_type,
                title=f"{incident.service} {incident.signal_type.replace('_', ' ')} response",
                steps=steps,
            )
            self.db.add(runbook)

        runbook.times_successful = (runbook.times_successful or 0) + 1
        runbook.times_used = runbook.times_used or 0
        runbook.last_used_at = utc_now()
        return runbook

    def _steps_from_incident(self, incident: Incident) -> list[str]:
        actions = incident.recommended_actions or []
        steps = [action for action in actions if not action.lower().startswith("sla warning")]
        if incident.resolution_text:
            steps.append(f"Resolution used: {incident.resolution_text}")
        if not steps:
            steps = [
                f"Review {incident.service} telemetry for {incident.signal_type}",
                "Check recent deploys and commits",
                "Apply the verified mitigation and confirm metrics return to baseline",
            ]
        return steps[:8]

    def serialize(self, runbook: RunbookLibrary) -> dict:
        success_rate = round(runbook.times_successful / runbook.times_used * 100) if runbook.times_used else 0
        return {
            "id": runbook.id,
            "service": runbook.service,
            "signal_type": runbook.signal_type,
            "title": runbook.title,
            "steps": runbook.steps or [],
            "times_used": runbook.times_used,
            "times_successful": runbook.times_successful,
            "success_rate": success_rate,
            "created_at": runbook.created_at.isoformat() if runbook.created_at else None,
            "last_used_at": runbook.last_used_at.isoformat() if runbook.last_used_at else None,
        }
