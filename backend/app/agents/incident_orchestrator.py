from sqlalchemy.orm import Session

from app.agents.detection_agent import DetectionAgent
from app.agents.investigator_agent import InvestigatorAgent
from app.models import Config, Incident
from app.schemas import SignalIn
from app.services.metrics_service import MetricsService
from app.services.response_agent import ResponseAgent
from app.services.serializers import serialize_incident
from app.services.timeline_service import TimelineService


class IncidentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.detection = DetectionAgent()
        self.investigator = InvestigatorAgent(db)
        self.metrics = MetricsService(db)
        self.timeline = TimelineService(db)

    def handle_signal(self, signal: SignalIn, config: Config) -> dict:
        self.metrics.record_signal(signal.service, signal.type, signal.value, signal.baseline)

        if not self.detection.should_trigger(signal, config):
            self.db.commit()
            return {
                "triggered": False,
                "reason": "Signal did not exceed configured thresholds",
                "service": signal.service,
                "signal_type": signal.type,
                "signal_value": signal.value,
            }

        investigation, matched_incident_id = self.investigator.investigate(signal)
        incident = Incident(
            service=signal.service,
            signal_type=signal.type,
            signal_value=signal.value,
            severity=investigation.severity,
            hypothesis=investigation.hypothesis,
            confidence=investigation.confidence,
            reasoning_chain=[step.model_dump() for step in investigation.reasoning_chain],
            affected_teams=investigation.affected_teams,
            matched_past_incident_id=matched_incident_id,
        )
        self.db.add(incident)
        self.db.flush()

        self.timeline.append(
            incident.id,
            "detection",
            f"{signal.type} detected for {signal.service}: {signal.value}",
            {"baseline": signal.baseline, "unit": signal.unit},
        )
        self.timeline.append(
            incident.id,
            "investigation_completed",
            f"Hypothesis formed with {investigation.confidence}% confidence",
            {"recommended_actions": investigation.recommended_actions},
        )
        self.db.commit()
        self.db.refresh(incident)

        actions_taken = ResponseAgent(self.db, config).route(incident)
        timeline = self.timeline.get(incident.id)
        return {
            **serialize_incident(incident, timeline),
            "triggered": True,
            "actions_taken": actions_taken,
            "recommended_actions": investigation.recommended_actions,
        }
