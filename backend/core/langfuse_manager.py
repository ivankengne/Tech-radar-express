"""
Gestionnaire Langfuse pour monitoring des LLM et collecte de métriques.

Ce module gère :
- Configuration du client Langfuse local
- Traçage automatique des appels LLM
- Collecte de métriques (latence, tokens, coûts)
- Dashboard de monitoring
- Intégration avec tous les providers LLM
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from enum import Enum

from langfuse import Langfuse, observe
from pydantic import BaseModel, Field

from .config_manager import ConfigManager
from database.redis_client import RedisClient

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    """Énumération des providers LLM supportés."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"

class CallType(str, Enum):
    """Types d'appels LLM."""
    COMPLETION = "completion"
    CHAT = "chat"
    EMBEDDING = "embedding"
    FUNCTION_CALL = "function_call"

@dataclass
class LLMMetrics:
    """Métriques d'un appel LLM."""
    call_id: str
    provider: LLMProvider
    model: str
    call_type: CallType
    timestamp: datetime
    duration_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    success: bool
    error: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class LLMTrace(BaseModel):
    """Modèle pour une trace LLM complète."""
    trace_id: str
    name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    input: Dict[str, Any]
    output: Dict[str, Any]
    metadata: Dict[str, Any] = {}
    tags: List[str] = []
    version: Optional[str] = None
    release: Optional[str] = None

