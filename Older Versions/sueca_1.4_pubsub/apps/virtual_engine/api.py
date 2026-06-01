"""Canonical ASGI entrypoint for the virtual engine."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt
from .routes import api_router


raw_origins = os.getenv("SUECA_ALLOWED_ORIGINS", "https://suecadaojogo.com,https://api.suecadaojogo.com")
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app = FastAPI(title='Sueca Virtual Engine', version='2.1-fastapi-modular')
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type'],
)
app.include_router(api_router)

from shared.logging_config import setup_logging, correlation_id_from_request, set_correlation_id, clear_correlation_id
from fastapi import Request

setup_logging()


@app.middleware("http")
async def _add_cid(request: Request, call_next):
    cid = correlation_id_from_request(request)
    request.state.correlation_id = cid
    set_correlation_id(cid)
    try:
        resp = await call_next(request)
        resp.headers['X-Correlation-ID'] = cid
        return resp
    finally:
        clear_correlation_id()


@app.on_event('startup')
def _on_startup():
    connect_mqtt()


@app.on_event('shutdown')
def _on_shutdown():
    disconnect_mqtt()
