"""
Routes API pour le monitoring Langfuse.

Permet de :
- Consulter les métriques LLM
- Visualiser les traces récentes
- Accéder au dashboard de monitoring
- Gérer les configurations de traçage
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
import asyncio
import structlog

from core.langfuse_manager import LangfuseManager, LLMProvider, CallType
from ...core.crawl_monitor import (
    get_crawl_monitor, 
    CrawlStatus, 
    ErrorType, 
    AlertLevel,
    MonitoringMetrics
)
from ...core.source_manager import get_source_manager

# Configuration du logger
logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])
limiter = Limiter(key_func=get_remote_address)

# === Modèles de réponse ===

class MetricsSummaryResponse(BaseModel):
    """Résumé des métriques LLM."""
    total_calls: int
    total_tokens: int
    total_cost: float
    avg_duration: float
    success_rate: float
    providers: Dict[str, Dict[str, Any]]
    models: Dict[str, Dict[str, Any]]
    period: str
    last_updated: str

class TraceResponse(BaseModel):
    """Réponse pour une trace LLM."""
    trace_id: str
    name: str
    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: float
    success: bool
    error: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class ProviderStatsResponse(BaseModel):
    """Statistiques par provider LLM."""
    provider: str
    total_calls: int
    total_tokens: int
    total_cost: float
    avg_duration: float
    success_rate: float
    most_used_model: str
    last_call: Optional[datetime] = None

class DashboardResponse(BaseModel):
    """Données complètes du dashboard monitoring."""
    summary: MetricsSummaryResponse
    recent_traces: List[TraceResponse]
    provider_stats: List[ProviderStatsResponse]
    hourly_stats: List[Dict[str, Any]]
    cost_breakdown: Dict[str, float]
    error_analysis: Dict[str, Any]

# === Dépendances ===

async def get_langfuse_manager(request: Request) -> LangfuseManager:
    """Récupère l'instance du gestionnaire Langfuse."""
    if not hasattr(request.app.state, 'langfuse_manager'):
        raise HTTPException(status_code=503, detail="Gestionnaire Langfuse non initialisé")
    return request.app.state.langfuse_manager

# === Endpoints ===