class LangfuseManager:
    """Gestionnaire principal pour Langfuse monitoring."""
    
    def __init__(self, config_manager: ConfigManager, redis_client: RedisClient):
        self.config = config_manager
        self.redis = redis_client
        self.client: Optional[Langfuse] = None
        self.is_enabled = True
        self.metrics_cache: List[LLMMetrics] = []
        self.cache_size_limit = 1000
        
        # Configuration des coûts par token (approximatifs)
        self.token_costs = {
            "gpt-4": {"input": 0.00003, "output": 0.00006},
            "gpt-4-turbo": {"input": 0.00001, "output": 0.00003},
            "gpt-3.5-turbo": {"input": 0.0000015, "output": 0.000002},
            "claude-3-opus": {"input": 0.000015, "output": 0.000075},
            "claude-3-sonnet": {"input": 0.000003, "output": 0.000015},
            "claude-3-haiku": {"input": 0.00000025, "output": 0.00000125},
            "gemini-pro": {"input": 0.0000005, "output": 0.0000015},
            "gemini-flash": {"input": 0.000000075, "output": 0.0000003},
            "ollama": {"input": 0.0, "output": 0.0}  # Local models = free
        }
    
    async def initialize(self):
        """Initialise le client Langfuse."""
        try:
            langfuse_config = self.config.langfuse
            
            # Configuration du client Langfuse v3.0.5 (API standard maintenue)
            self.client = Langfuse(
                secret_key=langfuse_config.secret_key,
                public_key=langfuse_config.public_key,
                host=langfuse_config.host,
                debug=langfuse_config.debug,
                threads=langfuse_config.threads,
                flush_at=langfuse_config.flush_at,
                flush_interval=langfuse_config.flush_interval,
                max_retries=langfuse_config.max_retries,
                timeout=langfuse_config.timeout
            )
            
            # Test de connexion
            await self._test_connection()
            
            logger.info("Langfuse initialisé avec succès", 
                       host=langfuse_config.host,
                       debug=langfuse_config.debug)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Langfuse: {e}")
            self.is_enabled = False
            raise
    
    async def _test_connection(self):
        """Test la connexion avec Langfuse."""
        try:
            # Test de connexion avec une trace simple
            trace = self.client.trace(
                name="connection_test",
                metadata={"test": True, "timestamp": datetime.utcnow().isoformat()}
            )
            
            # Flush pour envoyer immédiatement
            self.client.flush()
            
            logger.info("Test de connexion Langfuse v3.0.5 réussi")
            
        except Exception as e:
            logger.error(f"Test de connexion Langfuse v3.0.5 échoué: {e}")
            # En mode dégradé, on continue sans Langfuse
            self.is_enabled = False
            logger.warning("Langfuse désactivé - mode dégradé activé")
    
    @observe(name="llm_call")
    async def trace_llm_call(
        self,
        provider: LLMProvider,
        model: str,
        call_type: CallType,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Trace un appel LLM avec métriques complètes.
        
        Returns:
            str: L'ID de la trace créée
        """
        if not self.is_enabled or not self.client:
            return "disabled"
        
        start_time = datetime.utcnow()
        call_id = f"{provider.value}_{model}_{start_time.strftime('%Y%m%d_%H%M%S_%f')}"
        
        try:
            # Calcul des tokens et coûts
            input_tokens = self._estimate_tokens(input_data)
            output_tokens = self._estimate_tokens(output_data)
            total_tokens = input_tokens + output_tokens
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)
            
            # Durée de l'appel (sera calculée par le décorateur)
            duration_ms = 0.0  # Placeholder
            
            # Création de la trace Langfuse
            trace = self.client.trace(
                name=f"{provider.value}_{call_type.value}",
                input=input_data,
                output=output_data,
                metadata={
                    **(metadata or {}),
                    "provider": provider.value,
                    "model": model,
                    "call_type": call_type.value,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": cost_usd,
                    "timestamp": start_time.isoformat()
                },
                tags=[provider.value, model, call_type.value],
                user_id=user_id,
                session_id=session_id
            )
            
            # Sauvegarde des métriques
            metrics = LLMMetrics(
                call_id=call_id,
                provider=provider,
                model=model,
                call_type=call_type,
                timestamp=start_time,
                duration_ms=duration_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                success=True,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata
            )
            
            await self._save_metrics(metrics)
            
            logger.info("Trace LLM créée",
                       call_id=call_id,
                       provider=provider.value,
                       model=model,
                       tokens=total_tokens,
                       cost=cost_usd)
            
            # Retourner l'ID de la trace créée
            return trace.id if hasattr(trace, 'id') else call_id
            
        except Exception as e:
            logger.error(f"Erreur lors du traçage LLM: {e}")
            
            # Sauvegarde des métriques d'erreur
            error_metrics = LLMMetrics(
                call_id=call_id,
                provider=provider,
                model=model,
                call_type=call_type,
                timestamp=start_time,
                duration_ms=0.0,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                success=False,
                error=str(e),
                user_id=user_id,
                session_id=session_id,
                metadata=metadata
            )
            
            await self._save_metrics(error_metrics)
            return "error"
    
    async def create_generation(
        self,
        trace_id: str,
        name: str,
        model: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        usage: Dict[str, int],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Crée une génération dans une trace existante."""
        if not self.is_enabled or not self.client:
            return
        
        try:
            generation = self.client.generation(
                trace_id=trace_id,
                name=name,
                model=model,
                input=input_data,
                output=output_data,
                usage=usage,
                metadata=metadata or {}
            )
            
            logger.debug("Génération créée", trace_id=trace_id, name=name)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de génération: {e}")
    
    async def create_span(
        self,
        trace_id: str,
        name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Crée un span dans une trace existante."""
        if not self.is_enabled or not self.client:
            return
        
        try:
            span = self.client.span(
                trace_id=trace_id,
                name=name,
                input=input_data,
                output=output_data,
                metadata=metadata or {}
            )
            
            logger.debug("Span créé", trace_id=trace_id, name=name)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de span: {e}")
    
    async def get_metrics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Récupère un résumé des métriques LLM."""
        try:
            cache_key = "langfuse:metrics:summary"
            
            # Tentative de récupération du cache
            cached_summary = await self.redis.get(cache_key)
            if cached_summary and not any([start_date, end_date, provider, model]):
                return cached_summary
            
            # CORRECTION: Redis KEYS pattern au lieu de get_keys_pattern inexistant
            # Récupération des métriques depuis Redis
            try:
                # Utilisation de KEYS avec pattern (attention en production, préférer SCAN)
                all_metrics_keys = await self.redis.redis.keys("langfuse:metrics:*")
                all_metrics = []
                for key in all_metrics_keys:
                    metric_data = await self.redis.get(key)
                    if metric_data:
                        all_metrics.append(metric_data)
            except Exception as e:
                logger.error(f"Erreur récupération métriques: {e}")
                all_metrics = []
            
            if not all_metrics:
                return {
                    "total_calls": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "avg_duration": 0.0,
                    "success_rate": 0.0,
                    "providers": {},
                    "models": {},
                    "period": "all_time"
                }
            
            # Agrégation des métriques
            total_calls = len(all_metrics)
            total_tokens = 0
            total_cost = 0.0
            total_duration = 0.0
            successful_calls = 0
            
            providers_stats = {}
            models_stats = {}
            
            for metrics_data in all_metrics:
                if isinstance(metrics_data, dict):
                    total_tokens += metrics_data.get('total_tokens', 0)
                    total_cost += metrics_data.get('cost_usd', 0.0)
                    total_duration += metrics_data.get('duration_ms', 0.0)
                    
                    if metrics_data.get('success', False):
                        successful_calls += 1
                    
                    # Stats par provider
                    provider_name = metrics_data.get('provider', 'unknown')
                    if provider_name not in providers_stats:
                        providers_stats[provider_name] = {
                            'calls': 0, 'tokens': 0, 'cost': 0.0
                        }
                    providers_stats[provider_name]['calls'] += 1
                    providers_stats[provider_name]['tokens'] += metrics_data.get('total_tokens', 0)
                    providers_stats[provider_name]['cost'] += metrics_data.get('cost_usd', 0.0)
                    
                    # Stats par modèle
                    model_name = metrics_data.get('model', 'unknown')
                    if model_name not in models_stats:
                        models_stats[model_name] = {
                            'calls': 0, 'tokens': 0, 'cost': 0.0
                        }
                    models_stats[model_name]['calls'] += 1
                    models_stats[model_name]['tokens'] += metrics_data.get('total_tokens', 0)
                    models_stats[model_name]['cost'] += metrics_data.get('cost_usd', 0.0)
            
            summary = {
                "total_calls": total_calls,
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 4),
                "avg_duration": round(total_duration / max(total_calls, 1), 2),
                "success_rate": round((successful_calls / max(total_calls, 1)) * 100, 2),
                "providers": providers_stats,
                "models": models_stats,
                "period": "all_time",
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Cache du résumé
            await self.redis.set(
                cache_key, 
                summary, 
                expire=int(timedelta(minutes=15).total_seconds())
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques: {e}")
            return {"error": str(e)}
    
    async def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Récupère les traces récentes."""
        try:
            # Récupération des traces depuis le cache Redis
            traces_key = "langfuse:traces:recent"
            recent_traces = await self.redis.get(traces_key) or []
            
            # Limitation du nombre de traces
            if len(recent_traces) > limit:
                recent_traces = recent_traces[-limit:]
            
            return recent_traces
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des traces: {e}")
            return []
    
    async def flush_metrics(self):
        """Force l'envoi des métriques en attente."""
        if not self.is_enabled or not self.client:
            return
        
        try:
            # Flush du client Langfuse
            self.client.flush()
            
            # Sauvegarde du cache local en Redis
            if self.metrics_cache:
                cache_key = f"langfuse:metrics:batch:{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                await self.redis.set(
                    cache_key,
                    [asdict(metric) for metric in self.metrics_cache],
                    expire=int(timedelta(days=30).total_seconds())
                )
                
                logger.info(f"Sauvegarde de {len(self.metrics_cache)} métriques en cache")
                self.metrics_cache.clear()
            
        except Exception as e:
            logger.error(f"Erreur lors du flush des métriques: {e}")
    
    async def cleanup_old_metrics(self, days_to_keep: int = 30):
        """Nettoie les anciennes métriques."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # CORRECTION: Nettoyage des métriques Redis avec API standard
            try:
                pattern = "langfuse:metrics:*"
                keys = await self.redis.redis.keys(pattern)
                
                deleted_count = 0
                for key in keys:
                    # Extraction de la date depuis la clé si possible
                    try:
                        date_str = key.split(':')[-1]
                        key_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                        if key_date < cutoff_date:
                            await self.redis.delete(key)
                            deleted_count += 1
                    except (ValueError, IndexError):
                        # Clé sans date, on garde
                        continue
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage Redis: {e}")
                deleted_count = 0
            
            logger.info(f"Nettoyage: {deleted_count} anciennes métriques supprimées")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des métriques: {e}")
    
    # === Méthodes utilitaires ===
    
    def _estimate_tokens(self, data: Dict[str, Any]) -> int:
        """Estime le nombre de tokens dans les données."""
        try:
            # Conversion en texte
            if isinstance(data, dict):
                text = json.dumps(data, ensure_ascii=False)
            else:
                text = str(data)
            
            # Estimation approximative : 1 token ≈ 4 caractères
            return max(1, len(text) // 4)
            
        except Exception:
            return 1
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calcule le coût approximatif d'un appel."""
        try:
            # Recherche du modèle dans la table des coûts
            model_key = None
            for key in self.token_costs:
                if key in model.lower():
                    model_key = key
                    break
            
            if not model_key:
                return 0.0
            
            costs = self.token_costs[model_key]
            total_cost = (input_tokens * costs["input"]) + (output_tokens * costs["output"])
            
            return round(total_cost, 6)
            
        except Exception:
            return 0.0
    
    async def _save_metrics(self, metrics: LLMMetrics):
        """Sauvegarde les métriques en cache local et Redis."""
        try:
            # Cache local
            self.metrics_cache.append(metrics)
            
            # Limitation de la taille du cache
            if len(self.metrics_cache) > self.cache_size_limit:
                self.metrics_cache = self.metrics_cache[-self.cache_size_limit:]
            
            # Sauvegarde Redis
            metrics_key = f"langfuse:metrics:{metrics.call_id}"
            await self.redis.set(
                metrics_key,
                asdict(metrics),
                expire=int(timedelta(days=30).total_seconds())
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métriques: {e}")
    
    async def close(self):
        """Ferme proprement le gestionnaire Langfuse."""
        try:
            if self.client:
                # Flush final
                await self.flush_metrics()
                self.client.shutdown()
                
            logger.info("Langfuse fermé proprement")
            
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de Langfuse: {e}")

# === Context Manager ===

@asynccontextmanager
async def create_langfuse_manager(config_manager: ConfigManager, redis_client: RedisClient):
    """Context manager pour le gestionnaire Langfuse."""
    manager = LangfuseManager(config_manager, redis_client)
    
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.close() 