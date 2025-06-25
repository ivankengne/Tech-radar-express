"""
Tech Radar Express - Routes API Détection Alertes Critiques
"""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from core.critical_alerts_detector import (
    get_critical_alerts_detector,
    CriticalAlertsDetector
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/critical-alerts", tags=["critical-alerts"])

class CriticalAlertResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class AnalysisRequest(BaseModel):
    hours_back: int = Field(default=1, ge=1, le=24)

@router.post("/analyze")
async def analyze_content(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    detector: CriticalAlertsDetector = Depends(get_critical_alerts_detector)
):
    """Lance une analyse de détection d'alertes critiques"""
    try:
        logger.info("Analyse critique demandée")
        
        background_tasks.add_task(
            detector.analyze_recent_content,
            hours_back=request.hours_back
        )
        
        return CriticalAlertResponse(
            success=True,
            data={"message": "Analyse lancée"}
        )
        
    except Exception as e:
        logger.error("Erreur analyse", error=str(e))
        return CriticalAlertResponse(
            success=False,
            error=str(e)
        )

@router.get("/active")
async def get_active_alerts(
    max_age_hours: int = 24,
    detector: CriticalAlertsDetector = Depends(get_critical_alerts_detector)
):
    """Récupère les alertes critiques actives"""
    try:
        active_alerts = detector.get_active_alerts(max_age_hours)
        
        alerts_data = [{
            "id": alert.id,
            "priority_score": alert.priority_score,
            "created_at": alert.created_at.isoformat(),
            "analysis": {
                "source": alert.analysis.source,
                "criticality_level": alert.analysis.criticality_level.value,
                "confidence_score": alert.analysis.confidence_score,
                "categories": [cat.value for cat in alert.analysis.categories],
                "key_factors": alert.analysis.key_factors,
                "impact_assessment": alert.analysis.impact_assessment
            }
        } for alert in active_alerts]
        
        return CriticalAlertResponse(
            success=True,
            data={"alerts": alerts_data}
        )
        
    except Exception as e:
        logger.error("Erreur alertes", error=str(e))
        return CriticalAlertResponse(
            success=False,
            error=str(e)
        )

@router.get("/stats")
async def get_stats(
    detector: CriticalAlertsDetector = Depends(get_critical_alerts_detector)
):
    """Statistiques de détection"""
    try:
        stats = detector.get_stats()
        return CriticalAlertResponse(
            success=True,
            data={"stats": stats}
        )
    except Exception as e:
        logger.error("Erreur stats", error=str(e))
        return CriticalAlertResponse(
            success=False,
            error=str(e)
        )

@router.post("/alert/{alert_id}/mark-false-positive")
async def mark_false_positive(
    alert_id: str,
    detector: CriticalAlertsDetector = Depends(get_critical_alerts_detector)
):
    """Marque une alerte comme faux positif"""
    try:
        success = detector.mark_false_positive(alert_id)
        
        if not success:
            return CriticalAlertResponse(
                success=False,
                error="Alerte non trouvée"
            )
        
        return CriticalAlertResponse(
            success=True,
            data={"message": "Marquée comme faux positif"}
        )
        
    except Exception as e:
        logger.error("Erreur marquage", error=str(e))
        return CriticalAlertResponse(
            success=False,
            error=str(e)
        )

@router.post("/test-analysis")
async def test_analysis(
    content: str = Field(..., description="Contenu à analyser"),
    source: str = Field(default="test", description="Source"),
    detector: CriticalAlertsDetector = Depends(get_critical_alerts_detector)
):
    """Test d'analyse sur contenu"""
    try:
        test_item = {"content": content, "source": source}
        analysis = await detector._analyze_content(test_item)
        
        if not analysis:
            return CriticalAlertResponse(
                success=True,
                data={"analyzed": True, "critical": False}
            )
        
        is_critical = detector._is_critical(analysis)
        
        result = {
            "analyzed": True,
            "critical": is_critical,
            "analysis": {
                "criticality_level": analysis.criticality_level.value,
                "confidence_score": analysis.confidence_score,
                "categories": [cat.value for cat in analysis.categories],
                "key_factors": analysis.key_factors,
                "llm_reasoning": analysis.llm_reasoning
            }
        }
        
        return CriticalAlertResponse(success=True, data=result)
        
    except Exception as e:
        logger.error("Erreur test", error=str(e))
        return CriticalAlertResponse(
            success=False,
            error=str(e)
        )
