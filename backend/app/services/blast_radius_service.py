from sqlalchemy.orm import Session

from app.models import Incident, Service


class BlastRadiusService:
    def __init__(self, db: Session):
        self.db = db

    def analyze_incident(self, incident: Incident) -> dict:
        return self.analyze_service(incident.service)

    def analyze_service(self, service_name: str) -> dict:
        service = self.db.query(Service).filter(Service.name == service_name).first()
        if not service:
            return {
                "service": service_name,
                "affected_services": [],
                "upstream_dependencies": [],
                "downstream_dependents": [],
                "warning": f"No service catalog entry found for {service_name}. Blast radius is unknown.",
                "risk_level": "unknown",
            }

        upstream_dependencies = service.dependencies or []
        downstream_dependents = [
            item.name
            for item in self.db.query(Service).order_by(Service.name).all()
            if item.name != service_name and service_name in (item.dependencies or [])
        ]
        affected_services = sorted(set(upstream_dependencies + downstream_dependents))

        if affected_services:
            warning = (
                f"Rolling back {service_name} may affect {len(affected_services)} connected "
                f"service(s): {', '.join(affected_services)}."
            )
        else:
            warning = None

        return {
            "service": service_name,
            "affected_services": affected_services,
            "upstream_dependencies": upstream_dependencies,
            "downstream_dependents": downstream_dependents,
            "warning": warning,
            "risk_level": "high" if len(affected_services) > 3 else "medium" if affected_services else "low",
        }
