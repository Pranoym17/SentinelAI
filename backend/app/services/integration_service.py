from app.models import Incident
from app.services.jira_service import JiraService
from app.services.slack_service import SlackService
from app.services.openai_service import OpenAIService


class IntegrationService:
    def status(self) -> dict:
        jira = JiraService()
        slack = SlackService()
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
        }

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
        return SlackService().post_review_request(
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
        return JiraService().create_ticket(incident)
