from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Config
from app.schemas import ConfigIn, ConfigOut
from app.services.serializers import serialize_config


router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config(db: Session = Depends(get_db)) -> dict:
    config = db.query(Config).order_by(Config.id.desc()).first()
    if not config:
        raise HTTPException(status_code=404, detail="No config found")
    return serialize_config(config)


@router.post("")
def save_config(payload: ConfigIn, db: Session = Depends(get_db)) -> dict:
    config = Config(**payload.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return {"status": "saved", "config": serialize_config(config)}
