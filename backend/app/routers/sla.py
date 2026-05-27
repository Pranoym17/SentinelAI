from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.sla_service import SLAService


router = APIRouter(prefix="/api/sla", tags=["sla"])


@router.get("")
def get_sla_status(db: Session = Depends(get_db)) -> dict:
    return SLAService(db).all_statuses()
