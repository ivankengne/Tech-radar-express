"""
Tech Radar Express - Routes API pour Résumés Quotidiens
Endpoints pour la génération et récupération des résumés automatisés
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
import structlog

from core.daily_summary_generator import get_daily_summary_generator, SummaryScope, DailySummary
from core.config_manager import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/summary", tags=["daily-summary"])

class SummaryRequest(BaseModel):
    """Modèle de requête pour génération de résumé"""
    date: Optional[str] = Field(None, description="Date pour le résumé (YYYY-MM-DD), par défaut: hier")
    scope: SummaryScope = Field(SummaryScope.DAILY, description="Portée temporelle du résumé")

class SummaryResponse(BaseModel):
    """Modèle de réponse pour résumé généré"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class SummaryStats(BaseModel):
    """Statistiques d'un résumé"""
    date: str
    sections_count: int
    total_sources: int
    generation_time: float
    generated_at: str

@router.post("/generate", response_model=SummaryResponse)
async def generate_daily_summary(
    request: SummaryRequest,
    generator=Depends(get_daily_summary_generator)
):
    """
    Génère un nouveau résumé quotidien
    
    - **date**: Date pour le résumé (format YYYY-MM-DD), par défaut: hier
    - **scope**: Portée temporelle (daily, weekly, monthly)
    
    Retourne le résumé généré avec métadonnées et statistiques.
    """
    try:
        # Parsing de la date si fournie
        target_date = None
        if request.date:
            try:
                target_date = datetime.strptime(request.date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Format de date invalide. Utilisez YYYY-MM-DD"
                )
        
        logger.info(
            "Génération résumé demandée",
            date=request.date or "hier",
            scope=request.scope.value
        )
        
        # Génération du résumé
        summary = await generator.generate_daily_summary(
            date=target_date,
            scope=request.scope
        )
        
        # Formatage de la réponse
        response_data = {
            "summary": {
                "date": summary.date.strftime("%Y-%m-%d"),
                "scope": request.scope.value,
                "sections": [
                    {
                        "title": section.title,
                        "content": section.content,
                        "priority": section.priority,
                        "source_count": section.source_count
                    }
                    for section in summary.sections
                ],
                "stats": {
                    "sections_count": len(summary.sections),
                    "total_sources": summary.total_sources,
                    "generation_time": summary.generation_time,
                    "generated_at": datetime.now().isoformat()
                }
            },
            "metadata": summary.metadata
        }
        
        logger.info(
            "Résumé généré avec succès",
            sections=len(summary.sections),
            sources=summary.total_sources,
            time=f"{summary.generation_time:.2f}s"
        )
        
        return SummaryResponse(
            success=True,
            data=response_data,
            metadata={
                "request_timestamp": datetime.now().isoformat(),
                "generation_time": summary.generation_time
            }
        )
        
    except Exception as e:
        logger.error("Erreur génération résumé", error=str(e))
        return SummaryResponse(
            success=False,
            error=f"Erreur lors de la génération: {str(e)}",
            metadata={"error_timestamp": datetime.now().isoformat()}
        )

