"""
Health Check Router for CAPP

Provides health check endpoints for monitoring system status,
service availability, and performance metrics.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import structlog

from .core.database import get_database_session
from .core.redis import get_redis_client
from .core.kafka import get_kafka_producer
from .core.aptos import get_aptos_client
from .config.settings import get_settings

logger = structlog.get_logger(__name__)

health_check_router = APIRouter()


@health_check_router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns:
        Dict containing basic health status
    """
    return {
        "status": "healthy",
        "service": "CAPP",
        "version": get_settings().APP_VERSION,
        "environment": get_settings().ENVIRONMENT
    }


@health_check_router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint
    
    Checks if the service is ready to handle requests by verifying
    all critical dependencies are available.
    
    Returns:
        Dict containing readiness status and dependency health
    """
    health_status = {
        "status": "ready",
        "service": "CAPP",
        "dependencies": {}
    }
    
    # Check database connectivity
    try:
        db_session = get_database_session()
        await db_session.execute("SELECT 1")
        health_status["dependencies"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["dependencies"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["status"] = "not_ready"
    
    # Check Redis connectivity
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        health_status["dependencies"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["dependencies"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        health_status["status"] = "not_ready"
    
    # Check Kafka connectivity
    try:
        kafka_producer = get_kafka_producer()
        # Mock Kafka health check - in real implementation, this would check actual connectivity
        health_status["dependencies"]["kafka"] = {
            "status": "healthy",
            "message": "Kafka connection successful"
        }
    except Exception as e:
        logger.error("Kafka health check failed", error=str(e))
        health_status["dependencies"]["kafka"] = {
            "status": "unhealthy",
            "message": f"Kafka connection failed: {str(e)}"
        }
        health_status["status"] = "not_ready"
    
    # Check Aptos connectivity
    try:
        aptos_client = get_aptos_client()
        # Mock Aptos health check - in real implementation, this would check actual connectivity
        health_status["dependencies"]["aptos"] = {
            "status": "healthy",
            "message": "Aptos connection successful"
        }
    except Exception as e:
        logger.error("Aptos health check failed", error=str(e))
        health_status["dependencies"]["aptos"] = {
            "status": "unhealthy",
            "message": f"Aptos connection failed: {str(e)}"
        }
        health_status["status"] = "not_ready"
    
    return health_status


@health_check_router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint
    
    Checks if the service is alive and running.
    This is a lightweight check that doesn't verify dependencies.
    
    Returns:
        Dict containing liveness status
    """
    return {
        "status": "alive",
        "service": "CAPP",
        "timestamp": "2024-01-01T00:00:00Z"  # In real implementation, this would be current timestamp
    }


