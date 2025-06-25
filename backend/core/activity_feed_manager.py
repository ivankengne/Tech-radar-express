"""
Tech Radar Express - Gestionnaire Activity Feed
Système de flux d'activité temps réel avec liste défilante
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
from database.redis_client import RedisClient

logger = structlog.get_logger(__name__)

class ActivityType(str, Enum):
    """Types d'activités pour le feed"""
    INSIGHT_DISCOVERED = "insight_discovered"
    CRITICAL_ALERT = "critical_alert"
    CUSTOM_ALERT = "custom_alert"
    SOURCE_CRAWLED = "source_crawled"
    DAILY_SUMMARY = "daily_summary"
    FOCUS_MODE = "focus_mode"
    SOURCE_ADDED = "source_added"
    USER_SEARCH = "user_search"
    SYSTEM_UPDATE = "system_update"
    CRAWL_STARTED = "crawl_started"
    CRAWL_COMPLETED = "crawl_completed"
    LLM_ANALYSIS = "llm_analysis"

class ActivityPriority(str, Enum):
    """Niveaux de priorité d'activité"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class ActivitySource(str, Enum):
    """Sources d'activité"""
    SYSTEM = "system"
    USER = "user"
    SCHEDULER = "scheduler"
    MCP = "mcp"
    LLM = "llm"
    CRAWLER = "crawler"

@dataclass
class ActivityItem:
    """Modèle d'un élément d'activité"""
    id: str
    type: ActivityType
    priority: ActivityPriority
    source: ActivitySource
    title: str
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    source_name: Optional[str] = None
    url: Optional[str] = None
    tags: List[str] = None
    tech_areas: List[str] = None
    impact_score: float = 0.0
    read: bool = False
    bookmarked: bool = False

@dataclass
class ActivityStats:
    """Statistiques du flux d'activité"""
    total_activities: int
    activities_24h: int
    activities_by_type: Dict[str, int]
    activities_by_priority: Dict[str, int]
    avg_impact_score: float
    most_active_source: str
    last_activity: Optional[datetime]

