from fastapi import FastAPI
import requests

from .routes import game_router, proxy_router, state_router, websocket_router


app = FastAPI(title="CV Middleware", version="0.1")

app.include_router(state_router)
app.include_router(proxy_router)
app.include_router(game_router)
app.include_router(websocket_router)
