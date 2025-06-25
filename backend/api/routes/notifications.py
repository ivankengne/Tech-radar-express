"""
Tech Radar Express - Routes API Notifications
Endpoints pour la gestion des notifications WebSocket avec seuils configurables
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
import structlog
import json

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

class NotificationResponse(BaseModel):
    """Modèle de réponse pour notifications"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class PreferencesUpdateRequest(BaseModel):
    """Requête de mise à jour des préférences"""
    enabled_types: List[str] = Field(default=[], description="Types de notifications activés")
    min_priority: str = Field(default="medium", description="Priorité minimale")
    pertinence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Seuil de pertinence")
    quiet_hours_start: Optional[str] = Field(default=None)
    quiet_hours_end: Optional[str] = Field(default=None)
    max_notifications_per_hour: int = Field(default=10, ge=1, le=100)
    email_notifications: bool = Field(default=False)
    desktop_notifications: bool = Field(default=True)
    sound_enabled: bool = Field(default=True)

class TestNotificationRequest(BaseModel):
    """Requête de test de notification"""
    title: str = Field(..., max_length=100)
    message: str = Field(..., max_length=500)
    type: str = Field(default="system_status")
    priority: str = Field(default="medium")
    pertinence_score: float = Field(default=0.8, ge=0.0, le=1.0)

# Variables globales pour simplifier
_websocket_connections = {}

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(default="default", description="ID utilisateur")
):
    """Endpoint WebSocket pour notifications temps réel"""
    connection_id = f"conn_{datetime.now().timestamp()}"
    
    try:
        await websocket.accept()
        _websocket_connections[connection_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "connected_at": datetime.now()
        }
        
        logger.info("Connexion WebSocket établie", connection_id=connection_id, user_id=user_id)
        
        # Message de bienvenue
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {
                "connection_id": connection_id,
                "user_id": user_id,
                "server_time": datetime.now().isoformat()
            }
        }))
        
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Gestion des messages ping
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "data": {"timestamp": datetime.now().isoformat()}
                    }))
                
            except json.JSONDecodeError:
                logger.warning("Message WebSocket JSON invalide", connection_id=connection_id)
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Format JSON invalide"}
                }))
            
    except WebSocketDisconnect:
        logger.info("Déconnexion WebSocket", connection_id=connection_id)
    except Exception as e:
        logger.error("Erreur WebSocket", connection_id=connection_id, error=str(e))
    finally:
        if connection_id in _websocket_connections:
            del _websocket_connections[connection_id]

@router.get("/preferences", response_model=NotificationResponse)
async def get_user_preferences(
    user_id: str = Query(default="default", description="ID utilisateur")
):
    """Récupère les préférences de notifications d'un utilisateur"""
    try:
        # Valeurs par défaut simulées
        preferences_data = {
            "enabled_types": ["critical_alert", "custom_alert", "daily_summary"],
            "min_priority": "medium",
            "pertinence_threshold": 0.7,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "max_notifications_per_hour": 10,
            "email_notifications": False,
            "desktop_notifications": True,
            "sound_enabled": True,
            "updated_at": datetime.now().isoformat()
        }
        
        return NotificationResponse(
            success=True,
            data={"preferences": preferences_data},
            metadata={"user_id": user_id}
        )
        
    except Exception as e:
        logger.error("Erreur récupération préférences", user_id=user_id, error=str(e))
        return NotificationResponse(
            success=False,
            error=f"Erreur récupération préférences: {str(e)}"
        )

