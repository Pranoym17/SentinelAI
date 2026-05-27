from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import OnCallScheduleIn
from app.services.oncall_service import OnCallService


router = APIRouter(prefix="/api/oncall", tags=["oncall"])


@router.get("/current")
def current_oncall(db: Session = Depends(get_db)) -> dict:
    return OnCallService(db).current()


@router.post("")
def create_oncall(payload: OnCallScheduleIn, db: Session = Depends(get_db)) -> dict:
    return OnCallService(db).create(payload)
