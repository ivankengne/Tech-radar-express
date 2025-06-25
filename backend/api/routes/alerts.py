"""
Tech Radar Express - Routes API Alertes Personnalisées
Endpoints pour la gestion des alertes avec critères configurables
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from core.alerts_manager import (
    get_alerts_manager, 
    AlertsManager,
    AlertCriteria, 
    AlertNotification, 
    AlertPriority, 
    AlertStatus
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

class AlertCriteriaModel(BaseModel):
    """Modèle de critères d'alerte"""
    keywords: List[str] = Field(..., description="Mots-clés obligatoires")
    excluded_keywords: List[str] = Field(default=[], description="Mots-clés à exclure")
    tech_areas: List[str] = Field(default=[], description="Aires technologiques")
    sources: List[str] = Field(default=[], description="Sources spécifiques")
    min_impact_level: int = Field(default=1, ge=1, le=5, description="Niveau d'impact minimum")

class AlertNotificationModel(BaseModel):
    """Modèle de notification d'alerte"""
    email_recipients: List[str] = Field(default=[], description="Destinataires email")
    webhook_url: Optional[str] = Field(None, description="URL du webhook")
    throttle_minutes: int = Field(default=60, ge=1, description="Délai entre notifications")

class CreateAlertRequest(BaseModel):
    """Requête de création d'alerte"""
    name: str = Field(..., description="Nom de l'alerte")
    description: str = Field(..., description="Description de l'alerte")
    criteria: AlertCriteriaModel
    notifications: AlertNotificationModel
    priority: AlertPriority = Field(default=AlertPriority.MEDIUM, description="Priorité")

