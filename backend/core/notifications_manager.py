"""
Tech Radar Express - Gestionnaire de Notifications WebSocket
Système de notifications temps réel avec seuils de pertinence configurables
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
import uuid

from .config_manager import get_settings
from .websocket_manager import WebSocketManager
from database.redis_client import RedisClient

logger = structlog.get_logger(__name__)

class NotificationType(str, Enum):
    """Types de notifications"""
    CRITICAL_ALERT = "critical_alert"
    CUSTOM_ALERT = "custom_alert"
    DAILY_SUMMARY = "daily_summary"
    FOCUS_MODE = "focus_mode"
    SOURCE_UPDATE = "source_update"
    SYSTEM_STATUS = "system_status"
    CRAWL_COMPLETE = "crawl_complete"
    NEW_INSIGHT = "new_insight"

class NotificationPriority(str, Enum):
    """Niveaux de priorité"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

@dataclass
class NotificationPreferences:
    """Préférences utilisateur pour les notifications"""
    user_id: str
    enabled_types: Set[NotificationType]
    min_priority: NotificationPriority
    pertinence_threshold: float  # 0.0 à 1.0
    quiet_hours_start: Optional[str] = None  # Format "HH:MM"
    quiet_hours_end: Optional[str] = None
    max_notifications_per_hour: int = 10
    email_notifications: bool = False
    desktop_notifications: bool = True
    sound_enabled: bool = True
    updated_at: datetime = None

@dataclass
class Notification:
    """Modèle de notification"""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    pertinence_score: float
    data: Dict[str, Any]
    user_id: Optional[str] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    read: bool = False
    clicked: bool = False

@dataclass
class NotificationStats:
    """Statistiques des notifications"""
    total_sent: int
    total_read: int
    total_clicked: int
    avg_pertinence: float
    types_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    last_notification: Optional[datetime]

