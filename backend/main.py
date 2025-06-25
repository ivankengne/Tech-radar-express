"""
Tech Radar Express - Backend FastAPI
Point d'entrée principal de l'API backend - Production Ready 2024-2025
"""

import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
from pathlib import Path

# FastAPI et middleware
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configuration et environnement
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Import des routes
from api.routes import mcp, scheduler, monitoring, dashboard, websocket, search, llm, sources, daily_summary, focus_mode, alerts, critical_alerts, notifications, activity_feed

# Import des modules core
from core.config_manager import ConfigManager, get_settings
from core.structlog_manager import setup_logging, get_logger
from core.scheduler import TaskScheduler
from core.langfuse_manager import LangfuseManager
from database.redis_client import RedisClient

# Configuration structurée du logging
import structlog

# Chargement des variables d'environnement
load_dotenv()

class Settings(BaseSettings):
    """Configuration de l'application avec validation Pydantic"""
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # API Configuration
    api_title: str = "Tech Radar Express API"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    allowed_hosts: list = ["*"]
    cors_origins: list = ["http://localhost:3000"]
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Configuration globale
settings = Settings()

# Configuration du logging structuré selon la documentation officielle
def configure_logging():
    """Configuration du logging structuré avec structlog basée sur la documentation officielle"""
    try:
        # Récupération de la configuration
        config_manager = get_settings()
        logging_config = config_manager.logging
        
        # Setup structlog avec la configuration correcte
        setup_logging(logging_config)
        
        return get_logger(__name__)
    except Exception as e:
        # Fallback vers configuration basique
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        return logging.getLogger(__name__)

logger = configure_logging()

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire du cycle de vie de l'application avec gestion d'erreurs renforcée"""
    logger.info("🚀 Démarrage de Tech Radar Express Backend", 
                environment=settings.environment,
                version=settings.api_version)
    
    # Initialisation des services
    startup_tasks = []
    
    try:
        # Connexion Redis avec retry
        async def init_redis():
            redis_client = RedisClient()
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await redis_client.connect()
                    app.state.redis = redis_client
                    logger.info("✅ Redis connecté avec succès")
                    return
                except Exception as e:
                    logger.warning(f"Tentative Redis {attempt + 1}/{max_retries} échouée", error=str(e))
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
        
        startup_tasks.append(init_redis())
        
        # Démarrage du gestionnaire Langfuse
        async def init_langfuse():
            try:
                # CORRECTION: Utiliser l'instance unique de ConfigManager
                config_manager = ConfigManager()
                if hasattr(config_manager, 'monitoring_enabled') and config_manager.monitoring_enabled:
                    langfuse_manager = LangfuseManager(config_manager, app.state.redis)
                    await langfuse_manager.initialize()
                    app.state.langfuse_manager = langfuse_manager
                    logger.info("✅ Langfuse monitoring initialisé")
                else:
                    logger.warning("⚠️ Langfuse monitoring désactivé (clés manquantes)")
                    app.state.langfuse_manager = None
            except Exception as e:
                logger.error(f"❌ Erreur Langfuse (mode dégradé): {e}")
                app.state.langfuse_manager = None
        
        startup_tasks.append(init_langfuse())
        
        # Démarrage du scheduler avec ConfigManager et Redis
        async def init_scheduler():
            config_manager = ConfigManager()
            scheduler = TaskScheduler(config_manager, app.state.redis)
            await scheduler.start()
            app.state.scheduler = scheduler
            logger.info("✅ Scheduler démarré avec 5 tâches par défaut")
        
        startup_tasks.append(init_scheduler())
        
        # Exécution parallèle des tâches d'initialisation
        await asyncio.gather(*startup_tasks)
        
        logger.info("✅ Tous les services initialisés avec succès")
        
    except Exception as e:
        logger.error("❌ Erreur critique lors de l'initialisation", error=str(e))
        raise
    
    yield
    
    # Nettoyage lors de l'arrêt
    logger.info("🛑 Arrêt gracieux de Tech Radar Express Backend")
    
    cleanup_tasks = []
    
    try:
        # Arrêt du gestionnaire Langfuse
        if hasattr(app.state, 'langfuse_manager') and app.state.langfuse_manager:
            async def cleanup_langfuse():
                await app.state.langfuse_manager.close()
                logger.info("✅ Langfuse fermé")
            cleanup_tasks.append(cleanup_langfuse())
        
        # Arrêt du scheduler
        if hasattr(app.state, 'scheduler'):
            async def cleanup_scheduler():
                await app.state.scheduler.shutdown()
                logger.info("✅ Scheduler arrêté")
            cleanup_tasks.append(cleanup_scheduler())
            
        # Fermeture Redis
        if hasattr(app.state, 'redis'):
            async def cleanup_redis():
                await app.state.redis.disconnect()
                logger.info("✅ Redis déconnecté")
            cleanup_tasks.append(cleanup_redis())
        
        # Exécution parallèle du nettoyage
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        logger.info("✅ Nettoyage effectué avec succès")
        
    except Exception as e:
        logger.error("❌ Erreur lors du nettoyage", error=str(e))

# Initialisation de l'application FastAPI avec configuration de sécurité
app = FastAPI(
    title=settings.api_title,
    description="API backend pour le portail de veille technologique temps réel - Production Ready",
    version=settings.api_version,
    docs_url="/docs" if settings.debug else None,  # Désactiver en production
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
    # Configuration de sécurité
    swagger_ui_parameters={
        "displayOperationId": False,
        "displayRequestDuration": True,
    } if settings.debug else None
)

# Configuration du rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware de sécurité - TrustedHost
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.allowed_hosts
    )

# Configuration CORS sécurisée
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Middleware de compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Middleware de logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware de logging des requêtes avec ID de corrélation"""
    import uuid
    request_id = str(uuid.uuid4())
    
    # Ajouter l'ID de requête aux headers de réponse
    start_time = asyncio.get_event_loop().time()
    
    logger.info("📥 Requête reçue",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host,
                user_agent=request.headers.get("user-agent"))
    
    try:
        response = await call_next(request)
        
        process_time = asyncio.get_event_loop().time() - start_time
        
        logger.info("📤 Réponse envoyée",
                    request_id=request_id,
                    status_code=response.status_code,
                    process_time=f"{process_time:.4f}s")
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = asyncio.get_event_loop().time() - start_time
        
        logger.error("❌ Erreur de traitement",
                     request_id=request_id,
                     error=str(e),
                     process_time=f"{process_time:.4f}s")
        raise

