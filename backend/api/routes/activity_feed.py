"""
Tech Radar Express - API Activity Feed
Routes REST pour le flux d'activité temps réel
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

from core.activity_feed_manager import (
    get_activity_feed_manager, 
    ActivityType, 
    ActivityPriority,
    ActivitySource,
    ActivityItem,
    ActivityStats
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/activity-feed", tags=["Activity Feed"])

@router.get("/activities")
async def get_activities(
    limit: int = Query(50, ge=1, le=200, description="Nombre d'activités à récupérer"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    types: Optional[str] = Query(None, description="Types d'activités filtrés (séparés par virgule)"),
    priorities: Optional[str] = Query(None, description="Priorités filtrées (séparées par virgule)"),
    sources: Optional[str] = Query(None, description="Sources filtrées (séparées par virgule)"),
    tech_areas: Optional[str] = Query(None, description="Aires technologiques filtrées (séparées par virgule)"),
    since_hours: Optional[int] = Query(None, ge=1, le=168, description="Activités depuis X heures"),
    include_system: bool = Query(True, description="Inclure les activités système"),
    user_id: Optional[str] = Query(None, description="Filtrer par utilisateur")
) -> Dict[str, Any]:
    """
    Récupère la liste des activités avec filtres et pagination
    """
    try:
        manager = await get_activity_feed_manager()
        
        # Conversion des filtres
        activity_types = []
        if types:
            try:
                activity_types = [ActivityType(t.strip()) for t in types.split(',')]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Type d'activité invalide: {e}")
        
        activity_priorities = []
        if priorities:
            try:
                activity_priorities = [ActivityPriority(p.strip()) for p in priorities.split(',')]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Priorité invalide: {e}")
        
        activity_sources = []
        if sources:
            try:
                activity_sources = [ActivitySource(s.strip()) for s in sources.split(',')]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Source invalide: {e}")
        
        tech_areas_list = []
        if tech_areas:
            tech_areas_list = [area.strip() for area in tech_areas.split(',')]
        
        since_date = None
        if since_hours:
            since_date = datetime.now() - timedelta(hours=since_hours)
        
        # Récupération des activités
        activities = await manager.get_activities(
            limit=limit,
            offset=offset,
            activity_types=activity_types if activity_types else None,
            priorities=activity_priorities if activity_priorities else None,
            sources=activity_sources if activity_sources else None,
            user_id=user_id,
            tech_areas=tech_areas_list if tech_areas_list else None,
            since=since_date,
            include_system=include_system
        )
        
        # Formatage de la réponse
        activities_data = []
        for activity in activities:
            activities_data.append({
                "id": activity.id,
                "type": activity.type.value,
                "priority": activity.priority.value,
                "source": activity.source.value,
                "title": activity.title,
                "description": activity.description,
                "details": activity.details,
                "timestamp": activity.timestamp.isoformat(),
                "user_id": activity.user_id,
                "source_name": activity.source_name,
                "url": activity.url,
                "tags": activity.tags,
                "tech_areas": activity.tech_areas,
                "impact_score": activity.impact_score,
                "read": activity.read,
                "bookmarked": activity.bookmarked
            })
        
        return {
            "activities": activities_data,
            "total": len(activities_data),
            "limit": limit,
            "offset": offset,
            "has_more": len(activities_data) == limit
        }
        
    except Exception as e:
        logger.error("Erreur récupération activités", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/activities/{activity_id}")
async def get_activity_by_id(activity_id: str) -> Dict[str, Any]:
    """
    Récupère une activité spécifique par son ID
    """
    try:
        manager = await get_activity_feed_manager()
        
        activity = await manager.get_activity_by_id(activity_id)
        if not activity:
            raise HTTPException(status_code=404, detail="Activité non trouvée")
        
        return {
            "id": activity.id,
            "type": activity.type.value,
            "priority": activity.priority.value,
            "source": activity.source.value,
            "title": activity.title,
            "description": activity.description,
            "details": activity.details,
            "timestamp": activity.timestamp.isoformat(),
            "user_id": activity.user_id,
            "source_name": activity.source_name,
            "url": activity.url,
            "tags": activity.tags,
            "tech_areas": activity.tech_areas,
            "impact_score": activity.impact_score,
            "read": activity.read,
            "bookmarked": activity.bookmarked
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération activité", activity_id=activity_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/activities/{activity_id}/read")
async def mark_activity_read(
    activity_id: str,
    user_id: str = Query("default", description="ID utilisateur")
) -> Dict[str, Any]:
    """
    Marque une activité comme lue
    """
    try:
        manager = await get_activity_feed_manager()
        
        success = await manager.mark_activity_read(activity_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Activité non trouvée")
        
        return {"success": True, "message": "Activité marquée comme lue"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur marquage activité lue", activity_id=activity_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/activities/{activity_id}/bookmark")
async def toggle_bookmark_activity(
    activity_id: str,
    user_id: str = Query("default", description="ID utilisateur")
) -> Dict[str, Any]:
    """
    Ajoute/retire une activité des favoris
    """
    try:
        manager = await get_activity_feed_manager()
        
        success = await manager.bookmark_activity(activity_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Activité non trouvée")
        
        # Récupération de l'état actuel
        activity = await manager.get_activity_by_id(activity_id)
        bookmarked = activity.bookmarked if activity else False
        
        return {
            "success": True,
            "bookmarked": bookmarked,
            "message": f"Activité {'ajoutée aux' if bookmarked else 'retirée des'} favoris"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur bookmark activité", activity_id=activity_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/stats")
async def get_activity_stats(
    since_hours: Optional[int] = Query(168, ge=1, le=720, description="Période pour les statistiques (en heures)")
) -> Dict[str, Any]:
    """
    Récupère les statistiques du flux d'activité
    """
    try:
        manager = await get_activity_feed_manager()
        
        since_date = datetime.now() - timedelta(hours=since_hours)
        stats = await manager.get_activity_stats(since=since_date)
        
        return {
            "period_hours": since_hours,
            "total_activities": stats.total_activities,
            "activities_24h": stats.activities_24h,
            "activities_by_type": stats.activities_by_type,
            "activities_by_priority": stats.activities_by_priority,
            "avg_impact_score": round(stats.avg_impact_score, 2),
            "most_active_source": stats.most_active_source,
            "last_activity": stats.last_activity.isoformat() if stats.last_activity else None
        }
        
    except Exception as e:
        logger.error("Erreur récupération stats activités", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/types")
async def get_activity_types() -> Dict[str, Any]:
    """
    Récupère la liste des types d'activités disponibles
    """
    return {
        "activity_types": [
            {
                "value": activity_type.value,
                "label": _get_type_label(activity_type)
            }
            for activity_type in ActivityType
        ]
    }

@router.get("/priorities")
async def get_activity_priorities() -> Dict[str, Any]:
    """
    Récupère la liste des priorités disponibles
    """
    return {
        "priorities": [
            {
                "value": priority.value,
                "label": _get_priority_label(priority)
            }
            for priority in ActivityPriority
        ]
    }

@router.get("/sources")
async def get_activity_sources() -> Dict[str, Any]:
    """
    Récupère la liste des sources disponibles
    """
    return {
        "sources": [
            {
                "value": source.value,
                "label": _get_source_label(source)
            }
            for source in ActivitySource
        ]
    }

@router.post("/add")
async def add_activity(
    background_tasks: BackgroundTasks,
    activity_type: str,
    title: str,
    description: str,
    details: Optional[Dict[str, Any]] = None,
    priority: str = "normal",
    source: str = "system",
    user_id: Optional[str] = None,
    source_name: Optional[str] = None,
    url: Optional[str] = None,
    tags: Optional[List[str]] = None,
    tech_areas: Optional[List[str]] = None,
    impact_score: float = 0.0
) -> Dict[str, Any]:
    """
    Ajoute une nouvelle activité au flux (pour tests/démonstration)
    """
    try:
        manager = await get_activity_feed_manager()
        
        # Validation des énumérations
        try:
            activity_type_enum = ActivityType(activity_type)
            priority_enum = ActivityPriority(priority)
            source_enum = ActivitySource(source)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Valeur énumération invalide: {e}")
        
        # Ajout de l'activité
        activity_id = await manager.add_activity(
            activity_type=activity_type_enum,
            title=title,
            description=description,
            details=details or {},
            priority=priority_enum,
            source=source_enum,
            user_id=user_id,
            source_name=source_name,
            url=url,
            tags=tags or [],
            tech_areas=tech_areas or [],
            impact_score=impact_score
        )
        
        return {
            "success": True,
            "activity_id": activity_id,
            "message": "Activité ajoutée avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur ajout activité", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/demo/populate")
async def populate_demo_activities(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Peuple le flux avec des activités de démonstration
    """
    try:
        manager = await get_activity_feed_manager()
        
        # Activités de démonstration
        demo_activities = [
            {
                "activity_type": ActivityType.INSIGHT_DISCOVERED,
                "title": "💡 Nouvelle tendance IA détectée",
                "description": "Découverte d'une nouvelle approche en machine learning",
                "priority": ActivityPriority.HIGH,
                "source": ActivitySource.MCP,
                "tech_areas": ["AI/ML", "Deep Learning"],
                "impact_score": 0.85
            },
            {
                "activity_type": ActivityType.CRITICAL_ALERT,
                "title": "🚨 Vulnérabilité critique détectée",
                "description": "Faille de sécurité majeure dans OpenSSL",
                "priority": ActivityPriority.CRITICAL,
                "source": ActivitySource.LLM,
                "tech_areas": ["Security", "Infrastructure"],
                "impact_score": 0.95
            },
            {
                "activity_type": ActivityType.SOURCE_CRAWLED,
                "title": "📄 Nouveau contenu crawlé",
                "description": "Mise à jour de Hacker News avec 42 nouveaux articles",
                "priority": ActivityPriority.NORMAL,
                "source": ActivitySource.CRAWLER,
                "source_name": "Hacker News",
                "impact_score": 0.6
            },
            {
                "activity_type": ActivityType.DAILY_SUMMARY,
                "title": "📋 Résumé quotidien généré",
                "description": "Synthèse des 127 insights découverts aujourd'hui",
                "priority": ActivityPriority.NORMAL,
                "source": ActivitySource.LLM,
                "impact_score": 0.75
            },
            {
                "activity_type": ActivityType.USER_SEARCH,
                "title": "🔍 Recherche: React 19 features",
                "description": "8 résultats trouvés",
                "priority": ActivityPriority.LOW,
                "source": ActivitySource.USER,
                "tech_areas": ["Frontend", "React"],
                "user_id": "user_demo"
            }
        ]
        
        added_count = 0
        for demo_activity in demo_activities:
            try:
                await manager.add_activity(**demo_activity)
                added_count += 1
            except Exception as e:
                logger.warning("Erreur ajout activité demo", error=str(e))
        
        return {
            "success": True,
            "added_count": added_count,
            "message": f"{added_count} activités de démonstration ajoutées"
        }
        
    except Exception as e:
        logger.error("Erreur population activités demo", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/bookmarks")
async def get_bookmarked_activities(
    limit: int = Query(50, ge=1, le=200, description="Nombre d'activités à récupérer"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    user_id: str = Query("default", description="ID utilisateur")
) -> Dict[str, Any]:
    """Récupère la liste des activités bookmarkées par l'utilisateur"""
    try:
        manager = await get_activity_feed_manager()
        activities = await manager.get_bookmarked_activities(user_id=user_id, limit=limit, offset=offset)

        activities_data = [
            {
                "id": a.id,
                "type": a.type.value,
                "priority": a.priority.value,
                "source": a.source.value,
                "title": a.title,
                "description": a.description,
                "details": a.details,
                "timestamp": a.timestamp.isoformat(),
                "user_id": a.user_id,
                "source_name": a.source_name,
                "url": a.url,
                "tags": a.tags,
                "tech_areas": a.tech_areas,
                "impact_score": a.impact_score,
                "read": a.read,
                "bookmarked": True
            }
            for a in activities
        ]

        return {
            "activities": activities_data,
            "total": len(activities_data),
            "limit": limit,
            "offset": offset,
            "has_more": len(activities_data) == limit
        }
    except Exception as e:
        logger.error("Erreur récupération favoris", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# === Fonctions helper ===

def _get_type_label(activity_type: ActivityType) -> str:
    """Retourne le label français pour un type d'activité"""
    labels = {
        ActivityType.INSIGHT_DISCOVERED: "Insight Découvert",
        ActivityType.CRITICAL_ALERT: "Alerte Critique",
        ActivityType.CUSTOM_ALERT: "Alerte Personnalisée",
        ActivityType.SOURCE_CRAWLED: "Source Crawlée",
        ActivityType.DAILY_SUMMARY: "Résumé Quotidien",
        ActivityType.FOCUS_MODE: "Mode Focus",
        ActivityType.SOURCE_ADDED: "Source Ajoutée",
        ActivityType.USER_SEARCH: "Recherche Utilisateur",
        ActivityType.SYSTEM_UPDATE: "Mise à Jour Système",
        ActivityType.CRAWL_STARTED: "Crawl Démarré",
        ActivityType.CRAWL_COMPLETED: "Crawl Terminé",
        ActivityType.LLM_ANALYSIS: "Analyse LLM"
    }
    return labels.get(activity_type, activity_type.value)

def _get_priority_label(priority: ActivityPriority) -> str:
    """Retourne le label français pour une priorité"""
    labels = {
        ActivityPriority.LOW: "Faible",
        ActivityPriority.NORMAL: "Normale",
        ActivityPriority.HIGH: "Élevée",
        ActivityPriority.URGENT: "Urgente",
        ActivityPriority.CRITICAL: "Critique"
    }
    return labels.get(priority, priority.value)

def _get_source_label(source: ActivitySource) -> str:
    """Retourne le label français pour une source"""
    labels = {
        ActivitySource.SYSTEM: "Système",
        ActivitySource.USER: "Utilisateur",
        ActivitySource.SCHEDULER: "Planificateur",
        ActivitySource.MCP: "MCP",
        ActivitySource.LLM: "LLM",
        ActivitySource.CRAWLER: "Crawler"
    }
    return labels.get(source, source.value)
