from sqlalchemy.orm import Session

from app.models import IntegrationConfig
from app.time_utils import utc_now


class IntegrationConfigResolver:
    def __init__(self, db: Session):
        self.db = db

    def config_for(self, integration_type: str) -> dict:
        integration = (
            self.db.query(IntegrationConfig)
            .filter(
                IntegrationConfig.integration_type == integration_type,
                IntegrationConfig.enabled.is_(True),
            )
            .first()
        )
        if not integration:
            return {}
        integration.last_used_at = utc_now()
        return integration.config or {}