# Gestionnaire d'erreurs global
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire d'erreurs HTTP personnalisé"""
    logger.warning("⚠️ Erreur HTTP",
                   status_code=exc.status_code,
                   detail=exc.detail,
                   url=str(request.url))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs générales"""
    logger.error("💥 Erreur interne",
                 error=str(exc),
                 error_type=type(exc).__name__,
                 url=str(request.url))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Erreur interne du serveur",
            "status_code": 500,
            "path": str(request.url.path)
        }
    )

# Enregistrement des routes avec rate limiting
app.include_router(mcp.router, tags=["MCP crawl4ai-rag"])  # Déjà préfixé dans mcp.py
app.include_router(scheduler.router, tags=["Task Scheduler"])
app.include_router(monitoring.router, tags=["LLM Monitoring"])
app.include_router(dashboard.router, tags=["Dashboard Data"])  # Déjà préfixé dans dashboard.py
app.include_router(websocket.router, tags=["WebSocket"])  # Déjà préfixé dans websocket.py
app.include_router(search.router, tags=["Recherche Conversationnelle"])  # ✅ Activé - Proxy MCP RAG
app.include_router(llm.router, tags=["LLM Configuration"])  # ✅ Déjà préfixé dans llm.py
app.include_router(sources.router, tags=["Sources Management"])  # ✅ Déjà préfixé dans sources.py
app.include_router(daily_summary.router, tags=["Daily Summary"])  # ✅ Générateur résumés quotidiens
app.include_router(focus_mode.router, tags=["Focus Mode"])  # ✅ Mode focus synthèse rapide
app.include_router(alerts.router, tags=["Alerts"])  # ✅ Alertes personnalisées
app.include_router(critical_alerts.router, tags=["Critical Alerts"])  # ✅ Détection alertes critiques LLM
app.include_router(notifications.router, tags=["Notifications"])  # ✅ Système notifications WebSocket
app.include_router(activity_feed.router, tags=["Activity Feed"])  # ✅ Flux d'activité temps réel

# Import et intégration du monitoring des crawls
from api.routes.crawl_monitoring import router as crawl_monitoring_router
app.include_router(crawl_monitoring_router, tags=["Crawl Monitoring"])  # ✅ Monitoring temps réel des crawls MCP

# Import et intégration de la supervision des sources
from api.routes.source_supervision import router as source_supervision_router
app.include_router(source_supervision_router, tags=["Source Supervision"])  # ✅ Dashboard supervision sources avec MCP

@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    """Endpoint racine de l'API"""
    return {
        "message": "Tech Radar Express API",
        "version": settings.api_version,
        "status": "healthy",
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "disabled",
        "timestamp": structlog.processors.TimeStamper(fmt="iso")._stamper()
    }

