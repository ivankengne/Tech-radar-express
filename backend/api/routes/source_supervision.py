"""
Tech Radar Express - Source Supervision API Routes
Dashboard de supervision des sources avec intégration MCP get_available_sources
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from collections import defaultdict

from ...core.source_manager import get_source_manager, TechAxis, SourceType
from backend.core.mcp_client import MCPClient
from ...core.crawl_monitor import get_crawl_monitor

# Configuration du logger
logger = structlog.get_logger(__name__)

# Router pour les routes de supervision des sources
router = APIRouter(prefix="/api/v1/source-supervision", tags=["source-supervision"])

@router.get("/dashboard")
async def get_supervision_dashboard():
    """Récupère les données complètes du dashboard de supervision des sources"""
    try:
        # Récupération des gestionnaires
        source_manager = await get_source_manager()
        monitor = get_crawl_monitor()
        
        # Sources locales (configurées dans SourceManager)
        local_sources = source_manager.get_all_sources()
        
        # Sources MCP (crawlées et stockées)
        mcp_sources = []
        try:
            mcp_client = MCPClient()
            mcp_response = await mcp_client.get_available_sources()
            if mcp_response.get('success'):
                mcp_sources = mcp_response.get('sources', [])
        except Exception as e:
            logger.warning("Erreur récupération sources MCP", error=str(e))
        
        # Métriques de monitoring
        metrics = monitor.get_metrics()
        
        # Statistiques globales
        total_local_sources = len(local_sources)
        active_local_sources = len([s for s in local_sources if s.enabled])
        total_mcp_sources = len(mcp_sources)
        
        # Analyse par axe technologique
        sources_by_axis = defaultdict(int)
        for source in local_sources:
            for axis in source.tech_axes:
                sources_by_axis[axis.value] += 1
        
        # Analyse par type de source
        sources_by_type = defaultdict(int)
        for source in local_sources:
            sources_by_type[source.source_type.value] += 1
        
        # Sources récemment crawlées
        recent_crawls = []
        for source in local_sources:
            if source.last_crawled:
                recent_crawls.append({
                    "source_id": source.id,
                    "name": source.name,
                    "last_crawled": source.last_crawled.isoformat(),
                    "success": source.last_success is not None and source.last_success >= source.last_crawled,
                    "crawl_count": source.crawl_count,
                    "error_count": source.error_count
                })
        
        # Tri par date de crawl récent
        recent_crawls.sort(key=lambda x: x["last_crawled"], reverse=True)
        
        # Sources problématiques (erreurs récentes)
        problematic_sources = []
        for source in local_sources:
            if source.error_count > 0:
                error_rate = source.error_count / max(source.crawl_count, 1)
                if error_rate > 0.3:  # Plus de 30% d'erreurs
                    problematic_sources.append({
                        "source_id": source.id,
                        "name": source.name,
                        "error_count": source.error_count,
                        "crawl_count": source.crawl_count,
                        "error_rate": round(error_rate * 100, 1),
                        "last_crawled": source.last_crawled.isoformat() if source.last_crawled else None,
                        "enabled": source.enabled
                    })
        
        # Tri par taux d'erreur
        problematic_sources.sort(key=lambda x: x["error_rate"], reverse=True)
        
        # Sources MCP populaires (plus de contenu)
        popular_mcp_sources = []
        for mcp_source in mcp_sources:
            if mcp_source.get('total_words') and mcp_source['total_words'] > 1000:
                popular_mcp_sources.append({
                    "source_id": mcp_source['source_id'],
                    "summary": mcp_source['summary'][:200] + "..." if len(mcp_source['summary']) > 200 else mcp_source['summary'],
                    "total_words": mcp_source.get('total_words'),
                    "created_at": mcp_source['created_at'],
                    "updated_at": mcp_source['updated_at']
                })
        
        # Tri par nombre de mots
        popular_mcp_sources.sort(key=lambda x: x["total_words"] or 0, reverse=True)
        
        # Recommandations de nouvelles sources
        recommendations = await _generate_source_recommendations(local_sources, mcp_sources)
        
        return JSONResponse({
            "dashboard": {
                "overview": {
                    "total_local_sources": total_local_sources,
                    "active_local_sources": active_local_sources,
                    "total_mcp_sources": total_mcp_sources,
                    "active_crawls": metrics.active_crawls,
                    "success_rate": round(metrics.success_rate * 100, 1),
                    "error_rate": round(metrics.error_rate * 100, 1),
                    "avg_crawl_time": round(metrics.avg_crawl_time, 2),
                    "last_updated": datetime.now().isoformat()
                },
                "distribution": {
                    "by_axis": dict(sources_by_axis),
                    "by_type": dict(sources_by_type)
                },
                "recent_activity": {
                    "recent_crawls": recent_crawls[:10],
                    "problematic_sources": problematic_sources[:5],
                    "popular_mcp_sources": popular_mcp_sources[:10]
                },
                "recommendations": recommendations,
                "health_status": {
                    "overall": "healthy" if metrics.error_rate < 0.2 else "warning" if metrics.error_rate < 0.5 else "critical",
                    "active_sources_percentage": round((active_local_sources / max(total_local_sources, 1)) * 100, 1),
                    "problematic_sources_count": len(problematic_sources),
                    "mcp_integration": "connected" if mcp_sources else "disconnected"
                }
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur récupération dashboard supervision", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/local")
async def get_local_sources(
    enabled_only: bool = Query(False, description="Filtrer seulement les sources actives"),
    axis: Optional[str] = Query(None, description="Filtrer par axe technologique"),
    source_type: Optional[str] = Query(None, description="Filtrer par type de source")
):
    """Récupère les sources locales configurées dans SourceManager"""
    try:
        source_manager = await get_source_manager()
        sources = source_manager.get_all_sources()
        
        # Filtrage
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        
        if axis:
            try:
                axis_enum = TechAxis(axis)
                sources = [s for s in sources if axis_enum in s.tech_axes]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Axe technologique invalide: {axis}")
        
        if source_type:
            try:
                type_enum = SourceType(source_type)
                sources = [s for s in sources if s.source_type == type_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type de source invalide: {source_type}")
        
        # Conversion en format API
        sources_data = []
        for source in sources:
            sources_data.append({
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "source_type": source.source_type.value,
                "tech_axes": [axis.value for axis in source.tech_axes],
                "enabled": source.enabled,
                "crawl_frequency": source.crawl_frequency,
                "priority": source.priority,
                "description": source.description,
                "tags": source.tags,
                "created_at": source.created_at.isoformat(),
                "last_crawled": source.last_crawled.isoformat() if source.last_crawled else None,
                "last_success": source.last_success.isoformat() if source.last_success else None,
                "crawl_count": source.crawl_count,
                "error_count": source.error_count,
                "health_status": _calculate_source_health(source)
            })
        
        return JSONResponse({
            "sources": sources_data,
            "total_count": len(sources_data),
            "filters": {
                "enabled_only": enabled_only,
                "axis": axis,
                "source_type": source_type
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération sources locales", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/mcp")
async def get_mcp_sources(
    limit: int = Query(50, ge=1, le=200, description="Nombre max de sources"),
    search: Optional[str] = Query(None, description="Recherche dans les résumés")
):
    """Récupère les sources disponibles via MCP get_available_sources"""
    try:
        mcp_client = MCPClient()
        mcp_response = await mcp_client.get_available_sources()
        
        if not mcp_response.get('success'):
            raise HTTPException(status_code=503, detail="Service MCP indisponible")
            
            sources = mcp_response.get('sources', [])
            
            # Filtrage par recherche
            if search:
                search_lower = search.lower()
                sources = [
                    s for s in sources 
                    if search_lower in s.get('source_id', '').lower() or 
                       search_lower in s.get('summary', '').lower()
                ]
            
            # Limitation
            sources = sources[:limit]
            
            # Enrichissement des données
            enriched_sources = []
            for source in sources:
                enriched_sources.append({
                    "source_id": source['source_id'],
                    "summary": source['summary'],
                    "total_words": source.get('total_words'),
                    "created_at": source['created_at'],
                    "updated_at": source['updated_at'],
                    "domain": source['source_id'].split('.')[0] if '.' in source['source_id'] else source['source_id'],
                    "content_size": _categorize_content_size(source.get('total_words')),
                    "freshness": _calculate_freshness(source['updated_at'])
                })
            
            return JSONResponse({
                "sources": enriched_sources,
                "total_count": len(enriched_sources),
                "mcp_total": mcp_response.get('count', 0),
                "filters": {
                    "limit": limit,
                    "search": search
                },
                "timestamp": datetime.now().isoformat()
            })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération sources MCP", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/comparison")
async def get_sources_comparison():
    """Compare les sources locales et MCP pour identifier les gaps et opportunités"""
    try:
        source_manager = await get_source_manager()
        local_sources = source_manager.get_all_sources()
        
        # Sources MCP
        mcp_sources = []
        try:
            mcp_client = MCPClient()
            mcp_response = await mcp_client.get_available_sources()
            if mcp_response.get('success'):
                mcp_sources = mcp_response.get('sources', [])
        except Exception as e:
            logger.warning("Erreur récupération sources MCP", error=str(e))
        
        # Analyse des domaines
        local_domains = set()
        for source in local_sources:
            try:
                domain = source.url.split('//')[1].split('/')[0]
                local_domains.add(domain)
            except:
                pass
        
        mcp_domains = set(source['source_id'] for source in mcp_sources)
        
        # Domaines uniquement dans MCP (opportunités)
        mcp_only_domains = mcp_domains - local_domains
        
        # Domaines uniquement locaux (gaps potentiels)
        local_only_domains = local_domains - mcp_domains
        
        # Domaines communs
        common_domains = local_domains & mcp_domains
        
        # Recommandations basées sur l'analyse
        recommendations = []
        
        # Sources MCP populaires non configurées localement
        for source in mcp_sources:
            if source['source_id'] in mcp_only_domains:
                if source.get('total_words', 0) > 5000:  # Sources avec beaucoup de contenu
                    recommendations.append({
                        "type": "add_popular_source",
                        "source_id": source['source_id'],
                        "reason": f"Source populaire avec {source.get('total_words', 0)} mots de contenu",
                        "summary": source['summary'][:150] + "..." if len(source['summary']) > 150 else source['summary'],
                        "priority": "high" if source.get('total_words', 0) > 10000 else "medium"
                    })
        
        # Sources locales sans activité récente
        for source in local_sources:
            if source.enabled and (not source.last_crawled or 
                                 (datetime.now() - source.last_crawled).days > 7):
                recommendations.append({
                    "type": "check_inactive_source",
                    "source_id": source.id,
                    "reason": "Source active mais pas de crawl récent",
                    "url": source.url,
                    "priority": "medium"
                })
        
        # Tri des recommandations par priorité
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 2))
        
        return JSONResponse({
            "comparison": {
                "local_sources_count": len(local_sources),
                "mcp_sources_count": len(mcp_sources),
                "common_domains_count": len(common_domains),
                "mcp_only_domains_count": len(mcp_only_domains),
                "local_only_domains_count": len(local_only_domains)
            },
            "domains": {
                "common": list(common_domains)[:10],
                "mcp_only": list(mcp_only_domains)[:20],
                "local_only": list(local_only_domains)[:10]
            },
            "recommendations": recommendations[:15],
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur comparaison sources", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_supervision_analytics(
    days: int = Query(7, ge=1, le=30, description="Période d'analyse en jours")
):
    """Récupère les analytics de supervision des sources"""
    try:
        source_manager = await get_source_manager()
        monitor = get_crawl_monitor()
        
        # Métriques temporelles
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Analyse des crawls par jour
        daily_stats = defaultdict(lambda: {"crawls": 0, "successes": 0, "failures": 0})
        
        for source in source_manager.get_all_sources():
            history = monitor.get_crawl_history(source.id, limit=100)
            for crawl in history:
                crawl_date = datetime.fromisoformat(crawl['timestamp']).date()
                if datetime.combine(crawl_date, datetime.min.time()) >= cutoff_date:
                    daily_stats[crawl_date.isoformat()]["crawls"] += 1
                    if crawl['success']:
                        daily_stats[crawl_date.isoformat()]["successes"] += 1
                    else:
                        daily_stats[crawl_date.isoformat()]["failures"] += 1
        
        # Conversion en liste triée
        daily_analytics = []
        for date_str, stats in sorted(daily_stats.items()):
            daily_analytics.append({
                "date": date_str,
                "total_crawls": stats["crawls"],
                "successful_crawls": stats["successes"],
                "failed_crawls": stats["failures"],
                "success_rate": round(stats["successes"] / max(stats["crawls"], 1) * 100, 1)
            })
        
        # Top sources par activité
        source_activity = []
        for source in source_manager.get_all_sources():
            if source.crawl_count > 0:
                source_activity.append({
                    "source_id": source.id,
                    "name": source.name,
                    "crawl_count": source.crawl_count,
                    "error_count": source.error_count,
                    "success_rate": round((source.crawl_count - source.error_count) / source.crawl_count * 100, 1),
                    "last_crawled": source.last_crawled.isoformat() if source.last_crawled else None
                })
        
        # Tri par nombre de crawls
        source_activity.sort(key=lambda x: x["crawl_count"], reverse=True)
        
        # Analyse des erreurs
        error_analysis = monitor.get_error_history(limit=100)
        error_types_count = defaultdict(int)
        error_sources_count = defaultdict(int)
        
        for error in error_analysis:
            if error.timestamp >= cutoff_date:
                error_types_count[error.error_type.value] += 1
                error_sources_count[error.source_id] += 1
        
        return JSONResponse({
            "analytics": {
                "period_days": days,
                "daily_stats": daily_analytics,
                "top_sources": source_activity[:10],
                "error_analysis": {
                    "by_type": dict(error_types_count),
                    "by_source": dict(sorted(error_sources_count.items(), key=lambda x: x[1], reverse=True)[:10])
                },
                "summary": {
                    "total_crawls": sum(stats["crawls"] for stats in daily_stats.values()),
                    "total_successes": sum(stats["successes"] for stats in daily_stats.values()),
                    "total_failures": sum(stats["failures"] for stats in daily_stats.values()),
                    "avg_daily_crawls": round(sum(stats["crawls"] for stats in daily_stats.values()) / max(len(daily_stats), 1), 1),
                    "most_active_source": source_activity[0]["source_id"] if source_activity else None,
                    "most_problematic_error": max(error_types_count.items(), key=lambda x: x[1])[0] if error_types_count else None
                }
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error("Erreur récupération analytics supervision", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Fonctions utilitaires

async def _generate_source_recommendations(local_sources: List, mcp_sources: List) -> List[Dict]:
    """Génère des recommandations de nouvelles sources basées sur l'analyse"""
    recommendations = []
    
    # Analyse des axes technologiques sous-représentés
    axis_coverage = defaultdict(int)
    for source in local_sources:
        for axis in source.tech_axes:
            axis_coverage[axis.value] += 1
    
    # Identifier les axes avec peu de sources
    min_coverage = min(axis_coverage.values()) if axis_coverage else 0
    under_represented_axes = [axis for axis, count in axis_coverage.items() if count <= min_coverage + 1]
    
    if under_represented_axes:
        recommendations.append({
            "type": "axis_coverage",
            "title": "Améliorer la couverture des axes technologiques",
            "description": f"Axes sous-représentés: {', '.join(under_represented_axes)}",
            "priority": "medium",
            "action": "Ajouter des sources pour ces axes technologiques"
        })
    
    # Sources MCP populaires
    popular_mcp = [s for s in mcp_sources if s.get('total_words', 0) > 8000]
    if len(popular_mcp) > 5:
        recommendations.append({
            "type": "popular_sources",
            "title": "Sources MCP populaires disponibles",
            "description": f"{len(popular_mcp)} sources avec beaucoup de contenu détectées",
            "priority": "high",
            "action": "Examiner et ajouter les sources les plus pertinentes"
        })
    
    # Fréquence de crawl
    high_freq_sources = [s for s in local_sources if s.crawl_frequency < 12]  # Moins de 12h
    if len(high_freq_sources) > 3:
        recommendations.append({
            "type": "crawl_frequency",
            "title": "Optimiser la fréquence de crawl",
            "description": f"{len(high_freq_sources)} sources avec fréquence élevée",
            "priority": "low",
            "action": "Réviser les fréquences pour optimiser les ressources"
        })
    
    return recommendations[:5]  # Limiter à 5 recommandations

def _calculate_source_health(source) -> str:
    """Calcule le statut de santé d'une source"""
    if not source.enabled:
        return "disabled"
    
    if source.crawl_count == 0:
        return "new"
    
    error_rate = source.error_count / source.crawl_count
    
    if error_rate > 0.5:
        return "critical"
    elif error_rate > 0.3:
        return "warning"
    elif not source.last_crawled or (datetime.now() - source.last_crawled).days > 7:
        return "stale"
    else:
        return "healthy"

def _categorize_content_size(total_words: Optional[int]) -> str:
    """Catégorise la taille du contenu"""
    if not total_words:
        return "unknown"
    elif total_words < 1000:
        return "small"
    elif total_words < 5000:
        return "medium"
    elif total_words < 15000:
        return "large"
    else:
        return "xlarge"

def _calculate_freshness(updated_at: str) -> str:
    """Calcule la fraîcheur du contenu"""
    try:
        updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        days_ago = (datetime.now() - updated_date.replace(tzinfo=None)).days
        
        if days_ago == 0:
            return "today"
        elif days_ago == 1:
            return "yesterday"
        elif days_ago <= 7:
            return "this_week"
        elif days_ago <= 30:
            return "this_month"
        else:
            return "older"
    except:
        return "unknown" 