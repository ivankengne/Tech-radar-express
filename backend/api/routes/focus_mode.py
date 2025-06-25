"""
Tech Radar Express - Routes API Mode Focus
Endpoints pour la génération de synthèses rapides structurées
"""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
import structlog

from core.focus_mode_generator import get_focus_mode_generator, FocusMode, FocusSynthesis
from core.config_manager import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/focus", tags=["focus-mode"])

class FocusRequest(BaseModel):
    """Modèle de requête pour mode focus"""
    mode: FocusMode = Field(FocusMode.TECH_PULSE, description="Mode de focus sélectionné")
    custom_query: Optional[str] = Field(None, description="Requête personnalisée optionnelle")

class FocusResponse(BaseModel):
    """Modèle de réponse pour synthèse focus"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

@router.post("/generate", response_model=FocusResponse)
async def generate_focus_synthesis(
    request: FocusRequest,
    generator=Depends(get_focus_mode_generator)
):
    """
    Génère une synthèse focus rapide selon le mode sélectionné
    
    - **mode**: Type de focus (quick_scan, tech_pulse, critical_alerts, innovation_radar)
    - **custom_query**: Requête personnalisée pour cibler la recherche
    
    Retourne une synthèse structurée générée en moins de 2 minutes.
    """
    try:
        logger.info(
            "Synthèse focus demandée",
            mode=request.mode.value,
            custom_query=bool(request.custom_query)
        )
        
        # Génération de la synthèse avec timeout
        synthesis = await generator.generate_focus_synthesis(
            mode=request.mode,
            custom_query=request.custom_query
        )
        
        # Formatage de la réponse
        response_data = {
            "synthesis": {
                "mode": synthesis.mode.value,
                "insights": [
                    {
                        "title": insight.title,
                        "summary": insight.summary,
                        "impact_level": insight.impact_level,
                        "tech_area": insight.tech_area,
                        "keywords": insight.keywords
                    }
                    for insight in synthesis.insights
                ],
                "key_trends": synthesis.key_trends,
                "critical_alerts": synthesis.critical_alerts,
                "innovation_highlights": synthesis.innovation_highlights,
                "stats": {
                    "generation_time": synthesis.generation_time,
                    "sources_analyzed": synthesis.sources_analyzed,
                    "confidence_score": synthesis.confidence_score,
                    "timestamp": synthesis.timestamp.isoformat()
                }
            }
        }
        
        logger.info(
            "Synthèse focus générée",
            mode=request.mode.value,
            insights_count=len(synthesis.insights),
            generation_time=f"{synthesis.generation_time:.1f}s",
            confidence=f"{synthesis.confidence_score:.2f}"
        )
        
        return FocusResponse(
            success=True,
            data=response_data,
            metadata={
                "request_timestamp": datetime.now().isoformat(),
                "generation_time": synthesis.generation_time,
                "mode_config": {
                    "max_time": generator.focus_configs[request.mode]["target_time"],
                    "within_target": synthesis.generation_time <= generator.focus_configs[request.mode]["target_time"]
                }
            }
        )
        
    except Exception as e:
        logger.error("Erreur génération synthèse focus", error=str(e))
        return FocusResponse(
            success=False,
            error=f"Erreur lors de la génération: {str(e)}",
            metadata={"error_timestamp": datetime.now().isoformat()}
        )

@router.get("/modes")
async def get_available_modes():
    """
    Récupère la liste des modes focus disponibles avec leurs configurations
    
    Retourne les différents modes de focus avec leurs temps cibles et descriptions.
    """
    try:
        modes_info = {
            "quick_scan": {
                "name": "Scan Rapide",
                "description": "Analyse express des dernières tendances",
                "target_time": 30,
                "emoji": "⚡",
                "focus_areas": ["Nouvelles importantes", "Tendances émergentes", "Alertes urgentes"]
            },
            "tech_pulse": {
                "name": "Pouls Technologique", 
                "description": "Vue d'ensemble équilibrée de l'écosystème tech",
                "target_time": 60,
                "emoji": "💓",
                "focus_areas": ["Frontend & Backend", "DevOps & Mobile", "Innovations clés"]
            },
            "critical_alerts": {
                "name": "Alertes Critiques",
                "description": "Focus sur les points critiques et urgences",
                "target_time": 45,
                "emoji": "🚨",
                "focus_areas": ["Sécurité", "Vulnérabilités", "Breaking changes"]
            },
            "innovation_radar": {
                "name": "Radar Innovation",
                "description": "Exploration des technologies émergentes",
                "target_time": 90,
                "emoji": "🚀",
                "focus_areas": ["Emerging Tech", "AI/ML", "Technologies disruptives"]
            }
        }
        
        return FocusResponse(
            success=True,
            data={"modes": modes_info},
            metadata={
                "total_modes": len(modes_info),
                "retrieved_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Erreur récupération modes", error=str(e))
        return FocusResponse(
            success=False,
            error=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/quick")
async def quick_focus(
    query: Optional[str] = None,
    generator=Depends(get_focus_mode_generator)
):
    """
    Génération focus ultra-rapide (mode QUICK_SCAN)
    
    - **query**: Requête personnalisée optionnelle
    
    Endpoint optimisé pour une synthèse en 30 secondes maximum.
    """
    try:
        synthesis = await generator.generate_focus_synthesis(
            mode=FocusMode.QUICK_SCAN,
            custom_query=query
        )
        
        # Réponse simplifiée pour usage rapide
        quick_data = {
            "insights_count": len(synthesis.insights),
            "key_highlights": [insight.title for insight in synthesis.insights[:3]],
            "trends_count": len(synthesis.key_trends),
            "alerts_count": len(synthesis.critical_alerts),
            "generation_time": synthesis.generation_time,
            "confidence": synthesis.confidence_score,
            "summary_text": generator.format_summary(synthesis)
        }
        
        return FocusResponse(
            success=True,
            data={"quick_focus": quick_data},
            metadata={
                "mode": "quick_scan",
                "generated_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Erreur quick focus", error=str(e))
        return FocusResponse(
            success=False,
            error=f"Erreur génération rapide: {str(e)}"
        )

@router.get("/text")
async def get_focus_text(
    mode: FocusMode = FocusMode.TECH_PULSE,
    query: Optional[str] = None,
    generator=Depends(get_focus_mode_generator)
) -> PlainTextResponse:
    """
    Génère une synthèse focus formatée en texte brut
    
    - **mode**: Mode de focus désiré
    - **query**: Requête personnalisée optionnelle
    
    Retourne la synthèse directement en format texte pour affichage ou copie.
    """
    try:
        synthesis = await generator.generate_focus_synthesis(
            mode=mode,
            custom_query=query
        )
        
        # Formatage en texte avec en-tête
        text_content = f"""Tech Radar Express - Mode Focus
Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}

