from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def analytics(db: Session = Depends(get_db)) -> dict:
    return AnalyticsService(db).summary()
