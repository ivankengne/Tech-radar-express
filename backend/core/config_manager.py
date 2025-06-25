"""
Tech Radar Express - Configuration Manager
Gestionnaire de configuration centralisé avec Pydantic Settings
"""

import os
from typing import Optional, List, Dict, Any
from functools import lru_cache
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import structlog
import sys

logger = structlog.get_logger(__name__)

class LangfuseConfig(BaseModel):
    """Configuration spécifique pour Langfuse"""
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: str = "http://localhost:8007"
    debug: bool = False
    enabled: bool = True
    threads: int = 1
    flush_at: int = 15
    flush_interval: float = 0.5
    max_retries: int = 3
    timeout: float = 10.0
    sdk_integration: str = "python-fastapi"
    
    @property
    def is_configured(self) -> bool:
        """Vérifie si la configuration est complète"""
        return bool(self.enabled and self.public_key and self.secret_key)

class LoggingConfig(BaseModel):
    """Configuration pour le logging structuré avec structlog."""
    
    # Configuration générale
    level: str = Field(default="INFO", description="Niveau de log global")
    enable_structured: bool = Field(default=True, description="Activer le logging structuré")
    enable_json: bool = Field(default=False, description="Activer la sortie JSON en production")
    enable_colors: bool = Field(default=True, description="Activer les couleurs en développement")
    
    # Fichiers de logs
    log_file: Optional[str] = Field(default=None, description="Fichier de log optionnel")
    log_rotation: str = Field(default="1 day", description="Rotation des logs")
    log_retention: str = Field(default="30 days", description="Rétention des logs")
    
    # Performance
    cache_logger: bool = Field(default=True, description="Cache des loggers pour performance")
    async_logging: bool = Field(default=False, description="Logging asynchrone")
    
    # Contexte
    include_caller_info: bool = Field(default=True, description="Inclure infos appelant")
    include_process_info: bool = Field(default=True, description="Inclure infos processus")

    @property
    def is_production(self) -> bool:
        """Détecte si on est en production (pour activer JSON)."""
        return not sys.stderr.isatty()

