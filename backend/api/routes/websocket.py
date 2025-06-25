"""
Routes WebSocket - Tech Radar Express
Communication temps réel pour notifications dashboard et badge "NEW" animé
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.websockets import WebSocketState
from pydantic import BaseModel, Field
import uuid
from enum import Enum

from core.config_manager import get_settings
from core.structlog_manager import get_logger
from core.mcp_client import MCPCrawl4AIClient

# Configuration du logging
logger = get_logger(__name__)

# Router WebSocket
router = APIRouter(prefix="/ws")

class NotificationType(str, Enum):
    """Types de notifications WebSocket"""
    NEW_INSIGHT = "new_insight"
    KPI_UPDATE = "kpi_update"
    TRENDING_THEME = "trending_theme"
    SOURCE_UPDATE = "source_update"
    SYSTEM_STATUS = "system_status"
    USER_ACTION = "user_action"

class WebSocketMessage(BaseModel):
    """Modèle pour les messages WebSocket"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NotificationType = Field(..., description="Type de notification")
    data: Dict[str, Any] = Field(..., description="Données de la notification")
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: str = Field(default="normal", description="Priorité: low, normal, high, critical")
    badge_text: Optional[str] = Field(None, description="Texte pour badge animé (ex: 'NEW', '3 updates')")
    auto_dismiss: Optional[int] = Field(None, description="Auto-dismiss après X secondes")

