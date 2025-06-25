"""
Décorateur pour tracer automatiquement les appels LLM avec Langfuse.

Ce module fournit des décorateurs et utilitaires pour :
- Tracer automatiquement les appels aux providers LLM
- Calculer les métriques (tokens, coûts, latence)
- Gérer les erreurs et retry
- Intégrer avec Langfuse de manière transparente
"""

import asyncio
import functools
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union
import inspect

from .langfuse_manager import LangfuseManager, LLMProvider, CallType
from .config_manager import ConfigManager
from ..database.redis_client import RedisClient

import structlog
logger = structlog.get_logger(__name__)

class LLMTracer:
    """Traceur pour les appels LLM avec intégration Langfuse."""
    
    def __init__(self, langfuse_manager: Optional[LangfuseManager] = None):
        self.langfuse_manager = langfuse_manager
        self.is_enabled = langfuse_manager is not None and langfuse_manager.is_enabled
    
    def trace_llm_call(
        self,
        provider: Union[str, LLMProvider],
        model: str,
        call_type: Union[str, CallType] = CallType.CHAT,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Décorateur pour tracer les appels LLM.
        
        Args:
            provider: Provider LLM (openai, anthropic, google, ollama)
            model: Nom du modèle utilisé
            call_type: Type d'appel (chat, completion, embedding, function_call)
            user_id: Identifiant utilisateur optionnel
            session_id: Identifiant de session optionnel
            metadata: Métadonnées additionnelles
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._trace_async_call(
                    func, provider, model, call_type, user_id, session_id, metadata,
                    *args, **kwargs
                )
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._trace_sync_call(
                    func, provider, model, call_type, user_id, session_id, metadata,
                    *args, **kwargs
                )
            
            # Retourner le wrapper approprié selon si la fonction est async ou non
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def _trace_async_call(
        self,
        func: Callable,
        provider: Union[str, LLMProvider],
        model: str,
        call_type: Union[str, CallType],
        user_id: Optional[str],
        session_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
        *args,
        **kwargs
    ):
        """Trace un appel LLM asynchrone."""
        if not self.is_enabled:
            # Si le traçage n'est pas activé, on exécute directement la fonction
            return await func(*args, **kwargs)
        
        # Conversion des enums si nécessaire
        if isinstance(provider, str):
            try:
                provider = LLMProvider(provider.lower())
            except ValueError:
                logger.warning(f"Provider inconnu: {provider}, utilisation de 'ollama' par défaut")
                provider = LLMProvider.OLLAMA
        
        if isinstance(call_type, str):
            try:
                call_type = CallType(call_type.lower())
            except ValueError:
                call_type = CallType.CHAT
        
        start_time = time.time()
        
        try:
            # Préparation des données d'entrée
            input_data = self._prepare_input_data(func, args, kwargs)
            
            # Exécution de la fonction
            result = await func(*args, **kwargs)
            
            # Calcul de la durée
            duration_ms = (time.time() - start_time) * 1000
            
            # Préparation des données de sortie
            output_data = self._prepare_output_data(result)
            
            # Traçage avec Langfuse
            if self.langfuse_manager:
                trace_id = await self.langfuse_manager.trace_llm_call(
                    provider=provider,
                    model=model,
                    call_type=call_type,
                    input_data=input_data,
                    output_data=output_data,
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        **(metadata or {}),
                        "duration_ms": duration_ms,
                        "function_name": func.__name__,
                        "success": True
                    }
                )
                
                logger.debug(
                    "Appel LLM tracé",
                    trace_id=trace_id,
                    provider=provider.value,
                    model=model,
                    duration_ms=duration_ms
                )
            
            return result
            
        except Exception as e:
            # Calcul de la durée même en cas d'erreur
            duration_ms = (time.time() - start_time) * 1000
            
            # Traçage de l'erreur
            if self.langfuse_manager:
                try:
                    await self.langfuse_manager.trace_llm_call(
                        provider=provider,
                        model=model,
                        call_type=call_type,
                        input_data=self._prepare_input_data(func, args, kwargs),
                        output_data={"error": str(e), "error_type": type(e).__name__},
                        user_id=user_id,
                        session_id=session_id,
                        metadata={
                            **(metadata or {}),
                            "duration_ms": duration_ms,
                            "function_name": func.__name__,
                            "success": False,
                            "error": str(e)
                        }
                    )
                except Exception as trace_error:
                    logger.error(f"Erreur lors du traçage de l'erreur LLM: {trace_error}")
            
            logger.error(
                "Erreur dans l'appel LLM",
                provider=provider.value,
                model=model,
                error=str(e),
                duration_ms=duration_ms
            )
            
            # Re-lancer l'exception originale
            raise
    
    def _trace_sync_call(
        self,
        func: Callable,
        provider: Union[str, LLMProvider],
        model: str,
        call_type: Union[str, CallType],
        user_id: Optional[str],
        session_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
        *args,
        **kwargs
    ):
        """Trace un appel LLM synchrone."""
        if not self.is_enabled:
            return func(*args, **kwargs)
        
        # Conversion des enums si nécessaire
        if isinstance(provider, str):
            try:
                provider = LLMProvider(provider.lower())
            except ValueError:
                provider = LLMProvider.OLLAMA
        
        if isinstance(call_type, str):
            try:
                call_type = CallType(call_type.lower())
            except ValueError:
                call_type = CallType.CHAT
        
        start_time = time.time()
        
        try:
            # Préparation des données d'entrée
            input_data = self._prepare_input_data(func, args, kwargs)
            
            # Exécution de la fonction
            result = func(*args, **kwargs)
            
            # Calcul de la durée
            duration_ms = (time.time() - start_time) * 1000
            
            # Préparation des données de sortie
            output_data = self._prepare_output_data(result)
            
            # Traçage avec Langfuse (version synchrone)
            if self.langfuse_manager:
                # Pour les appels synchrones, on délègue le traçage à un thread séparé
                # ou on utilise une version synchrone du traçage
                try:
                    # Création d'un event loop temporaire si nécessaire
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    if loop.is_running():
                        # Si on est déjà dans un event loop, on planifie la tâche
                        asyncio.create_task(
                            self.langfuse_manager.trace_llm_call(
                                provider=provider,
                                model=model,
                                call_type=call_type,
                                input_data=input_data,
                                output_data=output_data,
                                user_id=user_id,
                                session_id=session_id,
                                metadata={
                                    **(metadata or {}),
                                    "duration_ms": duration_ms,
                                    "function_name": func.__name__,
                                    "success": True
                                }
                            )
                        )
                    else:
                        # Sinon on exécute synchronement
                        loop.run_until_complete(
                            self.langfuse_manager.trace_llm_call(
                                provider=provider,
                                model=model,
                                call_type=call_type,
                                input_data=input_data,
                                output_data=output_data,
                                user_id=user_id,
                                session_id=session_id,
                                metadata={
                                    **(metadata or {}),
                                    "duration_ms": duration_ms,
                                    "function_name": func.__name__,
                                    "success": True
                                }
                            )
                        )
                except Exception as trace_error:
                    logger.error(f"Erreur lors du traçage LLM synchrone: {trace_error}")
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "Erreur dans l'appel LLM synchrone",
                provider=provider.value,
                model=model,
                error=str(e),
                duration_ms=duration_ms
            )
            
            raise
    
    def _prepare_input_data(self, func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Prépare les données d'entrée pour le traçage."""
        try:
            # Obtenir la signature de la fonction
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Convertir en dictionnaire sérialisable
            input_data = {}
            for param_name, param_value in bound_args.arguments.items():
                try:
                    # Essayer de sérialiser la valeur
                    if isinstance(param_value, (str, int, float, bool, list, dict, type(None))):
                        input_data[param_name] = param_value
                    else:
                        # Pour les objets complexes, on prend leur représentation string
                        input_data[param_name] = str(param_value)
                except Exception:
                    input_data[param_name] = f"<{type(param_value).__name__}>"
            
            return input_data
            
        except Exception as e:
            logger.warning(f"Erreur lors de la préparation des données d'entrée: {e}")
            return {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
    
    def _prepare_output_data(self, result: Any) -> Dict[str, Any]:
        """Prépare les données de sortie pour le traçage."""
        try:
            if isinstance(result, (str, int, float, bool, list, dict, type(None))):
                return {"result": result}
            elif hasattr(result, '__dict__'):
                # Pour les objets avec attributs
                return {"result": vars(result)}
            else:
                return {"result": str(result)}
                
        except Exception as e:
            logger.warning(f"Erreur lors de la préparation des données de sortie: {e}")
            return {
                "result_type": type(result).__name__,
                "result_str": str(result)[:500]  # Limiter la taille
            }

# === Fonctions utilitaires ===

def create_llm_tracer(config_manager: ConfigManager, redis_client: RedisClient) -> LLMTracer:
    """Crée un traceur LLM avec la configuration fournie."""
    try:
        if config_manager.monitoring_enabled:
            langfuse_manager = LangfuseManager(config_manager, redis_client)
            # Note: l'initialisation devra être faite séparément
            return LLMTracer(langfuse_manager)
        else:
            logger.info("Monitoring Langfuse désactivé, traceur en mode passif")
            return LLMTracer(None)
    except Exception as e:
        logger.error(f"Erreur lors de la création du traceur LLM: {e}")
        return LLMTracer(None)

# === Décorateurs de convenance ===

def trace_openai_call(model: str, **trace_kwargs):
    """Décorateur de convenance pour tracer les appels OpenAI."""
    def decorator(func):
        tracer = LLMTracer()  # Sera initialisé globalement
        return tracer.trace_llm_call(
            provider=LLMProvider.OPENAI,
            model=model,
            **trace_kwargs
        )(func)
    return decorator

def trace_anthropic_call(model: str, **trace_kwargs):
    """Décorateur de convenance pour tracer les appels Anthropic."""
    def decorator(func):
        tracer = LLMTracer()
        return tracer.trace_llm_call(
            provider=LLMProvider.ANTHROPIC,
            model=model,
            **trace_kwargs
        )(func)
    return decorator

def trace_google_call(model: str, **trace_kwargs):
    """Décorateur de convenance pour tracer les appels Google."""
    def decorator(func):
        tracer = LLMTracer()
        return tracer.trace_llm_call(
            provider=LLMProvider.GOOGLE,
            model=model,
            **trace_kwargs
        )(func)
    return decorator

def trace_ollama_call(model: str, **trace_kwargs):
    """Décorateur de convenance pour tracer les appels Ollama."""
    def decorator(func):
        tracer = LLMTracer()
        return tracer.trace_llm_call(
            provider=LLMProvider.OLLAMA,
            model=model,
            **trace_kwargs
        )(func)
    return decorator

# === Instance globale ===
_global_tracer: Optional[LLMTracer] = None

def get_global_tracer() -> LLMTracer:
    """Récupère l'instance globale du traceur."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = LLMTracer(None)  # Mode passif par défaut
    return _global_tracer

def set_global_tracer(tracer: LLMTracer):
    """Définit l'instance globale du traceur."""
    global _global_tracer
    _global_tracer = tracer