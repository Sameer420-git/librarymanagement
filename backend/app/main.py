

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import register_exception_handlers

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    from app.jobs.scheduler import scheduler_manager

    scheduler_manager.start()
    logger.info("%s started (environment=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    try:
        yield
    finally:
        scheduler_manager.shutdown()
        logger.info("%s stopped", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "Backend API for the College Library Management System: catalogue, "
            "physical copies, circulation, reservations, fines, notifications and "
            "reporting."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    register_exception_handlers(app)

    from app.api.routers import (
        admin,
        auth,
        books,
        circulation,
        fines,
        members,
        notifications,
        reports,
        reservations,
    )

    app.include_router(auth.router, prefix=settings.API_PREFIX)
    app.include_router(books.router, prefix=settings.API_PREFIX)
    app.include_router(members.router, prefix=settings.API_PREFIX)
    app.include_router(circulation.router, prefix=settings.API_PREFIX)
    app.include_router(reservations.router, prefix=settings.API_PREFIX)
    app.include_router(fines.router, prefix=settings.API_PREFIX)
    app.include_router(notifications.router, prefix=settings.API_PREFIX)
    app.include_router(reports.router, prefix=settings.API_PREFIX)
    app.include_router(admin.router, prefix=settings.API_PREFIX)

    @app.get("/health", tags=["Health"], summary="Liveness / readiness probe")
    def health() -> JSONResponse:
        from sqlalchemy import text

        from app.db.session import get_session_factory

        database_ok = True
        detail = "ok"
        try:
            session = get_session_factory()()
            try:
                session.execute(text("SELECT 1"))
            finally:
                session.close()
        except Exception as exc:  
            database_ok = False
            detail = type(exc).__name__

        payload = {
            "status": "ok" if database_ok else "degraded",
            "app": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "database": detail,
            "email_backend": settings.EMAIL_BACKEND,
        }
        return JSONResponse(status_code=200 if database_ok else 503, content=payload)

    @app.get(f"{settings.API_PREFIX}/health", tags=["Health"], include_in_schema=False)
    def api_health() -> dict:
        return {"status": "ok"}

    @app.get("/", tags=["Health"], include_in_schema=False)
    def root() -> dict:
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "api": settings.API_PREFIX,
        }

    return app


app = create_app()