class ConnectionManager:
    """Gestionnaire des connexions WebSocket avec groupes et broadcast"""
    
    def __init__(self):
        # Connexions actives par ID de connexion
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Groupes de connexions par topic
        self.connection_groups: Dict[str, Set[str]] = {
            "dashboard": set(),
            "notifications": set(), 
            "admin": set(),
            "global": set()
        }
        
        # Métadonnées des connexions
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Historique des messages récents pour les nouvelles connexions
        self.recent_messages: List[WebSocketMessage] = []
        self.max_history = 50
    
    async def connect(self, websocket: WebSocket, connection_id: str, groups: List[str] = None) -> str:
        """Accepter une nouvelle connexion WebSocket et l'ajouter aux groupes"""
        try:
            await websocket.accept()
            
            # Ajouter la connexion
            self.active_connections[connection_id] = websocket
            
            # Ajouter aux groupes demandés (par défaut: global)
            if not groups:
                groups = ["global"]
            
            for group in groups:
                if group not in self.connection_groups:
                    self.connection_groups[group] = set()
                self.connection_groups[group].add(connection_id)
            
            # Métadonnées de connexion
            self.connection_metadata[connection_id] = {
                "connected_at": datetime.now(),
                "groups": groups,
                "last_ping": datetime.now(),
                "message_count": 0
            }
            
            logger.info("Nouvelle connexion WebSocket", 
                       connection_id=connection_id, 
                       groups=groups,
                       total_connections=len(self.active_connections))
            
            # Envoyer l'historique récent à la nouvelle connexion
            await self._send_history_to_connection(connection_id)
            
            # Notification de connexion aux autres
            welcome_message = WebSocketMessage(
                type=NotificationType.SYSTEM_STATUS,
                data={
                    "status": "user_connected",
                    "connection_id": connection_id,
                    "total_users": len(self.active_connections)
                },
                badge_text="NEW USER",
                auto_dismiss=3
            )
            await self.broadcast_to_group("admin", welcome_message, exclude=[connection_id])
            
            return connection_id
            
        except Exception as e:
            logger.error("Erreur lors de la connexion WebSocket", error=str(e))
            raise
    
    async def disconnect(self, connection_id: str):
        """Supprimer une connexion et nettoyer les métadonnées"""
        try:
            # Supprimer des groupes
            for group_connections in self.connection_groups.values():
                group_connections.discard(connection_id)
            
            # Supprimer la connexion et métadonnées
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            
            if connection_id in self.connection_metadata:
                metadata = self.connection_metadata.pop(connection_id)
                
                logger.info("Connexion WebSocket fermée",
                           connection_id=connection_id,
                           duration=str(datetime.now() - metadata["connected_at"]),
                           messages_sent=metadata["message_count"],
                           total_connections=len(self.active_connections))
            
            # Notification de déconnexion aux admins
            if len(self.active_connections) > 0:
                goodbye_message = WebSocketMessage(
                    type=NotificationType.SYSTEM_STATUS,
                    data={
                        "status": "user_disconnected", 
                        "connection_id": connection_id,
                        "total_users": len(self.active_connections)
                    },
                    priority="low",
                    auto_dismiss=2
                )
                await self.broadcast_to_group("admin", goodbye_message)
                
        except Exception as e:
            logger.error("Erreur lors de la déconnexion WebSocket", error=str(e))
    
    async def send_personal_message(self, message: WebSocketMessage, connection_id: str):
        """Envoyer un message à une connexion spécifique"""
        try:
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message.json())
                    
                    # Mise à jour des métadonnées
                    if connection_id in self.connection_metadata:
                        self.connection_metadata[connection_id]["message_count"] += 1
                        self.connection_metadata[connection_id]["last_ping"] = datetime.now()
                    
                    logger.debug("Message personnel envoyé", 
                               connection_id=connection_id,
                               message_type=message.type)
                else:
                    logger.warning("Connexion fermée côté client", connection_id=connection_id)
                    await self.disconnect(connection_id)
                    
        except Exception as e:
            logger.error("Erreur envoi message personnel", 
                        connection_id=connection_id, 
                        error=str(e))
            await self.disconnect(connection_id)
    
    async def broadcast_to_group(self, group: str, message: WebSocketMessage, exclude: List[str] = None):
        """Broadcaster un message à tous les membres d'un groupe"""
        if exclude is None:
            exclude = []
            
        if group not in self.connection_groups:
            logger.warning("Groupe WebSocket inexistant", group=group)
            return
        
        connections_to_notify = self.connection_groups[group] - set(exclude)
        
        if not connections_to_notify:
            logger.debug("Aucune connexion dans le groupe", group=group)
            return
        
        # Ajouter à l'historique
        self._add_to_history(message)
        
        # Envoi parallèle à toutes les connexions du groupe
        tasks = []
        for connection_id in connections_to_notify:
            tasks.append(self.send_personal_message(message, connection_id))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info("Message broadcasté au groupe", 
                       group=group, 
                       recipients=len(connections_to_notify),
                       message_type=message.type)
    
    async def broadcast_global(self, message: WebSocketMessage, exclude: List[str] = None):
        """Broadcaster à toutes les connexions actives"""
        await self.broadcast_to_group("global", message, exclude)
    
    def _add_to_history(self, message: WebSocketMessage):
        """Ajouter un message à l'historique récent"""
        self.recent_messages.append(message)
        
        # Limiter la taille de l'historique
        if len(self.recent_messages) > self.max_history:
            self.recent_messages = self.recent_messages[-self.max_history:]
    
    async def _send_history_to_connection(self, connection_id: str):
        """Envoyer l'historique récent à une nouvelle connexion"""
        if not self.recent_messages:
            return
            
        # Envoyer les 10 derniers messages
        recent_history = self.recent_messages[-10:]
        
        for message in recent_history:
            # Marquer comme historique pour éviter les badges "NEW"
            historical_message = message.copy()
            historical_message.badge_text = None
            historical_message.auto_dismiss = None
            
            await self.send_personal_message(historical_message, connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques des connexions WebSocket"""
        group_stats = {}
        for group, connections in self.connection_groups.items():
            group_stats[group] = len(connections)
        
        return {
            "total_connections": len(self.active_connections),
            "groups": group_stats,
            "history_size": len(self.recent_messages),
            "uptime_hours": 0  # TODO: calculer depuis le démarrage
        }

# Instance globale du gestionnaire de connexions
connection_manager = ConnectionManager()

async def get_mcp_client() -> MCPCrawl4AIClient:
    """Dependency pour obtenir une instance du client MCP"""
    try:
        config = get_settings()
        return MCPCrawl4AIClient(config)
    except Exception as e:
        logger.error("Erreur lors de l'initialisation du client MCP", error=str(e))
        raise HTTPException(status_code=500, detail="Service MCP indisponible")

@router.websocket("/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    client_id: Optional[str] = None
):
    """
    WebSocket endpoint pour les mises à jour temps réel du dashboard
    Notifications pour KPI, timeline, radar avec badges "NEW" animés
    """
    
    connection_id = client_id or str(uuid.uuid4())
    
    try:
        # Connexion avec groupes dashboard et notifications
        await connection_manager.connect(
            websocket, 
            connection_id, 
            groups=["dashboard", "notifications", "global"]
        )
        
        # Message de bienvenue personnalisé
        welcome_message = WebSocketMessage(
            type=NotificationType.SYSTEM_STATUS,
            data={
                "status": "connected",
                "connection_id": connection_id,
                "available_features": [
                    "real_time_kpi",
                    "live_timeline", 
                    "radar_updates",
                    "trend_alerts",
                    "badge_notifications"
                ]
            },
            badge_text="CONNECTED",
            auto_dismiss=5
        )
        await connection_manager.send_personal_message(welcome_message, connection_id)
        
        # Boucle de maintien de connexion
        while True:
            try:
                # Attendre les messages du client (ping, preferences, etc.)
                data = await websocket.receive_text()
                client_message = json.loads(data)
                
                # Traitement des messages clients
                await handle_client_message(client_message, connection_id)
                
            except WebSocketDisconnect:
                logger.info("Client WebSocket déconnecté", connection_id=connection_id)
                break
                
            except json.JSONDecodeError:
                error_message = WebSocketMessage(
                    type=NotificationType.SYSTEM_STATUS,
                    data={"error": "Message JSON invalide"},
                    priority="low"
                )
                await connection_manager.send_personal_message(error_message, connection_id)
                
    except Exception as e:
        logger.error("Erreur WebSocket dashboard", 
                    connection_id=connection_id, 
                    error=str(e))
    finally:
        await connection_manager.disconnect(connection_id)

@router.websocket("/admin")
async def websocket_admin(
    websocket: WebSocket,
    admin_token: Optional[str] = None
):
    """
    WebSocket endpoint pour les administrateurs
    Notifications système, monitoring, gestion des connexions
    """
    
    # TODO: Validation du token admin
    connection_id = f"admin_{str(uuid.uuid4())[:8]}"
    
    try:
        await connection_manager.connect(
            websocket,
            connection_id,
            groups=["admin", "global"]
        )
        
        # Statistiques initiales
        stats_message = WebSocketMessage(
            type=NotificationType.SYSTEM_STATUS,
            data={
                "status": "admin_connected",
                "stats": connection_manager.get_stats()
            }
        )
        await connection_manager.send_personal_message(stats_message, connection_id)
        
        # Boucle admin
        while True:
            try:
                data = await websocket.receive_text()
                admin_command = json.loads(data)
                
                await handle_admin_command(admin_command, connection_id)
                
            except WebSocketDisconnect:
                logger.info("Admin WebSocket déconnecté", connection_id=connection_id)
                break
                
    except Exception as e:
        logger.error("Erreur WebSocket admin", 
                    connection_id=connection_id, 
                    error=str(e))
    finally:
        await connection_manager.disconnect(connection_id)

async def handle_client_message(message: Dict[str, Any], connection_id: str):
    """Traiter les messages reçus des clients dashboard"""
    
    message_type = message.get("type", "unknown")
    
    if message_type == "ping":
        # Répondre au ping pour maintenir la connexion
        pong_message = WebSocketMessage(
            type=NotificationType.SYSTEM_STATUS,
            data={"status": "pong", "timestamp": datetime.now().isoformat()}
        )
        await connection_manager.send_personal_message(pong_message, connection_id)
        
    elif message_type == "subscribe":
        # Gérer les abonnements à des topics spécifiques
        topics = message.get("topics", [])
        logger.info("Client abonné aux topics", 
                   connection_id=connection_id, 
                   topics=topics)
        
    elif message_type == "unsubscribe":
        # Gérer les désabonnements
        topics = message.get("topics", [])
        logger.info("Client désabonné des topics", 
                   connection_id=connection_id, 
                   topics=topics)
    
    else:
        logger.warning("Message client non reconnu", 
                      connection_id=connection_id, 
                      message_type=message_type)

async def handle_admin_command(command: Dict[str, Any], connection_id: str):
    """Traiter les commandes administrateur"""
    
    command_type = command.get("command", "unknown")
    
    if command_type == "get_stats":
        # Envoyer les statistiques actuelles
        stats_message = WebSocketMessage(
            type=NotificationType.SYSTEM_STATUS,
            data={
                "command_response": "get_stats",
                "stats": connection_manager.get_stats()
            }
        )
        await connection_manager.send_personal_message(stats_message, connection_id)
        
    elif command_type == "broadcast_test":
        # Test de broadcast global
        test_message = WebSocketMessage(
            type=NotificationType.SYSTEM_STATUS,
            data={
                "message": "Test de broadcast depuis l'admin",
                "sender": connection_id
            },
            badge_text="ADMIN TEST",
            auto_dismiss=5
        )
        await connection_manager.broadcast_global(test_message, exclude=[connection_id])
        
    elif command_type == "disconnect_user":
        # Déconnecter un utilisateur spécifique
        target_id = command.get("user_id")
        if target_id and target_id in connection_manager.active_connections:
            await connection_manager.disconnect(target_id)
            
    else:
        logger.warning("Commande admin non reconnue", 
                      connection_id=connection_id, 
                      command=command_type)

# Fonctions utilitaires pour broadcaster depuis d'autres modules

async def notify_new_insight(insight_data: Dict[str, Any], priority: str = "normal"):
    """Notifier un nouveau insight via WebSocket"""
    
    message = WebSocketMessage(
        type=NotificationType.NEW_INSIGHT,
        data=insight_data,
        priority=priority,
        badge_text="NEW",
        auto_dismiss=10
    )
    
    await connection_manager.broadcast_to_group("dashboard", message)

async def notify_kpi_update(kpi_data: Dict[str, Any]):
    """Notifier une mise à jour des KPI"""
    
    message = WebSocketMessage(
        type=NotificationType.KPI_UPDATE,
        data=kpi_data,
        priority="normal",
        badge_text="UPDATED",
        auto_dismiss=5
    )
    
    await connection_manager.broadcast_to_group("dashboard", message)

async def notify_trending_theme(theme_data: Dict[str, Any]):
    """Notifier une nouvelle thématique en tendance"""
    
    message = WebSocketMessage(
        type=NotificationType.TRENDING_THEME,
        data=theme_data,
        priority="high",
        badge_text="TRENDING",
        auto_dismiss=15
    )
    
    await connection_manager.broadcast_to_group("dashboard", message)

# Endpoint REST pour déclencher des notifications (pour tests)
@router.post("/notify/test")
async def trigger_test_notification(
    notification_type: NotificationType,
    message_data: Dict[str, Any],
    target_group: str = "dashboard"
):
    """Déclencher une notification de test via l'API REST"""
    
    test_message = WebSocketMessage(
        type=notification_type,
        data=message_data,
        badge_text="TEST",
        auto_dismiss=10
    )
    
    await connection_manager.broadcast_to_group(target_group, test_message)
    
    return {
        "status": "notification_sent",
        "type": notification_type,
        "target_group": target_group,
        "recipients": len(connection_manager.connection_groups.get(target_group, set()))
    }

@router.get("/stats")
async def get_websocket_stats():
    """Obtenir les statistiques des connexions WebSocket"""
    return connection_manager.get_stats() 