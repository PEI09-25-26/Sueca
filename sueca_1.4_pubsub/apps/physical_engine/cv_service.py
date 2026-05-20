from fastapi import FastAPI
from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt

from .routes import cv_router as router


app = FastAPI(title="Computer Vision Service", version="1.0")
app.include_router(router)

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
