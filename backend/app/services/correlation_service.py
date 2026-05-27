from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Incident, Service
from app.schemas import SignalIn
from app.time_utils import utc_now


class CorrelationService:
    def __init__(self, db: Session):
        self.db = db

    def find(self, signal: SignalIn) -> dict:
        window_start = utc_now() - timedelta(minutes=5)
        recent_incidents = (
            self.db.query(Incident)
            .filter(Incident.status == "open", Incident.detected_at >= window_start)
            .order_by(Incident.detected_at)
            .all()
        )
        if not recent_incidents:
            return {"correlated": False}

        signal_service = self.db.query(Service).filter(Service.name == signal.service).first()
        signal_dependencies = set(signal_service.dependencies or []) if signal_service else set()

        for incident in recent_incidents:
            if incident.service == signal.service and incident.signal_type == signal.type:
                continue

            incident_service = self.db.query(Service).filter(Service.name == incident.service).first()
            incident_dependencies = set(incident_service.dependencies or []) if incident_service else set()
            shared_dependencies = sorted(signal_dependencies.intersection(incident_dependencies))
            same_signal_type = incident.signal_type == signal.type

            if shared_dependencies or same_signal_type:
                affected_services = sorted({incident.service, signal.service})
                evidence = []
                if shared_dependencies:
                    evidence.append(f"shared dependencies: {', '.join(shared_dependencies)}")
                if same_signal_type:
                    evidence.append(f"same signal type: {signal.type}")

                root_cause = (
                    f"Possible shared dependency issue involving {', '.join(shared_dependencies)}"
                    if shared_dependencies
                    else f"Multiple services reported {signal.type} within five minutes"
                )
                return {
                    "correlated": True,
                    "primary_incident_id": incident.id,
                    "root_cause": root_cause,
                    "evidence": "; ".join(evidence),
                    "affected_services": affected_services,
                }

        return {"correlated": False}
