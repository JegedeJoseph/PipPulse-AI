"""
FastAPI Main Application
Main entry point for the PipPulse AI backend API
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_databases, close_databases
from app.api import health, signals, news, admin, backtesting, websocket

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_databases()
    yield
    # Shutdown
    await close_databases()

app = FastAPI(
    title="PipPulse AI",
    description="Real-Time AI Sentiment Analysis Engine for Forex News Trading",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(backtesting.router, prefix="/api/backtesting", tags=["Backtesting"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


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
