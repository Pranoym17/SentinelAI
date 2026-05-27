from fastapi import APIRouter

from app.services.integration_service import IntegrationService


router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status")
def status() -> dict:
    return IntegrationService().status()


@router.post("/slack/test")
def test_slack() -> dict:
    return IntegrationService().test_slack()


@router.post("/jira/test")
def test_jira() -> dict:
    return IntegrationService().test_jira()
