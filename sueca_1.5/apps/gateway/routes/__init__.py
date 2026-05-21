from .state_routes import router as state_router
from .proxy_routes import router as proxy_router
from .game_routes import router as game_router
from .websocket_routes import router as websocket_router

__all__ = ["state_router", "proxy_router", "game_router", "websocket_router"]
