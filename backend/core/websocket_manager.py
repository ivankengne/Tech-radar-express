"""
Tech Radar Express - Gestionnaire WebSocket
Gestionnaire de connexions WebSocket pour notifications temps réel
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import structlog
import uuid
from fastapi import WebSocket

logger = structlog.get_logger(__name__)

@dataclass
class WebSocketConnection:
    """Informations d'une connexion WebSocket"""
    websocket: WebSocket
    user_id: Optional[str]
    connection_id: str
    connected_at: datetime
    last_ping: datetime
    subscriptions: Set[str]

class WebSocketManager:
    """Gestionnaire de connexions WebSocket pour notifications temps réel"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        
        self.ping_interval = 30
        self.connection_timeout = 120
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """Enregistre une nouvelle connexion WebSocket"""
        await websocket.accept()
        
        connection_id = f"ws_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        
        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            connection_id=connection_id,
            connected_at=now,
            last_ping=now,
            subscriptions=set()
        )
        
        self.connections[connection_id] = connection
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        if len(self.connections) == 1 and not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_connections())
        
        await self._send_to_connection(connection_id, {
            "type": "connection_established",
            "data": {
                "connection_id": connection_id,
                "user_id": user_id,
                "server_time": now.isoformat()
            }
        })
        
        logger.info("Nouvelle connexion WebSocket", 
                   connection_id=connection_id, 
                   user_id=user_id,
                   total_connections=len(self.connections))
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Ferme une connexion WebSocket"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        for topic in connection.subscriptions:
            if topic in self.subscriptions:
                self.subscriptions[topic].discard(connection_id)
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
        
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]
        
        del self.connections[connection_id]
        
        if not self.connections and self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        
        logger.info("Connexion WebSocket fermée", 
                   connection_id=connection_id,
                   total_connections=len(self.connections))
    
    async def subscribe(self, connection_id: str, topic: str) -> bool:
        """Abonne une connexion à un topic"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.subscriptions.add(topic)
        
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(connection_id)
        
        return True
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> int:
        """Envoie un message à toutes les connexions d'un utilisateur"""
        if user_id not in self.user_connections:
            return 0
        
        sent_count = 0
        connection_ids = list(self.user_connections[user_id])
        
        for connection_id in connection_ids:
            if await self._send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """Diffuse un message à toutes les connexions actives"""
        sent_count = 0
        connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            if await self._send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]) -> int:
        """Diffuse un message à toutes les connexions abonnées à un topic"""
        if topic not in self.subscriptions:
            return 0
        
        sent_count = 0
        connection_ids = list(self.subscriptions[topic])
        
        for connection_id in connection_ids:
            if await self._send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def handle_message(self, connection_id: str, message: Dict[str, Any]):
        """Traite un message reçu d'une connexion"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        connection.last_ping = datetime.now()
        
        message_type = message.get("type")
        
        if message_type == "ping":
            await self._send_to_connection(connection_id, {
                "type": "pong",
                "data": {"timestamp": datetime.now().isoformat()}
            })
        
        elif message_type == "subscribe":
            topic = message.get("topic")
            if topic:
                await self.subscribe(connection_id, topic)
                await self._send_to_connection(connection_id, {
                    "type": "subscription_confirmed",
                    "data": {"topic": topic}
                })
    
    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Envoie un message à une connexion spécifique"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        
        try:
            enhanced_message = {
                **message,
                "timestamp": datetime.now().isoformat(),
                "connection_id": connection_id
            }
            
            await connection.websocket.send_text(json.dumps(enhanced_message))
            return True
            
        except Exception as e:
            logger.warning("Erreur envoi message WebSocket", 
                          connection_id=connection_id,
                          error=str(e))
            
            await self.disconnect(connection_id)
            return False
    
    async def _cleanup_connections(self):
        """Tâche de nettoyage des connexions inactives"""
        while self.connections:
            try:
                now = datetime.now()
                timeout_threshold = now.timestamp() - self.connection_timeout
                
                expired_connections = [
                    connection_id for connection_id, connection in self.connections.items()
                    if connection.last_ping.timestamp() < timeout_threshold
                ]
                
                for connection_id in expired_connections:
                    logger.info("Connexion WebSocket expirée", connection_id=connection_id)
                    await self.disconnect(connection_id)
                
                await asyncio.sleep(self.ping_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Erreur dans la tâche de nettoyage WebSocket", error=str(e))
                await asyncio.sleep(5)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques des connexions"""
        return {
            "total_connections": len(self.connections),
            "unique_users": len(self.user_connections),
            "active_topics": len(self.subscriptions),
            "last_updated": datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Ferme toutes les connexions et arrête le gestionnaire"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        
        shutdown_message = {
            "type": "server_shutdown",
            "data": {"message": "Serveur en cours d'arrêt"}
        }
        
        await self.broadcast(shutdown_message)
        
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            try:
                connection = self.connections[connection_id]
                await connection.websocket.close()
            except Exception:
                pass
            
            await self.disconnect(connection_id)
        
        logger.info("WebSocketManager arrêté")

# Instance globale
_websocket_manager: Optional[WebSocketManager] = None

async def get_websocket_manager() -> WebSocketManager:
    """Récupère l'instance globale du gestionnaire WebSocket"""
    global _websocket_manager
    
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    
    return _websocket_manager
