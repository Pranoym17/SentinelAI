import os

os.environ["DATABASE_URL"] = "sqlite:///./test_sentinel.db"
os.environ["SENTINEL_WORKER_ENABLED"] = "false"
os.environ["JIRA_BASE_URL"] = ""
os.environ["JIRA_EMAIL"] = ""
os.environ["JIRA_API_TOKEN"] = ""
os.environ["SLACK_WEBHOOK_URL"] = ""
os.environ["SLACK_BOT_TOKEN"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["GITHUB_TOKEN"] = ""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine, get_db
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
