#!/usr/bin/env python
"""
Hybrid Engine for Sueca 1.5
Standalone hybrid-mode game engine.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt

# Import hybrid-specific components
from apps.hybrid_engine.core.hybrid_game_coordinator import HybridGameCoordinator
from apps.hybrid_engine.core.hybrid_vision_service import HybridVisionService

from apps.hybrid_engine.routes import api_router
import apps.hybrid_engine.routes.hybrid_routes as hybrid_routes_module
hybrid_routes = hybrid_routes_module.router

# Shared utilities
from shared.logging_config import setup_logging

# Setup logging (uses LOG_LEVEL env or INFO by default)
setup_logging()
logger = logging.getLogger(__name__)

hybrid_coordinator = HybridGameCoordinator()
hybrid_vision_service = HybridVisionService()

# Inject instances into hybrid routes module so the router uses the same objects
hybrid_routes_module.hybrid_coordinator = hybrid_coordinator
hybrid_routes_module.hybrid_vision = hybrid_vision_service

# FastAPI app
app = FastAPI(
    title="Sueca Hybrid Engine",
    description="Detached hybrid game engine with its own game state and hybrid CV workflow",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Lifespan / Startup / Shutdown ============

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Hybrid Engine starting up...")
    connect_mqtt()
    
    # Game manager is initialized globally
    logger.info("✅ Game Manager ready")
    
    # Initialize hybrid coordinator
    logger.info("✅ Hybrid Game Coordinator initialized")
    
    if await hybrid_vision_service.test_cv_service():
        logger.info(
            "✅ Built-in CV model configured (%s)",
            hybrid_vision_service.model_path,
        )
    else:
        logger.warning(
            "⚠️ Hybrid CV model not found — place best.pt in apps/hybrid_engine/cv/ "
            "or set HYBRID_CV_MODEL_PATH",
        )
    
    logger.info("✅ Hybrid Engine ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Hybrid Engine shutting down...")
    disconnect_mqtt()


# ============ Health Check ============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "hybrid_engine",
        "version": "1.0.0",
        "cv_model_configured": hybrid_vision_service.model_path is not None,
        "cv_model_path": hybrid_vision_service.model_path,
    }


# ============ Include Routers ============

# Core game routes (same as virtual engine)
app.include_router(api_router)
app.include_router(hybrid_routes, tags=["hybrid"])


# ============ Custom Error Handler ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
