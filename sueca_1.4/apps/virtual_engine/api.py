"""Canonical ASGI entrypoint for the virtual engine."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt
from .routes import api_router


app = FastAPI(title='Sueca Virtual Engine', version='2.1-fastapi-modular')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(api_router)


@app.on_event('startup')
def _on_startup():
    connect_mqtt()


@app.on_event('shutdown')
def _on_shutdown():
    disconnect_mqtt()

