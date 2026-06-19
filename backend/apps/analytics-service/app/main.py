import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core configurations
from app.core.config import settings
from app.core.logging import logger

# Routers
from app.api.v1 import dashboard, incidents, cameras, heatmap, reports, websockets, surveillance

# Async messaging and DB connections
from app.messaging.kafka_consumer import start_kafka_consumer
from app.db.redis import check_redis_connection

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="Omnisight Analytics Service - Aggregating time-series data for security metrics."
    )

    # Configure CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register REST API Routers
    api_prefix = settings.API_V1_STR + "/analytics"
    app.include_router(dashboard.router, prefix=api_prefix)
    app.include_router(incidents.router, prefix=api_prefix)
    app.include_router(cameras.router, prefix=api_prefix)
    app.include_router(heatmap.router, prefix=api_prefix)
    app.include_router(reports.router, prefix=api_prefix)
    app.include_router(surveillance.router, prefix=api_prefix)

    # Register WebSocket Router (Does not need the /analytics prefix)
    app.include_router(websockets.router, prefix=settings.API_V1_STR)
    
    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting up {settings.PROJECT_NAME}...")
    
    # 1. Verify Redis connection
    await check_redis_connection()
    
    # 2. Start Kafka Consumer loop in the background
    asyncio.create_task(start_kafka_consumer())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    # Add any graceful cleanup logic here (e.g., closing DB/Redis pools)

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for API Gateway / Kubernetes to verify service is running."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy"
    }