@router.get("/latest", response_model=SummaryResponse)
async def get_latest_summary(
    generator=Depends(get_daily_summary_generator)
):
    """
    Récupère le dernier résumé généré ou en génère un nouveau pour hier
    
    Cette route est optimisée pour l'affichage rapide du dernier résumé disponible.
    """
    try:
        # Pour cette version, on génère toujours un nouveau résumé
        # TODO: Implémenter un cache/stockage des résumés générés
        yesterday = datetime.now() - timedelta(days=1)
        
        summary = await generator.generate_daily_summary(
            date=yesterday,
            scope=SummaryScope.DAILY
        )
        
        response_data = {
            "summary": {
                "date": summary.date.strftime("%Y-%m-%d"),
                "sections": [
                    {
                        "title": section.title,
                        "content": section.content,
                        "priority": section.priority,
                        "source_count": section.source_count
                    }
                    for section in summary.sections
                ],
                "stats": {
                    "sections_count": len(summary.sections),
                    "total_sources": summary.total_sources,
                    "generation_time": summary.generation_time
                }
            }
        }
        
        return SummaryResponse(
            success=True,
            data=response_data,
            metadata={"retrieved_at": datetime.now().isoformat()}
        )
        
    except Exception as e:
        logger.error("Erreur récupération résumé", error=str(e))
        return SummaryResponse(
            success=False,
            error=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/markdown")
async def get_summary_markdown(
    date: Optional[str] = Query(None, description="Date du résumé (YYYY-MM-DD)"),
    generator=Depends(get_daily_summary_generator)
) -> PlainTextResponse:
    """
    Récupère un résumé formaté en Markdown
    
    - **date**: Date pour le résumé (format YYYY-MM-DD), par défaut: hier
    
    Retourne le résumé directement en format Markdown pour affichage ou téléchargement.
    """
    try:
        # Parsing de la date
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Format de date invalide. Utilisez YYYY-MM-DD"
                )
        
        # Génération du résumé
        summary = await generator.generate_daily_summary(
            date=target_date,
            scope=SummaryScope.DAILY
        )
        
        # Formatage en Markdown
        markdown_content = generator.format_as_markdown(summary)
        
        # Headers pour téléchargement
        filename = f"tech-radar-resume-{summary.date.strftime('%Y-%m-%d')}.md"
        
        return PlainTextResponse(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error("Erreur génération Markdown", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération Markdown: {str(e)}"
        )

@router.get("/stats")
async def get_summary_stats():
    """
    Récupère les statistiques globales des résumés
    
    Retourne des métriques sur l'utilisation et les performances du générateur de résumés.
    """
    try:
        # Pour cette version, on retourne des stats basiques
        # TODO: Implémenter un système de tracking des résumés générés
        
        stats = {
            "service_status": "active",
            "last_generation": datetime.now().isoformat(),
            "supported_scopes": [scope.value for scope in SummaryScope],
            "default_sections": [
                "Tendances & Innovations",
                "Axes Technologiques (4 principaux)",
                "Alertes & Points Critiques"
            ],
            "features": {
                "mcp_integration": True,
                "markdown_export": True,
                "automated_scheduling": True,
                "priority_ranking": True
            }
        }
        
        return SummaryResponse(
            success=True,
            data={"stats": stats},
            metadata={"retrieved_at": datetime.now().isoformat()}
        )
        
    except Exception as e:
        logger.error("Erreur récupération stats", error=str(e))
        return SummaryResponse(
            success=False,
            error=f"Erreur lors de la récupération des stats: {str(e)}"
        )

@router.post("/test")
async def test_summary_generation(
    generator=Depends(get_daily_summary_generator)
):
    """
    Endpoint de test pour vérifier le fonctionnement du générateur
    
    Génère un résumé de test avec des données limitées pour validation.
    """
    try:
        # Test avec la date d'hier
        test_date = datetime.now() - timedelta(days=1)
        
        logger.info("Test génération résumé", date=test_date.strftime("%Y-%m-%d"))
        
        summary = await generator.generate_daily_summary(
            date=test_date,
            scope=SummaryScope.DAILY
        )
        
        test_results = {
            "test_status": "success",
            "test_date": test_date.strftime("%Y-%m-%d"),
            "sections_generated": len(summary.sections),
            "total_sources": summary.total_sources,
            "generation_time": summary.generation_time,
            "sections_titles": [section.title for section in summary.sections],
            "markdown_preview": generator.format_as_markdown(summary)[:500] + "..."
        }
        
        return SummaryResponse(
            success=True,
            data={"test_results": test_results},
            metadata={
                "test_timestamp": datetime.now().isoformat(),
                "test_version": "1.0"
            }
        )
        
    except Exception as e:
        logger.error("Erreur test génération", error=str(e))
        return SummaryResponse(
            success=False,
            error=f"Test échoué: {str(e)}",
            metadata={"test_timestamp": datetime.now().isoformat()}
        ) 