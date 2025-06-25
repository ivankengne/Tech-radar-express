"""
Tech Radar Express - Gestionnaire d'Alertes Personnalisées
Système d'alertes configurable avec critères multiples et notifications
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
from collections import defaultdict

from .config_manager import get_settings
from .mcp_client import MCPCrawl4AIClient, RAGQueryRequest

logger = structlog.get_logger(__name__)

class AlertPriority(str, Enum):
    """Priorités d'alerte"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    """États d'alerte"""
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"

@dataclass
class AlertCriteria:
    """Critères d'une alerte personnalisée"""
    keywords: List[str]
    excluded_keywords: List[str] = None
    tech_areas: List[str] = None
    sources: List[str] = None
    min_impact_level: int = 1

    def __post_init__(self):
        if self.excluded_keywords is None:
            self.excluded_keywords = []
        if self.tech_areas is None:
            self.tech_areas = []
        if self.sources is None:
            self.sources = []

@dataclass
class AlertNotification:
    """Configuration des notifications"""
    email_recipients: List[str] = None
    webhook_url: Optional[str] = None
    throttle_minutes: int = 60

    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []

@dataclass
class PersonalizedAlert:
    """Alerte personnalisée"""
    id: str
    name: str
    description: str
    criteria: AlertCriteria
    notifications: AlertNotification
    priority: AlertPriority
    status: AlertStatus
    created_at: datetime
    updated_at: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

@dataclass
class AlertMatch:
    """Correspondance trouvée"""
    alert_id: str
    content: str
    source: str
    match_score: float
    matched_keywords: List[str]
    tech_area: str
    impact_level: int
    timestamp: datetime

@dataclass
class AlertTrigger:
    """Déclenchement d'alerte"""
    alert: PersonalizedAlert
    matches: List[AlertMatch]
    trigger_timestamp: datetime
    notification_sent: bool = False