@router.put("/preferences", response_model=NotificationResponse)
async def update_user_preferences(
    request: PreferencesUpdateRequest,
    user_id: str = Query(default="default", description="ID utilisateur")
):
    """Met à jour les préférences de notifications d'un utilisateur"""
    try:
        # Validation des types de notifications
        valid_types = {
            "critical_alert", "custom_alert", "daily_summary", "focus_mode",
            "source_update", "system_status", "crawl_complete", "new_insight"
        }
        
        invalid_types = set(request.enabled_types) - valid_types
        if invalid_types:
            return NotificationResponse(
                success=False,
                error=f"Types de notification invalides: {', '.join(invalid_types)}"
            )
        
        # Validation de la priorité
        valid_priorities = {"low", "medium", "high", "urgent", "critical"}
        if request.min_priority not in valid_priorities:
            return NotificationResponse(
                success=False,
                error=f"Priorité invalide: {request.min_priority}"
            )
        
        # Simulation de sauvegarde
        logger.info("Préférences mises à jour", user_id=user_id, preferences=request.dict())
        
        return NotificationResponse(
            success=True,
            data={"message": "Préférences mises à jour avec succès"},
            metadata={
                "user_id": user_id,
                "updated_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Erreur mise à jour préférences", user_id=user_id, error=str(e))
        return NotificationResponse(
            success=False,
            error=f"Erreur mise à jour préférences: {str(e)}"
        )

@router.get("/types", response_model=NotificationResponse)
async def get_notification_types():
    """Liste les types et priorités de notifications disponibles"""
    try:
        types_data = [
            {
                "value": "critical_alert",
                "label": "Alertes Critiques",
                "description": "Alertes critiques détectées automatiquement"
            },
            {
                "value": "custom_alert",
                "label": "Alertes Personnalisées",
                "description": "Alertes personnalisées configurées"
            },
            {
                "value": "daily_summary",
                "label": "Résumé Quotidien",
                "description": "Résumés quotidiens générés"
            },
            {
                "value": "focus_mode",
                "label": "Mode Focus",
                "description": "Synthèses focus mode rapides"
            },
            {
                "value": "system_status",
                "label": "Statut Système",
                "description": "Statut et alertes système"
            }
        ]
        
        priorities_data = [
            {
                "value": "low",
                "label": "Faible",
                "description": "Information générale sans urgence"
            },
            {
                "value": "medium",
                "label": "Moyenne",
                "description": "Information importante à connaître"
            },
            {
                "value": "high",
                "label": "Élevée",
                "description": "Attention requise prochainement"
            },
            {
                "value": "urgent",
                "label": "Urgent",
                "description": "Action recommandée rapidement"
            },
            {
                "value": "critical",
                "label": "Critique",
                "description": "Action immédiate nécessaire"
            }
        ]
        
        return NotificationResponse(
            success=True,
            data={
                "types": types_data,
                "priorities": priorities_data
            }
        )
        
    except Exception as e:
        logger.error("Erreur récupération types", error=str(e))
        return NotificationResponse(
            success=False,
            error=f"Erreur récupération types: {str(e)}"
        )

@router.post("/test", response_model=NotificationResponse)
async def send_test_notification(
    request: TestNotificationRequest,
    user_id: str = Query(default="default")
):
    """Envoie une notification de test"""
    try:
        # Simulation d'envoi via WebSocket
        notification_data = {
            "type": "notification",
            "data": {
                "id": f"test_{datetime.now().timestamp()}",
                "type": request.type,
                "priority": request.priority,
                "title": f"🧪 Test: {request.title}",
                "message": request.message,
                "pertinence_score": request.pertinence_score,
                "created_at": datetime.now().isoformat(),
                "test": True
            }
        }
        
        # Envoi à toutes les connexions WebSocket actives
        sent_count = 0
        for conn_id, conn_info in _websocket_connections.items():
            if conn_info["user_id"] == user_id or user_id == "default":
                try:
                    await conn_info["websocket"].send_text(json.dumps(notification_data))
                    sent_count += 1
                except Exception as e:
                    logger.warning("Erreur envoi notification test", error=str(e))
        
        logger.info("Notification de test envoyée",
                   user_id=user_id,
                   title=request.title,
                   type=request.type,
                   sent_to_connections=sent_count)
        
        return NotificationResponse(
            success=True,
            data={
                "message": "Notification de test envoyée",
                "sent_to_connections": sent_count
            },
            metadata={
                "test_notification": True,
                "sent_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Erreur notification de test", error=str(e))
        return NotificationResponse(
            success=False,
            error=f"Erreur envoi test: {str(e)}"
        )

@router.get("/websocket/stats", response_model=NotificationResponse)
async def get_websocket_stats():
    """Statistiques des connexions WebSocket actives"""
    try:
        active_users = set()
        for conn_info in _websocket_connections.values():
            if conn_info["user_id"]:
                active_users.add(conn_info["user_id"])
        
        stats = {
            "total_connections": len(_websocket_connections),
            "unique_users": len(active_users),
            "active_topics": 0,  # À implémenter
            "last_updated": datetime.now().isoformat()
        }
        
        return NotificationResponse(
            success=True,
            data={"websocket_stats": stats}
        )
        
    except Exception as e:
        logger.error("Erreur stats WebSocket", error=str(e))
        return NotificationResponse(
            success=False,
            error=f"Erreur stats WebSocket: {str(e)}"
        )
