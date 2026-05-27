from datetime import datetime

from sqlalchemy.orm import Session

from app.models import SLARecord, Service
from app.time_utils import utc_now


class SLAService:
    def __init__(self, db: Session):
        self.db = db

    def all_statuses(self) -> dict:
        services = self.db.query(Service).order_by(Service.name).all()
        if not services:
            return {"sla": []}
        return {"sla": [self.get_current_sla_status(service.name) for service in services]}

    def get_current_sla_status(self, service_name: str) -> dict:
        now = utc_now()
        month_key = now.strftime("%Y-%m")
        total_minutes = 30 * 24 * 60

        record = (
            self.db.query(SLARecord)
            .filter(SLARecord.service == service_name, SLARecord.month == month_key)
            .first()
        )
        service = self.db.query(Service).filter(Service.name == service_name).first()
        target = service.sla_target if service else 99.9
        downtime_minutes = record.total_downtime_minutes if record else 0
        allowed_downtime = total_minutes * (1 - target / 100)
        remaining_budget = max(0, allowed_downtime - downtime_minutes)
        actual_uptime = ((total_minutes - downtime_minutes) / total_minutes) * 100
        sla_breached = actual_uptime < target

        return {
            "service": service_name,
            "month": month_key,
            "target_uptime": target,
            "actual_uptime": round(actual_uptime, 4),
            "allowed_downtime_minutes": round(allowed_downtime, 1),
            "used_downtime_minutes": downtime_minutes,
            "remaining_budget_minutes": round(remaining_budget, 1),
            "sla_breached": sla_breached,
            "status": "breached" if sla_breached else "at_risk" if remaining_budget < 10 else "healthy",
        }

    def predict_breach(self, service_name: str) -> dict:
        status = self.get_current_sla_status(service_name)
        remaining = status["remaining_budget_minutes"]
        if remaining <= 0:
            return {
                "will_breach": True,
                "breach_in_minutes": 0,
                "message": f"SLA already breached for {service_name}.",
            }
        return {
            "will_breach": remaining < 30,
            "breach_in_minutes": round(remaining),
            "message": (
                f"SLA breach in {remaining:.0f} minutes if unresolved."
                if remaining < 30
                else f"{remaining:.0f} minutes of downtime budget remaining."
            ),
        }

    def record_downtime(self, service_name: str, duration_minutes: int, commit: bool = True) -> SLARecord:
        now = utc_now()
        month_key = now.strftime("%Y-%m")
        record = (
            self.db.query(SLARecord)
            .filter(SLARecord.service == service_name, SLARecord.month == month_key)
            .first()
        )
        if not record:
            service = self.db.query(Service).filter(Service.name == service_name).first()
            record = SLARecord(
                service=service_name,
                month=month_key,
                target_uptime=service.sla_target if service else 99.9,
                total_downtime_minutes=0,
                incident_count=0,
            )
            self.db.add(record)

        record.total_downtime_minutes += duration_minutes
        record.incident_count += 1
        record.updated_at = now
        total_minutes = 30 * 24 * 60
        actual = ((total_minutes - record.total_downtime_minutes) / total_minutes) * 100
        record.actual_uptime = round(actual, 4)
        record.sla_breached = actual < record.target_uptime
        if commit:
            self.db.commit()
            self.db.refresh(record)
        return record