@app.get("/health")
async def health_check(request: Request):
    """Vérification complète de l'état de santé des services"""
    health_status = {
        "api": "healthy",
        "redis": "unknown",
        "scheduler": "unknown",
        "timestamp": structlog.processors.TimeStamper(fmt="iso")._stamper(),
        "version": settings.api_version,
        "environment": settings.environment
    }
    
    overall_healthy = True
    
    # Vérification Redis avec timeout
    try:
        if hasattr(app.state, 'redis'):
            await asyncio.wait_for(app.state.redis.ping(), timeout=5.0)
            health_status["redis"] = "healthy"
        else:
            health_status["redis"] = "not_configured"
    except asyncio.TimeoutError:
        health_status["redis"] = "timeout"
        overall_healthy = False
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Vérification Scheduler
    try:
        if hasattr(app.state, 'scheduler') and app.state.scheduler.is_running:
            health_status["scheduler"] = "healthy"
        else:
            health_status["scheduler"] = "stopped"
            overall_healthy = False
    except Exception as e:
        health_status["scheduler"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Vérification Langfuse
    try:
        if hasattr(app.state, 'langfuse_manager') and app.state.langfuse_manager:
            if app.state.langfuse_manager.is_enabled:
                health_status["langfuse"] = "healthy"
            else:
                health_status["langfuse"] = "disabled"
        else:
            health_status["langfuse"] = "not_configured"
    except Exception as e:
        health_status["langfuse"] = f"unhealthy: {str(e)}"
    
    health_status["overall"] = "healthy" if overall_healthy else "degraded"
    
    return JSONResponse(
        content=health_status,
        status_code=200 if overall_healthy else 503
    )

@app.get("/api/v1/info")
@limiter.limit("20/minute")
async def api_info(request: Request):
    """Informations détaillées sur l'API et la configuration"""
    return {
        "name": "Tech Radar Express",
        "version": settings.api_version,
        "description": "Portail de veille technologique temps réel",
        "environment": settings.environment,
        "features": [
            "MCP Crawl4AI Integration",
            "Multi-LLM Provider Support (OpenAI, Anthropic, Google)",
            "Real-time WebSocket Communication",
            "Vector Search with Contextual Embeddings",
            "Knowledge Graph Integration",
            "Automated Crawling & Scheduling",
            "Rate Limiting & Security",
            "Structured Logging & Monitoring"
        ],
        "endpoints": {
            "llm": "/api/v1/llm",
            "sources": "/api/v1/sources",
            "search": "/api/v1/search",
            "dashboard": "/api/v1/dashboard",
            "scheduler": "/api/v1/scheduler",
            "monitoring": "/api/v1/monitoring",
            "websocket": "/ws",
            "health": "/health",
            "metrics": "/metrics" if settings.debug else "internal"
        },
        "configuration": {
            "rate_limiting": {
                "requests": settings.rate_limit_requests,
                "window": f"{settings.rate_limit_window}s"
            },
            "cors_origins": settings.cors_origins,
            "debug_mode": settings.debug
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Configuration pour le développement et la production
    uvicorn_config = {
        "app": "main:app",
        "host": settings.api_host,
        "port": settings.api_port,
        "log_level": settings.log_level.lower(),
        "access_log": True,
        "server_header": False,  # Masquer les informations serveur
        "date_header": False,
    }
    
    if settings.debug:
        uvicorn_config.update({
            "reload": True,
            "reload_dirs": ["./"],
        })
    else:
        uvicorn_config.update({
            "workers": settings.api_workers,
            "loop": "uvloop",  # Performance boost
            "http": "httptools",  # Performance boost
        })
    
    uvicorn.run(**uvicorn_config) 