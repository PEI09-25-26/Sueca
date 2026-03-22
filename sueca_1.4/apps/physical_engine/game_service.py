from fastapi import FastAPI

from routes.game_routes import router


app = FastAPI(title="Card Game Backend")
app.include_router(router)