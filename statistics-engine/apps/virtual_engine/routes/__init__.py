from fastapi import APIRouter

from .gameplay_routes import router as gameplay_router
from .player_routes import router as player_router
from .room_routes import router as room_router


api_router = APIRouter()
api_router.include_router(room_router)
api_router.include_router(player_router)
api_router.include_router(gameplay_router)

# Backward-compatible export name used by api.py.
router = api_router

__all__ = ["api_router", "router"]
