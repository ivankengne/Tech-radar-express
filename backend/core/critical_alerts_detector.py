"""
Tech Radar Express - Détecteur d'Alertes Critiques via LLM
Analyse automatique du contenu MCP pour détecter les alertes critiques
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import structlog
import re

from .config_manager import get_settings
from .mcp_client import MCPCrawl4AIClient, RAGQueryRequest
from .llm_provider_manager import get_llm_provider_manager
from .llm_tracer import trace_llm

logger = structlog.get_logger(__name__)

class CriticalityLevel(str, Enum):
    """Niveaux de criticité"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertCategory(str, Enum):
    """Catégories d'alertes"""
    SECURITY = "security"
    OUTAGE = "outage"
    DATA_BREACH = "data_breach"
    VULNERABILITY = "vulnerability"
    REGULATORY = "regulatory"
    MARKET = "market"

@dataclass
class CriticalAnalysis:
    """Résultat d'analyse de criticité"""
    content_id: str
    source: str
    content: str
    criticality_level: CriticalityLevel
    confidence_score: float
    categories: List[AlertCategory]
    key_factors: List[str]
    impact_assessment: str
    recommended_actions: List[str]
    time_sensitivity: str
    llm_reasoning: str
    analyzed_at: datetime

@dataclass
class CriticalAlert:
    """Alerte critique générée"""
    id: str
    analysis: CriticalAnalysis
    priority_score: float
    created_at: datetime
    notification_sent: bool = False
    false_positive: bool = False