class NotificationsManager:
    """
    Gestionnaire de notifications WebSocket avec seuils configurables
    """
    
    def __init__(self, websocket_manager: WebSocketManager, redis_client: RedisClient):
        self.websocket_manager = websocket_manager
        self.redis = redis_client
        self.settings = get_settings()
        
        # Stockage des préférences et notifications
        self.user_preferences: Dict[str, NotificationPreferences] = {}
        self.active_notifications: Dict[str, Notification] = {}
        
        # Configuration par défaut
        self.default_preferences = NotificationPreferences(
            user_id="default",
            enabled_types={
                NotificationType.CRITICAL_ALERT,
                NotificationType.CUSTOM_ALERT,
                NotificationType.DAILY_SUMMARY
            },
            min_priority=NotificationPriority.MEDIUM,
            pertinence_threshold=0.7,
            max_notifications_per_hour=10,
            updated_at=datetime.now()
        )
        
        # Compteurs pour rate limiting
        self.notification_counts: Dict[str, List[datetime]] = {}
    
    async def initialize(self):
        """Initialise le gestionnaire"""
        try:
            # Chargement des préférences depuis Redis
            await self._load_user_preferences()
            
            # Nettoyage des notifications expirées
            await self._cleanup_expired_notifications()
            
            logger.info("NotificationsManager initialisé")
        except Exception as e:
            logger.error("Erreur initialisation notifications", error=str(e))
            raise
    
    async def send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        pertinence_score: float,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        expires_in_minutes: int = 60
    ) -> bool:
        """
        Envoie une notification via WebSocket
        
        Returns:
            bool: True si la notification a été envoyée
        """
        try:
            # Création de la notification
            notification = Notification(
                id=f"notif_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
                type=notification_type,
                priority=priority,
                title=title,
                message=message,
                pertinence_score=pertinence_score,
                data=data or {},
                user_id=user_id,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=expires_in_minutes)
            )
            
            # Vérification des préférences utilisateur
            if not await self._should_send_notification(notification, user_id):
                logger.debug("Notification filtrée par préférences", notification_id=notification.id)
                return False
            
            # Vérification du rate limiting
            if not await self._check_rate_limit(user_id):
                logger.warning("Rate limit atteint pour notifications", user_id=user_id)
                return False
            
            # Stockage de la notification
            self.active_notifications[notification.id] = notification
            await self._save_notification_to_redis(notification)
            
            # Envoi via WebSocket
            await self._send_websocket_notification(notification)
            
            # Mise à jour des statistiques
            await self._update_notification_stats(notification)
            
            logger.info(
                "Notification envoyée",
                notification_id=notification.id,
                type=notification_type.value,
                priority=priority.value,
                pertinence=pertinence_score,
                user_id=user_id
            )
            
            return True
            
        except Exception as e:
            logger.error("Erreur envoi notification", error=str(e))
            return False
    
    async def send_critical_alert_notification(self, alert_data: Dict[str, Any]):
        """Envoie une notification pour une alerte critique"""
        await self.send_notification(
            notification_type=NotificationType.CRITICAL_ALERT,
            title=f"🚨 Alerte Critique Détectée",
            message=f"Niveau {alert_data.get('criticality_level', 'unknown')} - {alert_data.get('source', 'Source inconnue')}",
            pertinence_score=alert_data.get('confidence_score', 0.8),
            priority=NotificationPriority.CRITICAL,
            data=alert_data,
            expires_in_minutes=120
        )
    
    async def send_custom_alert_notification(self, alert_name: str, matches_count: int, alert_data: Dict[str, Any]):
        """Envoie une notification pour une alerte personnalisée"""
        priority_map = {
            "low": NotificationPriority.LOW,
            "medium": NotificationPriority.MEDIUM,
            "high": NotificationPriority.HIGH,
            "critical": NotificationPriority.URGENT
        }
        
        priority = priority_map.get(alert_data.get('priority', 'medium'), NotificationPriority.MEDIUM)
        
        await self.send_notification(
            notification_type=NotificationType.CUSTOM_ALERT,
            title=f"📢 Alerte: {alert_name}",
            message=f"{matches_count} nouvelle(s) correspondance(s) trouvée(s)",
            pertinence_score=min(1.0, matches_count * 0.2 + 0.6),
            priority=priority,
            data=alert_data,
            expires_in_minutes=180
        )
    
    async def send_daily_summary_notification(self, summary_data: Dict[str, Any]):
        """Envoie une notification pour un résumé quotidien"""
        await self.send_notification(
            notification_type=NotificationType.DAILY_SUMMARY,
            title="📋 Résumé Quotidien Disponible",
            message=f"Nouveau résumé avec {summary_data.get('sections_count', 0)} sections",
            pertinence_score=0.8,
            priority=NotificationPriority.MEDIUM,
            data=summary_data,
            expires_in_minutes=1440  # 24h
        )
    
    async def send_system_notification(self, title: str, message: str, level: str = "info"):
        """Envoie une notification système"""
        priority_map = {
            "info": NotificationPriority.LOW,
            "warning": NotificationPriority.MEDIUM,
            "error": NotificationPriority.HIGH,
            "critical": NotificationPriority.URGENT
        }
        
        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨"
        }
        
        await self.send_notification(
            notification_type=NotificationType.SYSTEM_STATUS,
            title=f"{icons.get(level, 'ℹ️')} {title}",
            message=message,
            pertinence_score=0.6,
            priority=priority_map.get(level, NotificationPriority.LOW),
            data={"level": level},
            expires_in_minutes=60
        )
    
    async def get_user_preferences(self, user_id: str = "default") -> NotificationPreferences:
        """Récupère les préférences d'un utilisateur"""
        if user_id in self.user_preferences:
            return self.user_preferences[user_id]
        
        # Chargement depuis Redis
        preferences_data = await self.redis.get(f"notifications:preferences:{user_id}")
        if preferences_data:
            try:
                preferences = NotificationPreferences(**preferences_data)
                self.user_preferences[user_id] = preferences
                return preferences
            except Exception as e:
                logger.warning("Erreur chargement préférences", user_id=user_id, error=str(e))
        
        return self.default_preferences
    
    async def update_user_preferences(self, user_id: str, preferences: NotificationPreferences) -> bool:
        """Met à jour les préférences d'un utilisateur"""
        try:
            preferences.user_id = user_id
            preferences.updated_at = datetime.now()
            
            # Stockage en mémoire et Redis
            self.user_preferences[user_id] = preferences
            await self.redis.set(
                f"notifications:preferences:{user_id}",
                asdict(preferences),
                expire=int(timedelta(days=365).total_seconds())
            )
            
            logger.info("Préférences notifications mises à jour", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Erreur mise à jour préférences", user_id=user_id, error=str(e))
            return False
    
    async def mark_notification_read(self, notification_id: str, user_id: str = "default") -> bool:
        """Marque une notification comme lue"""
        try:
            if notification_id in self.active_notifications:
                self.active_notifications[notification_id].read = True
                await self._save_notification_to_redis(self.active_notifications[notification_id])
                
                logger.debug("Notification marquée comme lue", notification_id=notification_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Erreur marquage notification lue", error=str(e))
            return False
    
    async def mark_notification_clicked(self, notification_id: str, user_id: str = "default") -> bool:
        """Marque une notification comme cliquée"""
        try:
            if notification_id in self.active_notifications:
                self.active_notifications[notification_id].clicked = True
                await self._save_notification_to_redis(self.active_notifications[notification_id])
                
                logger.debug("Notification marquée comme cliquée", notification_id=notification_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Erreur marquage notification cliquée", error=str(e))
            return False
    
    async def get_notifications_history(self, user_id: str = "default", limit: int = 50) -> List[Notification]:
        """Récupère l'historique des notifications d'un utilisateur"""
        try:
            # Filtrage par utilisateur (ou toutes si default)
            if user_id == "default":
                notifications = list(self.active_notifications.values())
            else:
                notifications = [n for n in self.active_notifications.values() 
                               if n.user_id == user_id or n.user_id is None]
            
            # Tri par date décroissante et limitation
            notifications.sort(key=lambda n: n.created_at, reverse=True)
            return notifications[:limit]
            
        except Exception as e:
            logger.error("Erreur récupération historique", error=str(e))
            return []
    
    async def get_notification_stats(self, user_id: str = "default") -> NotificationStats:
        """Calcule les statistiques des notifications"""
        try:
            # Filtrage par utilisateur
            if user_id == "default":
                notifications = list(self.active_notifications.values())
            else:
                notifications = [n for n in self.active_notifications.values() 
                               if n.user_id == user_id or n.user_id is None]
            
            if not notifications:
                return NotificationStats(
                    total_sent=0,
                    total_read=0,
                    total_clicked=0,
                    avg_pertinence=0.0,
                    types_distribution={},
                    priority_distribution={},
                    last_notification=None
                )
            
            # Calculs statistiques
            total_sent = len(notifications)
            total_read = len([n for n in notifications if n.read])
            total_clicked = len([n for n in notifications if n.clicked])
            avg_pertinence = sum(n.pertinence_score for n in notifications) / total_sent
            
            # Distributions
            types_dist = {}
            priority_dist = {}
            
            for n in notifications:
                types_dist[n.type.value] = types_dist.get(n.type.value, 0) + 1
                priority_dist[n.priority.value] = priority_dist.get(n.priority.value, 0) + 1
            
            last_notification = max(n.created_at for n in notifications)
            
            return NotificationStats(
                total_sent=total_sent,
                total_read=total_read,
                total_clicked=total_clicked,
                avg_pertinence=avg_pertinence,
                types_distribution=types_dist,
                priority_distribution=priority_dist,
                last_notification=last_notification
            )
            
        except Exception as e:
            logger.error("Erreur calcul statistiques", error=str(e))
            return NotificationStats(0, 0, 0, 0.0, {}, {}, None)
    
    async def _should_send_notification(self, notification: Notification, user_id: Optional[str]) -> bool:
        """Vérifie si une notification doit être envoyée selon les préférences"""
        preferences = await self.get_user_preferences(user_id or "default")
        
        # Vérification du type activé
        if notification.type not in preferences.enabled_types:
            return False
        
        # Vérification du niveau de priorité minimum
        priority_values = {
            NotificationPriority.LOW: 1,
            NotificationPriority.MEDIUM: 2,
            NotificationPriority.HIGH: 3,
            NotificationPriority.URGENT: 4,
            NotificationPriority.CRITICAL: 5
        }
        
        if priority_values.get(notification.priority, 0) < priority_values.get(preferences.min_priority, 2):
            return False
        
        # Vérification du seuil de pertinence
        if notification.pertinence_score < preferences.pertinence_threshold:
            return False
        
        # Vérification des heures de silence
        if preferences.quiet_hours_start and preferences.quiet_hours_end:
            now_time = datetime.now().strftime("%H:%M")
            if preferences.quiet_hours_start <= now_time <= preferences.quiet_hours_end:
                return False
        
        return True
    
    async def _check_rate_limit(self, user_id: Optional[str]) -> bool:
        """Vérifie le rate limiting des notifications"""
        user_key = user_id or "default"
        preferences = await self.get_user_preferences(user_key)
        
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Nettoyage des anciens compteurs
        if user_key in self.notification_counts:
            self.notification_counts[user_key] = [
                dt for dt in self.notification_counts[user_key] if dt > hour_ago
            ]
        else:
            self.notification_counts[user_key] = []
        
        # Vérification du limite
        if len(self.notification_counts[user_key]) >= preferences.max_notifications_per_hour:
            return False
        
        # Ajout du timestamp actuel
        self.notification_counts[user_key].append(now)
        return True
    
    async def _send_websocket_notification(self, notification: Notification):
        """Envoie la notification via WebSocket"""
        try:
            message = {
                "type": "notification",
                "data": {
                    "id": notification.id,
                    "type": notification.type.value,
                    "priority": notification.priority.value,
                    "title": notification.title,
                    "message": notification.message,
                    "pertinence_score": notification.pertinence_score,
                    "data": notification.data,
                    "created_at": notification.created_at.isoformat(),
                    "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
                }
            }
            
            # Envoi à tous les clients connectés ou à un utilisateur spécifique
            if notification.user_id:
                await self.websocket_manager.send_to_user(notification.user_id, message)
            else:
                await self.websocket_manager.broadcast(message)
                
        except Exception as e:
            logger.error("Erreur envoi WebSocket notification", error=str(e))
    
    async def _save_notification_to_redis(self, notification: Notification):
        """Sauvegarde une notification en Redis"""
        try:
            notification_data = asdict(notification)
            # Conversion des datetime en string pour JSON
            notification_data['created_at'] = notification.created_at.isoformat()
            if notification.expires_at:
                notification_data['expires_at'] = notification.expires_at.isoformat()
            
            # Sauvegarde avec TTL basé sur expiration
            ttl = int(timedelta(days=7).total_seconds())  # 7 jours par défaut
            if notification.expires_at:
                remaining = notification.expires_at - datetime.now()
                if remaining.total_seconds() > 0:
                    ttl = max(int(remaining.total_seconds()) + 3600, ttl)  # +1h de marge
            
            await self.redis.set(
                f"notifications:data:{notification.id}",
                notification_data,
                expire=ttl
            )
            
        except Exception as e:
            logger.error("Erreur sauvegarde notification Redis", error=str(e))
    
    async def _update_notification_stats(self, notification: Notification):
        """Met à jour les statistiques de notifications"""
        try:
            stats_key = f"notifications:stats:{notification.user_id or 'global'}"
            current_stats = await self.redis.get(stats_key) or {}
            
            # Mise à jour des compteurs
            current_stats['total_sent'] = current_stats.get('total_sent', 0) + 1
            current_stats['last_notification'] = notification.created_at.isoformat()
            
            # Distribution par type
            type_key = f"type_{notification.type.value}"
            current_stats[type_key] = current_stats.get(type_key, 0) + 1
            
            # Distribution par priorité
            priority_key = f"priority_{notification.priority.value}"
            current_stats[priority_key] = current_stats.get(priority_key, 0) + 1
            
            await self.redis.set(stats_key, current_stats, expire=int(timedelta(days=30).total_seconds()))
            
        except Exception as e:
            logger.error("Erreur mise à jour stats notifications", error=str(e))
    
    async def _load_user_preferences(self):
        """Charge les préférences utilisateur depuis Redis"""
        try:
            # Chargement des préférences par défaut
            default_prefs = await self.redis.get("notifications:preferences:default")
            if default_prefs:
                self.user_preferences["default"] = NotificationPreferences(**default_prefs)
            
        except Exception as e:
            logger.warning("Erreur chargement préférences", error=str(e))
    
    async def _cleanup_expired_notifications(self):
        """Nettoie les notifications expirées"""
        try:
            now = datetime.now()
            expired_ids = [
                notification_id for notification_id, notification in self.active_notifications.items()
                if notification.expires_at and notification.expires_at < now
            ]
            
            for notification_id in expired_ids:
                del self.active_notifications[notification_id]
                # Nettoyage Redis également fait automatiquement via TTL
            
            if expired_ids:
                logger.info(f"Nettoyage de {len(expired_ids)} notifications expirées")
                
        except Exception as e:
            logger.error("Erreur nettoyage notifications", error=str(e))
    
    async def cleanup(self):
        """Nettoie les ressources"""
        await self._cleanup_expired_notifications()
        logger.info("NotificationsManager nettoyé")

# Instance globale
_notifications_manager: Optional[NotificationsManager] = None

async def get_notifications_manager() -> NotificationsManager:
    """Récupère l'instance globale du gestionnaire de notifications"""
    global _notifications_manager
    
    if _notifications_manager is None:
        # Import local pour éviter les dépendances circulaires
        from .websocket_manager import get_websocket_manager
        from database.redis_client import RedisClient
        
        websocket_manager = await get_websocket_manager()
        redis_client = RedisClient()
        
        _notifications_manager = NotificationsManager(websocket_manager, redis_client)
        await _notifications_manager.initialize()
    
    return _notifications_manager 