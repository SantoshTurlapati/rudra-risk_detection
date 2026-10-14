from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine, Base, ensure_database_compatibility

# Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.brands import router as brands_router
from app.api.v1.brand_images import router as brand_images_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.threat_graph import router as threat_graph_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.reports import router as reports_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.settings_router import router as settings_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and backfill any newer columns for older SQLite databases.
    Base.metadata.create_all(bind=engine)
    ensure_database_compatibility()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Digital Risk Protection platform for social, app, and brand impersonation defense.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api/v1
api_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_prefix)
app.include_router(brands_router, prefix=api_prefix)
app.include_router(brand_images_router, prefix=api_prefix)
app.include_router(investigations_router, prefix=api_prefix)
app.include_router(analysis_router, prefix=api_prefix)
app.include_router(alerts_router, prefix=api_prefix)
app.include_router(campaigns_router, prefix=api_prefix)
app.include_router(threat_graph_router, prefix=api_prefix)
app.include_router(copilot_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(settings_router, prefix=api_prefix)

@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
    except SQLAlchemyError:
        logger.exception("Health check failed because the database is not ready")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "database": "unavailable",
            },
        )

    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "ready",
    }

@app.get("/")
def root():
    return {
        "message": "Welcome to RudraShield AI API",
        "docs_url": "/docs",
        "health_check": "/health"
    }