@router.get("/status")
@limiter.limit("10/minute")
async def get_monitoring_status(
    request: Request,
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Récupère le statut du système de monitoring."""
    try:
        return JSONResponse(
            status_code=200,
            content={
                "enabled": langfuse_manager.is_enabled,
                "connected": langfuse_manager.client is not None,
                "cache_size": len(langfuse_manager.metrics_cache),
                "host": langfuse_manager.config.langfuse.host,
                "version": "1.0.0",
                "uptime": "À calculer",
                "last_flush": "À implémenter"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du statut: {e}")

@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
@limiter.limit("20/minute")
async def get_metrics_summary(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    provider: Optional[str] = Query(None, description="Filtrer par provider"),
    model: Optional[str] = Query(None, description="Filtrer par modèle"),
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Récupère un résumé des métriques LLM."""
    try:
        # Conversion du provider en enum si fourni
        provider_enum = None
        if provider:
            try:
                provider_enum = LLMProvider(provider.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Provider invalide: {provider}")
        
        summary = await langfuse_manager.get_metrics_summary(
            start_date=start_date,
            end_date=end_date,
            provider=provider_enum,
            model=model
        )
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        return MetricsSummaryResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des métriques: {e}")

@router.get("/traces/recent", response_model=List[TraceResponse])
@limiter.limit("30/minute")
async def get_recent_traces(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Nombre de traces à récupérer"),
    provider: Optional[str] = Query(None, description="Filtrer par provider"),
    success_only: bool = Query(False, description="Seulement les traces réussies"),
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Récupère les traces récentes."""
    try:
        traces = await langfuse_manager.get_recent_traces(limit=limit)
        
        # Filtrage par provider si spécifié
        if provider:
            traces = [t for t in traces if t.get('provider', '').lower() == provider.lower()]
        
        # Filtrage par succès si demandé
        if success_only:
            traces = [t for t in traces if t.get('success', False)]
        
        # Conversion en modèles de réponse
        trace_responses = []
        for trace in traces:
            try:
                trace_response = TraceResponse(
                    trace_id=trace.get('call_id', ''),
                    name=f"{trace.get('provider', '')}_{trace.get('call_type', '')}",
                    timestamp=datetime.fromisoformat(trace.get('timestamp', datetime.utcnow().isoformat())),
                    provider=trace.get('provider', ''),
                    model=trace.get('model', ''),
                    input_tokens=trace.get('input_tokens', 0),
                    output_tokens=trace.get('output_tokens', 0),
                    total_tokens=trace.get('total_tokens', 0),
                    cost_usd=trace.get('cost_usd', 0.0),
                    duration_ms=trace.get('duration_ms', 0.0),
                    success=trace.get('success', False),
                    error=trace.get('error'),
                    user_id=trace.get('user_id'),
                    session_id=trace.get('session_id')
                )
                trace_responses.append(trace_response)
            except Exception as e:
                # Log l'erreur mais continue avec les autres traces
                continue
        
        return trace_responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des traces: {e}")

@router.get("/providers/stats", response_model=List[ProviderStatsResponse])
@limiter.limit("20/minute")
async def get_provider_stats(
    request: Request,
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Récupère les statistiques par provider LLM."""
    try:
        summary = await langfuse_manager.get_metrics_summary()
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        provider_stats = []
        for provider_name, stats in summary.get("providers", {}).items():
            # Calcul du modèle le plus utilisé (placeholder)
            most_used_model = "À implémenter"  # Nécessite plus de données détaillées
            
            # Calcul du taux de succès (placeholder)
            success_rate = 95.0  # Placeholder
            
            # Durée moyenne (placeholder)
            avg_duration = 1500.0  # Placeholder
            
            provider_stat = ProviderStatsResponse(
                provider=provider_name,
                total_calls=stats.get('calls', 0),
                total_tokens=stats.get('tokens', 0),
                total_cost=stats.get('cost', 0.0),
                avg_duration=avg_duration,
                success_rate=success_rate,
                most_used_model=most_used_model,
                last_call=None  # À implémenter
            )
            provider_stats.append(provider_stat)
        
        return provider_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des stats providers: {e}")

@router.get("/dashboard", response_model=DashboardResponse)
@limiter.limit("10/minute")
async def get_dashboard_data(
    request: Request,
    hours: int = Query(24, ge=1, le=168, description="Période en heures"),
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Récupère toutes les données pour le dashboard de monitoring."""
    try:
        # Récupération des données de base
        summary = await langfuse_manager.get_metrics_summary()
        recent_traces_data = await langfuse_manager.get_recent_traces(limit=20)
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        # Conversion du résumé
        summary_response = MetricsSummaryResponse(**summary)
        
        # Conversion des traces récentes
        recent_traces = []
        for trace in recent_traces_data:
            try:
                trace_response = TraceResponse(
                    trace_id=trace.get('call_id', ''),
                    name=f"{trace.get('provider', '')}_{trace.get('call_type', '')}",
                    timestamp=datetime.fromisoformat(trace.get('timestamp', datetime.utcnow().isoformat())),
                    provider=trace.get('provider', ''),
                    model=trace.get('model', ''),
                    input_tokens=trace.get('input_tokens', 0),
                    output_tokens=trace.get('output_tokens', 0),
                    total_tokens=trace.get('total_tokens', 0),
                    cost_usd=trace.get('cost_usd', 0.0),
                    duration_ms=trace.get('duration_ms', 0.0),
                    success=trace.get('success', False),
                    error=trace.get('error'),
                    user_id=trace.get('user_id'),
                    session_id=trace.get('session_id')
                )
                recent_traces.append(trace_response)
            except Exception:
                continue
        
        # Stats par provider
        provider_stats = []
        for provider_name, stats in summary.get("providers", {}).items():
            provider_stat = ProviderStatsResponse(
                provider=provider_name,
                total_calls=stats.get('calls', 0),
                total_tokens=stats.get('tokens', 0),
                total_cost=stats.get('cost', 0.0),
                avg_duration=1500.0,  # Placeholder
                success_rate=95.0,    # Placeholder
                most_used_model="À implémenter",
                last_call=None
            )
            provider_stats.append(provider_stat)
        
        # Statistiques horaires (placeholder)
        hourly_stats = []
        for i in range(hours):
            hour_stat = {
                "hour": (datetime.utcnow() - timedelta(hours=i)).strftime("%H:00"),
                "calls": 10 - i,  # Placeholder
                "tokens": (10 - i) * 1000,  # Placeholder
                "cost": (10 - i) * 0.01,  # Placeholder
                "errors": max(0, i - 20)  # Placeholder
            }
            hourly_stats.append(hour_stat)
        
        # Répartition des coûts
        cost_breakdown = {}
        for provider_name, stats in summary.get("providers", {}).items():
            cost_breakdown[provider_name] = stats.get('cost', 0.0)
        
        # Analyse des erreurs (placeholder)
        error_analysis = {
            "total_errors": 5,  # Placeholder
            "error_rate": 2.1,  # Placeholder
            "common_errors": {
                "timeout": 2,
                "api_limit": 2,
                "invalid_request": 1
            },
            "error_trend": "stable"  # Placeholder
        }
        
        dashboard_data = DashboardResponse(
            summary=summary_response,
            recent_traces=recent_traces,
            provider_stats=provider_stats,
            hourly_stats=hourly_stats,
            cost_breakdown=cost_breakdown,
            error_analysis=error_analysis
        )
        
        return dashboard_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données dashboard: {e}")

@router.post("/flush")
@limiter.limit("5/minute")
async def flush_metrics(
    request: Request,
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Force l'envoi des métriques en attente vers Langfuse."""
    try:
        await langfuse_manager.flush_metrics()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Métriques envoyées avec succès",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du flush des métriques: {e}")

@router.delete("/metrics/cleanup")
@limiter.limit("2/minute")
async def cleanup_old_metrics(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Nombre de jours à conserver"),
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Nettoie les anciennes métriques."""
    try:
        await langfuse_manager.cleanup_old_metrics(days_to_keep=days)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Nettoyage effectué : métriques de plus de {days} jours supprimées",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du nettoyage: {e}")

@router.get("/config")
@limiter.limit("10/minute")
async def get_monitoring_config(
    request: Request,
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Récupère la configuration actuelle du monitoring."""
    try:
        config = langfuse_manager.config.langfuse
        
        return JSONResponse(
            status_code=200,
            content={
                "host": config.host,
                "enabled": config.enabled,
                "debug": config.debug,
                "threads": config.threads,
                "flush_at": config.flush_at,
                "flush_interval": config.flush_interval,
                "max_retries": config.max_retries,
                "timeout": config.timeout,
                "sdk_integration": config.sdk_integration,
                "is_configured": config.is_configured
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de la configuration: {e}")

@router.get("/health")
async def monitoring_health_check(
    request: Request,
    langfuse_manager: LangfuseManager = Depends(get_langfuse_manager)
):
    """Vérification de santé du système de monitoring."""
    try:
        health_status = {
            "langfuse_enabled": langfuse_manager.is_enabled,
            "client_connected": langfuse_manager.client is not None,
            "cache_size": len(langfuse_manager.metrics_cache),
            "cache_limit": langfuse_manager.cache_size_limit,
        }
        
        # Test de connectivité basique
        try:
            if langfuse_manager.client:
                # Test simple - cela devrait être remplacé par un vrai test
                health_status["connectivity"] = "ok"
            else:
                health_status["connectivity"] = "no_client"
        except Exception:
            health_status["connectivity"] = "error"
        
        overall_healthy = (
            health_status["langfuse_enabled"] 
            and health_status["client_connected"]
            and health_status["connectivity"] == "ok"
        )
        
        return JSONResponse(
            status_code=200 if overall_healthy else 503,
            content={
                **health_status,
                "overall_status": "healthy" if overall_healthy else "degraded",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Router pour les routes de monitoring
monitoring_router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

# Gestionnaire des connexions WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connecté", total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket déconnecté", total_connections=len(self.active_connections))
    
    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.warning("Erreur envoi WebSocket", error=str(e))
                disconnected.append(connection)
        
        # Nettoyage des connexions fermées
        for connection in disconnected:
            self.disconnect(connection)

connection_manager = ConnectionManager()

@monitoring_router.get("/crawls/active")
async def get_active_crawls():
    """Récupère tous les crawls actifs"""
    try:
        monitor = get_crawl_monitor()
        active_crawls = monitor.get_all_active_crawls()
        
        return JSONResponse({
            "active_crawls": [
                {
                    "source_id": progress.source_id,
                    "status": progress.status.value,
                    "current_step": progress.current_step,
                    "start_time": progress.start_time.isoformat(),
                    "pages_discovered": progress.pages_discovered,
                    "pages_crawled": progress.pages_crawled,
                    "pages_processed": progress.pages_processed,
                    "chunks_created": progress.chunks_created,
                    "errors_count": progress.errors_count,
                    "last_error": progress.last_error,
                    "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                    "duration_seconds": (datetime.now() - progress.start_time).total_seconds(),
                    "progress_percentage": round((progress.pages_crawled / max(progress.pages_discovered, 1)) * 100, 1),
                    "metadata": progress.metadata
                }
                for progress in active_crawls.values()
            ],
            "total_active": len(active_crawls),
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur récupération crawls actifs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/crawls/{source_id}/status")
async def get_crawl_status(source_id: str):
    """Récupère le statut d'un crawl spécifique"""
    try:
        monitor = get_crawl_monitor()
        progress = monitor.get_crawl_status(source_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail=f"Crawl {source_id} non trouvé")
        
        return JSONResponse({
            "source_id": progress.source_id,
            "status": progress.status.value,
            "current_step": progress.current_step,
            "start_time": progress.start_time.isoformat(),
            "pages_discovered": progress.pages_discovered,
            "pages_crawled": progress.pages_crawled,
            "pages_processed": progress.pages_processed,
            "chunks_created": progress.chunks_created,
            "errors_count": progress.errors_count,
            "last_error": progress.last_error,
            "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
            "duration_seconds": (datetime.now() - progress.start_time).total_seconds(),
            "progress_percentage": round((progress.pages_crawled / max(progress.pages_discovered, 1)) * 100, 1),
            "metadata": progress.metadata
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération statut crawl", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.post("/crawls/{source_id}/cancel")
async def cancel_crawl(source_id: str, reason: str = "Annulé par l'utilisateur"):
    """Annule un crawl en cours"""
    try:
        monitor = get_crawl_monitor()
        progress = monitor.get_crawl_status(source_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail=f"Crawl {source_id} non trouvé")
        
        monitor.cancel_crawl(source_id, reason)
        
        # Notification WebSocket
        await connection_manager.broadcast({
            "type": "crawl_cancelled",
            "source_id": source_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        return JSONResponse({
            "message": f"Crawl {source_id} annulé",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur annulation crawl", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/crawls/{source_id}/history")
async def get_crawl_history(
    source_id: str,
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats")
):
    """Récupère l'historique des crawls d'une source"""
    try:
        monitor = get_crawl_monitor()
        history = monitor.get_crawl_history(source_id, limit)
        
        return JSONResponse({
            "source_id": source_id,
            "history": history,
            "total_records": len(history),
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur récupération historique crawl", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/errors")
async def get_errors(
    source_id: Optional[str] = Query(None, description="Filtrer par source"),
    error_type: Optional[str] = Query(None, description="Filtrer par type d'erreur"),
    limit: int = Query(100, ge=1, le=500, description="Nombre max de résultats"),
    hours: int = Query(24, ge=1, le=168, description="Période en heures")
):
    """Récupère l'historique des erreurs"""
    try:
        monitor = get_crawl_monitor()
        errors = monitor.get_error_history(source_id, limit)
        
        # Filtrage par période
        cutoff = datetime.now() - timedelta(hours=hours)
        errors = [e for e in errors if e.timestamp >= cutoff]
        
        # Filtrage par type d'erreur
        if error_type:
            try:
                error_enum = ErrorType(error_type)
                errors = [e for e in errors if e.error_type == error_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type d'erreur invalide: {error_type}")
        
        return JSONResponse({
            "errors": [
                {
                    "source_id": error.source_id,
                    "error_type": error.error_type.value,
                    "error_message": error.error_message,
                    "error_details": error.error_details,
                    "timestamp": error.timestamp.isoformat(),
                    "url": error.url,
                    "retry_count": error.retry_count,
                    "resolved": error.resolved
                }
                for error in errors
            ],
            "total_errors": len(errors),
            "filters": {
                "source_id": source_id,
                "error_type": error_type,
                "hours": hours
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération erreurs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/errors/patterns")
async def get_error_patterns():
    """Récupère les patterns d'erreurs les plus fréquents"""
    try:
        monitor = get_crawl_monitor()
        
        # Analyse des patterns dans les dernières 24h
        cutoff = datetime.now() - timedelta(hours=24)
        recent_errors = [e for e in monitor.error_history if e.timestamp >= cutoff]
        
        # Comptage par type et source
        patterns = {}
        for error in recent_errors:
            pattern_key = f"{error.error_type.value}:{error.source_id}"
            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    "error_type": error.error_type.value,
                    "source_id": error.source_id,
                    "count": 0,
                    "first_occurrence": error.timestamp,
                    "last_occurrence": error.timestamp,
                    "sample_message": error.error_message
                }
            
            patterns[pattern_key]["count"] += 1
            if error.timestamp > patterns[pattern_key]["last_occurrence"]:
                patterns[pattern_key]["last_occurrence"] = error.timestamp
        
        # Tri par fréquence
        sorted_patterns = sorted(patterns.values(), key=lambda x: x["count"], reverse=True)
        
        return JSONResponse({
            "patterns": [
                {
                    **pattern,
                    "first_occurrence": pattern["first_occurrence"].isoformat(),
                    "last_occurrence": pattern["last_occurrence"].isoformat()
                }
                for pattern in sorted_patterns[:20]
            ],
            "total_patterns": len(sorted_patterns),
            "analysis_period_hours": 24,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur récupération patterns erreurs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/alerts")
async def get_alerts(
    acknowledged: Optional[bool] = Query(None, description="Filtrer par statut d'acquittement"),
    level: Optional[str] = Query(None, description="Filtrer par niveau d'alerte"),
    source_id: Optional[str] = Query(None, description="Filtrer par source"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats")
):
    """Récupère les alertes"""
    try:
        monitor = get_crawl_monitor()
        alerts = monitor.get_alerts(acknowledged, limit)
        
        # Filtrage par niveau
        if level:
            try:
                level_enum = AlertLevel(level)
                alerts = [a for a in alerts if a.level == level_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Niveau d'alerte invalide: {level}")
        
        # Filtrage par source
        if source_id:
            alerts = [a for a in alerts if a.source_id == source_id]
        
        return JSONResponse({
            "alerts": [
                {
                    "id": alert.id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "message": alert.message,
                    "source_id": alert.source_id,
                    "timestamp": alert.timestamp.isoformat(),
                    "acknowledged": alert.acknowledged,
                    "metadata": alert.metadata
                }
                for alert in alerts
            ],
            "total_alerts": len(alerts),
            "filters": {
                "acknowledged": acknowledged,
                "level": level,
                "source_id": source_id
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération alertes", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Marque une alerte comme acquittée"""
    try:
        monitor = get_crawl_monitor()
        success = monitor.acknowledge_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Alerte {alert_id} non trouvée")
        
        # Notification WebSocket
        await connection_manager.broadcast({
            "type": "alert_acknowledged",
            "alert_id": alert_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return JSONResponse({
            "message": f"Alerte {alert_id} acquittée",
            "timestamp": datetime.now().isoformat()
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur acquittement alerte", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/metrics")
async def get_metrics():
    """Récupère les métriques de monitoring"""
    try:
        monitor = get_crawl_monitor()
        metrics = monitor.get_metrics()
        
        return JSONResponse({
            "metrics": {
                "total_crawls": metrics.total_crawls,
                "active_crawls": metrics.active_crawls,
                "successful_crawls": metrics.successful_crawls,
                "failed_crawls": metrics.failed_crawls,
                "success_rate": round(metrics.success_rate * 100, 2),
                "error_rate": round(metrics.error_rate * 100, 2),
                "avg_crawl_time": round(metrics.avg_crawl_time, 2),
                "avg_pages_per_crawl": round(metrics.avg_pages_per_crawl, 1),
                "avg_chunks_per_crawl": round(metrics.avg_chunks_per_crawl, 1),
                "throughput_per_hour": metrics.throughput_per_hour,
                "last_updated": metrics.last_updated.isoformat()
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur récupération métriques", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/metrics/history")
async def get_metrics_history(
    hours: int = Query(24, ge=1, le=168, description="Période en heures")
):
    """Récupère l'historique des métriques"""
    try:
        monitor = get_crawl_monitor()
        metrics_history = monitor.get_metrics_history(hours)
        
        return JSONResponse({
            "metrics_history": [
                {
                    "total_crawls": m.total_crawls,
                    "active_crawls": m.active_crawls,
                    "successful_crawls": m.successful_crawls,
                    "failed_crawls": m.failed_crawls,
                    "success_rate": round(m.success_rate * 100, 2),
                    "error_rate": round(m.error_rate * 100, 2),
                    "avg_crawl_time": round(m.avg_crawl_time, 2),
                    "throughput_per_hour": m.throughput_per_hour,
                    "timestamp": m.last_updated.isoformat()
                }
                for m in metrics_history
            ],
            "total_records": len(metrics_history),
            "period_hours": hours,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur récupération historique métriques", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@monitoring_router.get("/health")
async def get_monitoring_health():
    """Vérifie la santé du système de monitoring"""
    try:
        monitor = get_crawl_monitor()
        source_manager = await get_source_manager()
        
        # Vérifications de santé
        health_checks = {
            "monitor_active": True,
            "source_manager_active": True,
            "active_crawls": len(monitor.get_all_active_crawls()),
            "recent_errors": len([e for e in monitor.error_history 
                                if e.timestamp >= datetime.now() - timedelta(hours=1)]),
            "unacknowledged_alerts": len(monitor.get_alerts(acknowledged=False)),
            "websocket_connections": len(connection_manager.active_connections)
        }
        
        # Statut général
        status = "healthy"
        if health_checks["recent_errors"] > 10:
            status = "degraded"
        if health_checks["unacknowledged_alerts"] > 5:
            status = "warning"
        
        return JSONResponse({
            "status": status,
            "health_checks": health_checks,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur vérification santé monitoring", error=str(e))
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status_code=503)

@monitoring_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les mises à jour temps réel"""
    await connection_manager.connect(websocket)
    try:
        while True:
            # Envoi périodique du statut
            monitor = get_crawl_monitor()
            active_crawls = monitor.get_all_active_crawls()
            
            status_update = {
                "type": "status_update",
                "active_crawls": [
                    {
                        "source_id": progress.source_id,
                        "status": progress.status.value,
                        "current_step": progress.current_step,
                        "progress_percentage": round((progress.pages_crawled / max(progress.pages_discovered, 1)) * 100, 1),
                        "pages_crawled": progress.pages_crawled,
                        "chunks_created": progress.chunks_created,
                        "errors_count": progress.errors_count
                    }
                    for progress in active_crawls.values()
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_text(json.dumps(status_update, default=str))
            await asyncio.sleep(5)  # Mise à jour toutes les 5 secondes
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error("Erreur WebSocket monitoring", error=str(e))
        connection_manager.disconnect(websocket)