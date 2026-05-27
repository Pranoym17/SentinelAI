from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DeployIn
from app.services.deploy_service import DeployService


router = APIRouter(prefix="/api/deploys", tags=["deploys"])


@router.get("")
def list_deploys(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    return DeployService(db).list(limit=limit)


@router.post("")
def create_deploy(payload: DeployIn, db: Session = Depends(get_db)) -> dict:
    return DeployService(db).create(payload)