class AlertsManager:
    """Gestionnaire d'alertes personnalisées"""
    
    def __init__(self):
        self.settings = get_settings()
        self.mcp_client: Optional[MCPCrawl4AIClient] = None
        
        # Stockage des alertes
        self.alerts: Dict[str, PersonalizedAlert] = {}
        self.alert_history: List[AlertTrigger] = []
        
        # Configuration des aires technologiques
        self.tech_areas_keywords = {
            "AI/ML": ["intelligence artificielle", "machine learning", "ia", "ml", "gpt"],
            "Cloud": ["cloud", "aws", "azure", "kubernetes", "docker"],
            "Security": ["sécurité", "cybersecurity", "vulnerability", "breach"],
            "Frontend": ["react", "vue", "angular", "javascript", "typescript"],
            "Backend": ["api", "database", "server", "microservices", "python"],
            "DevOps": ["ci/cd", "deployment", "infrastructure", "monitoring"],
            "Mobile": ["ios", "android", "react native", "flutter", "mobile"],
            "Blockchain": ["blockchain", "cryptocurrency", "bitcoin", "ethereum"],
            "Data": ["big data", "analytics", "data science", "etl"]
        }
    
    async def initialize(self):
        """Initialise le gestionnaire"""
        try:
            self.mcp_client = MCPCrawl4AIClient()
            await self.mcp_client.connect()
            logger.info("AlertsManager initialisé")
        except Exception as e:
            logger.error("Erreur initialisation AlertsManager", error=str(e))
            raise
    
    def create_alert(
        self,
        name: str,
        description: str,
        criteria: AlertCriteria,
        notifications: AlertNotification,
        priority: AlertPriority = AlertPriority.MEDIUM
    ) -> PersonalizedAlert:
        """Crée une nouvelle alerte"""
        
        alert_id = f"alert_{int(time.time() * 1000)}"
        
        alert = PersonalizedAlert(
            id=alert_id,
            name=name,
            description=description,
            criteria=criteria,
            notifications=notifications,
            priority=priority,
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.alerts[alert_id] = alert
        
        logger.info(
            "Alerte créée",
            alert_id=alert_id,
            name=name,
            keywords=len(criteria.keywords)
        )
        
        return alert
    
    def update_alert(self, alert_id: str, **updates) -> Optional[PersonalizedAlert]:
        """Met à jour une alerte"""
        if alert_id not in self.alerts:
            return None
        
        alert = self.alerts[alert_id]
        
        for key, value in updates.items():
            if hasattr(alert, key):
                setattr(alert, key, value)
        
        alert.updated_at = datetime.now()
        logger.info("Alerte mise à jour", alert_id=alert_id)
        return alert
    
    def delete_alert(self, alert_id: str) -> bool:
        """Supprime une alerte"""
        if alert_id not in self.alerts:
            return False
        
        del self.alerts[alert_id]
        logger.info("Alerte supprimée", alert_id=alert_id)
        return True
    
    def get_alert(self, alert_id: str) -> Optional[PersonalizedAlert]:
        """Récupère une alerte"""
        return self.alerts.get(alert_id)
    
    def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        priority: Optional[AlertPriority] = None
    ) -> List[PersonalizedAlert]:
        """Liste les alertes avec filtres"""
        alerts = list(self.alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    async def check_alerts(self) -> List[AlertTrigger]:
        """Vérifie toutes les alertes actives"""
        if not self.mcp_client:
            return []
        
        active_alerts = [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]
        if not active_alerts:
            return []
        
        logger.info(f"Vérification de {len(active_alerts)} alertes")
        
        triggers = []
        
        for alert in active_alerts:
            try:
                trigger = await self._check_single_alert(alert)
                if trigger:
                    triggers.append(trigger)
                    alert.last_triggered = datetime.now()
                    alert.trigger_count += 1
                    await self._send_notifications(trigger)
            except Exception as e:
                logger.warning(f"Erreur alerte {alert.id}", error=str(e))
        
        self.alert_history.extend(triggers)
        
        if triggers:
            logger.info(f"{len(triggers)} alertes déclenchées")
        
        return triggers
    
    async def _check_single_alert(self, alert: PersonalizedAlert) -> Optional[AlertTrigger]:
        """Vérifie une alerte spécifique"""
        # Vérification du throttling
        if self._is_throttled(alert):
            return None
        
        # Construction de la requête
        query = self._build_search_query(alert.criteria)
        
        # Recherche MCP
        rag_request = RAGQueryRequest(query=query, match_count=5)
        response = await self.mcp_client.perform_rag_query(rag_request)
        
        if not response.success or not response.data:
            return None
        
        results = response.data.get("results", [])
        if not results:
            return None
        
        # Analyse des résultats
        matches = []
        for result in results:
            match = self._analyze_result(alert, result)
            if match and match.match_score >= 0.4:
                matches.append(match)
        
        if not matches:
            return None
        
        return AlertTrigger(
            alert=alert,
            matches=matches,
            trigger_timestamp=datetime.now()
        )
    
    def _build_search_query(self, criteria: AlertCriteria) -> str:
        """Construit une requête de recherche"""
        query_parts = []
        
        # Mots-clés obligatoires
        if criteria.keywords:
            keywords_query = " OR ".join(criteria.keywords)
            query_parts.append(keywords_query)
        
        # Aires technologiques
        if criteria.tech_areas:
            tech_keywords = []
            for area in criteria.tech_areas:
                if area in self.tech_areas_keywords:
                    tech_keywords.extend(self.tech_areas_keywords[area])
            
            if tech_keywords:
                tech_query = " OR ".join(tech_keywords)
                query_parts.append(tech_query)
        
        return " ".join(query_parts) if query_parts else " ".join(criteria.keywords)
    
    def _analyze_result(self, alert: PersonalizedAlert, result: Dict[str, Any]) -> Optional[AlertMatch]:
        """Analyse un résultat"""
        content = result.get("content", "").lower()
        source = result.get("source", "")
        
        if not content:
            return None
        
        criteria = alert.criteria
        
        # Vérification des mots exclus
        for excluded in criteria.excluded_keywords:
            if excluded.lower() in content:
                return None
        
        # Vérification des sources
        if criteria.sources:
            if not any(src.lower() in source.lower() for src in criteria.sources):
                return None
        
        # Calcul du score
        score = 0.0
        matched_keywords = []
        
        # Score mots-clés obligatoires
        for keyword in criteria.keywords:
            if keyword.lower() in content:
                matched_keywords.append(keyword)
                score += 0.4
        
        # Détection aire tech
        tech_area = self._detect_tech_area(content)
        
        # Bonus aire tech
        if criteria.tech_areas and tech_area in criteria.tech_areas:
            score += 0.3
        
        # Calcul impact
        impact_level = self._calculate_impact_level(content, matched_keywords)
        
        # Vérification impact minimum
        if impact_level < criteria.min_impact_level:
            score *= 0.5
        
        score = min(score, 1.0)
        
        if score < 0.3:
            return None
        
        return AlertMatch(
            alert_id=alert.id,
            content=content[:300],
            source=source,
            match_score=score,
            matched_keywords=matched_keywords,
            tech_area=tech_area,
            impact_level=impact_level,
            timestamp=datetime.now()
        )
    
    def _detect_tech_area(self, content: str) -> str:
        """Détecte l'aire technologique"""
        content_lower = content.lower()
        
        for area, keywords in self.tech_areas_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return area
        
        return "General"
    
    def _calculate_impact_level(self, content: str, matched_keywords: List[str]) -> int:
        """Calcule le niveau d'impact (1-5)"""
        content_lower = content.lower()
        
        high_impact = ["critique", "breaking", "urgent", "révolutionnaire"]
        medium_impact = ["important", "significatif", "nouveau"]
        
        score = 0
        
        for word in high_impact:
            if word in content_lower:
                score += 2
        
        for word in medium_impact:
            if word in content_lower:
                score += 1
        
        score += len(matched_keywords)
        
        if score >= 6:
            return 5
        elif score >= 4:
            return 4
        elif score >= 3:
            return 3
        elif score >= 2:
            return 2
        else:
            return 1
    
    def _is_throttled(self, alert: PersonalizedAlert) -> bool:
        """Vérifie le throttling"""
        if not alert.last_triggered:
            return False
        
        throttle_delta = timedelta(minutes=alert.notifications.throttle_minutes)
        return datetime.now() - alert.last_triggered < throttle_delta
    
    async def _send_notifications(self, trigger: AlertTrigger):
        """Envoie les notifications"""
        try:
            # Log de notification (implémentation simple)
            logger.info(
                "Notification alerte",
                alert_name=trigger.alert.name,
                matches=len(trigger.matches),
                priority=trigger.alert.priority.value
            )
            
            trigger.notification_sent = True
            
        except Exception as e:
            logger.error("Erreur notification", error=str(e))
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Statistiques des alertes"""
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE])
        
        priority_stats = {p.value: 0 for p in AlertPriority}
        for alert in self.alerts.values():
            priority_stats[alert.priority.value] += 1
        
        recent_triggers = [
            t for t in self.alert_history 
            if t.trigger_timestamp >= datetime.now() - timedelta(days=1)
        ]
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "priority_distribution": priority_stats,
            "recent_triggers_24h": len(recent_triggers)
        }
    
    async def cleanup(self):
        """Nettoie les ressources"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
        logger.info("AlertsManager nettoyé")

# Instance globale
_alerts_manager: Optional[AlertsManager] = None

async def get_alerts_manager() -> AlertsManager:
    """Récupère l'instance globale"""
    global _alerts_manager
    
    if _alerts_manager is None:
        _alerts_manager = AlertsManager()
        await _alerts_manager.initialize()
    
    return _alerts_manager 