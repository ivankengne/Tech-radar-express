"""
Tech Radar Express - Routes API LLM Provider Management
Routes pour configuration LLM et switch de providers
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import structlog

from core.llm_provider_manager import (
    LLMProviderManager,
    get_llm_provider_manager,
    LLMProvider,
    LLMModel,
    LLMProviderConfig
)
from core.config_manager import get_settings

# Configuration du logger
logger = structlog.get_logger(__name__)

# Router principal pour la gestion LLM
router = APIRouter(
    prefix="/api/v1/llm",
    tags=["LLM Provider Management"],
    responses={
        404: {"description": "Provider ou modèle non trouvé"},
        500: {"description": "Erreur serveur LLM"},
        503: {"description": "Provider LLM indisponible"}
    }
)

# ===================================
# MODÈLES DE REQUÊTE ET RÉPONSE
# ===================================

class ProviderSwitchRequest(BaseModel):
    """Requête pour changer de provider LLM"""
    provider: LLMProvider = Field(description="Provider à activer")
    model: Optional[str] = Field(default=None, description="Modèle spécifique (optionnel)")

class ProviderConfigRequest(BaseModel):
    """Requête pour configurer un provider"""
    provider: LLMProvider = Field(description="Provider à configurer")
    api_key: Optional[str] = Field(default=None, description="Clé API")
    base_url: Optional[str] = Field(default=None, description="URL de base")
    organization: Optional[str] = Field(default=None, description="Organisation (OpenAI)")
    project: Optional[str] = Field(default=None, description="Projet (OpenAI)")
    region: Optional[str] = Field(default=None, description="Région (Gemini)")
    enabled: bool = Field(default=True, description="Activer le provider")
    timeout: int = Field(default=30, ge=5, le=120, description="Timeout en secondes")
    max_retries: int = Field(default=3, ge=1, le=5, description="Nombre max de retry")

class APIKeyValidationRequest(BaseModel):
    """Requête pour valider une clé API"""
    provider: LLMProvider = Field(description="Provider à tester")
    api_key: str = Field(description="Clé API à valider")
    base_url: Optional[str] = Field(default=None, description="URL personnalisée")

class ProviderStatusResponse(BaseModel):
    """Réponse statut complet des providers"""
    active_provider: Optional[str] = Field(description="Provider actuel")
    active_model: Optional[str] = Field(description="Modèle actuel")
    providers: Dict[str, Any] = Field(description="Statut détaillé par provider")
    total_providers: int = Field(description="Nombre total de providers")
    enabled_providers: int = Field(description="Nombre de providers activés")
    healthy_providers: int = Field(description="Nombre de providers en santé")

class ModelListResponse(BaseModel):
    """Réponse liste des modèles"""
    provider: str = Field(description="Provider des modèles")
    models: List[LLMModel] = Field(description="Liste des modèles disponibles")
    total_models: int = Field(description="Nombre total de modèles")
    cached: bool = Field(description="Résultats mis en cache")
    last_updated: float = Field(description="Timestamp dernière MAJ")

# ===================================
# ENDPOINTS PRINCIPAUX
# ===================================

@router.get(
    "/status",
    response_model=ProviderStatusResponse,
    summary="Statut des providers LLM",
    description="Récupère le statut complet de tous les providers LLM configurés"
)
async def get_providers_status(
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> ProviderStatusResponse:
    """Retourne le statut de tous les providers LLM"""
    try:
        logger.info("Récupération statut providers LLM")
        
        status = await llm_manager.get_provider_status()
        
        # Calcul des métriques
        providers = status["providers"]
        enabled_count = sum(1 for p in providers.values() if p["enabled"])
        healthy_count = sum(1 for p in providers.values() if p["healthy"])
        
        return ProviderStatusResponse(
            active_provider=status["active_provider"],
            active_model=status["active_model"],
            providers=providers,
            total_providers=len(providers),
            enabled_providers=enabled_count,
            healthy_providers=healthy_count
        )
        
    except Exception as e:
        logger.error("Erreur récupération statut providers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du statut: {str(e)}"
        )

@router.post(
    "/switch",
    summary="Changer de provider LLM",
    description="Change le provider LLM actif et optionnellement le modèle"
)
async def switch_provider(
    request: ProviderSwitchRequest,
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> Dict[str, Any]:
    """Change le provider LLM actif"""
    try:
        logger.info(
            "Changement provider LLM demandé",
            provider=request.provider.value,
            model=request.model
        )
        
        success = await llm_manager.set_active_provider(
            provider=request.provider,
            model=request.model
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible de changer vers le provider {request.provider.value}"
            )
        
        # Récupérer le nouveau statut
        new_status = await llm_manager.get_provider_status()
        
        return {
            "success": True,
            "message": f"Provider changé vers {request.provider.value}",
            "active_provider": new_status["active_provider"],
            "active_model": new_status["active_model"],
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur changement provider", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du changement de provider: {str(e)}"
        )

@router.get(
    "/models/{provider}",
    response_model=ModelListResponse,
    summary="Liste des modèles d'un provider",
    description="Récupère la liste des modèles disponibles pour un provider spécifique"
)
async def get_provider_models(
    provider: LLMProvider = Path(..., description="Provider LLM"),
    refresh: bool = Query(default=False, description="Forcer le refresh du cache"),
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> ModelListResponse:
    """Récupère les modèles disponibles pour un provider"""
    try:
        logger.info("Récupération modèles", provider=provider.value, refresh=refresh)
        
        # Forcer le refresh du cache si demandé
        if refresh and provider in llm_manager.models_cache:
            del llm_manager.models_cache[provider]
        
        models = await llm_manager.get_available_models(provider)
        
        return ModelListResponse(
            provider=provider.value,
            models=models,
            total_models=len(models),
            cached=provider in llm_manager.models_cache and not refresh,
            last_updated=time.time()
        )
        
    except Exception as e:
        logger.error("Erreur récupération modèles", provider=provider.value, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des modèles {provider.value}: {str(e)}"
        )

@router.get(
    "/models",
    summary="Tous les modèles disponibles",
    description="Récupère tous les modèles de tous les providers activés"
)
async def get_all_models(
    enabled_only: bool = Query(default=True, description="Seulement les providers activés"),
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> Dict[str, Any]:
    """Récupère tous les modèles de tous les providers"""
    try:
        logger.info("Récupération tous modèles", enabled_only=enabled_only)
        
        all_models = {}
        total_models = 0
        
        for provider in LLMProvider:
            config = llm_manager.configs.get(provider)
            if enabled_only and (not config or not config.enabled):
                continue
            
            try:
                models = await llm_manager.get_available_models(provider)
                all_models[provider.value] = [model.dict() for model in models]
                total_models += len(models)
                
            except Exception as e:
                logger.warning(f"Échec récupération modèles {provider.value}", error=str(e))
                all_models[provider.value] = []
        
        return {
            "models_by_provider": all_models,
            "total_models": total_models,
            "providers_count": len(all_models),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Erreur récupération tous modèles", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des modèles: {str(e)}"
        )

@router.post(
    "/validate-key",
    summary="Valider une clé API",
    description="Valide une clé API pour un provider donné"
)
async def validate_api_key(
    request: APIKeyValidationRequest,
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> Dict[str, Any]:
    """Valide une clé API pour un provider"""
    try:
        logger.info("Validation clé API", provider=request.provider.value)
        
        # Créer une configuration temporaire pour le test
        original_config = llm_manager.configs[request.provider]
        
        # Test avec la nouvelle clé
        test_config = original_config.copy()
        test_config.api_key = request.api_key
        if request.base_url:
            test_config.base_url = request.base_url
        
        # Remplacer temporairement la config
        llm_manager.configs[request.provider] = test_config
        
        try:
            # Réinitialiser le client pour prendre en compte la nouvelle clé
            if request.provider in llm_manager.clients:
                await llm_manager.clients[request.provider].aclose()
                del llm_manager.clients[request.provider]
            
            await llm_manager.initialize_clients()
            
            # Tester la santé du provider
            health = await llm_manager.check_provider_health(request.provider)
            
            # Tenter de récupérer les modèles
            models_count = 0
            try:
                # Supprimer le cache pour forcer un appel API
                if request.provider in llm_manager.models_cache:
                    del llm_manager.models_cache[request.provider]
                
                models = await llm_manager.get_available_models(request.provider)
                models_count = len(models)
            except Exception:
                pass  # Les modèles ne sont pas critiques pour la validation
            
            return {
                "valid": health,
                "provider": request.provider.value,
                "models_accessible": models_count > 0,
                "models_count": models_count,
                "message": "Clé API valide" if health else "Clé API invalide ou service indisponible",
                "timestamp": time.time()
            }
            
        finally:
            # Restaurer la configuration originale
            llm_manager.configs[request.provider] = original_config
            
            # Réinitialiser le client avec l'ancienne config
            if request.provider in llm_manager.clients:
                await llm_manager.clients[request.provider].aclose()
                del llm_manager.clients[request.provider]
            
            await llm_manager.initialize_clients()
        
    except Exception as e:
        logger.error("Erreur validation clé API", provider=request.provider.value, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la validation: {str(e)}"
        )

@router.get(
    "/statistics",
    summary="Statistiques d'utilisation LLM",
    description="Récupère les statistiques d'utilisation des providers LLM"
)
async def get_llm_statistics(
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> Dict[str, Any]:
    """Retourne les statistiques d'utilisation LLM"""
    try:
        stats = llm_manager.get_statistics()
        
        # Ajouter des métriques calculées
        success_rate = 0.0
        if stats["total_requests"] > 0:
            success_rate = (stats["successful_requests"] / stats["total_requests"]) * 100
        
        return {
            **stats,
            "success_rate": f"{success_rate:.1f}%",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Erreur récupération statistiques LLM", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )

@router.post(
    "/config/{provider}",
    summary="Configurer un provider",
    description="Met à jour la configuration d'un provider LLM"
)
async def configure_provider(
    provider: LLMProvider = Path(..., description="Provider à configurer"),
    request: ProviderConfigRequest = ...,
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> Dict[str, Any]:
    """Configure un provider LLM"""
    try:
        logger.info("Configuration provider", provider=provider.value)
        
        if provider != request.provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le provider dans l'URL doit correspondre à celui dans le body"
            )
        
        # Mettre à jour la configuration
        config = llm_manager.configs[provider]
        
        if request.api_key is not None:
            config.api_key = request.api_key
        if request.base_url is not None:
            config.base_url = request.base_url
        if request.organization is not None:
            config.organization = request.organization
        if request.project is not None:
            config.project = request.project
        if request.region is not None:
            config.region = request.region
        
        config.enabled = request.enabled
        config.timeout = request.timeout
        config.max_retries = request.max_retries
        
        # Réinitialiser le client avec la nouvelle config
        if provider in llm_manager.clients:
            await llm_manager.clients[provider].aclose()
            del llm_manager.clients[provider]
        
        # Vider le cache des modèles
        if provider in llm_manager.models_cache:
            del llm_manager.models_cache[provider]
        
        await llm_manager.initialize_clients()
        
        # Tester la santé du provider
        health = await llm_manager.check_provider_health(provider)
        
        return {
            "success": True,
            "provider": provider.value,
            "healthy": health,
            "enabled": config.enabled,
            "message": f"Configuration {provider.value} mise à jour",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Erreur configuration provider", provider=provider.value, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la configuration: {str(e)}"
        )

@router.post(
    "/reset-cache",
    summary="Vider le cache des modèles",
    description="Vide le cache des modèles pour forcer un refresh"
)
async def reset_models_cache(
    provider: Optional[LLMProvider] = Query(default=None, description="Provider spécifique (optionnel)"),
    llm_manager: LLMProviderManager = Depends(get_llm_provider_manager)
) -> Dict[str, Any]:
    """Vide le cache des modèles"""
    try:
        if provider:
            if provider in llm_manager.models_cache:
                del llm_manager.models_cache[provider]
            logger.info("Cache modèles vidé", provider=provider.value)
            message = f"Cache {provider.value} vidé"
        else:
            llm_manager.models_cache.clear()
            logger.info("Cache modèles complètement vidé")
            message = "Cache complet vidé"
        
        return {
            "success": True,
            "message": message,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Erreur reset cache", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du reset du cache: {str(e)}"
        ) 