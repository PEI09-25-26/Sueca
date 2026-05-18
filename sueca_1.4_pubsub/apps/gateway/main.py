from fastapi import FastAPI, Request
from fastapi.responses import Response

from .routes import auth_router, game_router, proxy_router, state_router, websocket_router
from shared.logging_config import setup_logging, correlation_id_from_request
import logging

setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI(title="CV Middleware", version="0.1")


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
	cid = correlation_id_from_request(request)
	# attach to request.state for handlers
	request.state.correlation_id = cid
	# set in contextvar so CorrelationIdFilter can read it
	from shared.logging_config import set_correlation_id, clear_correlation_id
	set_correlation_id(cid)
	try:
		response: Response = await call_next(request)
		response.headers['X-Correlation-ID'] = cid
		return response
	finally:
		clear_correlation_id()


app.include_router(state_router)
app.include_router(auth_router)
app.include_router(proxy_router)
app.include_router(game_router)
app.include_router(websocket_router)
