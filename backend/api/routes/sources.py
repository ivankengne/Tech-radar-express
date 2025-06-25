"""
Tech Radar Express - Routes API Sources
Gestion des sources de veille technologique
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import structlog

from ...core.source_manager import (
    get_source_manager, 
    SourceManager, 
    SourceConfig, 
    SourceType, 
    TechAxis,
    CrawlResult
)
from ...core.config_manager import get_settings

# Configuration du logger
logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/sources", tags=["Sources"])

# Modèles Pydantic pour les requêtes/réponses

class SourceCreateRequest(BaseModel):
    """Requête de création d'une source"""
    id: str = Field(..., min_length=1, max_length=50, description="Identifiant unique")
    name: str = Field(..., min_length=1, max_length=100, description="Nom d'affichage")
    url: str = Field(..., description="URL principale")
    source_type: SourceType = Field(..., description="Type de source")
    tech_axes: List[TechAxis] = Field(..., min_items=1, description="Axes technologiques")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    tags: List[str] = Field(default_factory=list, description="Tags")
    priority: int = Field(default=1, ge=1, le=5, description="Priorité (1=max, 5=min)")
    crawl_frequency: int = Field(default=24, ge=1, le=168, description="Fréquence en heures")
    max_depth: int = Field(default=2, ge=1, le=5, description="Profondeur max")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Sessions parallèles")
    chunk_size: int = Field(default=5000, ge=1000, le=10000, description="Taille chunks")

class SourceUpdateRequest(BaseModel):
    """Requête de mise à jour d'une source"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None)
    source_type: Optional[SourceType] = Field(None)
    tech_axes: Optional[List[TechAxis]] = Field(None, min_items=1)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = Field(None)
    priority: Optional[int] = Field(None, ge=1, le=5)
    enabled: Optional[bool] = Field(None)
    crawl_frequency: Optional[int] = Field(None, ge=1, le=168)
    max_depth: Optional[int] = Field(None, ge=1, le=5)
    max_concurrent: Optional[int] = Field(None, ge=1, le=20)
    chunk_size: Optional[int] = Field(None, ge=1000, le=10000)

class SourceResponse(BaseModel):
    """Réponse avec informations d'une source"""
    id: str
    name: str
    url: str
    source_type: SourceType
    tech_axes: List[TechAxis]
    enabled: bool
    crawl_frequency: int
    max_depth: int
    max_concurrent: int
    chunk_size: int
    description: Optional[str]
    tags: List[str]
    priority: int
    created_at: datetime
    last_crawled: Optional[datetime]
    last_success: Optional[datetime]
    crawl_count: int
    error_count: int

class CrawlResultResponse(BaseModel):
    """Réponse avec résultat de crawl"""
    source_id: str
    success: bool
    pages_crawled: int
    chunks_created: int
    execution_time: float
    error_message: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime

class SourceStatsResponse(BaseModel):
    """Réponse avec statistiques des sources"""
    total_sources: int
    active_sources: int
    total_crawls: int
    successful_crawls: int
    failed_crawls: int
    avg_crawl_time: float
    last_crawl_batch: Optional[datetime]
    sources_by_type: Dict[str, int]
    sources_by_axis: Dict[str, int]
    active_crawls: int
    sources_with_errors: int

# Routes principales

