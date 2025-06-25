"""
Tech Radar Express - LLM Provider Manager
Gestionnaire des providers LLM avec switch dynamique et configuration
Support: OpenAI, Claude (Anthropic), Gemini (Google), Ollama (local)
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from pydantic import BaseModel, Field, validator
import structlog

from .config_manager import get_settings

# Configuration du logger
logger = structlog.get_logger(__name__)

class LLMProvider(str, Enum):
    """Providers LLM supportés"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    OLLAMA = "ollama"

class LLMModel(BaseModel):
    """Modèle LLM avec métadonnées"""
    id: str = Field(description="Identifiant unique du modèle")
    name: str = Field(description="Nom d'affichage du modèle")
    provider: LLMProvider = Field(description="Provider du modèle")
    context_length: int = Field(default=4096, description="Longueur max du contexte")
    supports_streaming: bool = Field(default=True, description="Support du streaming")
    supports_function_calling: bool = Field(default=False, description="Support des function calls")
    cost_per_1k_tokens: Optional[float] = Field(default=None, description="Coût par 1000 tokens (input)")
    cost_output_per_1k_tokens: Optional[float] = Field(default=None, description="Coût par 1000 tokens (output)")
    max_output_tokens: Optional[int] = Field(default=None, description="Nombre max de tokens en sortie")
    multimodal: bool = Field(default=False, description="Support multimodal (images)")
    description: Optional[str] = Field(default=None, description="Description du modèle")

class LLMProviderConfig(BaseModel):
    """Configuration d'un provider LLM"""
    provider: LLMProvider
    api_key: Optional[str] = Field(default=None, description="Clé API du provider")
    base_url: Optional[str] = Field(default=None, description="URL de base pour l'API")
    organization: Optional[str] = Field(default=None, description="Organisation (OpenAI)")
    project: Optional[str] = Field(default=None, description="Projet (OpenAI)")
    region: Optional[str] = Field(default=None, description="Région (Gemini)")
    model_prefix: Optional[str] = Field(default=None, description="Préfixe des modèles")
    enabled: bool = Field(default=True, description="Provider activé")
    timeout: int = Field(default=30, description="Timeout en secondes")
    max_retries: int = Field(default=3, description="Nombre max de retry")
    rate_limit_rpm: Optional[int] = Field(default=None, description="Rate limit requests/minute")
    rate_limit_tpm: Optional[int] = Field(default=None, description="Rate limit tokens/minute")

@dataclass
class LLMResponse:
    """Réponse standardisée des LLM"""
    content: str
    provider: LLMProvider
    model: str
    usage: Dict[str, Any]
    finish_reason: str
    response_time: float
    metadata: Dict[str, Any]

