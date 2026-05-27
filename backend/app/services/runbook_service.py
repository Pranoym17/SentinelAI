from sqlalchemy.orm import Session

from app.models import RunbookLibrary
from app.schemas import RunbookIn


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
