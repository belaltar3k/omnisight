import asyncio
import logging
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import config
from src.api.routes.health import router as health_router, init_health
from src.api.routes.config_routes import router as config_router, init_config_routes
from src.api.routes.cameras import router as cameras_router, init_cameras_routes
from src.api.routes.stream_routes import router as stream_router, init_stream_routes
from src.detection.incident_sender import IncidentSender
from src.detection.model_manager import ModelManager
from src.workers.worker_pool import WorkerPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ai-detection")

model_manager = ModelManager(config)
incident_sender = IncidentSender(
    incident_service_url=config.INCIDENT_SERVICE_URL,
    edge_sync_secret=config.EDGE_SYNC_SECRET,
    edge_node_code=config.EDGE_NODE_CODE,
)
worker_pool = WorkerPool(config, model_manager, incident_sender)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Omnisight AI Detection Service",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_health(model_manager, worker_pool)
    init_config_routes(config, model_manager, worker_pool)
    init_cameras_routes(worker_pool)
    init_stream_routes(worker_pool)

    app.include_router(health_router)
    app.include_router(config_router)
    app.include_router(cameras_router)
    app.include_router(stream_router)

    @app.on_event("startup")
    async def startup():
        logger.info("AI Detection Service starting on port %d", config.SERVICE_PORT)
        logger.info("Device: %s", config.DEVICE)
        logger.info("Disabled models: %s", config.DISABLED_MODELS or "none")

        load_thread = threading.Thread(target=_load_and_start, daemon=True)
        load_thread.start()

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("Shutting down AI Detection Service")
        worker_pool.stop()
        incident_sender.close()

    return app


def _load_and_start():
    model_manager.load_all()
    logger.info("All models loaded — starting camera worker pool")
    worker_pool.start()


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=config.SERVICE_PORT,
        log_level="info",
    )
