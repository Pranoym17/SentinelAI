from datetime import timedelta
from typing import List

from sqlalchemy.orm import Session

from app.models import Incident, RecentDeploy
from app.schemas import DeployIn


class DeployService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, limit: int = 20) -> dict:
        deploys = (
            self.db.query(RecentDeploy)
            .order_by(RecentDeploy.deployed_at.desc())
            .limit(max(1, min(limit, 100)))
            .all()
        )
        active_incidents = self.db.query(Incident).filter(Incident.status == "open").all()
        return {"deploys": [self.serialize(deploy, active_incidents) for deploy in deploys]}

    def create(self, payload: DeployIn) -> dict:
        deploy = RecentDeploy(**payload.model_dump())
        self.db.add(deploy)
        self.db.commit()
        self.db.refresh(deploy)
        return self.serialize(deploy, self.db.query(Incident).filter(Incident.status == "open").all())

    def serialize(self, deploy: RecentDeploy, incidents: List[Incident]) -> dict:
        correlated_incident = self._correlated_incident(deploy, incidents)
        return {
            "id": deploy.id,
            "service": deploy.service,
            "version": deploy.version,
            "author": deploy.author,
            "deployed_at": deploy.deployed_at.isoformat(),
            "changes_summary": deploy.changes_summary or "",
            "suspected_cause": correlated_incident is not None,
            "correlated_incident_id": correlated_incident.id if correlated_incident else None,
        }

    def _correlated_incident(self, deploy: RecentDeploy, incidents: List[Incident]) -> Incident | None:
        for incident in incidents:
            if incident.service not in deploy.service:
                continue
            lower_bound = deploy.deployed_at - timedelta(minutes=30)
            upper_bound = deploy.deployed_at + timedelta(minutes=30)
            if lower_bound <= incident.detected_at <= upper_bound:
                return incident
        return None
