"""
Tech Radar Express - Source Manager
Orchestrateur pour la gestion des sources et crawls MCP
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
import structlog
from sqlalchemy.orm import Session

from .mcp_client import MCPCrawl4AIClient, CrawlRequest, get_mcp_client
from .config_manager import get_settings
from .scheduler import get_scheduler

# Configuration du logger
logger = structlog.get_logger(__name__)

# Import des enums de monitoring (lazy import pour éviter les imports circulaires)
try:
    from .crawl_monitor import CrawlStatus, ErrorType
except ImportError:
    # Fallback si le module n'est pas encore disponible
    CrawlStatus = None
    ErrorType = None

class SourceType(str, Enum):
    """Types de sources supportées"""
    WEBSITE = "website"
    SITEMAP = "sitemap"
    RSS_FEED = "rss_feed"
    GITHUB_REPO = "github_repo"
    DOCUMENTATION = "documentation"
    BLOG = "blog"
    NEWS = "news"

class SourceStatus(str, Enum):
    """Statuts des sources"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CRAWLING = "crawling"
    ERROR = "error"
    PENDING = "pending"

class TechAxis(str, Enum):
    """Axes technologiques du Tech Radar"""
    LANGUAGES_FRAMEWORKS = "languages_frameworks"
    TOOLS = "tools"
    PLATFORMS = "platforms"
    TECHNIQUES = "techniques"

@dataclass
class CrawlResult:
    """Résultat d'un crawl"""
    source_id: str
    success: bool
    pages_crawled: int = 0
    chunks_created: int = 0
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class SourceConfig(BaseModel):
    """Configuration d'une source"""
    id: str = Field(description="Identifiant unique de la source")
    name: str = Field(description="Nom d'affichage de la source")
    url: str = Field(description="URL principale de la source")
    source_type: SourceType = Field(description="Type de source")
    tech_axes: List[TechAxis] = Field(description="Axes technologiques associés")
    
    # Configuration crawling
    enabled: bool = Field(default=True, description="Source activée")
    crawl_frequency: int = Field(default=24, ge=1, le=168, description="Fréquence de crawl en heures")
    max_depth: int = Field(default=2, ge=1, le=5, description="Profondeur max de crawl")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Sessions parallèles max")
    chunk_size: int = Field(default=5000, ge=1000, le=10000, description="Taille des chunks")
    
    # Métadonnées
    description: Optional[str] = Field(default=None, description="Description de la source")
    tags: List[str] = Field(default_factory=list, description="Tags pour catégorisation")
    priority: int = Field(default=1, ge=1, le=5, description="Priorité de crawl (1=max, 5=min)")
    
    # Historique
    created_at: datetime = Field(default_factory=datetime.now)
    last_crawled: Optional[datetime] = Field(default=None)
    last_success: Optional[datetime] = Field(default=None)
    crawl_count: int = Field(default=0)
    error_count: int = Field(default=0)

    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL doit commencer par http:// ou https://')
        return v

