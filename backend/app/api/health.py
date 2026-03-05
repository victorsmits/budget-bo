"""Health check endpoint for monitoring system status."""

import asyncio
from datetime import datetime
from typing import Any

import httpx
import redis.asyncio as redis
from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal

router = APIRouter(prefix="/health", tags=["health"])

settings = get_settings()


async def check_postgres() -> dict[str, Any]:
    """Check PostgreSQL connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            row = result.scalar()
            return {
                "status": "healthy" if row == 1 else "unhealthy",
                "latency_ms": None,  # Could add timing if needed
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=5)
        await client.ping()
        await client.close()
        return {"status": "healthy"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_ollama() -> dict[str, Any]:
    """Check Ollama API connectivity."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags"
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                target_model = settings.ollama_model
                model_available = any(
                    target_model in m for m in models
                )
                return {
                    "status": "healthy",
                    "models_loaded": len(models),
                    f"target_model_{target_model}_available": model_available,
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Verifies connectivity to:
    - PostgreSQL database
    - Redis cache/broker
    - Ollama AI service
    """
    # Run checks concurrently
    postgres_task = asyncio.create_task(check_postgres())
    redis_task = asyncio.create_task(check_redis())
    ollama_task = asyncio.create_task(check_ollama())

    postgres_health = await postgres_task
    redis_health = await redis_task
    ollama_health = await ollama_task

    # Determine overall status
    services = {
        "postgres": postgres_health,
        "redis": redis_health,
        "ollama": ollama_health,
    }

    all_healthy = all(
        s.get("status") == "healthy" for s in services.values()
    )

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    response = {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "services": services,
    }

    # Note: FastAPI doesn't allow dynamic status codes in response model,
    # but we can use the status_code parameter in the decorator
    # For proper 503 handling, we'd need a custom exception handler
    return response


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> dict[str, str]:
    """
    Kubernetes-style liveness probe.
    Simple check that the application is running.
    """
    return {"status": "alive"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_probe() -> dict[str, Any]:
    """
    Kubernetes-style readiness probe.
    Checks if the application is ready to serve traffic.
    """
    # Check critical dependencies
    postgres_ok = (await check_postgres()).get("status") == "healthy"
    redis_ok = (await check_redis()).get("status") == "healthy"

    ready = postgres_ok and redis_ok

    return {
        "status": "ready" if ready else "not_ready",
        "dependencies": {
            "postgres": "ok" if postgres_ok else "fail",
            "redis": "ok" if redis_ok else "fail",
        },
    }
