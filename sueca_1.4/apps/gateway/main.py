from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import requests

from .lifecycle import shutdown_services, startup_services
from .routes import game_router, proxy_router, state_router, websocket_router


app = FastAPI(title="CV Middleware", version="0.1")

app.on_event("startup")(startup_services)
app.on_event("shutdown")(shutdown_services)

app.include_router(state_router)
app.include_router(proxy_router)
app.include_router(game_router)
app.include_router(websocket_router)

website_dir = Path(__file__).resolve().parents[3] / "website"
if website_dir.exists():
    app.mount("/site", StaticFiles(directory=website_dir, html=True), name="site")
