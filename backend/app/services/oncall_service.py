from sqlalchemy.orm import Session

from app.models import OnCallSchedule
from app.schemas import OnCallScheduleIn
from app.time_utils import utc_now


class OnCallService:
    def __init__(self, db: Session):
        self.db = db

    def current(self) -> dict:
        now = utc_now()
        oncall = (
            self.db.query(OnCallSchedule)
            .filter(
                OnCallSchedule.is_active.is_(True),
                OnCallSchedule.start_time <= now,
                OnCallSchedule.end_time >= now,
            )
            .order_by(OnCallSchedule.start_time.desc())
            .first()
        )
        return {"oncall": self.serialize(oncall) if oncall else None}

    def create(self, payload: OnCallScheduleIn) -> dict:
        schedule = OnCallSchedule(**payload.model_dump())
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return {"status": "created", "oncall": self.serialize(schedule)}

    def serialize(self, schedule: OnCallSchedule) -> dict:
        return {
            "id": schedule.id,
            "name": schedule.engineer_name,
            "email": schedule.engineer_email,
            "slack_handle": schedule.slack_handle,
            "team": schedule.team,
            "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
            "end_time": schedule.end_time.isoformat() if schedule.end_time else None,
            "is_active": schedule.is_active,
        }
