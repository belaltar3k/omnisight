from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

router = APIRouter()
_worker_pool = None


def init_stream_routes(worker_pool):
    global _worker_pool
    _worker_pool = worker_pool


async def _mjpeg_generator(camera_id: str, fps: int) -> AsyncGenerator[bytes, None]:
    interval = 1.0 / fps
    while True:
        pipeline = _worker_pool.get_pipeline(camera_id)
        if pipeline is None:
            break
        frame_bytes = await asyncio.get_event_loop().run_in_executor(
            None, pipeline.get_stream_frame
        )
        if frame_bytes:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_bytes +
                b"\r\n"
            )
        await asyncio.sleep(interval)


@router.get("/stream/{camera_id}", summary="MJPEG live stream with detection overlay")
async def stream(camera_id: str, fps: int = 10):
    if _worker_pool is None or _worker_pool.get_pipeline(camera_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return StreamingResponse(
        _mjpeg_generator(camera_id, fps=min(fps, 25)),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/snapshot/{camera_id}", summary="Single JPEG snapshot with detection overlay")
async def snapshot(camera_id: str):
    if _worker_pool is None or _worker_pool.get_pipeline(camera_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    pipeline = _worker_pool.get_pipeline(camera_id)
    frame_bytes = await asyncio.get_event_loop().run_in_executor(
        None, pipeline.get_stream_frame
    )
    if frame_bytes is None:
        raise HTTPException(status_code=503, detail="No frame available yet")
    return Response(content=frame_bytes, media_type="image/jpeg")
