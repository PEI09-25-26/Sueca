from fastapi import FastAPI
from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt

from routes.game_routes import router


app = FastAPI(title="Card Game Backend")
app.include_router(router)


@app.on_event('startup')
def _on_startup():
	connect_mqtt()


@app.on_event('shutdown')
def _on_shutdown():
	disconnect_mqtt()