import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models  # noqa: F401
from app.routers import analytics, config, demo, deploys, incidents, integrations, metrics, oncall, runbooks, seed, services, sla


Base.metadata.create_all(bind=engine)


def _apply_sqlite_compat_migrations():
    if not str(engine.url).startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "incidents" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("incidents")}
    statements = []
    if "recommended_actions" not in columns:
        statements.append("ALTER TABLE incidents ADD COLUMN recommended_actions JSON")
    if "fix_preview" not in columns:
        statements.append("ALTER TABLE incidents ADD COLUMN fix_preview JSON")
    if "raw_model_response" not in columns:
        statements.append("ALTER TABLE incidents ADD COLUMN raw_model_response TEXT")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


_apply_sqlite_compat_migrations()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SENTINEL_WORKER_ENABLED", "true").lower() == "true":
        from app.background_worker import worker

        worker.start()
    yield


app = FastAPI(title="SentinelAI API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(config.router)
app.include_router(metrics.router)
app.include_router(deploys.router)
app.include_router(seed.router)
app.include_router(demo.router)
app.include_router(incidents.router)
app.include_router(integrations.router)
app.include_router(services.router)
app.include_router(sla.router)
app.include_router(oncall.router)
app.include_router(runbooks.router)
app.include_router(analytics.router)
