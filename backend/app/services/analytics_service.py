from sqlalchemy.orm import Session

from app.models import Incident, SLARecord


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict:
        resolved = self.db.query(Incident).filter(Incident.status == "resolved").all()
        active_count = self.db.query(Incident).filter(Incident.status == "open").count()
        by_service = {}
        by_severity = {}
        mttr_by_service = {}
        for incident in resolved:
            by_service[incident.service] = by_service.get(incident.service, 0) + 1
            by_severity[incident.severity or "unknown"] = by_severity.get(incident.severity or "unknown", 0) + 1
            mttr_by_service.setdefault(incident.service, []).append(incident.duration_minutes or 0)

        mttr = 0
        if resolved:
            mttr = sum(incident.duration_minutes or 0 for incident in resolved) / len(resolved)

        records = self.db.query(SLARecord).all()
        if records:
            compliant = len([record for record in records if not record.sla_breached])
            sla_compliance = round(compliant / len(records) * 100, 1)
        else:
            sla_compliance = 100.0
        sla_breach_history = [
            {
                "service": record.service,
                "month": record.month,
                "target_uptime": record.target_uptime,
                "actual_uptime": record.actual_uptime,
                "total_downtime_minutes": record.total_downtime_minutes,
                "incident_count": record.incident_count,
                "sla_breached": record.sla_breached,
            }
            for record in records
        ]

        mttr_by_service = {
            service: round(sum(durations) / len(durations), 1)
            for service, durations in mttr_by_service.items()
            if durations
        }

        total_with_hypothesis = len([incident for incident in resolved if incident.hypothesis])
        agent_accuracy = round(total_with_hypothesis / len(resolved) * 100, 1) if resolved else 0

        return {
            "mttd_seconds": 0,
            "mttr_minutes": round(mttr, 1),
            "total_incidents": len(resolved),
            "active_incidents": active_count,
            "by_service": by_service,
            "by_severity": by_severity,
            "mttr_by_service": mttr_by_service,
            "sla_compliance": sla_compliance,
            "sla_breach_history": sla_breach_history,
            "agent_accuracy": agent_accuracy,
        }
