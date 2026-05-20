from fastapi import APIRouter, WebSocket

from ..cv.cv_service import (
    StartCVRequest,
    health_check as cv_health_check,
    start_cv_service as cv_start_service,
    stop_cv_service as cv_stop_service,
    cv_stream as cv_stream_service,
)


router = APIRouter()


@router.post("/cv/start")
async def start_cv_service(request: StartCVRequest):
    return await cv_start_service(request)


@router.websocket("/cv/stream/{game_id}")
async def cv_stream(websocket: WebSocket, game_id: str):
    await cv_stream_service(websocket, game_id)


@router.post("/cv/stop")
async def stop_cv_service(game_id: str):
    return await cv_stop_service(game_id)


@router.get("/health")
async def health_check():
    return await cv_health_check()
