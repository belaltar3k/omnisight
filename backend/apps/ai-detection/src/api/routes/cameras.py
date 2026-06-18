from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/cameras")

_worker_pool = None


def init_cameras_routes(worker_pool):
    global _worker_pool
    _worker_pool = worker_pool


@router.get("")
async def list_cameras():
    if _worker_pool is None:
        return []
    return _worker_pool.get_all_status()
