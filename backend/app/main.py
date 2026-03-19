"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth, items, lists, suggestions
from app.websocket.handlers import websocket_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Tables are managed by Alembic in production.
    # Uncomment below for quick dev bootstrapping:
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


import os

# Disable docs/openapi in production
_is_production = os.getenv("ENVIRONMENT", "production") == "production"

app = FastAPI(
    title="Hopper Shopper",
    description="Collaborative grocery list Telegram Mini App",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST Routers ─────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(lists.router)
app.include_router(items.router)
app.include_router(suggestions.router)

# ── WebSocket ────────────────────────────────────────────────────
app.websocket("/ws/{list_id}")(websocket_endpoint)


# ── Health check ─────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok"}
