from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_model_manager = None
_worker_pool = None


def init_health(model_manager, worker_pool):
    global _model_manager, _worker_pool
    _model_manager = model_manager
    _worker_pool = worker_pool


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai-detection"}


@router.get("/readiness")
async def readiness():
    if _model_manager is None or not _model_manager.is_ready:
        return JSONResponse(
            status_code=503,
            content={"status": "loading", "message": "Models still loading"},
        )
    return {
        "status": "ready",
        "detectors": _model_manager.get_active_names(),
        "load_times": _model_manager.load_times,
    }
