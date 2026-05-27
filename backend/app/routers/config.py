from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Config
from app.schemas import ConfigIn, ConfigOut


router = APIRouter(prefix="/api/config", tags=["config"])


def serialize_config(config: Config) -> dict:
    return {
        "id": config.id,
        "services": config.services or [],
        "signals": config.signals or [],
        "actions": config.actions or [],
        "thresholds": config.thresholds or {},
        "slack_channel": config.slack_channel or "#incidents",
        "jira_project_key": config.jira_project_key or "INC",
    }


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