class SourceManager:
    """
    Gestionnaire des sources de veille technologique
    Orchestration des crawls MCP avec planification et monitoring
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.sources: Dict[str, SourceConfig] = {}
        self.crawl_queue: asyncio.Queue = asyncio.Queue()
        self.active_crawls: Set[str] = set()
        self.crawl_results: Dict[str, List[CrawlResult]] = {}
        self.scheduler = None
        self.running = False
        
        # Statistiques
        self.stats = {
            "total_sources": 0,
            "active_sources": 0,
            "total_crawls": 0,
            "successful_crawls": 0,
            "failed_crawls": 0,
            "avg_crawl_time": 0.0,
            "last_crawl_batch": None
        }
    
    async def initialize(self):
        """Initialise le SourceManager"""
        try:
            logger.info("Initialisation SourceManager")
            
            # Récupération du scheduler
            self.scheduler = await get_scheduler()
            
            # Chargement des sources depuis la base de données
            await self.load_sources_from_db()
            
            # Planification des crawls automatiques
            await self.schedule_automatic_crawls()
            
            logger.info(
                "SourceManager initialisé",
                total_sources=len(self.sources),
                active_sources=len([s for s in self.sources.values() if s.enabled])
            )
            
        except Exception as e:
            logger.error("Erreur initialisation SourceManager", error=str(e))
            raise
    
    async def load_sources_from_db(self):
        """Charge les sources depuis la base de données"""
        # TODO: Implémenter le chargement depuis la DB
        # Pour l'instant, on utilise des sources par défaut
        default_sources = [
            SourceConfig(
                id="github-trending",
                name="GitHub Trending",
                url="https://github.com/trending",
                source_type=SourceType.WEBSITE,
                tech_axes=[TechAxis.LANGUAGES_FRAMEWORKS, TechAxis.TOOLS],
                description="Projets GitHub trending",
                tags=["github", "trending", "open-source"],
                priority=1
            ),
            SourceConfig(
                id="hacker-news",
                name="Hacker News",
                url="https://news.ycombinator.com",
                source_type=SourceType.NEWS,
                tech_axes=[TechAxis.TECHNIQUES, TechAxis.PLATFORMS],
                description="Actualités tech Hacker News",
                tags=["news", "tech", "startup"],
                priority=2
            ),
            SourceConfig(
                id="dev-to",
                name="Dev.to",
                url="https://dev.to",
                source_type=SourceType.BLOG,
                tech_axes=[TechAxis.LANGUAGES_FRAMEWORKS, TechAxis.TECHNIQUES],
                description="Communauté de développeurs",
                tags=["blog", "community", "tutorials"],
                priority=2
            )
        ]
        
        for source in default_sources:
            self.sources[source.id] = source
        
        self.stats["total_sources"] = len(self.sources)
        self.stats["active_sources"] = len([s for s in self.sources.values() if s.enabled])
    
    async def add_source(self, source_config: SourceConfig) -> bool:
        """Ajoute une nouvelle source"""
        try:
            # Validation de l'URL avec test de connectivité
            if not await self._validate_source_url(source_config.url):
                raise ValueError(f"URL non accessible: {source_config.url}")
            
            # Ajout de la source
            self.sources[source_config.id] = source_config
            
            # Sauvegarde en base
            await self._save_source_to_db(source_config)
            
            # Planification du premier crawl
            if source_config.enabled:
                await self.schedule_source_crawl(source_config.id)
            
            # Mise à jour des stats
            self.stats["total_sources"] = len(self.sources)
            self.stats["active_sources"] = len([s for s in self.sources.values() if s.enabled])
            
            logger.info("Source ajoutée", source_id=source_config.id, url=source_config.url)
            return True
            
        except Exception as e:
            logger.error("Erreur ajout source", source_id=source_config.id, error=str(e))
            return False
    
    async def update_source(self, source_id: str, updates: Dict[str, Any]) -> bool:
        """Met à jour une source existante"""
        try:
            if source_id not in self.sources:
                raise ValueError(f"Source {source_id} non trouvée")
            
            source = self.sources[source_id]
            
            # Mise à jour des champs
            for field, value in updates.items():
                if hasattr(source, field):
                    setattr(source, field, value)
            
            # Sauvegarde en base
            await self._save_source_to_db(source)
            
            # Re-planification si nécessaire
            if 'crawl_frequency' in updates or 'enabled' in updates:
                await self.reschedule_source_crawl(source_id)
            
            logger.info("Source mise à jour", source_id=source_id, updates=list(updates.keys()))
            return True
            
        except Exception as e:
            logger.error("Erreur mise à jour source", source_id=source_id, error=str(e))
            return False
    
    async def remove_source(self, source_id: str) -> bool:
        """Supprime une source"""
        try:
            if source_id not in self.sources:
                raise ValueError(f"Source {source_id} non trouvée")
            
            # Annulation des crawls planifiés
            await self.unschedule_source_crawl(source_id)
            
            # Suppression de la source
            del self.sources[source_id]
            
            # Suppression en base
            await self._delete_source_from_db(source_id)
            
            # Nettoyage des résultats
            if source_id in self.crawl_results:
                del self.crawl_results[source_id]
            
            # Mise à jour des stats
            self.stats["total_sources"] = len(self.sources)
            self.stats["active_sources"] = len([s for s in self.sources.values() if s.enabled])
            
            logger.info("Source supprimée", source_id=source_id)
            return True
            
        except Exception as e:
            logger.error("Erreur suppression source", source_id=source_id, error=str(e))
            return False
    
    async def crawl_source(self, source_id: str, force: bool = False) -> CrawlResult:
        """Lance le crawl d'une source spécifique"""
        if source_id not in self.sources:
            raise ValueError(f"Source {source_id} non trouvée")
        
        source = self.sources[source_id]
        
        # Vérification si crawl déjà en cours
        if source_id in self.active_crawls and not force:
            raise ValueError(f"Crawl déjà en cours pour {source_id}")
        
        # Vérification de la fréquence de crawl
        if not force and source.last_crawled:
            time_since_last = datetime.now() - source.last_crawled
            min_interval = timedelta(hours=source.crawl_frequency)
            if time_since_last < min_interval:
                raise ValueError(f"Crawl trop récent pour {source_id}")
        
        start_time = time.time()
        self.active_crawls.add(source_id)
        
        # Initialisation du monitoring
        from .crawl_monitor import get_crawl_monitor
        monitor = get_crawl_monitor()
        monitor.start_crawl_monitoring(source_id, source.url)
        
        try:
            logger.info("Début crawl source", source_id=source_id, url=source.url)
            
            # Mise à jour du statut de monitoring
            monitor.update_crawl_progress(source_id, 
                                        status=CrawlStatus.STARTING,
                                        current_step="Préparation de la requête MCP")
            
            # Préparation de la requête MCP
            crawl_request = CrawlRequest(
                url=source.url,
                max_depth=source.max_depth,
                max_concurrent=source.max_concurrent,
                chunk_size=source.chunk_size
            )
            
            # Mise à jour du monitoring
            monitor.update_crawl_progress(source_id,
                                        status=CrawlStatus.CONNECTING,
                                        current_step="Connexion au service MCP")
            
            # Exécution du crawl via MCP
            async with MCPCrawl4AIClient() as mcp_client:
                monitor.update_crawl_progress(source_id,
                                            status=CrawlStatus.CRAWLING,
                                            current_step="Crawl en cours")
                mcp_response = await mcp_client.smart_crawl_url(crawl_request)
            
            execution_time = time.time() - start_time
            
            # Mise à jour du monitoring - traitement
            monitor.update_crawl_progress(source_id,
                                        status=CrawlStatus.PROCESSING,
                                        current_step="Traitement des résultats")
            
            if mcp_response.success:
                # Crawl réussi
                pages_crawled = mcp_response.metadata.get('pages_crawled', 0)
                chunks_created = mcp_response.metadata.get('chunks_created', 0)
                
                # Mise à jour du monitoring avec les résultats
                monitor.update_crawl_progress(source_id,
                                            pages_crawled=pages_crawled,
                                            chunks_created=chunks_created,
                                            metadata=mcp_response.metadata)
                
                result = CrawlResult(
                    source_id=source_id,
                    success=True,
                    pages_crawled=pages_crawled,
                    chunks_created=chunks_created,
                    execution_time=execution_time,
                    metadata=mcp_response.metadata
                )
                
                # Mise à jour de la source
                source.last_crawled = datetime.now()
                source.last_success = datetime.now()
                source.crawl_count += 1
                
                # Mise à jour des stats
                self.stats["successful_crawls"] += 1
                
                logger.info(
                    "Crawl réussi",
                    source_id=source_id,
                    pages=result.pages_crawled,
                    chunks=result.chunks_created,
                    duration=f"{execution_time:.2f}s"
                )
                
                # Finalisation du monitoring - succès
                monitor.complete_crawl(source_id, True, pages_crawled, chunks_created, execution_time, mcp_response.metadata)
                
            else:
                # Crawl échoué
                from .crawl_monitor import ErrorType
                monitor.report_crawl_error(source_id, ErrorType.MCP_ERROR, mcp_response.error, {"response": mcp_response.__dict__})
                
                result = CrawlResult(
                    source_id=source_id,
                    success=False,
                    execution_time=execution_time,
                    error_message=mcp_response.error
                )
                
                # Mise à jour de la source
                source.last_crawled = datetime.now()
                source.error_count += 1
                
                # Mise à jour des stats
                self.stats["failed_crawls"] += 1
                
                logger.error(
                    "Crawl échoué",
                    source_id=source_id,
                    error=mcp_response.error,
                    duration=f"{execution_time:.2f}s"
                )
                
                # Finalisation du monitoring - échec
                monitor.complete_crawl(source_id, False, 0, 0, execution_time, {"error": mcp_response.error})
            
            # Sauvegarde des résultats
            if source_id not in self.crawl_results:
                self.crawl_results[source_id] = []
            self.crawl_results[source_id].append(result)
            
            # Limitation de l'historique (garder les 50 derniers)
            if len(self.crawl_results[source_id]) > 50:
                self.crawl_results[source_id] = self.crawl_results[source_id][-50:]
            
            # Mise à jour des stats globales
            self.stats["total_crawls"] += 1
            self._update_avg_crawl_time(execution_time)
            
            # Sauvegarde de la source mise à jour
            await self._save_source_to_db(source)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Gestion des erreurs avec monitoring
            from .crawl_monitor import ErrorType
            error_type = ErrorType.UNKNOWN_ERROR
            if "timeout" in str(e).lower():
                error_type = ErrorType.TIMEOUT_ERROR
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                error_type = ErrorType.NETWORK_ERROR
            elif "permission" in str(e).lower() or "access" in str(e).lower():
                error_type = ErrorType.PERMISSION_ERROR
            
            monitor.report_crawl_error(source_id, error_type, str(e), {"exception_type": type(e).__name__})
            
            result = CrawlResult(
                source_id=source_id,
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            
            # Mise à jour des erreurs
            source.error_count += 1
            self.stats["failed_crawls"] += 1
            self.stats["total_crawls"] += 1
            
            logger.error("Erreur crawl source", source_id=source_id, error=str(e))
            
            # Finalisation du monitoring - erreur
            monitor.complete_crawl(source_id, False, 0, 0, execution_time, {"error": str(e)})
            
            return result
            
        finally:
            self.active_crawls.discard(source_id)
    
    async def crawl_all_sources(self, force: bool = False) -> Dict[str, CrawlResult]:
        """Lance le crawl de toutes les sources actives"""
        results = {}
        
        active_sources = [s for s in self.sources.values() if s.enabled]
        
        logger.info("Début crawl batch", sources_count=len(active_sources))
        
        # Crawl en parallèle avec limitation de concurrence
        semaphore = asyncio.Semaphore(self.settings.MAX_CONCURRENT_CRAWLS)
        
        async def crawl_with_semaphore(source_id: str):
            async with semaphore:
                try:
                    return await self.crawl_source(source_id, force)
                except Exception as e:
                    logger.error("Erreur crawl batch", source_id=source_id, error=str(e))
                    return CrawlResult(source_id=source_id, success=False, error_message=str(e))
        
        tasks = [crawl_with_semaphore(source.id) for source in active_sources]
        crawl_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compilation des résultats
        for i, result in enumerate(crawl_results):
            source_id = active_sources[i].id
            if isinstance(result, Exception):
                results[source_id] = CrawlResult(
                    source_id=source_id,
                    success=False,
                    error_message=str(result)
                )
            else:
                results[source_id] = result
        
        self.stats["last_crawl_batch"] = datetime.now()
        
        logger.info(
            "Crawl batch terminé",
            total=len(results),
            successful=len([r for r in results.values() if r.success]),
            failed=len([r for r in results.values() if not r.success])
        )
        
        return results
    
    async def schedule_automatic_crawls(self):
        """Planifie les crawls automatiques pour toutes les sources"""
        if not self.scheduler:
            logger.warning("Scheduler non disponible pour planification automatique")
            return
        
        for source in self.sources.values():
            if source.enabled:
                await self.schedule_source_crawl(source.id)
    
    async def schedule_source_crawl(self, source_id: str):
        """Planifie le crawl automatique d'une source"""
        if source_id not in self.sources:
            return
        
        source = self.sources[source_id]
        
        # Job ID unique
        job_id = f"crawl_source_{source_id}"
        
        # Planification avec la fréquence définie
        if self.scheduler:
            self.scheduler.add_job(
                func=self._scheduled_crawl_wrapper,
                trigger="interval",
                hours=source.crawl_frequency,
                args=[source_id],
                id=job_id,
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(
                "Crawl planifié",
                source_id=source_id,
                frequency=f"{source.crawl_frequency}h",
                job_id=job_id
            )
    
    async def unschedule_source_crawl(self, source_id: str):
        """Annule la planification d'une source"""
        job_id = f"crawl_source_{source_id}"
        
        if self.scheduler:
            try:
                self.scheduler.remove_job(job_id)
                logger.info("Planification annulée", source_id=source_id, job_id=job_id)
            except Exception:
                pass  # Job n'existe pas
    
    async def reschedule_source_crawl(self, source_id: str):
        """Re-planifie le crawl d'une source"""
        await self.unschedule_source_crawl(source_id)
        await self.schedule_source_crawl(source_id)
    
    def _scheduled_crawl_wrapper(self, source_id: str):
        """Wrapper pour les crawls planifiés"""
        asyncio.create_task(self.crawl_source(source_id))
    
    async def _validate_source_url(self, url: str) -> bool:
        """Valide qu'une URL est accessible"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(url)
                return response.status_code < 400
        except Exception:
            return False
    
    def _update_avg_crawl_time(self, execution_time: float):
        """Met à jour le temps moyen de crawl"""
        current_avg = self.stats["avg_crawl_time"]
        total_crawls = self.stats["total_crawls"]
        
        if total_crawls == 1:
            self.stats["avg_crawl_time"] = execution_time
        else:
            self.stats["avg_crawl_time"] = (current_avg * (total_crawls - 1) + execution_time) / total_crawls
    
    async def _save_source_to_db(self, source: SourceConfig):
        """Sauvegarde une source en base de données"""
        # TODO: Implémenter la sauvegarde en base
        pass
    
    async def _delete_source_from_db(self, source_id: str):
        """Supprime une source de la base de données"""
        # TODO: Implémenter la suppression en base
        pass
    
    def get_source(self, source_id: str) -> Optional[SourceConfig]:
        """Récupère une source par son ID"""
        return self.sources.get(source_id)
    
    def get_all_sources(self) -> List[SourceConfig]:
        """Récupère toutes les sources"""
        return list(self.sources.values())
    
    def get_sources_by_axis(self, axis: TechAxis) -> List[SourceConfig]:
        """Récupère les sources par axe technologique"""
        return [s for s in self.sources.values() if axis in s.tech_axes]
    
    def get_crawl_history(self, source_id: str, limit: int = 10) -> List[CrawlResult]:
        """Récupère l'historique des crawls d'une source"""
        if source_id not in self.crawl_results:
            return []
        return self.crawl_results[source_id][-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques du SourceManager"""
        return {
            **self.stats,
            "sources_by_type": self._get_sources_by_type_stats(),
            "sources_by_axis": self._get_sources_by_axis_stats(),
            "active_crawls": len(self.active_crawls),
            "sources_with_errors": len([s for s in self.sources.values() if s.error_count > 0])
        }
    
    def _get_sources_by_type_stats(self) -> Dict[str, int]:
        """Statistiques par type de source"""
        stats = {}
        for source in self.sources.values():
            source_type = source.source_type.value
            stats[source_type] = stats.get(source_type, 0) + 1
        return stats
    
    def _get_sources_by_axis_stats(self) -> Dict[str, int]:
        """Statistiques par axe technologique"""
        stats = {}
        for source in self.sources.values():
            for axis in source.tech_axes:
                axis_name = axis.value
                stats[axis_name] = stats.get(axis_name, 0) + 1
        return stats

# Instance globale du SourceManager
_source_manager: Optional[SourceManager] = None

async def get_source_manager() -> SourceManager:
    """Récupère l'instance globale du SourceManager"""
    global _source_manager
    if _source_manager is None:
        _source_manager = SourceManager()
        await _source_manager.initialize()
    return _source_manager 