class AlertResponse(BaseModel):
    """Modèle de réponse"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

@router.post("/create", response_model=AlertResponse)
async def create_alert(
    request: CreateAlertRequest,
    manager: AlertsManager = Depends(get_alerts_manager)
):
    """Crée une nouvelle alerte personnalisée"""
    try:
        logger.info(
            "Création alerte demandée",
            name=request.name,
            keywords=len(request.criteria.keywords)
        )
        
        # Conversion vers dataclasses
        criteria = AlertCriteria(
            keywords=request.criteria.keywords,
            excluded_keywords=request.criteria.excluded_keywords,
            tech_areas=request.criteria.tech_areas,
            sources=request.criteria.sources,
            min_impact_level=request.criteria.min_impact_level
        )
        
        notifications = AlertNotification(
            email_recipients=request.notifications.email_recipients,
            webhook_url=request.notifications.webhook_url,
            throttle_minutes=request.notifications.throttle_minutes
        )
        
        # Création de l'alerte
        alert = manager.create_alert(
            name=request.name,
            description=request.description,
            criteria=criteria,
            notifications=notifications,
            priority=request.priority
        )
        
        alert_data = {
            "id": alert.id,
            "name": alert.name,
            "description": alert.description,
            "criteria": {
                "keywords": alert.criteria.keywords,
                "excluded_keywords": alert.criteria.excluded_keywords,
                "tech_areas": alert.criteria.tech_areas,
                "sources": alert.criteria.sources,
                "min_impact_level": alert.criteria.min_impact_level
            },
            "priority": alert.priority.value,
            "status": alert.status.value,
            "created_at": alert.created_at.isoformat()
        }
        
        return AlertResponse(
            success=True,
            data={"alert": alert_data},
            metadata={"alert_id": alert.id}
        )
        
    except Exception as e:
        logger.error("Erreur création alerte", error=str(e))
        return AlertResponse(
            success=False,
            error=f"Erreur création: {str(e)}"
        )

@router.get("/list", response_model=AlertResponse)
async def list_alerts(
    status: Optional[AlertStatus] = None,
    priority: Optional[AlertPriority] = None,
    manager: AlertsManager = Depends(get_alerts_manager)
):
    """Liste toutes les alertes avec filtres optionnels"""
    try:
        alerts = manager.list_alerts(status=status, priority=priority)
        
        alerts_data = []
        for alert in alerts:
            alert_data = {
                "id": alert.id,
                "name": alert.name,
                "description": alert.description,
                "priority": alert.priority.value,
                "status": alert.status.value,
                "created_at": alert.created_at.isoformat(),
                "last_triggered": alert.last_triggered.isoformat() if alert.last_triggered else None,
                "trigger_count": alert.trigger_count
            }
            alerts_data.append(alert_data)
        
        return AlertResponse(
            success=True,
            data={"alerts": alerts_data},
            metadata={"total_count": len(alerts_data)}
        )
        
    except Exception as e:
        logger.error("Erreur liste alertes", error=str(e))
        return AlertResponse(
            success=False,
            error=f"Erreur récupération: {str(e)}"
        )

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    manager: AlertsManager = Depends(get_alerts_manager)
):
    """Récupère une alerte spécifique"""
    try:
        alert = manager.get_alert(alert_id)
        
        if not alert:
            return AlertResponse(success=False, error="Alerte non trouvée")
        
        alert_data = {
            "id": alert.id,
            "name": alert.name,
            "description": alert.description,
            "criteria": {
                "keywords": alert.criteria.keywords,
                "excluded_keywords": alert.criteria.excluded_keywords,
                "tech_areas": alert.criteria.tech_areas,
                "sources": alert.criteria.sources,
                "min_impact_level": alert.criteria.min_impact_level
            },
            "notifications": {
                "email_recipients": alert.notifications.email_recipients,
                "webhook_url": alert.notifications.webhook_url,
                "throttle_minutes": alert.notifications.throttle_minutes
            },
            "priority": alert.priority.value,
            "status": alert.status.value,
            "created_at": alert.created_at.isoformat(),
            "trigger_count": alert.trigger_count
        }
        
        return AlertResponse(
            success=True,
            data={"alert": alert_data}
        )
        
    except Exception as e:
        logger.error("Erreur récupération alerte", error=str(e))
        return AlertResponse(
            success=False,
            error=f"Erreur récupération: {str(e)}"
        )

@router.delete("/{alert_id}", response_model=AlertResponse)
async def delete_alert(
    alert_id: str,
    manager: AlertsManager = Depends(get_alerts_manager)
):
    """Supprime une alerte"""
    try:
        success = manager.delete_alert(alert_id)
        
        if not success:
            return AlertResponse(success=False, error="Alerte non trouvée")
        
        return AlertResponse(
            success=True,
            data={"message": "Alerte supprimée"}
        )
        
    except Exception as e:
        logger.error("Erreur suppression alerte", error=str(e))
        return AlertResponse(
            success=False,
            error=f"Erreur suppression: {str(e)}"
        )

@router.post("/check", response_model=AlertResponse)
async def check_alerts(
    background_tasks: BackgroundTasks,
    manager: AlertsManager = Depends(get_alerts_manager)
):
    """Déclenche une vérification manuelle des alertes"""
    try:
        background_tasks.add_task(manager.check_alerts)
        
        return AlertResponse(
            success=True,
            data={"message": "Vérification lancée"}
        )
        
    except Exception as e:
        logger.error("Erreur vérification alertes", error=str(e))
        return AlertResponse(
            success=False,
            error=f"Erreur vérification: {str(e)}"
        )

@router.get("/stats/overview", response_model=AlertResponse)
async def get_alerts_stats(
    manager: AlertsManager = Depends(get_alerts_manager)
):
    """Récupère les statistiques des alertes"""
    try:
        stats = manager.get_alert_stats()
        
        return AlertResponse(
            success=True,
            data={"stats": stats}
        )
        
    except Exception as e:
        logger.error("Erreur stats alertes", error=str(e))
        return AlertResponse(
            success=False,
            error=f"Erreur stats: {str(e)}"
        )

@router.get("/templates/suggest", response_model=AlertResponse)
async def suggest_alert_templates():
    """Suggère des modèles d'alertes prédéfinis"""
    try:
        templates = {
            "security_critical": {
                "name": "Alertes Sécurité Critiques",
                "description": "Surveillance des vulnérabilités critiques",
                "criteria": {
                    "keywords": ["vulnerability", "breach", "exploit", "critical"],
                    "excluded_keywords": ["false positive"],
                    "tech_areas": ["Security"],
                    "min_impact_level": 4
                },
                "priority": "critical"
            },
            "ai_innovations": {
                "name": "Innovations IA/ML",
                "description": "Nouvelles technologies IA",
                "criteria": {
                    "keywords": ["GPT", "LLM", "AI", "machine learning"],
                    "tech_areas": ["AI/ML"],
                    "min_impact_level": 3
                },
                "priority": "high"
            },
            "framework_releases": {
                "name": "Nouvelles Versions Frameworks",
                "description": "Mises à jour des frameworks",
                "criteria": {
                    "keywords": ["release", "version", "React", "Vue", "Angular"],
                    "tech_areas": ["Frontend"],
                    "min_impact_level": 2
                },
                "priority": "medium"
            }
        }
        
        return AlertResponse(
            success=True,
            data={"templates": templates}
        )
        
    except Exception as e:
        logger.error("Erreur templates", error=str(e))
        return AlertResponse(
            success=False,
            error=f"Erreur templates: {str(e)}"
        ) 