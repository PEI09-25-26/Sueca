"""Combined entry point for Physical Engine with both CV and Game services."""

from fastapi import FastAPI
from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt

from .routes.cv_routes import router as cv_router
from .routes.game_routes import router as game_router


app = FastAPI(title="Physical Engine", version="1.0")

# Include both CV and Game service routers
app.include_router(cv_router)
app.include_router(game_router)


@app.on_event("startup")
def _on_startup():
    connect_mqtt()


@app.on_event("shutdown")
def _on_shutdown():
    disconnect_mqtt()
