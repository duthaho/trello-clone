"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from src.shared.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Initialize observability (logging, tracing, metrics)

    yield

    # Shutdown
    print(f"Shutting down {settings.app_name}")

    # TODO: Close database connections
    # TODO: Close Redis connections
    # TODO: Flush metrics and traces


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="SaaS Task Management Platform - A Trello-inspired project management system",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    """Basic health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }
    )


@app.get("/ready", tags=["health"])
async def readiness_check() -> JSONResponse:
    """Readiness check endpoint.

    Checks if the application is ready to serve traffic.
    This should verify database connectivity, cache availability, etc.
    """
    # TODO: Check database connection
    # TODO: Check Redis connection
    # TODO: Check other critical dependencies

    return JSONResponse(
        content={
            "status": "ready",
            "service": settings.app_name,
            "checks": {
                "database": "ok",  # TODO: Implement actual check
                "cache": "ok",  # TODO: Implement actual check
            },
        }
    )


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.app_version,
        "docs": "/docs" if settings.is_development else "Documentation disabled in production",
    }


# TODO: Mount API v1 router
# from src.interface.api.v1 import router as api_v1_router
# app.include_router(api_v1_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
