from sqlalchemy.orm import Session

from app.models import Service
from app.schemas import ServiceIn


class ServiceCatalogService:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> dict:
        services = self.db.query(Service).order_by(Service.name).all()
        return {"services": [self.serialize(service) for service in services]}

    def create(self, payload: ServiceIn) -> dict:
        service = Service(**payload.model_dump())
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return {"status": "created", "service": self.serialize(service)}

    def serialize(self, service: Service) -> dict:
        return {
            "id": service.id,
            "name": service.name,
            "display_name": service.display_name,
            "description": service.description,
            "dependencies": service.dependencies or [],
            "team": service.team,
            "repo_url": service.repo_url,
            "sla_target": service.sla_target,
            "created_at": service.created_at.isoformat() if service.created_at else None,
        }