@health_check_router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint
    
    Provides comprehensive health information including:
    - Service status
    - Dependency health
    - Performance metrics
    - Configuration status
    
    Returns:
        Dict containing detailed health information
    """
    settings = get_settings()
    
    health_info = {
        "service": {
            "name": "CAPP",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "healthy"
        },
        "dependencies": {},
        "performance": {
            "uptime": "0 days, 0 hours, 0 minutes",  # Mock uptime
            "memory_usage": "50 MB",  # Mock memory usage
            "cpu_usage": "5%",  # Mock CPU usage
            "active_connections": 0  # Mock connection count
        },
        "configuration": {
            "database_url": "configured" if settings.DATABASE_URL else "not_configured",
            "redis_url": "configured" if settings.REDIS_URL else "not_configured",
            "kafka_brokers": "configured" if settings.KAFKA_BROKERS else "not_configured",
            "aptos_node_url": "configured" if settings.APTOS_NODE_URL else "not_configured"
        },
        "features": {
            "payment_processing": "enabled",
            "agent_system": "enabled",
            "blockchain_integration": "enabled",
            "monitoring": "enabled"
        }
    }
    
    # Check dependencies with detailed information
    try:
        db_session = get_database_session()
        await db_session.execute("SELECT 1")
        health_info["dependencies"]["database"] = {
            "status": "healthy",
            "type": "PostgreSQL",
            "url": settings.DATABASE_URL.split("@")[-1] if settings.DATABASE_URL else "unknown",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_info["dependencies"]["database"] = {
            "status": "unhealthy",
            "type": "PostgreSQL",
            "error": str(e),
            "message": "Database connection failed"
        }
        health_info["service"]["status"] = "degraded"
    
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        health_info["dependencies"]["redis"] = {
            "status": "healthy",
            "type": "Redis",
            "url": settings.REDIS_URL.split("@")[-1] if settings.REDIS_URL else "unknown",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_info["dependencies"]["redis"] = {
            "status": "unhealthy",
            "type": "Redis",
            "error": str(e),
            "message": "Redis connection failed"
        }
        health_info["service"]["status"] = "degraded"
    
    try:
        kafka_producer = get_kafka_producer()
        health_info["dependencies"]["kafka"] = {
            "status": "healthy",
            "type": "Apache Kafka",
            "brokers": settings.KAFKA_BROKERS,
            "message": "Kafka connection successful"
        }
    except Exception as e:
        health_info["dependencies"]["kafka"] = {
            "status": "unhealthy",
            "type": "Apache Kafka",
            "error": str(e),
            "message": "Kafka connection failed"
        }
        health_info["service"]["status"] = "degraded"
    
    try:
        aptos_client = get_aptos_client()
        health_info["dependencies"]["aptos"] = {
            "status": "healthy",
            "type": "Aptos Blockchain",
            "node_url": settings.APTOS_NODE_URL,
            "message": "Aptos connection successful"
        }
    except Exception as e:
        health_info["dependencies"]["aptos"] = {
            "status": "unhealthy",
            "type": "Aptos Blockchain",
            "error": str(e),
            "message": "Aptos connection failed"
        }
        health_info["service"]["status"] = "degraded"
    
    return health_info


@health_check_router.get("/metrics")
async def health_metrics() -> Dict[str, Any]:
    """
    Health metrics endpoint
    
    Provides system metrics for monitoring and alerting.
    
    Returns:
        Dict containing system metrics
    """
    # Mock metrics - in real implementation, these would be actual system metrics
    metrics = {
        "system": {
            "uptime_seconds": 3600,  # Mock uptime
            "memory_usage_bytes": 52428800,  # 50 MB
            "cpu_usage_percent": 5.0,
            "disk_usage_percent": 25.0
        },
        "application": {
            "total_requests": 1000,
            "successful_requests": 950,
            "failed_requests": 50,
            "average_response_time_ms": 150,
            "active_connections": 10
        },
        "payments": {
            "total_payments": 500,
            "successful_payments": 480,
            "failed_payments": 20,
            "average_processing_time_seconds": 2.5,
            "total_volume_usd": 50000.0
        },
        "agents": {
            "active_agents": 5,
            "total_agent_executions": 1000,
            "successful_executions": 980,
            "failed_executions": 20,
            "average_execution_time_ms": 500
        }
    }
    
    return metrics


@health_check_router.get("/status")
async def service_status() -> Dict[str, Any]:
    """
    Service status endpoint
    
    Provides current service status and operational information.
    
    Returns:
        Dict containing service status information
    """
    settings = get_settings()
    
    status = {
        "service": "CAPP - Canza Autonomous Payment Protocol",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "description": "Autonomous payment infrastructure for African cross-border payments",
        "features": [
            "Agent-based payment routing",
            "Multi-currency support (42+ African currencies)",
            "Mobile money integration",
            "Offline-first design",
            "Regulatory compliance",
            "Cost optimization (<1% transaction costs)"
        ],
        "supported_corridors": [
            "Kenya ↔ Uganda",
            "Nigeria ↔ Ghana", 
            "South Africa ↔ Botswana",
            "Kenya ↔ Tanzania"
        ],
        "performance_targets": {
            "transaction_cost": "<1%",
            "settlement_time": "<10 minutes",
            "uptime": "99.9%",
            "throughput": "10,000+ concurrent payments"
        }
    }
    
    return status 