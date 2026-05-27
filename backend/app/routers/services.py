from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ServiceIn
from app.services.service_catalog_service import ServiceCatalogService


router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("")
def list_services(db: Session = Depends(get_db)) -> dict:
    return ServiceCatalogService(db).list()


@router.post("")
def create_service(payload: ServiceIn, db: Session = Depends(get_db)) -> dict:
    return ServiceCatalogService(db).create(payload)
