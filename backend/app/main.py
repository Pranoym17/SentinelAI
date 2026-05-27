import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401
from app.routers import config, demo, incidents, integrations, metrics, seed


Base.metadata.create_all(bind=engine)


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
app.include_router(seed.router)
app.include_router(demo.router)
app.include_router(incidents.router)
app.include_router(integrations.router)
