"""Canonical ASGI entrypoint for the virtual engine."""

import gc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt
from .routes import api_router


# Tune garbage collection for better latency during batch operations
gc.set_debug(0)  # Disable debug mode
# Increase collection thresholds to reduce GC pauses
gc.set_threshold(10000, 20, 20)

app = FastAPI(title='Sueca Virtual Engine', version='2.1-fastapi-modular')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(api_router)


# Minimal request timing middleware to surface slow endpoints during profiling
@app.middleware("http")
async def timing_middleware(request, call_next):
    import time
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    # Only log slow requests to avoid noisy output
    if elapsed > 0.01:
        try:
            from apps.virtual_engine.core.game_core import logger as core_logger
            core_logger.debug(f"Request {request.method} {request.url.path} took {elapsed:.4f}s")
        except Exception:
            pass
    return response


@app.on_event('startup')
def _on_startup():
    gc.collect()  # Clear garbage before starting
    connect_mqtt()


@app.on_event('shutdown')
def _on_shutdown():
    disconnect_mqtt()

