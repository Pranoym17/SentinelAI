from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RunbookIn
from app.services.runbook_service import RunbookService


router = APIRouter(prefix="/api/runbooks", tags=["runbooks"])


@router.get("")
def list_runbooks(db: Session = Depends(get_db)) -> dict:
    return RunbookService(db).list()


@router.post("")
def create_runbook(payload: RunbookIn, db: Session = Depends(get_db)) -> dict:
    return RunbookService(db).create(payload)
