from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import IntegrationConfigIn
from app.services.integration_service import IntegrationService


router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    return IntegrationService(db).status()


@router.get("")
def list_integrations(db: Session = Depends(get_db)) -> dict:
    return IntegrationService(db).list_configs()


@router.post("")
def save_integration(payload: IntegrationConfigIn, db: Session = Depends(get_db)) -> dict:
    return IntegrationService(db).save_config(payload)


@router.post("/slack/test")
def test_slack(db: Session = Depends(get_db)) -> dict:
    return IntegrationService(db).test_slack()


@router.post("/jira/test")
def test_jira(db: Session = Depends(get_db)) -> dict:
    return IntegrationService(db).test_jira()
