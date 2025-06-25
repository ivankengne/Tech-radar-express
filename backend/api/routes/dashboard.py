"""
Routes API Dashboard - Tech Radar Express
Endpoints pour les données du dashboard et KPI temps réel
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import random

from core.config_manager import get_settings
from core.structlog_manager import get_logger
from core.mcp_client import MCPCrawl4AIClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Configuration du logging et rate limiting
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Création du router avec préfixe
router = APIRouter(prefix="/api/v1/dashboard")

# Modèles Pydantic pour la réponse
class KPIData(BaseModel):
    """Modèle pour les KPI principaux"""
    total_insights: int = Field(..., description="Nombre total d'insights collectés")
    new_today: int = Field(..., description="Nouveaux insights aujourd'hui")
    trending_themes: int = Field(..., description="Thématiques en tendance")
    active_sources: int = Field(..., description="Sources actives de veille")
    growth_rate: float = Field(..., description="Taux de croissance quotidien (%)")

class TimelineItem(BaseModel):
    """Modèle pour un élément de timeline"""
    id: str = Field(..., description="Identifiant unique")
    title: str = Field(..., description="Titre de l'insight")
    description: str = Field(..., description="Description courte")
    tech_axis: str = Field(..., description="Axe technologique (Frontend, Backend, DevOps, AI/ML)")
    impact_level: str = Field(..., description="Niveau d'impact (High, Medium, Low)")
    source: str = Field(..., description="Source de l'information")
    timestamp: datetime = Field(..., description="Date et heure de collecte")
    url: Optional[str] = Field(None, description="URL vers la source originale")
    tags: List[str] = Field(default_factory=list, description="Tags associés")

class RadarData(BaseModel):
    """Modèle pour les données du graphique radar"""
    theme: str = Field(..., description="Thématique technologique")
    volume: int = Field(..., description="Volume d'insights pour cette thématique")
    growth: float = Field(..., description="Croissance par rapport à la période précédente (%)")

class DashboardData(BaseModel):
    """Modèle complet pour les données du dashboard"""
    kpi: KPIData = Field(..., description="Indicateurs clés de performance")
    timeline: List[TimelineItem] = Field(..., description="Timeline des derniers insights")
    radar: List[RadarData] = Field(..., description="Données pour le graphique radar")
    last_updated: datetime = Field(..., description="Dernière mise à jour des données")
    refresh_interval: int = Field(default=30, description="Intervalle de rafraîchissement en secondes")

class DashboardFilters(BaseModel):
    """Modèle pour les filtres du dashboard"""
    tech_axes: Optional[List[str]] = Field(None, description="Filtrer par axes technologiques")
    period_days: Optional[int] = Field(7, description="Période en jours (défaut: 7)")
    sources: Optional[List[str]] = Field(None, description="Filtrer par sources spécifiques")
    impact_levels: Optional[List[str]] = Field(None, description="Filtrer par niveau d'impact")

async def get_mcp_client() -> MCPCrawl4AIClient:
    """Dependency pour obtenir une instance du client MCP"""
    try:
        config = get_settings()
        return MCPCrawl4AIClient(config)
    except Exception as e:
        logger.error("Erreur lors de l'initialisation du client MCP", error=str(e))
        raise HTTPException(status_code=500, detail="Service MCP indisponible")

def generate_mock_timeline_data(count: int = 10) -> List[TimelineItem]:
    """Génère des données mock pour la timeline en attendant les vraies données MCP"""
    
    tech_axes = ["Frontend", "Backend", "DevOps", "AI/ML", "Security", "Mobile"]
    impact_levels = ["High", "Medium", "Low"]
    sources = ["TechCrunch", "Hacker News", "GitHub Trending", "Stack Overflow", "Reddit", "Medium"]
    
    mock_titles = [
        "Nouvelle release majeure de React 19 avec Server Components",
        "FastAPI 0.105 introduit le support natif WebSocket avancé",
        "Kubernetes 1.29 améliore la sécurité des conteneurs",
        "GPT-4 Turbo devient 3x plus rapide avec les nouvelles optimisations",
        "Vulnerability critique découverte dans OpenSSL 3.0",
        "Flutter 3.16 supporte nativement les animations 120fps",
        "PostgreSQL 16 introduit le support JSON avancé",
        "Docker Desktop optimise l'usage RAM de 40%",
        "Anthropic Claude 3 dépasse GPT-4 sur les benchmarks coding",
        "Nouveau framework CSS Zero-JS gagne en popularité"
    ]
    
    timeline_items = []
    for i in range(count):
        timestamp = datetime.now() - timedelta(hours=random.randint(1, 72))
        
        item = TimelineItem(
            id=f"insight_{i+1:03d}",
            title=random.choice(mock_titles),
            description=f"Détails techniques et impact sur l'écosystème de développement. Analyse approfondie des implications pour les équipes.",
            tech_axis=random.choice(tech_axes),
            impact_level=random.choice(impact_levels),
            source=random.choice(sources),
            timestamp=timestamp,
            url=f"https://example.com/insight/{i+1}",
            tags=[f"tag{j}" for j in range(random.randint(1, 4))]
        )
        timeline_items.append(item)
    
    # Trier par timestamp décroissant (plus récent en premier)
    timeline_items.sort(key=lambda x: x.timestamp, reverse=True)
    return timeline_items

def generate_mock_radar_data() -> List[RadarData]:
    """Génère des données mock pour le graphique radar"""
    
    themes = [
        "JavaScript/TypeScript",
        "Python/FastAPI", 
        "Cloud/DevOps",
        "AI/Machine Learning",
        "Security/Privacy",
        "Mobile Development",
        "Database/Storage",
        "API/Microservices"
    ]
    
    radar_data = []
    for theme in themes:
        radar_data.append(RadarData(
            theme=theme,
            volume=random.randint(15, 85),
            growth=random.uniform(-5.0, 25.0)
        ))
    
    return radar_data

@router.get("/data", response_model=DashboardData)
@limiter.limit("30/minute")
async def get_dashboard_data(
    request: Request,
    period_days: int = Query(7, ge=1, le=90, description="Période en jours pour les données"),
    tech_axes: Optional[str] = Query(None, description="Axes technologiques séparés par virgule"),
    sources: Optional[str] = Query(None, description="Sources séparées par virgule"),
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> DashboardData:
    """
    Endpoint principal pour récupérer toutes les données du dashboard temps réel
    
    Retourne:
    - KPI principaux (insights totaux, nouveautés, tendances)
    - Timeline des derniers insights
    - Données radar par thématique
    - Metadata de fraîcheur des données
    """
    
    logger.info("Récupération des données dashboard", 
                period_days=period_days,
                tech_axes=tech_axes,
                sources=sources)
    
    try:
        # Préparation des filtres
        filter_tech_axes = tech_axes.split(",") if tech_axes else None
        filter_sources = sources.split(",") if sources else None
        
        # TODO: Récupérer les vraies données via MCP
        # Pour l'instant, on utilise des données mock
        
        # Récupération des données KPI
        kpi_data = KPIData(
            total_insights=random.randint(1200, 1500),
            new_today=random.randint(15, 45),
            trending_themes=random.randint(5, 12),
            active_sources=random.randint(8, 15),
            growth_rate=random.uniform(2.5, 8.3)
        )
        
        # Récupération des données timeline
        timeline_data = generate_mock_timeline_data(count=20)
        
        # Application des filtres si spécifiés
        if filter_tech_axes:
            timeline_data = [item for item in timeline_data if item.tech_axis in filter_tech_axes]
        
        if filter_sources:
            timeline_data = [item for item in timeline_data if item.source in filter_sources]
        
        # Limitation au nombre d'éléments timeline pour la performance
        timeline_data = timeline_data[:15]
        
        # Récupération des données radar
        radar_data = generate_mock_radar_data()
        
        # Construction de la réponse complète
        dashboard_response = DashboardData(
            kpi=kpi_data,
            timeline=timeline_data,
            radar=radar_data,
            last_updated=datetime.now(),
            refresh_interval=30
        )
        
        logger.info("Données dashboard récupérées avec succès",
                    kpi_total=kpi_data.total_insights,
                    timeline_count=len(timeline_data),
                    radar_themes=len(radar_data))
        
        return dashboard_response
        
    except Exception as e:
        logger.error("Erreur lors de la récupération des données dashboard", error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Impossible de récupérer les données dashboard: {str(e)}"
        )

@router.get("/kpi", response_model=KPIData)
@limiter.limit("60/minute")
async def get_kpi_only(
    request: Request,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> KPIData:
    """
    Endpoint optimisé pour récupérer uniquement les KPI principaux
    Utilisé pour les mises à jour fréquentes des cartes KPI
    """
    
    logger.info("Récupération KPI uniquement")
    
    try:
        # TODO: Intégrer avec les vraies données MCP
        # mcp_sources = await mcp_client.get_available_sources()
        # insights_data = await mcp_client.perform_rag_query("recent insights")
        
        kpi_data = KPIData(
            total_insights=random.randint(1200, 1500),
            new_today=random.randint(15, 45),
            trending_themes=random.randint(5, 12),
            active_sources=random.randint(8, 15),
            growth_rate=random.uniform(2.5, 8.3)
        )
        
        logger.info("KPI récupérés avec succès", total_insights=kpi_data.total_insights)
        return kpi_data
        
    except Exception as e:
        logger.error("Erreur lors de la récupération des KPI", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de récupérer les KPI: {str(e)}"
        )

@router.get("/timeline", response_model=List[TimelineItem])
@limiter.limit("20/minute") 
async def get_timeline_only(
    request: Request,
    limit: int = Query(10, ge=1, le=50, description="Nombre maximum d'éléments"),
    tech_axis: Optional[str] = Query(None, description="Filtrer par axe technologique"),
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> List[TimelineItem]:
    """
    Endpoint pour récupérer uniquement la timeline
    Permet un rafraîchissement ciblé de la timeline
    """
    
    logger.info("Récupération timeline uniquement", limit=limit, tech_axis=tech_axis)
    
    try:
        # TODO: Intégrer avec MCP pour les vraies données
        timeline_data = generate_mock_timeline_data(count=limit*2)
        
        # Application du filtre tech_axis
        if tech_axis:
            timeline_data = [item for item in timeline_data if item.tech_axis == tech_axis]
        
        # Limitation au nombre demandé
        timeline_data = timeline_data[:limit]
        
        logger.info("Timeline récupérée avec succès", count=len(timeline_data))
        return timeline_data
        
    except Exception as e:
        logger.error("Erreur lors de la récupération de la timeline", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de récupérer la timeline: {str(e)}"
        )

@router.get("/radar", response_model=List[RadarData])
@limiter.limit("10/minute")
async def get_radar_only(
    request: Request,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> List[RadarData]:
    """
    Endpoint pour récupérer uniquement les données du graphique radar
    Optimisé pour les mises à jour du RadarChart
    """
    
    logger.info("Récupération données radar uniquement")
    
    try:
        # TODO: Intégrer avec MCP pour calculer les volumes réels par thématique
        radar_data = generate_mock_radar_data()
        
        logger.info("Données radar récupérées avec succès", themes_count=len(radar_data))
        return radar_data
        
    except Exception as e:
        logger.error("Erreur lors de la récupération des données radar", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de récupérer les données radar: {str(e)}"
        )

@router.get("/health")
async def dashboard_health_check(request: Request) -> Dict[str, Any]:
    """Vérification de santé spécifique aux services dashboard"""
    
    health_status = {
        "service": "dashboard",
        "status": "healthy",
        "timestamp": datetime.now(),
        "components": {
            "kpi_generator": "healthy",
            "timeline_generator": "healthy", 
            "radar_calculator": "healthy",
            "mcp_integration": "pending"  # TODO: vérifier vraie connexion MCP
        }
    }
    
    return health_status 