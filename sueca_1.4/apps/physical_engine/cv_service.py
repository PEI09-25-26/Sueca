from fastapi import FastAPI

from routes.cv_routes import router


app = FastAPI(title="Computer Vision Service", version="1.0")
app.include_router(router)
