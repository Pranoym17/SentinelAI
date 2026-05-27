from sqlalchemy.orm import Session

from app.models import Incident, IntegrationConfig
from app.schemas import IntegrationConfigIn
from app.services.jira_service import JiraService
from app.services.github_service import GitHubService
from app.services.slack_service import SlackService
from app.services.openai_service import OpenAIService
from app.time_utils import utc_now


class IntegrationService:
    def __init__(self, db: Session | None = None):
        self.db = db

    def status(self) -> dict:
        configs = {}
        if self.db:
            for integration in self.db.query(IntegrationConfig).filter(IntegrationConfig.enabled.is_(True)).all():
                configs[integration.integration_type] = integration.config or {}
        jira = JiraService(configs.get("jira"))
        slack = SlackService(configs.get("slack"))
        openai = OpenAIService()
        return {
            "openai": {
                "configured": openai.configured,
                "model": openai.model,
            },
            "jira": {
                "configured": jira.configured,
                "base_url": jira.base_url,
                "project_key": jira.project_key,
                "issue_type": jira.issue_type,
            },
            "slack": {
                "configured": slack.configured,
                "channel": slack.channel,
            },
            "github": {
                "configured": GitHubService(self.db, configs.get("github")).configured,
            },
        }

    def list_configs(self) -> dict:
        if not self.db:
            return {"integrations": []}
        integrations = self.db.query(IntegrationConfig).order_by(IntegrationConfig.integration_type).all()
        return {"integrations": [self.serialize_config(integration) for integration in integrations]}

    def save_config(self, payload: IntegrationConfigIn) -> dict:
        if not self.db:
            raise RuntimeError("Database session required")
        integration = (
            self.db.query(IntegrationConfig)
            .filter(IntegrationConfig.integration_type == payload.type)
            .first()
        )
        if not integration:
            integration = IntegrationConfig(integration_type=payload.type)
            self.db.add(integration)

        integration.enabled = payload.enabled
        integration.config = payload.config
        integration.connected_at = utc_now()
        self.db.commit()
        self.db.refresh(integration)
        return {"status": "saved", "integration": self.serialize_config(integration)}

    def serialize_config(self, integration: IntegrationConfig) -> dict:
        return {
            "id": integration.id,
            "type": integration.integration_type,
            "enabled": integration.enabled,
            "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
            "last_used_at": integration.last_used_at.isoformat() if integration.last_used_at else None,
            "config": self._masked_config(integration.config or {}),
        }

    def _masked_config(self, config: dict) -> dict:
        masked = {}
        for key, value in config.items():
            if any(secret in key.lower() for secret in ["token", "key", "password", "secret"]):
                masked[key] = ""
            else:
                masked[key] = value
        return masked

    def test_slack(self) -> dict:
        incident = Incident(
            service="payments",
            severity="SEV-3",
            signal_type="slack_smoke_test",
            signal_value=1.0,
            hypothesis="SentinelAI Slack smoke test from integration endpoint. Safe to ignore.",
            confidence=55,
            affected_teams=["platform"],
        )
        config = {}
        if self.db:
            integration = (
                self.db.query(IntegrationConfig)
                .filter(IntegrationConfig.integration_type == "slack", IntegrationConfig.enabled.is_(True))
                .first()
            )
            config = integration.config if integration else {}
        return SlackService(config).post_review_request(
            incident,
            ["Verify webhook delivery", "Confirm channel visibility"],
        )

    def test_jira(self) -> dict:
        incident = Incident(
            service="payments",
            severity="SEV-3",
            signal_type="jira_smoke_test",
            signal_value=1.0,
            hypothesis="SentinelAI Jira smoke test from integration endpoint. Safe to close.",
            confidence=51,
            reasoning_chain=[{"step": "SMOKE TEST", "detail": "Testing Jira credential and project configuration"}],
            affected_teams=["platform"],
        )
        config = {}
        if self.db:
            integration = (
                self.db.query(IntegrationConfig)
                .filter(IntegrationConfig.integration_type == "jira", IntegrationConfig.enabled.is_(True))
                .first()
            )
            config = integration.config if integration else {}
        return JiraService(config).create_ticket(incident)

    def test_github(self) -> dict:
        config = {}
        if self.db:
            integration = (
                self.db.query(IntegrationConfig)
                .filter(IntegrationConfig.integration_type == "github", IntegrationConfig.enabled.is_(True))
                .first()
            )
            config = integration.config if integration else {}
        return GitHubService(self.db, config).smoke_test()
