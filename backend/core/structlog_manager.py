"""
Gestionnaire de logging structuré avec structlog.
Basé sur la documentation officielle structlog.

Ce module configure le logging structuré pour l'application Tech Radar Express.
Il utilise les best practices de structlog pour une intégration avec le logging standard Python.
"""

import sys
import logging
import structlog
from typing import Any, Dict, Optional
from pathlib import Path
from .config_manager import LoggingConfig


def configure_structlog(config: LoggingConfig) -> None:
    """
    Configure structlog selon la documentation officielle.
    
    Args:
        config: Configuration du logging
    """
    # Configuration du logging standard Python d'abord
    _configure_standard_logging(config)
    
    # Processeurs partagés (pour les logs structlog ET standard)
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    
    # Ajout des informations d'appelant si demandé
    if config.include_caller_info:
        shared_processors.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            )
        )
    
    # Processeurs finaux selon l'environnement
    if config.enable_json or config.is_production:
        # Configuration pour la production (JSON)
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        
        # Formatter pour ProcessorFormatter
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(serializer=_safe_json_serializer),
            ],
        )
    else:
        # Configuration pour le développement (console avec couleurs)
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        
        # Formatter coloré pour le développement
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=config.enable_colors),
            ],
        )
    
    # Configuration de structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=config.cache_logger,
    )
    
    # Application du formatter aux handlers existants
    _apply_formatter_to_handlers(formatter)
    
    # Log de confirmation
    logger = structlog.get_logger(__name__)
    logger.info(
        "Structlog configuré avec succès",
        json_mode=config.enable_json or config.is_production,
        colors_enabled=config.enable_colors,
        cache_enabled=config.cache_logger,
        level=config.level
    )


def _configure_standard_logging(config: LoggingConfig) -> None:
    """
    Configure le logging standard Python selon la documentation structlog.
    """
    # Configuration basique selon structlog docs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.level.upper()),
    )
    
    # Configuration du logger root
    root_logger = logging.getLogger()
    
    # Ajout d'un handler pour fichier si spécifié
    if config.log_file:
        _add_file_handler(root_logger, config)


def _add_file_handler(root_logger: logging.Logger, config: LoggingConfig) -> None:
    """
    Ajoute un handler de fichier avec rotation.
    """
    try:
        from logging.handlers import TimedRotatingFileHandler
        
        # Créer le répertoire si nécessaire
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handler avec rotation
        file_handler = TimedRotatingFileHandler(
            config.log_file,
            when="midnight",
            interval=1,
            backupCount=30,  # Garder 30 jours
            encoding="utf-8"
        )
        
        file_handler.setLevel(getattr(logging, config.level.upper()))
        root_logger.addHandler(file_handler)
        
    except Exception as e:
        # Fallback vers handler basique
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, config.level.upper()))
        root_logger.addHandler(file_handler)


def _apply_formatter_to_handlers(formatter) -> None:
    """
    Applique le formatter structlog aux handlers existants.
    """
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def _safe_json_serializer(obj: Any) -> str:
    """
    Sérialiseur JSON sécurisé avec fallback.
    """
    try:
        import orjson
        return orjson.dumps(obj).decode()
    except ImportError:
        import json
        return json.dumps(obj, default=str, ensure_ascii=False)


def setup_logging(config: LoggingConfig) -> None:
    """
    Point d'entrée principal pour configurer le logging.
    
    Args:
        config: Configuration du logging
    """
    if config.enable_structured:
        configure_structlog(config)
    else:
        # Configuration logging standard seulement
        logging.basicConfig(
            level=getattr(logging, config.level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Retourne un logger structlog configuré.
    
    Args:
        name: Nom du logger (optionnel)
        
    Returns:
        Logger structlog configuré
    """
    return structlog.get_logger(name)


# Fonctions de convenance pour différents niveaux
def debug(msg: str, **kwargs) -> None:
    """Log de debug."""
    get_logger().debug(msg, **kwargs)


def info(msg: str, **kwargs) -> None:
    """Log d'information."""
    get_logger().info(msg, **kwargs)


def warning(msg: str, **kwargs) -> None:
    """Log d'avertissement."""
    get_logger().warning(msg, **kwargs)


def error(msg: str, **kwargs) -> None:
    """Log d'erreur."""
    get_logger().error(msg, **kwargs)


def critical(msg: str, **kwargs) -> None:
    """Log critique."""
    get_logger().critical(msg, **kwargs) 