@router.get("/", response_model=List[SourceResponse])
async def get_all_sources(
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Récupère toutes les sources configurées"""
    try:
        sources = source_manager.get_all_sources()
        return [SourceResponse(**source.dict()) for source in sources]
        
    except Exception as e:
        logger.error("Erreur récupération sources", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Récupère une source spécifique"""
    try:
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_id} non trouvée")
        
        return SourceResponse(**source.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération source", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.post("/", response_model=SourceResponse)
async def create_source(
    request: SourceCreateRequest,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Crée une nouvelle source"""
    try:
        # Vérification que l'ID n'existe pas déjà
        if source_manager.get_source(request.id):
            raise HTTPException(status_code=400, detail=f"Source {request.id} existe déjà")
        
        # Création de la configuration
        source_config = SourceConfig(**request.dict())
        
        # Ajout de la source
        success = await source_manager.add_source(source_config)
        if not success:
            raise HTTPException(status_code=400, detail="Échec création source")
        
        logger.info("Source créée", source_id=request.id, url=request.url)
        return SourceResponse(**source_config.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur création source", source_id=request.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: str,
    request: SourceUpdateRequest,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Met à jour une source existante"""
    try:
        # Vérification que la source existe
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_id} non trouvée")
        
        # Préparation des mises à jour (exclure les valeurs None)
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="Aucune mise à jour fournie")
        
        # Mise à jour
        success = await source_manager.update_source(source_id, updates)
        if not success:
            raise HTTPException(status_code=400, detail="Échec mise à jour source")
        
        # Récupération de la source mise à jour
        updated_source = source_manager.get_source(source_id)
        
        logger.info("Source mise à jour", source_id=source_id, updates=list(updates.keys()))
        return SourceResponse(**updated_source.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur mise à jour source", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Supprime une source"""
    try:
        # Vérification que la source existe
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_id} non trouvée")
        
        # Suppression
        success = await source_manager.remove_source(source_id)
        if not success:
            raise HTTPException(status_code=400, detail="Échec suppression source")
        
        logger.info("Source supprimée", source_id=source_id)
        return {"message": f"Source {source_id} supprimée avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur suppression source", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Routes de crawling

@router.post("/{source_id}/crawl", response_model=CrawlResultResponse)
async def crawl_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Forcer le crawl même si récent"),
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Lance le crawl d'une source spécifique"""
    try:
        # Vérification que la source existe
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_id} non trouvée")
        
        if not source.enabled:
            raise HTTPException(status_code=400, detail=f"Source {source_id} désactivée")
        
        # Lancement du crawl
        result = await source_manager.crawl_source(source_id, force=force)
        
        logger.info(
            "Crawl lancé",
            source_id=source_id,
            success=result.success,
            pages=result.pages_crawled,
            duration=f"{result.execution_time:.2f}s"
        )
        
        return CrawlResultResponse(**result.__dict__)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erreur crawl source", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.post("/crawl-all")
async def crawl_all_sources(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Forcer le crawl même si récent"),
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Lance le crawl de toutes les sources actives"""
    try:
        # Lancement du crawl batch en arrière-plan
        background_tasks.add_task(source_manager.crawl_all_sources, force)
        
        active_sources = len([s for s in source_manager.get_all_sources() if s.enabled])
        
        logger.info("Crawl batch lancé", active_sources=active_sources)
        
        return {
            "message": f"Crawl batch lancé pour {active_sources} sources actives",
            "active_sources": active_sources,
            "force": force
        }
        
    except Exception as e:
        logger.error("Erreur crawl batch", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/{source_id}/crawl-history", response_model=List[CrawlResultResponse])
async def get_crawl_history(
    source_id: str,
    limit: int = Query(10, ge=1, le=50, description="Nombre de résultats"),
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Récupère l'historique des crawls d'une source"""
    try:
        # Vérification que la source existe
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_id} non trouvée")
        
        # Récupération de l'historique
        history = source_manager.get_crawl_history(source_id, limit)
        
        return [CrawlResultResponse(**result.__dict__) for result in history]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération historique", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Routes de filtrage et recherche

