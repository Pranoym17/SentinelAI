from sqlalchemy.orm import Session

from app.agents.detection_agent import DetectionAgent
from app.agents.investigator_agent import InvestigatorAgent
from app.models import Config, Incident
from app.schemas import SignalIn
from app.services.metrics_service import MetricsService
from app.services.response_agent import ResponseAgent
from app.services.serializers import serialize_incident
from app.services.sla_service import SLAService
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

        existing = self._existing_open_incident(signal)
        if existing:
            existing.signal_value = signal.value
            self.timeline.append(
                existing.id,
                "duplicate_signal",
                f"Additional {signal.type} signal received for {signal.service}: {signal.value}",
                {"baseline": signal.baseline, "unit": signal.unit},
            )
            self.db.commit()
            self.db.refresh(existing)
            return {
                **serialize_incident(existing, self.timeline.get(existing.id)),
                "triggered": True,
                "duplicate": True,
                "actions_taken": [],
                "recommended_actions": [],
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

        sla_prediction = self._apply_sla_prediction(incident, investigation.recommended_actions)
        self.db.commit()
        self.db.refresh(incident)

        actions_taken = ResponseAgent(self.db, config).route(incident, investigation.recommended_actions)
        timeline = self.timeline.get(incident.id)
        return {
            **serialize_incident(incident, timeline),
            "triggered": True,
            "actions_taken": actions_taken,
            "recommended_actions": investigation.recommended_actions,
            "sla_prediction": sla_prediction,
        }

    def _existing_open_incident(self, signal: SignalIn) -> Incident | None:
        return (
            self.db.query(Incident)
            .filter(
                Incident.status == "open",
                Incident.service == signal.service,
                Incident.signal_type == signal.type,
            )
            .order_by(Incident.detected_at.desc())
            .first()
        )

    def _apply_sla_prediction(self, incident: Incident, recommended_actions: list[str]) -> dict:
        prediction = SLAService(self.db).predict_breach(incident.service)

        if prediction["will_breach"]:
            sla_action = f"SLA warning: {prediction['message']}"
            if sla_action not in recommended_actions:
                recommended_actions.insert(0, sla_action)
            self.timeline.append(
                incident.id,
                "sla_warning",
                prediction["message"],
                {
                    "breach_in_minutes": prediction["breach_in_minutes"],
                    "service": incident.service,
                },
            )
            if prediction["breach_in_minutes"] < 30 and incident.severity != "SEV-1":
                previous_severity = incident.severity
                incident.severity = "SEV-1"
                self.timeline.append(
                    incident.id,
                    "severity_escalated",
                    f"Severity escalated from {previous_severity} to SEV-1 due to SLA risk",
                    {"reason": "sla_breach_risk", "previous_severity": previous_severity},
                )

        return prediction
