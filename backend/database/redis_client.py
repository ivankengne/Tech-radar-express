"""
Tech Radar Express - Client Redis/Valkey
Client pour cache et pub/sub avec Valkey (fork de Redis compatible)
"""

import redis.asyncio as redis
import structlog
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone, timedelta
from core.config_manager import get_settings

logger = structlog.get_logger(__name__)

class RedisClient:
    """Client Redis/Valkey pour cache et pub/sub temps réel"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Connexion à Redis/Valkey avec gestion d'erreurs"""
        try:
            self.redis = redis.from_url(
                self.settings.REDIS_URL,
                password=self.settings.REDIS_PASSWORD,
                db=self.settings.REDIS_DB,
                max_connections=self.settings.REDIS_POOL_SIZE,
                decode_responses=True,
                health_check_interval=30
            )
            
            # Test de connexion
            await self.redis.ping()
            self.is_connected = True
            
            logger.info("✅ Connexion Redis/Valkey établie", 
                       url=self.settings.REDIS_URL,
                       db=self.settings.REDIS_DB)
            return True
            
        except Exception as e:
            logger.error("❌ Erreur connexion Redis/Valkey", error=str(e))
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Fermeture des connexions"""
        try:
            if self.pubsub:
                await self.pubsub.close()
            if self.redis:
                await self.redis.close()
            self.is_connected = False
            logger.info("✅ Connexions Redis/Valkey fermées")
        except Exception as e:
            logger.error("❌ Erreur fermeture Redis/Valkey", error=str(e))
    
    # ===================================
    # Fonctions Cache
    # ===================================
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Définir une valeur avec expiration optionnelle"""
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            await self.redis.set(key, serialized_value, ex=expire)
            return True
        except Exception as e:
            logger.error("❌ Erreur set Redis", key=key, error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Récupérer une valeur"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            # Tenter de désérialiser le JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error("❌ Erreur get Redis", key=key, error=str(e))
            return None
    
    async def delete(self, key: str) -> bool:
        """Supprimer une clé"""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error("❌ Erreur delete Redis", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Vérifier l'existence d'une clé"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error("❌ Erreur exists Redis", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Définir une expiration sur une clé"""
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error("❌ Erreur expire Redis", key=key, error=str(e))
            return False
    
    # ===================================
    # Cache Structured Data
    # ===================================
    
    async def cache_dashboard_data(self, data: Dict[str, Any], ttl: int = 300):
        """Cache spécialisé pour données dashboard"""
        cache_key = "tech_radar:dashboard:data"
        cached_data = {
            "data": data,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl": ttl
        }
        return await self.set(cache_key, cached_data, expire=ttl)
    
    async def get_cached_dashboard_data(self) -> Optional[Dict[str, Any]]:
        """Récupérer données dashboard cachées"""
        cache_key = "tech_radar:dashboard:data"
        cached = await self.get(cache_key)
        
        if cached and isinstance(cached, dict):
            return cached.get("data")
        return None
    
    async def cache_search_results(self, query_hash: str, results: List[Dict], ttl: int = 1800):
        """Cache des résultats de recherche"""
        cache_key = f"tech_radar:search:{query_hash}"
        cached_results = {
            "results": results,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "query_hash": query_hash
        }
        return await self.set(cache_key, cached_results, expire=ttl)
    
    async def get_cached_search_results(self, query_hash: str) -> Optional[List[Dict]]:
        """Récupérer résultats de recherche cachés"""
        cache_key = f"tech_radar:search:{query_hash}"
        cached = await self.get(cache_key)
        
        if cached and isinstance(cached, dict):
            return cached.get("results")
        return None
    
    # ===================================
    # Pub/Sub pour WebSocket
    # ===================================
    
    async def publish_notification(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publier une notification"""
        try:
            notification = {
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": channel
            }
            
            await self.redis.publish(channel, json.dumps(notification))
            logger.debug("✅ Notification publiée", channel=channel)
            return True
            
        except Exception as e:
            logger.error("❌ Erreur publication notification", 
                        channel=channel, error=str(e))
            return False
    
    async def subscribe_to_notifications(self, channels: List[str]):
        """S'abonner aux notifications"""
        try:
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(*channels)
            logger.info("✅ Abonné aux notifications", channels=channels)
            return self.pubsub
            
        except Exception as e:
            logger.error("❌ Erreur abonnement notifications", 
                        channels=channels, error=str(e))
            return None
    
    async def publish_insight_update(self, insight_data: Dict[str, Any]):
        """Publier mise à jour d'insight"""
        return await self.publish_notification("insights:updates", {
            "type": "new_insight",
            "data": insight_data
        })
    
    async def publish_crawl_status(self, source_id: str, status: str, message: str = ""):
        """Publier statut de crawl"""
        return await self.publish_notification("crawl:status", {
            "type": "crawl_status_update",
            "source_id": source_id,
            "status": status,
            "message": message
        })
    
    async def publish_dashboard_update(self, update_type: str, data: Dict[str, Any]):
        """Publier mise à jour dashboard"""
        return await self.publish_notification("dashboard:updates", {
            "type": update_type,
            "data": data
        })
    
    # ===================================
    # Sessions et Rate Limiting
    # ===================================
    
    async def increment_request_count(self, client_ip: str, window_seconds: int = 60) -> int:
        """Incrémenter compteur de requêtes pour rate limiting"""
        try:
            key = f"rate_limit:{client_ip}:{window_seconds}"
            
            # Utiliser un pipeline pour atomicité
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            
            return results[0]  # Nombre de requêtes
            
        except Exception as e:
            logger.error("❌ Erreur rate limiting", client_ip=client_ip, error=str(e))
            return 0
    
    async def store_session(self, session_id: str, session_data: Dict[str, Any], ttl: int = 3600):
        """Stocker données de session"""
        session_key = f"session:{session_id}"
        return await self.set(session_key, session_data, expire=ttl)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer données de session"""
        session_key = f"session:{session_id}"
        return await self.get(session_key)
    
    async def delete_session(self, session_id: str) -> bool:
        """Supprimer session"""
        session_key = f"session:{session_id}"
        return await self.delete(session_key)
    
    # ===================================
    # Health Check et Stats
    # ===================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérification santé Redis/Valkey"""
        try:
            start_time = datetime.now()
            
            # Test ping
            await self.redis.ping()
            ping_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Récupérer infos serveur
            info = await self.redis.info()
            
            return {
                "status": "healthy",
                "ping_ms": round(ping_time, 2),
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
            
        except Exception as e:
            logger.error("❌ Health check Redis échoué", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # ===================================
    # Maintenance
    # ===================================
    
    async def cleanup_expired_keys(self, pattern: str = "tech_radar:*"):
        """Nettoyer les clés expirées (maintenance)"""
        try:
            # Compter les clés avant nettoyage
            keys_before = len(await self.redis.keys(pattern))
            
            # Redis/Valkey gère automatiquement l'expiration
            # Cette fonction peut être utilisée pour un nettoyage manuel si nécessaire
            
            keys_after = len(await self.redis.keys(pattern))
            
            logger.info("✅ Nettoyage Redis effectué", 
                       keys_before=keys_before,
                       keys_after=keys_after,
                       pattern=pattern)
            
        except Exception as e:
            logger.error("❌ Erreur nettoyage Redis", error=str(e)) 