class Settings(BaseSettings):
    """Configuration centralisée de l'application Tech Radar Express"""
    
    # ===================================
    # Configuration Environnement
    # ===================================
    ENVIRONMENT: str = Field(default="development", description="Environnement d'exécution")
    DEBUG: bool = Field(default=False, description="Mode debug")
    
    # ===================================
    # Configuration FastAPI
    # ===================================
    API_HOST: str = Field(default="0.0.0.0", description="Host API")
    API_PORT: int = Field(default=8000, ge=1000, le=65535, description="Port API")
    API_RELOAD: bool = Field(default=True, description="Auto-reload FastAPI")
    API_WORKERS: int = Field(default=1, ge=1, le=10, description="Nombre de workers")
    API_ROOT_PATH: str = Field(default="", description="Root path pour proxy")
    
    # ===================================
    # Configuration Sécurité
    # ===================================
    SECRET_KEY: str = Field(..., min_length=32, description="Clé secrète pour JWT")
    ALGORITHM: str = Field(default="HS256", description="Algorithme JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440, description="Expiration token")
    ENCRYPT_KEY: str = Field(..., min_length=32, description="Clé chiffrement")
    
    # ===================================
    # Configuration MCP crawl4ai-rag
    # ===================================
    MCP_SERVER_HOST: str = Field(default="localhost", description="Host serveur MCP")
    MCP_SERVER_PORT: int = Field(default=8051, ge=1000, le=65535, description="Port serveur MCP")
    MCP_TRANSPORT: str = Field(default="sse", description="Type transport MCP")
    MCP_MAX_RETRIES: int = Field(default=3, ge=1, le=10, description="Nombre max de retry")
    
    # Timeouts MCP
    MCP_TIMEOUT_CONNECT: float = Field(default=10.0, ge=1.0, le=60.0, description="Timeout connexion")
    MCP_TIMEOUT_READ: float = Field(default=30.0, ge=5.0, le=300.0, description="Timeout lecture")
    MCP_TIMEOUT_WRITE: float = Field(default=30.0, ge=5.0, le=300.0, description="Timeout écriture")
    MCP_TIMEOUT_POOL: float = Field(default=10.0, ge=1.0, le=60.0, description="Timeout pool")
    
    # Configuration MCP Crawl4AI
    USE_CONTEXTUAL_EMBEDDINGS: bool = Field(default=True, description="Utiliser embeddings contextuels")
    USE_HYBRID_SEARCH: bool = Field(default=True, description="Recherche hybride")
    USE_AGGRESSIVE_CONTENT_EXTRACTION: bool = Field(default=True, description="Extraction contenu agressive")
    CHUNK_SIZE: int = Field(default=5000, ge=1000, le=10000, description="Taille des chunks")
    CHUNK_OVERLAP: int = Field(default=200, ge=50, le=500, description="Overlap des chunks")
    
    # ===================================
    # Configuration Supabase (Local Docker)
    # ===================================
    SUPABASE_URL: str = Field(default="http://localhost:8005", description="URL Supabase local")
    SUPABASE_ANON_KEY: str = Field(..., description="Clé anonyme Supabase")
    SUPABASE_SERVICE_KEY: str = Field(..., description="Clé service Supabase")
    SUPABASE_JWT_SECRET: str = Field(..., description="Secret JWT Supabase")
    
    # ===================================
    # Configuration Neo4j (Local Docker)
    # ===================================
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="URI Neo4j local")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Username Neo4j")
    NEO4J_PASSWORD: str = Field(default="your_password", description="Password Neo4j")
    NEO4J_DATABASE: str = Field(default="neo4j", description="Database Neo4j")
    
    # ===================================
    # Configuration Redis/Valkey (Local Docker)
    # ===================================
    REDIS_URL: str = Field(default="redis://localhost:6379", description="URL Redis/Valkey local")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Password Redis/Valkey")
    REDIS_DB: int = Field(default=0, ge=0, le=15, description="Database Redis/Valkey")
    REDIS_POOL_SIZE: int = Field(default=20, ge=5, le=100, description="Taille pool Redis/Valkey")
    

    
    # ===================================
    # Configuration LLM Providers
    # ===================================
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="Clé API OpenAI")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo", description="Modèle OpenAI par défaut")
    OPENAI_MAX_TOKENS: int = Field(default=4000, ge=100, le=32000, description="Max tokens OpenAI")
    
    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Clé API Anthropic")
    ANTHROPIC_MODEL: str = Field(default="claude-3-sonnet-20240229", description="Modèle Anthropic par défaut")
    ANTHROPIC_MAX_TOKENS: int = Field(default=4000, ge=100, le=32000, description="Max tokens Anthropic")
    
    # Google
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Clé API Google")
    GOOGLE_MODEL: str = Field(default="gemini-pro", description="Modèle Google par défaut")
    GOOGLE_MAX_TOKENS: int = Field(default=4000, ge=100, le=32000, description="Max tokens Google")
    
    # Ollama (Local Docker)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:8004", description="URL base Ollama local (via Caddy)")
    OLLAMA_MODEL: str = Field(default="qwen2.5:7b-instruct-q4_K_M", description="Modèle Ollama par défaut")
    OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text", description="Modèle embeddings Ollama")
    OLLAMA_MAX_TOKENS: int = Field(default=4000, ge=100, le=32000, description="Max tokens Ollama")
    OLLAMA_CONTEXT_LENGTH: int = Field(default=8192, description="Longueur contexte Ollama")
    
    # ===================================
    # Configuration Monitoring Langfuse (Local Docker)
    # ===================================
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None, description="Clé publique Langfuse")
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None, description="Clé secrète Langfuse")
    LANGFUSE_HOST: str = Field(default="http://localhost:8007", description="Host Langfuse local")
    LANGFUSE_DEBUG: bool = Field(default=False, description="Mode debug Langfuse")
    LANGFUSE_ENABLED: bool = Field(default=True, description="Activer Langfuse monitoring")
    LANGFUSE_THREADS: int = Field(default=1, ge=1, le=10, description="Nombre threads Langfuse")
    LANGFUSE_FLUSH_AT: int = Field(default=15, ge=1, le=100, description="Flush après N événements")
    LANGFUSE_FLUSH_INTERVAL: float = Field(default=0.5, ge=0.1, le=10.0, description="Interval flush (secondes)")
    LANGFUSE_MAX_RETRIES: int = Field(default=3, ge=0, le=10, description="Max retry Langfuse")
    LANGFUSE_TIMEOUT: float = Field(default=10.0, ge=1.0, le=60.0, description="Timeout Langfuse")
    LANGFUSE_SDK_INTEGRATION: str = Field(default="python-fastapi", description="Type intégration SDK")
    
    # ===================================
    # Configuration Logging
    # ===================================
    LOG_LEVEL: str = Field(default="INFO", description="Niveau de log")
    LOG_FORMAT: str = Field(default="json", description="Format de log")
    LOG_FILE: Optional[str] = Field(default=None, description="Fichier de log")
    
    # ===================================
    # Configuration CORS
    # ===================================
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Origins CORS autorisés"
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Méthodes HTTP autorisées"
    )
    CORS_HEADERS: List[str] = Field(
        default=["*"],
        description="Headers autorisés"
    )
    
    # ===================================
    # Configuration Rate Limiting
    # ===================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Activer rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1, le=10000, description="Nombre de requêtes")
    RATE_LIMIT_WINDOW: int = Field(default=60, ge=1, le=3600, description="Fenêtre en secondes")
    
    # ===================================
    # Configuration Cache
    # ===================================
    CACHE_ENABLED: bool = Field(default=True, description="Activer le cache")
    CACHE_TTL: int = Field(default=300, ge=60, le=86400, description="TTL cache en secondes")
    CACHE_MAX_SIZE: int = Field(default=1000, ge=100, le=10000, description="Taille max cache")
    
    # ===================================
    # Configuration WebSocket
    # ===================================
    WEBSOCKET_ENABLED: bool = Field(default=True, description="Activer WebSocket")
    WEBSOCKET_HEARTBEAT: int = Field(default=30, ge=10, le=300, description="Heartbeat WebSocket")
    WEBSOCKET_MAX_CONNECTIONS: int = Field(default=100, ge=10, le=1000, description="Max connexions WebSocket")
    
    # ===================================
    # Configuration Scheduler
    # ===================================
    SCHEDULER_ENABLED: bool = Field(default=True, description="Activer le scheduler")
    SCHEDULER_TIMEZONE: str = Field(default="Europe/Paris", description="Timezone du scheduler")
    CRAWL_SCHEDULE: str = Field(default="0 */6 * * *", description="Cron expression crawl")
    CLEANUP_SCHEDULE: str = Field(default="0 2 * * *", description="Cron expression cleanup")
    SUMMARY_SCHEDULE: str = Field(default="0 8 * * *", description="Cron expression résumés")
    
    # ===================================
    # Validators
    # ===================================
    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('ENVIRONMENT must be one of: development, staging, production')
        return v
    
    @field_validator('MCP_TRANSPORT')
    @classmethod
    def validate_mcp_transport(cls, v):
        if v not in ['sse', 'stdio', 'websocket']:
            raise ValueError('MCP_TRANSPORT must be one of: sse, stdio, websocket')
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        if v not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError('LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL')
        return v
    
    @field_validator('LOG_FORMAT')
    @classmethod
    def validate_log_format(cls, v):
        if v not in ['json', 'text']:
            raise ValueError('LOG_FORMAT must be one of: json, text')
        return v
    
    @field_validator('SCHEDULER_TIMEZONE')
    @classmethod
    def validate_timezone(cls, v):
        try:
            import pytz
            pytz.timezone(v)
        except Exception:
            raise ValueError(f'Invalid timezone: {v}')
        return v
    
    # ===================================
    # Propriétés calculées
    # ===================================
    @property
    def is_production(self) -> bool:
        """Vérifie si on est en production"""
        return self.ENVIRONMENT == 'production'
    
    @property
    def is_development(self) -> bool:
        """Vérifie si on est en développement"""
        return self.ENVIRONMENT == 'development'
    
    @property
    def database_url(self) -> str:
        """URL complète de la base de données"""
        return self.SUPABASE_URL
    
    @property
    def mcp_server_url(self) -> str:
        """URL complète du serveur MCP"""
        return f"http://{self.MCP_SERVER_HOST}:{self.MCP_SERVER_PORT}"
    
    @property
    def available_llm_providers(self) -> List[str]:
        """Liste des providers LLM configurés"""
        providers = []
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        if self.GOOGLE_API_KEY:
            providers.append("google")
        if self.OLLAMA_BASE_URL:
            providers.append("ollama")
        return providers
    
    @property
    def monitoring_enabled(self) -> bool:
        """Vérifie si le monitoring est activé"""
        return (
            self.LANGFUSE_ENABLED
            and self.LANGFUSE_PUBLIC_KEY is not None 
            and self.LANGFUSE_SECRET_KEY is not None
        )
    
    @property
    def langfuse(self) -> 'LangfuseConfig':
        """Configuration Langfuse"""
        return LangfuseConfig(
            public_key=self.LANGFUSE_PUBLIC_KEY,
            secret_key=self.LANGFUSE_SECRET_KEY,
            host=self.LANGFUSE_HOST,
            debug=self.LANGFUSE_DEBUG,
            enabled=self.LANGFUSE_ENABLED,
            threads=self.LANGFUSE_THREADS,
            flush_at=self.LANGFUSE_FLUSH_AT,
            flush_interval=self.LANGFUSE_FLUSH_INTERVAL,
            max_retries=self.LANGFUSE_MAX_RETRIES,
            timeout=self.LANGFUSE_TIMEOUT,
            sdk_integration=self.LANGFUSE_SDK_INTEGRATION
        )
    
    @property
    def logging(self) -> 'LoggingConfig':
        """Configuration Logging structuré"""
        return LoggingConfig(
            level=self.LOG_LEVEL,
            enable_structured=True,
            enable_json=(self.LOG_FORMAT == "json" or not sys.stderr.isatty()),
            enable_colors=(self.LOG_FORMAT != "json" and sys.stderr.isatty()),
            log_file=self.LOG_FILE,
            cache_logger=True,
            async_logging=False,
            include_caller_info=self.DEBUG,
            include_process_info=True
        )
    
    # ===================================
    # Méthodes utilitaires
    # ===================================
    def get_llm_config(self, provider: str) -> Dict[str, Any]:
        """Retourne la configuration pour un provider LLM"""
        configs = {
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "max_tokens": self.OPENAI_MAX_TOKENS,
                "base_url": "https://api.openai.com/v1"
            },
            "anthropic": {
                "api_key": self.ANTHROPIC_API_KEY,
                "model": self.ANTHROPIC_MODEL,
                "max_tokens": self.ANTHROPIC_MAX_TOKENS,
                "base_url": "https://api.anthropic.com/v1"
            },
            "google": {
                "api_key": self.GOOGLE_API_KEY,
                "model": self.GOOGLE_MODEL,
                "max_tokens": self.GOOGLE_MAX_TOKENS,
                "base_url": "https://generativelanguage.googleapis.com/v1"
            },
            "ollama": {
                "model": self.OLLAMA_MODEL,
                "max_tokens": self.OLLAMA_MAX_TOKENS,
                "base_url": self.OLLAMA_BASE_URL
            }
        }
        return configs.get(provider, {})
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """Retourne la configuration MCP complète"""
        return {
            "server_host": self.MCP_SERVER_HOST,
            "server_port": self.MCP_SERVER_PORT,
            "transport": self.MCP_TRANSPORT,
            "max_retries": self.MCP_MAX_RETRIES,
            "timeouts": {
                "connect": self.MCP_TIMEOUT_CONNECT,
                "read": self.MCP_TIMEOUT_READ,
                "write": self.MCP_TIMEOUT_WRITE,
                "pool": self.MCP_TIMEOUT_POOL
            },
            "crawl_config": {
                "use_contextual_embeddings": self.USE_CONTEXTUAL_EMBEDDINGS,
                "use_hybrid_search": self.USE_HYBRID_SEARCH,
                "use_aggressive_content_extraction": self.USE_AGGRESSIVE_CONTENT_EXTRACTION,
                "chunk_size": self.CHUNK_SIZE,
                "chunk_overlap": self.CHUNK_OVERLAP
            }
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Retourne la configuration des bases de données"""
        return {
            "supabase": {
                "url": self.SUPABASE_URL,
                "key": self.SUPABASE_KEY,
                "jwt_secret": self.SUPABASE_JWT_SECRET
            },
            "neo4j": {
                "uri": self.NEO4J_URI,
                "username": self.NEO4J_USERNAME,
                "password": self.NEO4J_PASSWORD,
                "database": self.NEO4J_DATABASE
            },
            "redis": {
                "url": self.REDIS_URL,
                "password": self.REDIS_PASSWORD,
                "db": self.REDIS_DB,
                "pool_size": self.REDIS_POOL_SIZE
            }
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True

# Instance globale des settings
_settings: Optional[Settings] = None

@lru_cache()
def get_settings() -> Settings:
    """
    Retourne l'instance globale des settings avec cache
    Utilise @lru_cache pour éviter de recharger la config à chaque appel
    """
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
            logger.info("Configuration chargée avec succès", environment=_settings.ENVIRONMENT)
        except Exception as e:
            logger.error("Erreur lors du chargement de la configuration", error=str(e))
            raise
    return _settings

def reload_settings() -> Settings:
    """
    Recharge la configuration (utile pour les tests)
    """
    global _settings
    _settings = None
    get_settings.cache_clear()
    return get_settings()

# Alias pour la compatibilité avec le code existant
ConfigManager = Settings

def validate_settings(settings: Settings) -> bool:
    """
    Valide la configuration et retourne True si tout est OK
    """
    try:
        # Validation des clés secrètes
        if len(settings.SECRET_KEY) < 32:
            logger.error("SECRET_KEY trop courte (minimum 32 caractères)")
            return False
        
        if len(settings.ENCRYPT_KEY) < 32:
            logger.error("ENCRYPT_KEY trop courte (minimum 32 caractères)")
            return False
        
        # Validation des URLs
        required_urls = [
            ("SUPABASE_URL", settings.SUPABASE_URL),
            ("NEO4J_URI", settings.NEO4J_URI),
            ("REDIS_URL", settings.REDIS_URL)
        ]
        
        for name, url in required_urls:
            if not url or not url.startswith(('http://', 'https://', 'bolt://', 'redis://')):
                logger.error(f"URL invalide pour {name}: {url}")
                return False
        
        # Validation des providers LLM
        if not settings.available_llm_providers:
            logger.warning("Aucun provider LLM configuré")
        
        logger.info("Validation de la configuration réussie")
        return True
        
    except Exception as e:
        logger.error("Erreur lors de la validation de la configuration", error=str(e))
        return False