@router.get("/by-type/{source_type}", response_model=List[SourceResponse])
async def get_sources_by_type(
    source_type: SourceType,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Récupère les sources par type"""
    try:
        all_sources = source_manager.get_all_sources()
        filtered_sources = [s for s in all_sources if s.source_type == source_type]
        
        return [SourceResponse(**source.dict()) for source in filtered_sources]
        
    except Exception as e:
        logger.error("Erreur filtrage par type", source_type=source_type, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/by-axis/{tech_axis}", response_model=List[SourceResponse])
async def get_sources_by_axis(
    tech_axis: TechAxis,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Récupère les sources par axe technologique"""
    try:
        sources = source_manager.get_sources_by_axis(tech_axis)
        
        return [SourceResponse(**source.dict()) for source in sources]
        
    except Exception as e:
        logger.error("Erreur filtrage par axe", tech_axis=tech_axis, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Routes de monitoring et statistiques

@router.get("/stats/overview", response_model=SourceStatsResponse)
async def get_sources_statistics(
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Récupère les statistiques des sources"""
    try:
        stats = source_manager.get_statistics()
        
        return SourceStatsResponse(**stats)
        
    except Exception as e:
        logger.error("Erreur récupération statistiques", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/health")
async def get_sources_health():
    """Vérification de la santé du service sources"""
    try:
        source_manager = await get_source_manager()
        
        total_sources = len(source_manager.get_all_sources())
        active_sources = len([s for s in source_manager.get_all_sources() if s.enabled])
        
        return {
            "status": "healthy",
            "total_sources": total_sources,
            "active_sources": active_sources,
            "active_crawls": len(source_manager.active_crawls),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Erreur vérification santé sources", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Routes utilitaires

@router.post("/{source_id}/toggle")
async def toggle_source(
    source_id: str,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Active/désactive une source"""
    try:
        # Vérification que la source existe
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_id} non trouvée")
        
        # Toggle de l'état
        new_enabled = not source.enabled
        success = await source_manager.update_source(source_id, {"enabled": new_enabled})
        
        if not success:
            raise HTTPException(status_code=400, detail="Échec toggle source")
        
        logger.info("Source toggle", source_id=source_id, enabled=new_enabled)
        
        return {
            "source_id": source_id,
            "enabled": new_enabled,
            "message": f"Source {'activée' if new_enabled else 'désactivée'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur toggle source", source_id=source_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/enums/source-types")
async def get_source_types():
    """Récupère la liste des types de sources disponibles"""
    return {
        "source_types": [
            {"value": st.value, "label": st.value.replace("_", " ").title()}
            for st in SourceType
        ]
    }

@router.get("/enums/tech-axes")
async def get_tech_axes():
    """Récupère la liste des axes technologiques disponibles"""
    return {
        "tech_axes": [
            {"value": ta.value, "label": ta.value.replace("_", " ").title()}
            for ta in TechAxis
        ]
    }

@router.post("/analyze-url")
async def analyze_url(
    request: dict,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Analyse intelligente d'une URL pour suggérer la configuration"""
    try:
        url = request.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="URL requise")
        
        # Analyse de l'URL
        analysis = perform_url_analysis(url)
        
        logger.info("Analyse URL effectuée", url=url, confidence=analysis["confidence"])
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur analyse URL", url=request.get("url"), error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

def perform_url_analysis(url: str) -> dict:
    """Effectue l'analyse intelligente d'une URL"""
    try:
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.hostname.lower() if parsed.hostname else ""
        path = parsed.path.lower()
        
        # Mapping des types de sources
        source_type_mapping = {
            "github.com": "github_repo",
            "docs.": "documentation", 
            "doc.": "documentation",
            "blog": "blog",
            "medium.com": "blog",
            "dev.to": "blog",
            "news": "news",
            "techcrunch": "news",
            "ycombinator": "news",
            "rss": "rss_feed",
            "feed": "rss_feed",
            "sitemap": "sitemap"
        }
        
        # Détection du type
        suggested_type = "website"
        confidence = 0.5
        
        for keyword, stype in source_type_mapping.items():
            if keyword in domain or keyword in path:
                suggested_type = stype
                confidence = 0.8
                break
        
        # Mapping des axes technologiques
        tech_axes_mapping = {
            "languages_frameworks": [
                "javascript", "python", "react", "vue", "angular", "node", 
                "django", "spring", "laravel", "rails", "golang", "rust", 
                "kotlin", "swift", "typescript", "php", "java", "c#", "ruby"
            ],
            "tools": [
                "docker", "kubernetes", "jenkins", "github", "gitlab", 
                "vscode", "webpack", "vite", "eslint", "jest", "cypress"
            ],
            "platforms": [
                "aws", "azure", "gcp", "vercel", "netlify", "heroku", 
                "firebase", "supabase", "mongodb", "postgresql", "redis"
            ],
            "techniques": [
                "microservices", "devops", "ci/cd", "testing", "security", 
                "api", "rest", "graphql", "ai", "machine learning", "blockchain"
            ]
        }
        
        # Détection des axes
        suggested_axes = []
        full_url = url.lower()
        
        for axis, keywords in tech_axes_mapping.items():
            if any(keyword in full_url for keyword in keywords):
                suggested_axes.append(axis)
        
        # Axes par défaut selon le type
        if not suggested_axes:
            default_axes = {
                "github_repo": ["languages_frameworks", "tools"],
                "documentation": ["techniques"],
                "blog": ["techniques", "tools"],
                "news": ["techniques", "platforms"],
                "website": ["techniques"]
            }
            suggested_axes = default_axes.get(suggested_type, ["techniques"])
        
        # Génération du nom
        suggested_name = domain.replace("www.", "").split(".")[0]
        suggested_name = suggested_name.capitalize()
        
        if "github.com" in domain:
            path_parts = [p for p in path.split("/") if p]
            if len(path_parts) >= 2:
                suggested_name = f"{path_parts[0]}/{path_parts[1]}"
        
        # Description
        type_labels = {
            "website": "Site Web",
            "github_repo": "Repository GitHub", 
            "documentation": "Documentation",
            "blog": "Blog",
            "news": "Actualités",
            "rss_feed": "Flux RSS",
            "sitemap": "Sitemap"
        }
        
        axes_labels = {
            "languages_frameworks": "Langages & Frameworks",
            "tools": "Outils", 
            "platforms": "Plateformes",
            "techniques": "Techniques"
        }
        
        suggested_description = f"{type_labels.get(suggested_type, 'Source')} spécialisé en {', '.join([axes_labels.get(axis, axis) for axis in suggested_axes])} - {domain}"
        
        # Tags
        suggested_tags = [suggested_type]
        if "github" in domain:
            suggested_tags.extend(["open-source", "git"])
        if "dev.to" in domain:
            suggested_tags.extend(["community", "tutorials"])
        if "medium" in domain:
            suggested_tags.extend(["articles", "blog"])
        
        # Priorité
        suggested_priority = 3
        priority_keywords = {
            1: ["trending", "breaking", "urgent"],
            2: ["important", "major"],
            4: ["minor", "secondary"],
            5: ["archive", "old"]
        }
        
        for priority, keywords in priority_keywords.items():
            if any(keyword in full_url for keyword in keywords):
                suggested_priority = priority
                break
        
        # Avertissements
        warnings = []
        if confidence < 0.7:
            warnings.append("Confiance faible dans la détection automatique")
        if not url.startswith("https://"):
            warnings.append("URL non sécurisée (HTTP)")
        if suggested_type == "github_repo" and "github.com" not in domain:
            warnings.append("Type GitHub détecté mais URL incorrecte")
        
        return {
            "suggested_name": suggested_name,
            "suggested_type": suggested_type,
            "suggested_axes": suggested_axes,
            "suggested_description": suggested_description,
            "suggested_tags": list(set(suggested_tags)),
            "suggested_priority": suggested_priority,
            "confidence": confidence,
            "reasoning": f"Analyse du domaine '{domain}': Type '{suggested_type}' détecté avec {int(confidence*100)}% de confiance. Axes suggérés: {', '.join(suggested_axes)}.",
            "warnings": warnings
        }
        
    except Exception as e:
        logger.error("Erreur analyse URL interne", error=str(e))
        return {
            "suggested_name": "Source",
            "suggested_type": "website", 
            "suggested_axes": ["techniques"],
            "suggested_description": "Source de veille technologique",
            "suggested_tags": ["website"],
            "suggested_priority": 3,
            "confidence": 0.3,
            "reasoning": f"Erreur lors de l'analyse: {str(e)}",
            "warnings": ["Analyse automatique échouée"]
        } 