class LLMProviderManager:
    """
    Gestionnaire central des providers LLM avec switch dynamique
    Gestion unifiée des différents providers et modèles
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.configs: Dict[LLMProvider, LLMProviderConfig] = {}
        self.active_provider: Optional[LLMProvider] = None
        self.active_model: Optional[str] = None
        self.models_cache: Dict[LLMProvider, List[LLMModel]] = {}
        self.clients: Dict[LLMProvider, httpx.AsyncClient] = {}
        self.last_health_check: Dict[LLMProvider, float] = {}
        
        # Statistiques d'utilisation
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "provider_usage": {provider.value: 0 for provider in LLMProvider},
            "avg_response_time": 0.0
        }
        
        # Initialisation des configurations par défaut
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Initialise les configurations par défaut des providers"""
        
        # OpenAI
        self.configs[LLMProvider.OPENAI] = LLMProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key=getattr(self.settings, 'OPENAI_API_KEY', None),
            base_url="https://api.openai.com/v1",
            organization=getattr(self.settings, 'OPENAI_ORG_ID', None),
            project=getattr(self.settings, 'OPENAI_PROJECT_ID', None),
            timeout=30,
            max_retries=3,
            rate_limit_rpm=3000,
            rate_limit_tpm=90000
        )
        
        # Claude (Anthropic)
        self.configs[LLMProvider.CLAUDE] = LLMProviderConfig(
            provider=LLMProvider.CLAUDE,
            api_key=getattr(self.settings, 'ANTHROPIC_API_KEY', None),
            base_url="https://api.anthropic.com/v1",
            timeout=30,
            max_retries=3,
            rate_limit_rpm=1000,
            rate_limit_tpm=40000
        )
        
        # Gemini (Google)
        self.configs[LLMProvider.GEMINI] = LLMProviderConfig(
            provider=LLMProvider.GEMINI,
            api_key=getattr(self.settings, 'GOOGLE_API_KEY', None),
            base_url="https://generativelanguage.googleapis.com/v1beta",
            region=getattr(self.settings, 'GOOGLE_REGION', 'us-central1'),
            timeout=30,
            max_retries=3,
            rate_limit_rpm=1500,
            rate_limit_tpm=60000
        )
        
        # Ollama (local)
        self.configs[LLMProvider.OLLAMA] = LLMProviderConfig(
            provider=LLMProvider.OLLAMA,
            base_url=getattr(self.settings, 'OLLAMA_BASE_URL', "http://localhost:11434"),
            timeout=60,  # Plus long pour les modèles locaux
            max_retries=2,
            enabled=True  # Toujours activé par défaut
        )
        
        # Définir le provider actif par défaut
        self.active_provider = LLMProvider.OLLAMA  # Défaut local
        if hasattr(self.settings, 'DEFAULT_LLM_PROVIDER'):
            try:
                self.active_provider = LLMProvider(self.settings.DEFAULT_LLM_PROVIDER)
            except ValueError:
                logger.warning("Provider par défaut invalide, utilisation d'Ollama")
    
    async def initialize_clients(self):
        """Initialise les clients HTTP pour chaque provider"""
        for provider, config in self.configs.items():
            if not config.enabled:
                continue
                
            timeout = httpx.Timeout(
                connect=5.0,
                read=config.timeout,
                write=10.0,
                pool=30.0
            )
            
            headers = {"User-Agent": "TechRadarExpress/1.0"}
            
            # Headers spécifiques par provider
            if provider == LLMProvider.OPENAI:
                if config.api_key:
                    headers["Authorization"] = f"Bearer {config.api_key}"
                if config.organization:
                    headers["OpenAI-Organization"] = config.organization
                if config.project:
                    headers["OpenAI-Project"] = config.project
                    
            elif provider == LLMProvider.CLAUDE:
                if config.api_key:
                    headers["x-api-key"] = config.api_key
                headers["anthropic-version"] = "2023-06-01"
                
            elif provider == LLMProvider.GEMINI:
                # Gemini utilise l'API key dans l'URL
                pass
                
            elif provider == LLMProvider.OLLAMA:
                headers["Content-Type"] = "application/json"
            
            self.clients[provider] = httpx.AsyncClient(
                base_url=config.base_url,
                headers=headers,
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            logger.info(
                "Client LLM initialisé",
                provider=provider.value,
                base_url=config.base_url,
                enabled=config.enabled
            )
    
    async def get_available_models(self, provider: LLMProvider) -> List[LLMModel]:
        """Récupère la liste des modèles disponibles pour un provider"""
        
        # Vérifier le cache
        if provider in self.models_cache:
            return self.models_cache[provider]
        
        models = []
        
        try:
            if provider == LLMProvider.OPENAI:
                models = await self._get_openai_models()
            elif provider == LLMProvider.CLAUDE:
                models = await self._get_claude_models()
            elif provider == LLMProvider.GEMINI:
                models = await self._get_gemini_models()
            elif provider == LLMProvider.OLLAMA:
                models = await self._get_ollama_models()
            
            self.models_cache[provider] = models
            logger.info(f"Modèles {provider.value} récupérés", count=len(models))
            
        except Exception as e:
            logger.error(f"Erreur récupération modèles {provider.value}", error=str(e))
            models = self._get_fallback_models(provider)
        
        return models
    
    async def _get_openai_models(self) -> List[LLMModel]:
        """Récupère les modèles OpenAI disponibles"""
        if LLMProvider.OPENAI not in self.clients:
            await self.initialize_clients()
        
        try:
            client = self.clients[LLMProvider.OPENAI]
            response = await client.get("/models")
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            # Modèles principaux avec métadonnées (Juin 2025)
            model_specs = {
                "gpt-4.1": {"context": 1047576, "output": 32768, "cost_in": 0.002, "cost_out": 0.008, "multimodal": True},
                "gpt-4.5": {"context": 200000, "output": 16384, "cost_in": 0.004, "cost_out": 0.012, "multimodal": True},
                "o4-mini": {"context": 200000, "output": 8192, "cost_in": 0.0005, "cost_out": 0.002, "multimodal": True},
                "o3": {"context": 200000, "output": 32768, "cost_in": 0.02, "cost_out": 0.08, "multimodal": False},
                "o3-mini": {"context": 200000, "output": 16384, "cost_in": 0.005, "cost_out": 0.02, "multimodal": False},
                "gpt-4o": {"context": 128000, "output": 4096, "cost_in": 0.0025, "cost_out": 0.01, "multimodal": True},
                "gpt-4o-mini": {"context": 128000, "output": 16384, "cost_in": 0.00015, "cost_out": 0.0006, "multimodal": True},
                "gpt-4-turbo": {"context": 128000, "output": 4096, "cost_in": 0.01, "cost_out": 0.03, "multimodal": True},
                "gpt-4": {"context": 8192, "output": 4096, "cost_in": 0.03, "cost_out": 0.06},
                "gpt-3.5-turbo": {"context": 16385, "output": 4096, "cost_in": 0.0005, "cost_out": 0.0015}
            }
            
            for model_data in data.get("data", []):
                model_id = model_data["id"]
                if any(key in model_id for key in model_specs.keys()):
                    # Trouver la spec la plus proche
                    spec_key = next(key for key in model_specs.keys() if key in model_id)
                    spec = model_specs[spec_key]
                    
                    # Modèles de raisonnement (o3, o1) ne supportent pas les function calls
                    supports_func_calling = not any(keyword in model_id for keyword in ["o3", "o1"])
                    
                    models.append(LLMModel(
                        id=model_id,
                        name=model_id.replace("-", " ").title(),
                        provider=LLMProvider.OPENAI,
                        context_length=spec["context"],
                        max_output_tokens=spec["output"],
                        cost_per_1k_tokens=spec["cost_in"],
                        cost_output_per_1k_tokens=spec["cost_out"],
                        supports_function_calling=supports_func_calling,
                        multimodal=spec.get("multimodal", False),
                        description=f"OpenAI {spec_key} - {spec['context']}k context"
                    ))
            
            return models
        except Exception:
            return self._get_fallback_models(LLMProvider.OPENAI)
    
    async def _get_claude_models(self) -> List[LLMModel]:
        """Récupère les modèles Claude disponibles (Juin 2025)"""
        # Claude n'a pas d'endpoint /models, on utilise une liste statique
        return [
            LLMModel(
                id="claude-opus-4-20250514",
                name="Claude Opus 4",
                provider=LLMProvider.CLAUDE,
                context_length=200000,
                max_output_tokens=32000,
                cost_per_1k_tokens=0.015,
                cost_output_per_1k_tokens=0.075,
                supports_function_calling=True,
                multimodal=True,
                description="Claude Opus 4 - Le plus intelligent (Mars 2025)"
            ),
            LLMModel(
                id="claude-sonnet-4-20250514",
                name="Claude Sonnet 4",
                provider=LLMProvider.CLAUDE,
                context_length=200000,
                max_output_tokens=64000,
                cost_per_1k_tokens=0.003,
                cost_output_per_1k_tokens=0.015,
                supports_function_calling=True,
                multimodal=True,
                description="Claude Sonnet 4 - Balance performance/coût (Mars 2025)"
            ),
            LLMModel(
                id="claude-3-7-sonnet-20250219",
                name="Claude 3.7 Sonnet",
                provider=LLMProvider.CLAUDE,
                context_length=200000,
                max_output_tokens=64000,
                cost_per_1k_tokens=0.003,
                cost_output_per_1k_tokens=0.015,
                supports_function_calling=True,
                multimodal=True,
                description="Claude 3.7 Sonnet - Extended Thinking (Nov 2024)"
            ),
            LLMModel(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                provider=LLMProvider.CLAUDE,
                context_length=200000,
                max_output_tokens=8192,
                cost_per_1k_tokens=0.003,
                cost_output_per_1k_tokens=0.015,
                supports_function_calling=True,
                multimodal=True,
                description="Claude 3.5 Sonnet - Performant et efficace"
            ),
            LLMModel(
                id="claude-3-5-haiku-20241022",
                name="Claude 3.5 Haiku",
                provider=LLMProvider.CLAUDE,
                context_length=200000,
                max_output_tokens=8192,
                cost_per_1k_tokens=0.0008,
                cost_output_per_1k_tokens=0.004,
                supports_function_calling=True,
                multimodal=True,
                description="Claude 3.5 Haiku - Le plus rapide et économique"
            )
        ]
    
    async def _get_gemini_models(self) -> List[LLMModel]:
        """Récupère les modèles Gemini disponibles (Juin 2025)"""
        return [
            LLMModel(
                id="gemini-2.5-pro",
                name="Gemini 2.5 Pro",
                provider=LLMProvider.GEMINI,
                context_length=1048576,
                max_output_tokens=65536,
                cost_per_1k_tokens=0.00125,  # $1.25-2.50/MTok selon contexte
                cost_output_per_1k_tokens=0.01,  # $10/MTok
                supports_function_calling=True,
                multimodal=True,
                description="Gemini 2.5 Pro - Le plus avancé avec thinking (Jan 2025)"
            ),
            LLMModel(
                id="gemini-2.5-flash",
                name="Gemini 2.5 Flash",
                provider=LLMProvider.GEMINI,
                context_length=1048576,
                max_output_tokens=65536,
                cost_per_1k_tokens=0.0003,  # $0.30/MTok
                cost_output_per_1k_tokens=0.0025,  # $2.50/MTok
                supports_function_calling=True,
                multimodal=True,
                description="Gemini 2.5 Flash - Hybrid reasoning, 1M context (Jan 2025)"
            ),
            LLMModel(
                id="gemini-2.5-flash-lite-preview-06-17",
                name="Gemini 2.5 Flash-Lite",
                provider=LLMProvider.GEMINI,
                context_length=1000000,
                max_output_tokens=64000,
                cost_per_1k_tokens=0.0001,  # $0.10/MTok
                cost_output_per_1k_tokens=0.0004,  # $0.40/MTok
                supports_function_calling=True,
                multimodal=True,
                description="Gemini 2.5 Flash-Lite - Cost-effective thinking (Juin 2025)"
            ),
            LLMModel(
                id="gemini-2.0-flash",
                name="Gemini 2.0 Flash",
                provider=LLMProvider.GEMINI,
                context_length=1048576,
                max_output_tokens=8192,
                cost_per_1k_tokens=0.0001,  # $0.10/MTok
                cost_output_per_1k_tokens=0.0004,  # $0.40/MTok
                supports_function_calling=True,
                multimodal=True,
                description="Gemini 2.0 Flash - Agent-ready with tool use (Fév 2025)"
            ),
            LLMModel(
                id="gemini-1.5-flash",
                name="Gemini 1.5 Flash",
                provider=LLMProvider.GEMINI,
                context_length=1000000,
                max_output_tokens=8192,
                cost_per_1k_tokens=0.000075,
                cost_output_per_1k_tokens=0.0003,
                supports_function_calling=True,
                multimodal=True,
                description="Gemini 1.5 Flash - Rapide et économique, 1M tokens context"
            ),
            LLMModel(
                id="gemini-1.5-pro",
                name="Gemini 1.5 Pro",
                provider=LLMProvider.GEMINI,
                context_length=2000000,
                max_output_tokens=8192,
                cost_per_1k_tokens=0.00125,
                cost_output_per_1k_tokens=0.005,
                supports_function_calling=True,
                multimodal=True,
                description="Gemini 1.5 Pro - 2M tokens context (legacy)"
            )
        ]
    
    async def _get_ollama_models(self) -> List[LLMModel]:
        """Récupère les modèles Ollama disponibles"""
        try:
            if LLMProvider.OLLAMA not in self.clients:
                await self.initialize_clients()
            
            client = self.clients[LLMProvider.OLLAMA]
            response = await client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model_data in data.get("models", []):
                model_name = model_data.get("name", "")
                size_gb = model_data.get("size", 0) / (1024**3)  # Convertir en GB
                
                models.append(LLMModel(
                    id=model_name,
                    name=model_name.split(":")[0].title(),
                    provider=LLMProvider.OLLAMA,
                    context_length=self._estimate_context_length(model_name),
                    cost_per_1k_tokens=0.0,  # Gratuit (local)
                    cost_output_per_1k_tokens=0.0,
                    description=f"Modèle local Ollama - {size_gb:.1f}GB"
                ))
            
            return models
            
        except Exception as e:
            logger.error("Erreur récupération modèles Ollama", error=str(e))
            return self._get_fallback_models(LLMProvider.OLLAMA)
    
    def _estimate_context_length(self, model_name: str) -> int:
        """Estime la longueur de contexte selon le nom du modèle (2025)"""
        model_lower = model_name.lower()
        if "llama3.3" in model_lower or "llama4" in model_lower:
            return 131072  # 128K pour les nouveaux modèles
        elif "llama" in model_lower and ("70b" in model_lower or "13b" in model_lower):
            return 8192
        elif "qwen3" in model_lower:
            return 1000000  # 1M tokens pour Qwen3
        elif "qwen2.5" in model_lower or "qwen" in model_lower:
            return 32768
        elif "deepseek-r1" in model_lower:
            return 32768
        elif "olympic-coder" in model_lower:
            return 16384  # Modèle de coding
        elif "mixtral" in model_lower:
            return 32768
        elif "phi" in model_lower:
            return 4096
        elif "gemma2" in model_lower:
            return 8192
        else:
            return 4096  # Défaut conservateur
    
    def _get_fallback_models(self, provider: LLMProvider) -> List[LLMModel]:
        """Retourne des modèles par défaut si l'API n'est pas accessible"""
        fallbacks = {
            LLMProvider.OPENAI: [
                LLMModel(id="gpt-4.1", name="GPT-4.1", provider=provider, context_length=1047576),
                LLMModel(id="gpt-4o-mini", name="GPT-4o Mini", provider=provider, context_length=128000)
            ],
            LLMProvider.CLAUDE: [
                LLMModel(id="claude-sonnet-4-20250514", name="Claude Sonnet 4", provider=provider, context_length=200000),
                LLMModel(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", provider=provider, context_length=200000)
            ],
            LLMProvider.GEMINI: [
                LLMModel(id="gemini-2.5-flash", name="Gemini 2.5 Flash", provider=provider, context_length=1048576),
                LLMModel(id="gemini-1.5-flash", name="Gemini 1.5 Flash", provider=provider, context_length=1000000)
            ],
            LLMProvider.OLLAMA: [
                LLMModel(id="llama3.3:latest", name="Llama 3.3", provider=provider, context_length=131072),
                LLMModel(id="qwen2.5:7b", name="Qwen2.5 7B", provider=provider, context_length=32768)
            ]
        }
        return fallbacks.get(provider, [])
    
    async def set_active_provider(self, provider: LLMProvider, model: str = None) -> bool:
        """Change le provider et modèle actifs"""
        try:
            if provider not in self.configs:
                raise ValueError(f"Provider {provider.value} non configuré")
            
            config = self.configs[provider]
            if not config.enabled:
                raise ValueError(f"Provider {provider.value} désactivé")
            
            # Vérifier que le modèle existe
            if model:
                available_models = await self.get_available_models(provider)
                if not any(m.id == model for m in available_models):
                    raise ValueError(f"Modèle {model} non disponible pour {provider.value}")
                self.active_model = model
            else:
                # Prendre le premier modèle disponible
                available_models = await self.get_available_models(provider)
                if available_models:
                    self.active_model = available_models[0].id
            
            old_provider = self.active_provider
            self.active_provider = provider
            
            logger.info(
                "Provider LLM changé",
                old_provider=old_provider.value if old_provider else None,
                new_provider=provider.value,
                model=self.active_model
            )
            
            return True
            
        except Exception as e:
            logger.error("Erreur changement provider", provider=provider.value, error=str(e))
            return False
    
    async def check_provider_health(self, provider: LLMProvider) -> bool:
        """Vérifie la santé d'un provider"""
        try:
            # Cache des vérifications (5 minutes)
            now = time.time()
            if provider in self.last_health_check:
                if now - self.last_health_check[provider] < 300:
                    return True
            
            if provider not in self.clients:
                await self.initialize_clients()
            
            client = self.clients[provider]
            
            # Test spécifique par provider
            if provider == LLMProvider.OLLAMA:
                response = await client.get("/api/tags", timeout=5.0)
                healthy = response.status_code == 200
            else:
                # Pour les autres providers, on considère qu'ils sont up si configurés
                healthy = self.configs[provider].api_key is not None
            
            if healthy:
                self.last_health_check[provider] = now
            
            return healthy
            
        except Exception as e:
            logger.debug(f"Health check échoué pour {provider.value}", error=str(e))
            return False
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Retourne le statut de tous les providers"""
        status = {
            "active_provider": self.active_provider.value if self.active_provider else None,
            "active_model": self.active_model,
            "providers": {}
        }
        
        for provider in LLMProvider:
            config = self.configs.get(provider)
            if not config:
                continue
                
            health = await self.check_provider_health(provider)
            models = await self.get_available_models(provider)
            
            status["providers"][provider.value] = {
                "enabled": config.enabled,
                "healthy": health,
                "models_count": len(models),
                "api_key_configured": bool(config.api_key),
                "base_url": config.base_url,
                "usage_count": self.stats["provider_usage"].get(provider.value, 0)
            }
        
        return status
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation"""
        return {
            **self.stats,
            "active_provider": self.active_provider.value if self.active_provider else None,
            "active_model": self.active_model,
            "providers_configured": len([c for c in self.configs.values() if c.enabled])
        }
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for client in self.clients.values():
            await client.aclose()
        self.clients.clear()
        logger.info("LLM Provider Manager nettoyé")

# Instance globale
llm_provider_manager = LLMProviderManager()

async def get_llm_provider_manager() -> LLMProviderManager:
    """Dependency injection pour FastAPI"""
    if not llm_provider_manager.clients:
        await llm_provider_manager.initialize_clients()
    return llm_provider_manager 