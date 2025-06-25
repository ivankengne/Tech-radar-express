"""
Tech Radar Express - Crawl Monitoring API Routes
Routes pour le monitoring des crawls MCP avec statuts temps réel
"""

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio
import structlog

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

# Router pour les routes de monitoring des crawls
router = APIRouter(prefix="/api/v1/crawl-monitoring", tags=["crawl-monitoring"])

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

@router.get("/status")
async def get_monitoring_status():
    """Récupère le statut général du monitoring des crawls"""
    try:
        monitor = get_crawl_monitor()
        source_manager = await get_source_manager()
        
        active_crawls = monitor.get_all_active_crawls()
        metrics = monitor.get_metrics()
        recent_alerts = monitor.get_alerts(acknowledged=False, limit=10)
        
        return JSONResponse({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_crawls_count": len(active_crawls),
            "total_sources": len(source_manager.get_all_sources()),
            "enabled_sources": len([s for s in source_manager.get_all_sources() if s.enabled]),
            "metrics": {
                "total_crawls": metrics.total_crawls,
                "success_rate": round(metrics.success_rate * 100, 1),
                "error_rate": round(metrics.error_rate * 100, 1),
                "avg_crawl_time": round(metrics.avg_crawl_time, 2),
                "throughput_per_hour": metrics.throughput_per_hour
            },
            "unacknowledged_alerts": len(recent_alerts),
            "recent_alerts": [
                {
                    "id": alert.id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in recent_alerts[:5]
            ]
        })
    
    except Exception as e:
        logger.error("Erreur récupération statut monitoring", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/crawls/active")
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

@router.get("/crawls/{source_id}/status")
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

@router.post("/crawls/{source_id}/cancel")
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

@router.get("/crawls/{source_id}/history")
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

@router.get("/errors")
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

@router.get("/errors/patterns")
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

@router.get("/alerts")
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

@router.post("/alerts/{alert_id}/acknowledge")
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

@router.get("/metrics")
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

@router.get("/metrics/history")
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

@router.get("/health")
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

@router.websocket("/ws")
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