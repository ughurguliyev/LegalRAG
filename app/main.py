"""Main FastAPI application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import chat
from app.services.redis_service import get_redis_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Azerbaijan Legal RAG API...")

    # Initialize Redis connection
    redis_service = await get_redis_service()
    print("✅ Redis connected")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    if redis_service:
        await redis_service.disconnect()
    print("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered legal assistant for Azerbaijan law codes",
    lifespan=lifespan,
    openapi_url=settings.openapi_url,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Application health check"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


# API info endpoint
@app.get("/")
async def root():
    """API information"""
    base_info = {
        "app": settings.app_name,
        "version": settings.app_version,
        "description": "Azerbaijan Legal RAG API",
        "endpoints": {
            "chat": f"{settings.api_prefix}/chat",
            "chat_stream": f"{settings.api_prefix}/chat/stream",
            "chat_history": f"{settings.api_prefix}/chat/history/{{session_id}}",
        },
    }

    return base_info


# Include routers
app.include_router(chat.router, prefix=settings.api_prefix)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred",
        },
    )
