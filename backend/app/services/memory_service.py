from sqlalchemy.orm import Session

from app.models import HistoricalIncident


class MemoryService:
    def __init__(self, db: Session):
        self.db = db

    def find_matches(self, service: str, signal_type: str, limit: int = 3) -> list[HistoricalIncident]:
        return (
            self.db.query(HistoricalIncident)
            .filter(
                HistoricalIncident.service == service,
                HistoricalIncident.signal_type == signal_type,
            )
            .order_by(HistoricalIncident.occurred_at.desc())
            .limit(limit)
            .all()
        )

    def remember(
        self,
        service: str,
        signal_type: str,
        root_cause: str,
        resolution: str,
        duration_minutes: int,
        occurred_at,
    ) -> HistoricalIncident:
        memory = HistoricalIncident(
            service=service,
            signal_type=signal_type,
            root_cause=root_cause,
            resolution=resolution,
            duration_minutes=duration_minutes,
            occurred_at=occurred_at,
        )
        self.db.add(memory)
        return memory
