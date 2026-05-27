from sqlalchemy.orm import Session

from app.models import TimelineEvent


class TimelineService:
    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        incident_id: int,
        event_type: str,
        description: str,
        metadata: dict | None = None,
    ) -> TimelineEvent:
        event = TimelineEvent(
            incident_id=incident_id,
            event_type=event_type,
            description=description,
            event_metadata=metadata,
        )
        self.db.add(event)
        return event

    def get(self, incident_id: int) -> list[TimelineEvent]:
        return (
            self.db.query(TimelineEvent)
            .filter(TimelineEvent.incident_id == incident_id)
            .order_by(TimelineEvent.occurred_at)
            .all()
        )