class ActivityFeedManager:
    """
    Gestionnaire de flux d'activité temps réel
    """
    
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.settings = get_settings()
        
        # Configuration du feed
        self.max_activities = 1000  # Limite en mémoire
        self.max_activities_redis = 5000  # Limite Redis
        self.activity_ttl = int(timedelta(days=30).total_seconds())
        
        # Cache en mémoire pour performance
        self.recent_activities: List[ActivityItem] = []
        self.activity_cache: Dict[str, ActivityItem] = {}
        
        # Configuration des abonnements WebSocket
        self.websocket_manager = None
        
        # Filtres et configuration
        self.default_filters = {
            "types": list(ActivityType),
            "priorities": list(ActivityPriority),
            "sources": list(ActivitySource),
            "limit": 50,
            "include_system": True
        }
    
    async def initialize(self):
        """Initialise le gestionnaire d'activité"""
        try:
            # Chargement des activités récentes depuis Redis
            await self._load_recent_activities()
            
            # Configuration WebSocket si disponible
            await self._setup_websocket()
            
            logger.info("ActivityFeedManager initialisé")
        except Exception as e:
            logger.error("Erreur initialisation ActivityFeedManager", error=str(e))
            raise
    
    async def add_activity(
        self,
        activity_type: ActivityType,
        title: str,
        description: str,
        details: Dict[str, Any] = None,
        priority: ActivityPriority = ActivityPriority.NORMAL,
        source: ActivitySource = ActivitySource.SYSTEM,
        user_id: Optional[str] = None,
        source_name: Optional[str] = None,
        url: Optional[str] = None,
        tags: List[str] = None,
        tech_areas: List[str] = None,
        impact_score: float = 0.0
    ) -> str:
        """
        Ajoute une nouvelle activité au flux
        
        Returns:
            str: ID de l'activité créée
        """
        try:
            # Création de l'activité
            activity = ActivityItem(
                id=f"activity_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
                type=activity_type,
                priority=priority,
                source=source,
                title=title,
                description=description,
                details=details or {},
                timestamp=datetime.now(),
                user_id=user_id,
                source_name=source_name,
                url=url,
                tags=tags or [],
                tech_areas=tech_areas or [],
                impact_score=impact_score
            )
            
            # Ajout au cache en mémoire
            self.recent_activities.insert(0, activity)
            self.activity_cache[activity.id] = activity
            
            # Limitation de la taille en mémoire
            if len(self.recent_activities) > self.max_activities:
                removed = self.recent_activities.pop()
                self.activity_cache.pop(removed.id, None)
            
            # Sauvegarde en Redis
            await self._save_activity_to_redis(activity)
            
            # Diffusion WebSocket temps réel
            await self._broadcast_activity(activity)
            
            # Mise à jour des statistiques
            await self._update_activity_stats(activity)
            
            logger.debug(
                "Nouvelle activité ajoutée",
                activity_id=activity.id,
                type=activity_type.value,
                priority=priority.value,
                title=title
            )
            
            return activity.id
            
        except Exception as e:
            logger.error("Erreur ajout activité", error=str(e))
            raise
    
    async def get_activities(
        self,
        limit: int = 50,
        offset: int = 0,
        activity_types: List[ActivityType] = None,
        priorities: List[ActivityPriority] = None,
        sources: List[ActivitySource] = None,
        user_id: Optional[str] = None,
        tech_areas: List[str] = None,
        since: Optional[datetime] = None,
        include_system: bool = True
    ) -> List[ActivityItem]:
        """
        Récupère les activités selon les filtres spécifiés
        """
        try:
            # Filtrage en mémoire pour les requêtes récentes
            if offset == 0 and limit <= len(self.recent_activities):
                activities = self._filter_activities(
                    self.recent_activities,
                    activity_types=activity_types,
                    priorities=priorities,
                    sources=sources,
                    user_id=user_id,
                    tech_areas=tech_areas,
                    since=since,
                    include_system=include_system
                )
                # Mise à jour du champ bookmarked selon l'utilisateur
                if user_id:
                    bookmarked_ids = await self._get_user_bookmarked_ids(user_id)
                    for act in activities:
                        act.bookmarked = act.id in bookmarked_ids
                return activities[:limit]
            
            # Récupération depuis Redis pour les requêtes plus larges
            activities = await self._load_activities_from_redis(
                limit=limit + offset,
                activity_types=activity_types,
                priorities=priorities,
                sources=sources,
                user_id=user_id,
                tech_areas=tech_areas,
                since=since,
                include_system=include_system
            )
            
            # Mise à jour du champ bookmarked selon l'utilisateur
            if user_id:
                bookmarked_ids = await self._get_user_bookmarked_ids(user_id)
                for act in activities:
                    act.bookmarked = act.id in bookmarked_ids

            return activities[offset:offset + limit]
            
        except Exception as e:
            logger.error("Erreur récupération activités", error=str(e))
            return []
    
    async def get_activity_by_id(self, activity_id: str) -> Optional[ActivityItem]:
        """Récupère une activité par son ID"""
        try:
            # Vérification cache mémoire
            if activity_id in self.activity_cache:
                return self.activity_cache[activity_id]
            
            # Récupération depuis Redis
            activity_data = await self.redis.get(f"activity:data:{activity_id}")
            if activity_data:
                return self._deserialize_activity(activity_data)
            
            return None
            
        except Exception as e:
            logger.error("Erreur récupération activité", activity_id=activity_id, error=str(e))
            return None
    
    async def mark_activity_read(self, activity_id: str, user_id: str = "default") -> bool:
        """Marque une activité comme lue"""
        try:
            activity = await self.get_activity_by_id(activity_id)
            if not activity:
                return False
            
            activity.read = True
            
            # Mise à jour cache et Redis
            self.activity_cache[activity_id] = activity
            await self._save_activity_to_redis(activity)
            
            return True
            
        except Exception as e:
            logger.error("Erreur marquage activité lue", error=str(e))
            return False
    
    async def bookmark_activity(self, activity_id: str, user_id: str = "default") -> bool:
        """Ajoute/retire une activité des favoris"""
        try:
            activity = await self.get_activity_by_id(activity_id)
            if not activity:
                return False
            
            # Inverser l'état de favoris pour CET utilisateur
            bookmark_key_prefix = f"activity:bookmarks:{user_id}"
            bookmark_key = f"{bookmark_key_prefix}:{activity_id}"

            is_bookmarked = await self.redis.exists(bookmark_key)

            if is_bookmarked:
                # Retirer des favoris
                await self.redis.delete(bookmark_key)
                activity.bookmarked = False  # Pour le retour immédiat si même utilisateur
            else:
                # Ajouter aux favoris avec TTL identique aux activités
                await self.redis.set(bookmark_key, activity.timestamp.isoformat(), expire=self.activity_ttl)
                activity.bookmarked = True

            # Mettre à jour en cache (statut global inchangé pour les autres)
            self.activity_cache[activity_id] = activity
            
            return True
            
        except Exception as e:
            logger.error("Erreur bookmark activité", error=str(e))
            return False
    
    async def get_activity_stats(self, since: Optional[datetime] = None) -> ActivityStats:
        """Calcule les statistiques du flux d'activité"""
        try:
            if since is None:
                since = datetime.now() - timedelta(days=7)
            
            # Filtrage des activités pour les stats
            activities = await self.get_activities(
                limit=self.max_activities,
                since=since,
                include_system=True
            )
            
            if not activities:
                return ActivityStats(
                    total_activities=0,
                    activities_24h=0,
                    activities_by_type={},
                    activities_by_priority={},
                    avg_impact_score=0.0,
                    most_active_source="",
                    last_activity=None
                )
            
            # Calculs statistiques
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            
            activities_24h = len([a for a in activities if a.timestamp > last_24h])
            
            # Distribution par type
            types_count = {}
            for activity in activities:
                activity_type = activity.type.value
                types_count[activity_type] = types_count.get(activity_type, 0) + 1
            
            # Distribution par priorité
            priorities_count = {}
            for activity in activities:
                priority = activity.priority.value
                priorities_count[priority] = priorities_count.get(priority, 0) + 1
            
            # Source la plus active
            sources_count = {}
            for activity in activities:
                source = activity.source.value
                sources_count[source] = sources_count.get(source, 0) + 1
            
            most_active_source = max(sources_count.items(), key=lambda x: x[1])[0] if sources_count else ""
            
            # Score d'impact moyen
            impact_scores = [a.impact_score for a in activities if a.impact_score > 0]
            avg_impact_score = sum(impact_scores) / len(impact_scores) if impact_scores else 0.0
            
            return ActivityStats(
                total_activities=len(activities),
                activities_24h=activities_24h,
                activities_by_type=types_count,
                activities_by_priority=priorities_count,
                avg_impact_score=avg_impact_score,
                most_active_source=most_active_source,
                last_activity=activities[0].timestamp if activities else None
            )
            
        except Exception as e:
            logger.error("Erreur calcul stats activités", error=str(e))
            return ActivityStats(0, 0, {}, {}, 0.0, "", None)
    
    # === Méthodes de commodité pour types d'activités spécifiques ===
    
    async def add_insight_activity(self, insight_data: Dict[str, Any]):
        """Ajoute une activité pour un nouvel insight découvert"""
        await self.add_activity(
            activity_type=ActivityType.INSIGHT_DISCOVERED,
            title=f" Nouvel Insight Découvert",
            description=insight_data.get("title", "Insight sans titre"),
            details=insight_data,
            priority=ActivityPriority.NORMAL,
            source=ActivitySource.MCP,
            tech_areas=insight_data.get("tech_areas", []),
            impact_score=insight_data.get("impact_score", 0.7),
            url=insight_data.get("url")
        )
    
    async def add_alert_activity(self, alert_data: Dict[str, Any], is_critical: bool = False):
        """Ajoute une activité pour une alerte"""
        priority = ActivityPriority.CRITICAL if is_critical else ActivityPriority.HIGH
        activity_type = ActivityType.CRITICAL_ALERT if is_critical else ActivityType.CUSTOM_ALERT
        
        await self.add_activity(
            activity_type=activity_type,
            title=f" {'Alerte Critique' if is_critical else 'Alerte'}: {alert_data.get('name', 'Sans nom')}",
            description=alert_data.get("description", ""),
            details=alert_data,
            priority=priority,
            source=ActivitySource.LLM if is_critical else ActivitySource.SYSTEM,
            impact_score=alert_data.get("confidence_score", 0.8)
        )
    
    async def add_crawl_activity(self, source_name: str, status: str, details: Dict[str, Any] = None):
        """Ajoute une activité pour un crawl de source"""
        if status == "started":
            activity_type = ActivityType.CRAWL_STARTED
            title = f" Crawl Démarré: {source_name}"
            priority = ActivityPriority.LOW
        elif status == "completed":
            activity_type = ActivityType.CRAWL_COMPLETED
            title = f" Crawl Terminé: {source_name}"
            priority = ActivityPriority.NORMAL
        else:
            activity_type = ActivityType.SOURCE_CRAWLED
            title = f" Source Crawlée: {source_name}"
            priority = ActivityPriority.NORMAL
        
        await self.add_activity(
            activity_type=activity_type,
            title=title,
            description=f"Crawl de {source_name} - Statut: {status}",
            details=details or {},
            priority=priority,
            source=ActivitySource.CRAWLER,
            source_name=source_name
        )
    
    async def add_search_activity(self, query: str, results_count: int, user_id: str = "default"):
        """Ajoute une activité pour une recherche utilisateur"""
        await self.add_activity(
            activity_type=ActivityType.USER_SEARCH,
            title=f" Recherche: \"{query[:50]}{'...' if len(query) > 50 else ''}\"",
            description=f"{results_count} résultats trouvés",
            details={"query": query, "results_count": results_count},
            priority=ActivityPriority.LOW,
            source=ActivitySource.USER,
            user_id=user_id
        )
    
    async def add_summary_activity(self, summary_type: str, summary_data: Dict[str, Any]):
        """Ajoute une activité pour un résumé généré"""
        if summary_type == "daily":
            activity_type = ActivityType.DAILY_SUMMARY
            title = "📋 Résumé Quotidien Généré"
        elif summary_type == "focus":
            activity_type = ActivityType.FOCUS_MODE
            title = "🎯 Synthèse Focus Générée"
        else:
            activity_type = ActivityType.LLM_ANALYSIS
            title = f"🤖 Analyse LLM: {summary_type}"
        
        await self.add_activity(
            activity_type=activity_type,
            title=title,
            description=f"Analyse générée avec {summary_data.get('sections_count', 0)} sections",
            details=summary_data,
            priority=ActivityPriority.NORMAL,
            source=ActivitySource.LLM,
            impact_score=0.8
        )
    
    # === Méthodes internes ===
    
    def _filter_activities(
        self,
        activities: List[ActivityItem],
        activity_types: List[ActivityType] = None,
        priorities: List[ActivityPriority] = None,
        sources: List[ActivitySource] = None,
        user_id: Optional[str] = None,
        tech_areas: List[str] = None,
        since: Optional[datetime] = None,
        include_system: bool = True
    ) -> List[ActivityItem]:
        """Filtre une liste d'activités selon les critères"""
        filtered = activities
        
        # Filtre par timestamp
        if since:
            filtered = [a for a in filtered if a.timestamp >= since]
        
        # Filtre par types
        if activity_types:
            filtered = [a for a in filtered if a.type in activity_types]
        
        # Filtre par priorités
        if priorities:
            filtered = [a for a in filtered if a.priority in priorities]
        
        # Filtre par sources
        if sources:
            filtered = [a for a in filtered if a.source in sources]
        
        # Filtre par utilisateur
        if user_id:
            filtered = [a for a in filtered if a.user_id == user_id or a.user_id is None]
        
        # Filtre par aires technologiques
        if tech_areas:
            filtered = [a for a in filtered if any(area in a.tech_areas for area in tech_areas)]
        
        # Filtre système
        if not include_system:
            filtered = [a for a in filtered if a.source != ActivitySource.SYSTEM]
        
        return filtered
    
    async def _save_activity_to_redis(self, activity: ActivityItem):
        """Sauvegarde une activité en Redis"""
        try:
            activity_data = self._serialize_activity(activity)
            
            # Sauvegarde activité individuelle
            await self.redis.set(
                f"activity:data:{activity.id}",
                activity_data,
                expire=self.activity_ttl
            )
            
            # Ajout à la liste triée par timestamp
            await self._add_to_sorted_list(activity)
            
        except Exception as e:
            logger.error("Erreur sauvegarde activité Redis", error=str(e))
    
    async def _add_to_sorted_list(self, activity: ActivityItem):
        """Ajoute l'activité à la liste triée Redis"""
        try:
            # Utilisation d'un score basé sur timestamp pour tri
            score = int(activity.timestamp.timestamp() * 1000)
            
            # Ajout à la liste globale
            list_key = "activity:sorted:global"
            await self.redis.redis.zadd(list_key, {activity.id: score})
            
            # Limitation de la taille
            await self.redis.redis.zremrangebyrank(list_key, 0, -(self.max_activities_redis + 1))
            
            # TTL sur la liste
            await self.redis.redis.expire(list_key, self.activity_ttl)
            
        except Exception as e:
            logger.error("Erreur ajout liste triée Redis", error=str(e))
    
    async def _load_activities_from_redis(
        self,
        limit: int = 100,
        activity_types: List[ActivityType] = None,
        priorities: List[ActivityPriority] = None,
        sources: List[ActivitySource] = None,
        user_id: Optional[str] = None,
        tech_areas: List[str] = None,
        since: Optional[datetime] = None,
        include_system: bool = True
    ) -> List[ActivityItem]:
        """Charge les activités depuis Redis avec filtres"""
        try:
            # Récupération des IDs triés (plus récents en premier)
            list_key = "activity:sorted:global"
            activity_ids = await self.redis.redis.zrevrange(list_key, 0, limit * 2)  # Marge pour filtrage
            
            if not activity_ids:
                return []
            
            # Chargement des activités
            activities = []
            for activity_id in activity_ids:
                activity_data = await self.redis.get(f"activity:data:{activity_id}")
                if activity_data:
                    activity = self._deserialize_activity(activity_data)
                    activities.append(activity)
            
            # Application des filtres
            filtered_activities = self._filter_activities(
                activities,
                activity_types=activity_types,
                priorities=priorities,
                sources=sources,
                user_id=user_id,
                tech_areas=tech_areas,
                since=since,
                include_system=include_system
            )
            
            return filtered_activities[:limit]
            
        except Exception as e:
            logger.error("Erreur chargement activités Redis", error=str(e))
            return []
    
    async def _load_recent_activities(self):
        """Charge les activités récentes en mémoire au démarrage"""
        try:
            recent_activities = await self._load_activities_from_redis(limit=self.max_activities)
            
            self.recent_activities = recent_activities
            self.activity_cache = {a.id: a for a in recent_activities}
            
            logger.info(f"Chargé {len(recent_activities)} activités récentes")
            
        except Exception as e:
            logger.error("Erreur chargement activités récentes", error=str(e))
    
    async def _setup_websocket(self):
        """Configure la connexion WebSocket pour diffusion temps réel"""
        try:
            from .websocket_manager import get_websocket_manager
            self.websocket_manager = await get_websocket_manager()
        except Exception as e:
            logger.warning("WebSocket non disponible pour ActivityFeed", error=str(e))
    
    async def _broadcast_activity(self, activity: ActivityItem):
        """Diffuse une nouvelle activité via WebSocket"""
        try:
            # Diffusion via le WebSocketManager (abonnements de type 'activity_feed')
            if self.websocket_manager:
                message = {
                    "type": "new_activity",
                    "data": {
                        "id": activity.id,
                        "type": activity.type.value,
                        "priority": activity.priority.value,
                        "source": activity.source.value,
                        "title": activity.title,
                        "description": activity.description,
                        "timestamp": activity.timestamp.isoformat(),
                        "tech_areas": activity.tech_areas,
                        "impact_score": activity.impact_score,
                        "url": activity.url
                    }
                }
                await self.websocket_manager.broadcast_to_topic("activity_feed", message)

            # --- Nouvel ajout : compatibilité avec ConnectionManager (/ws endpoints) ---
            # On tente d'utiliser le connection_manager (si présent) afin que les
            # clients connectés sur l'endpoint /ws/dashboard reçoivent également
            # l'événement en temps réel, sans dépendre du système d'abonnement.
            try:
                from api.routes.websocket import connection_manager, WebSocketMessage, NotificationType

                ws_msg = WebSocketMessage(
                    type=NotificationType.USER_ACTION,  # Type générique réutilisable
                    data={
                        "event": "new_activity",
                        "activity": {
                            "id": activity.id,
                            "type": activity.type.value,
                            "priority": activity.priority.value,
                            "source": activity.source.value,
                            "title": activity.title,
                            "description": activity.description,
                            "timestamp": activity.timestamp.isoformat(),
                            "tech_areas": activity.tech_areas,
                            "impact_score": activity.impact_score,
                            "url": activity.url
                        }
                    },
                    badge_text="NEW",
                    priority="low"
                )

                # Diffusion aux groupes principaux susceptibles d'afficher le feed
                await connection_manager.broadcast_to_group("dashboard", ws_msg)
                await connection_manager.broadcast_to_group("notifications", ws_msg)

            except ImportError:
                # Le module peut ne pas être disponible dans certains contextes (tests)
                pass
            except Exception as e:
                logger.warning("Erreur diffusion ConnectionManager", error=str(e))

        except Exception as e:
            logger.warning("Erreur diffusion activité WebSocket", error=str(e))
    
    async def _update_activity_stats(self, activity: ActivityItem):
        """Met à jour les statistiques d'activité"""
        try:
            # Mise à jour compteurs Redis
            stats_key = "activity:stats:global"
            current_stats = await self.redis.get(stats_key) or {}
            
            # Mise à jour compteurs
            current_stats['total_count'] = current_stats.get('total_count', 0) + 1
            current_stats['last_activity'] = activity.timestamp.isoformat()
            
            # Compteur par type
            type_key = f"type_{activity.type.value}"
            current_stats[type_key] = current_stats.get(type_key, 0) + 1
            
            # Compteur par priorité
            priority_key = f"priority_{activity.priority.value}"
            current_stats[priority_key] = current_stats.get(priority_key, 0) + 1
            
            await self.redis.set(stats_key, current_stats, expire=self.activity_ttl)
            
        except Exception as e:
            logger.error("Erreur mise à jour stats activités", error=str(e))
    
    def _serialize_activity(self, activity: ActivityItem) -> Dict[str, Any]:
        """Sérialise une activité pour Redis"""
        data = asdict(activity)
        data['timestamp'] = activity.timestamp.isoformat()
        return data
    
    def _deserialize_activity(self, data: Dict[str, Any]) -> ActivityItem:
        """Désérialise une activité depuis Redis"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['type'] = ActivityType(data['type'])
        data['priority'] = ActivityPriority(data['priority'])
        data['source'] = ActivitySource(data['source'])
        return ActivityItem(**data)
    
    async def cleanup(self):
        """Nettoie les ressources"""
        self.recent_activities.clear()
        self.activity_cache.clear()
        logger.info("ActivityFeedManager nettoyé")

    # === Méthodes utilitaires bookmarks ===

    async def _get_user_bookmarked_ids(self, user_id: str) -> Set[str]:
        """Récupère l'ensemble des IDs bookmarkés par l'utilisateur"""
        try:
            pattern = f"activity:bookmarks:{user_id}:*"
            keys = await self.redis.redis.keys(pattern)
            # Extraire l'ID (dernier segment après colon)
            return {key.split(":")[-1] for key in keys}
        except Exception as e:
            logger.error("Erreur récupération clés bookmarks", error=str(e))
            return set()

    async def get_bookmarked_activities(self, user_id: str = "default", limit: int = 50, offset: int = 0) -> List[ActivityItem]:
        """Retourne la liste des activités bookmarkées par l'utilisateur"""
        try:
            bookmarked_ids = await self._get_user_bookmarked_ids(user_id)
            if not bookmarked_ids:
                return []

            activities: List[ActivityItem] = []
            for activity_id in bookmarked_ids:
                activity = await self.get_activity_by_id(activity_id)
                if activity:
                    activity.bookmarked = True
                    activities.append(activity)

            # Tri par date décroissante
            activities.sort(key=lambda a: a.timestamp, reverse=True)
            return activities[offset: offset + limit]
        except Exception as e:
            logger.error("Erreur récupération activités bookmarkées", error=str(e))
            return []

# Instance globale
_activity_feed_manager: Optional[ActivityFeedManager] = None

async def get_activity_feed_manager() -> ActivityFeedManager:
    """Récupère l'instance globale du gestionnaire d'activité"""
    global _activity_feed_manager
    
    if _activity_feed_manager is None:
        from database.redis_client import RedisClient
        
        redis_client = RedisClient()
        _activity_feed_manager = ActivityFeedManager(redis_client)
        await _activity_feed_manager.initialize()
    
    return _activity_feed_manager
