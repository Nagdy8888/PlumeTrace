"""The FastAPI application: scenarios, replay and health on 127.0.0.1:8000.

Run from ``app/``: ``uv run uvicorn plumetrace.api.main:app --host 127.0.0.1 --port 8000 --reload``.
"""

from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from plumetrace.api.routes import health, scenarios

ALLOWED_ORIGINS: Final = ("http://localhost:5173", "http://127.0.0.1:5173")


def create_app() -> FastAPI:
    """Build the application with CORS limited to the Vite dev origins.

    Returns:
        The configured FastAPI application.
    """
    app = FastAPI(
        title="PlumeTrace API",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    app.include_router(health.router)
    app.include_router(scenarios.router)
    return app


app = create_app()
