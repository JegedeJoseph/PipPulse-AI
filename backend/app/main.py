"""
FastAPI Main Application
Main entry point for the PipPulse AI backend API
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List, Optional
import logging
from datetime import datetime

from app.config import get_settings
from app.api import signals, news, admin, health, websocket, backtesting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting PipPulse AI backend...")
    try:
        from app.database import connect_all_databases
        await connect_all_databases()
        logger.info("Databases initialized")
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down PipPulse AI backend...")
    try:
        from app.database import disconnect_all_databases
        await disconnect_all_databases()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="PipPulse AI",
    description="Real-Time AI Sentiment Analysis Engine for Forex News Trading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(backtesting.router, prefix="/api/backtesting", tags=["Backtesting"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "PipPulse AI",
        "version": "1.0.0",
        "description": "Real-Time AI Sentiment Analysis Engine for Forex News Trading",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred"
        }
    )


# 404 handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "detail": "The requested resource was not found"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
