from fastapi import APIRouter, WebSocket

try:
    from ..core.cv_core import StartCVRequest, health_status, start_cv, stop_cv, stream_cv
except ImportError:
    from ..core.cv_core import StartCVRequest, health_status, start_cv, stop_cv, stream_cv


router = APIRouter()


@router.post("/cv/start")
async def start_cv_service(request: StartCVRequest):
    return await start_cv(request)


@router.websocket("/cv/stream/{game_id}")
async def cv_stream(websocket: WebSocket, game_id: str):
    await stream_cv(websocket, game_id)


@router.post("/cv/stop")
async def stop_cv_service(game_id: str):
    return await stop_cv(game_id)


@router.get("/health")
async def health_check():
    return await health_status()