class CriticalAlertsDetector:
    """Détecteur d'alertes critiques avec analyse LLM"""
    
    def __init__(self):
        self.settings = get_settings()
        self.mcp_client: Optional[MCPCrawl4AIClient] = None
        self.llm_manager = None
        
        # Stockage des alertes
        self.critical_alerts: Dict[str, CriticalAlert] = {}
        self.analysis_history: List[CriticalAnalysis] = []
        
        # Configuration
        self.criticality_threshold = 0.7
        self.max_content_length = 1500
        
        # Prompt d'analyse
        self.analysis_prompt = """
Tu es un expert en cybersécurité et analyse de risques. Analyse ce contenu pour détecter s'il représente une situation critique.

CONTENU:
{content}

SOURCE: {source}

Réponds au format JSON exact:
{{
    "criticality_level": "low|medium|high|critical|emergency",
    "confidence_score": 0.85,
    "categories": ["security", "vulnerability"],
    "key_factors": ["Vulnérabilité zero-day", "Impact massif"],
    "impact_assessment": "Description de l'impact",
    "recommended_actions": ["Action 1", "Action 2"],
    "time_sensitivity": "Immédiat|24h|Semaine",
    "reasoning": "Explication du raisonnement"
}}

NIVEAUX:
- EMERGENCY: Menace immédiate, exploitation active
- CRITICAL: Vulnérabilité majeure, panne critique
- HIGH: Risque élevé, faille importante
- MEDIUM: Tendance préoccupante
- LOW: Information générale

CATÉGORIES:
- security: Sécurité/cybersécurité
- outage: Panne de service
- data_breach: Fuite de données
- vulnerability: Vulnérabilité
- regulatory: Changement réglementaire
- market: Disruption marché

Sois factuel et précis.
"""
    
    async def initialize(self):
        """Initialise le détecteur"""
        try:
            self.mcp_client = MCPCrawl4AIClient()
            await self.mcp_client.connect()
            
            self.llm_manager = await get_llm_provider_manager()
            
            logger.info("CriticalAlertsDetector initialisé")
        except Exception as e:
            logger.error("Erreur initialisation", error=str(e))
            raise
    
    async def analyze_recent_content(self, hours_back: int = 1) -> List[CriticalAlert]:
        """Analyse le contenu récent"""
        if not self.mcp_client or not self.llm_manager:
            return []
        
        try:
            logger.info(f"Analyse contenu {hours_back}h")
            
            # Recherche de contenu critique
            search_queries = [
                "vulnerability security breach critical",
                "emergency outage down failure",
                "data leak privacy violation",
                "breaking urgent crisis"
            ]
            
            all_content = []
            for query in search_queries:
                try:
                    rag_request = RAGQueryRequest(query=query, match_count=3)
                    response = await self.mcp_client.perform_rag_query(rag_request)
                    
                    if response.success and response.data:
                        results = response.data.get("results", [])
                        all_content.extend(results)
                except Exception as e:
                    logger.warning(f"Erreur requête: {query}", error=str(e))
            
            if not all_content:
                return []
            
            # Déduplication
            unique_content = {}
            for item in all_content:
                content_hash = hash(item.get("content", "")[:100])
                unique_content[content_hash] = item
            
            logger.info(f"Analyse {len(unique_content)} contenus")
            
            # Analyse parallèle limitée
            analyses = []
            for content_item in list(unique_content.values())[:5]:  # Limite à 5
                analysis = await self._analyze_content(content_item)
                if analysis:
                    analyses.append(analysis)
                await asyncio.sleep(1)  # Pause entre analyses
            
            # Génération d'alertes
            critical_alerts = []
            for analysis in analyses:
                if self._is_critical(analysis):
                    alert = self._create_alert(analysis)
                    critical_alerts.append(alert)
                    self.critical_alerts[alert.id] = alert
            
            self.analysis_history.extend(analyses)
            
            logger.info(
                "Analyse terminée",
                analyzed=len(analyses),
                critical=len(critical_alerts)
            )
            
            return critical_alerts
            
        except Exception as e:
            logger.error("Erreur analyse", error=str(e))
            return []
    
    async def _analyze_content(self, content_item: Dict[str, Any]) -> Optional[CriticalAnalysis]:
        """Analyse un contenu via LLM"""
        try:
            content = content_item.get("content", "")
            source = content_item.get("source", "unknown")
            
            # Limitation de taille
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "..."
            
            # Filtrage rapide
            if not self._contains_critical_keywords(content):
                return None
            
            # Prompt LLM
            prompt = self.analysis_prompt.format(
                content=content,
                source=source
            )
            
            # Appel LLM
            @trace_llm(operation="critical_analysis")
            async def analyze():
                return await self.llm_manager.generate_response(
                    prompt=prompt,
                    temperature=0.1,
                    max_tokens=800
                )
            
            response = await analyze()
            
            # Parsing JSON
            try:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if not json_match:
                    return None
                
                result = json.loads(json_match.group(0))
                
                analysis = CriticalAnalysis(
                    content_id=f"content_{hash(content)}"[:12],
                    source=source,
                    content=content[:500],  # Stockage limité
                    criticality_level=CriticalityLevel(result.get("criticality_level", "low")),
                    confidence_score=float(result.get("confidence_score", 0.0)),
                    categories=[AlertCategory(cat) for cat in result.get("categories", []) 
                              if cat in [c.value for c in AlertCategory]],
                    key_factors=result.get("key_factors", []),
                    impact_assessment=result.get("impact_assessment", ""),
                    recommended_actions=result.get("recommended_actions", []),
                    time_sensitivity=result.get("time_sensitivity", ""),
                    llm_reasoning=result.get("reasoning", ""),
                    analyzed_at=datetime.now()
                )
                
                return analysis
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Erreur parsing LLM", error=str(e))
                return None
                
        except Exception as e:
            logger.error("Erreur analyse contenu", error=str(e))
            return None
    
    def _contains_critical_keywords(self, content: str) -> bool:
        """Vérifie si le contenu contient des mots-clés critiques"""
        keywords = [
            "critical", "urgent", "emergency", "breach", "vulnerability",
            "exploit", "zero-day", "ransomware", "outage", "down",
            "leak", "compromised", "attack", "threat", "crisis"
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in keywords)
    
    def _is_critical(self, analysis: CriticalAnalysis) -> bool:
        """Détermine si l'analyse justifie une alerte"""
        if analysis.confidence_score < self.criticality_threshold:
            return False
        
        critical_levels = {CriticalityLevel.HIGH, CriticalityLevel.CRITICAL, CriticalityLevel.EMERGENCY}
        return analysis.criticality_level in critical_levels
    
    def _create_alert(self, analysis: CriticalAnalysis) -> CriticalAlert:
        """Crée une alerte critique"""
        # Calcul du score de priorité
        priority_score = analysis.confidence_score
        
        # Bonus selon criticité
        if analysis.criticality_level == CriticalityLevel.EMERGENCY:
            priority_score += 0.3
        elif analysis.criticality_level == CriticalityLevel.CRITICAL:
            priority_score += 0.2
        elif analysis.criticality_level == CriticalityLevel.HIGH:
            priority_score += 0.1
        
        priority_score = min(1.0, priority_score)
        
        return CriticalAlert(
            id=f"critical_{int(time.time() * 1000)}",
            analysis=analysis,
            priority_score=priority_score,
            created_at=datetime.now()
        )
    
    def get_active_alerts(self, max_age_hours: int = 24) -> List[CriticalAlert]:
        """Récupère les alertes actives"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        active = [
            alert for alert in self.critical_alerts.values()
            if alert.created_at > cutoff and not alert.false_positive
        ]
        
        return sorted(active, key=lambda a: a.priority_score, reverse=True)
    
    def mark_false_positive(self, alert_id: str) -> bool:
        """Marque comme faux positif"""
        if alert_id in self.critical_alerts:
            self.critical_alerts[alert_id].false_positive = True
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques de détection"""
        total = len(self.critical_alerts)
        false_positives = len([a for a in self.critical_alerts.values() if a.false_positive])
        
        categories_count = {}
        for alert in self.critical_alerts.values():
            for cat in alert.analysis.categories:
                categories_count[cat.value] = categories_count.get(cat.value, 0) + 1
        
        return {
            "total_alerts": total,
            "false_positives": false_positives,
            "accuracy_rate": (total - false_positives) / total if total > 0 else 1.0,
            "categories_distribution": categories_count,
            "last_analysis": max([a.analyzed_at for a in self.analysis_history]) if self.analysis_history else None
        }
    
    async def cleanup(self):
        """Nettoie les ressources"""
        if self.mcp_client:
            await self.mcp_client.disconnect()

# Instance globale
_detector: Optional[CriticalAlertsDetector] = None

async def get_critical_alerts_detector() -> CriticalAlertsDetector:
    """Récupère l'instance globale"""
    global _detector
    
    if _detector is None:
        _detector = CriticalAlertsDetector()
        await _detector.initialize()
    
    return _detector 