{generator.format_summary(synthesis)}

---
Temps de génération: {synthesis.generation_time:.1f}s
Score de confiance: {synthesis.confidence_score:.0%}
Sources analysées: {synthesis.sources_analyzed}
"""
        
        return PlainTextResponse(
            content=text_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=focus-{mode.value}-{datetime.now().strftime('%Y%m%d-%H%M')}.txt"
            }
        )
        
    except Exception as e:
        logger.error("Erreur génération texte focus", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Erreur génération texte: {str(e)}"
        )

@router.post("/benchmark")
async def benchmark_focus_modes(
    generator=Depends(get_focus_mode_generator)
):
    """
    Lance un benchmark de tous les modes focus pour évaluer les performances
    
    Utile pour tester les temps de réponse et la qualité des synthèses.
    """
    try:
        benchmark_results = {}
        
        for mode in FocusMode:
            try:
                logger.info(f"Benchmark mode {mode.value}")
                
                synthesis = await generator.generate_focus_synthesis(mode=mode)
                
                benchmark_results[mode.value] = {
                    "success": True,
                    "generation_time": synthesis.generation_time,
                    "target_time": generator.focus_configs[mode]["target_time"],
                    "within_target": synthesis.generation_time <= generator.focus_configs[mode]["target_time"],
                    "confidence_score": synthesis.confidence_score,
                    "insights_count": len(synthesis.insights),
                    "trends_count": len(synthesis.key_trends),
                    "alerts_count": len(synthesis.critical_alerts),
                    "innovations_count": len(synthesis.innovation_highlights)
                }
                
            except Exception as e:
                benchmark_results[mode.value] = {
                    "success": False,
                    "error": str(e),
                    "generation_time": 0,
                    "target_time": generator.focus_configs[mode]["target_time"]
                }
        
        # Calcul des statistiques globales
        successful_modes = [r for r in benchmark_results.values() if r["success"]]
        avg_time = sum(r["generation_time"] for r in successful_modes) / len(successful_modes) if successful_modes else 0
        success_rate = len(successful_modes) / len(FocusMode)
        
        return FocusResponse(
            success=True,
            data={
                "benchmark_results": benchmark_results,
                "global_stats": {
                    "success_rate": success_rate,
                    "avg_generation_time": avg_time,
                    "total_modes_tested": len(FocusMode),
                    "successful_modes": len(successful_modes)
                }
            },
            metadata={
                "benchmark_timestamp": datetime.now().isoformat(),
                "total_duration": sum(r.get("generation_time", 0) for r in benchmark_results.values())
            }
        )
        
    except Exception as e:
        logger.error("Erreur benchmark focus", error=str(e))
        return FocusResponse(
            success=False,
            error=f"Erreur benchmark: {str(e)}"
        )

@router.get("/stats")
async def get_focus_stats(
    generator=Depends(get_focus_mode_generator)
):
    """
    Récupère les statistiques du générateur de mode focus
    
    Retourne des métriques sur les performances et la configuration.
    """
    try:
        stats = {
            "service_status": "active",
            "available_modes": [mode.value for mode in FocusMode],
            "mode_configurations": {
                mode.value: {
                    "target_time": config["target_time"],
                    "max_sources": config["max_sources"],
                    "max_insights": config["max_insights"],
                    "focus_areas": config["areas"]
                }
                for mode, config in generator.focus_configs.items()
            },
            "features": {
                "parallel_processing": True,
                "timeout_protection": True,
                "confidence_scoring": True,
                "custom_queries": True,
                "text_export": True,
                "benchmark_mode": True
            },
            "performance_targets": {
                "quick_scan": "30s",
                "tech_pulse": "60s", 
                "critical_alerts": "45s",
                "innovation_radar": "90s"
            }
        }
        
        return FocusResponse(
            success=True,
            data={"stats": stats},
            metadata={"retrieved_at": datetime.now().isoformat()}
        )
        
    except Exception as e:
        logger.error("Erreur récupération stats focus", error=str(e))
        return FocusResponse(
            success=False,
            error=f"Erreur stats: {str(e)}"
        ) 