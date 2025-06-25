"""
Tech Radar Express - Générateur Mode Focus
Synthèse ultra-rapide structurée en 2 minutes maximum
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import structlog

from .config_manager import get_settings
from .mcp_client import MCPCrawl4AIClient, RAGQueryRequest

logger = structlog.get_logger(__name__)

class FocusMode(str, Enum):
    """Types de mode focus disponibles"""
    QUICK_SCAN = "quick_scan"          # Scan rapide (30s)
    TECH_PULSE = "tech_pulse"          # Pouls tech (60s) 
    CRITICAL_ALERTS = "critical_alerts" # Alertes critiques (45s)
    INNOVATION_RADAR = "innovation_radar" # Radar innovations (90s)

@dataclass
class FocusInsight:
    """Insight condensé pour le mode focus"""
    title: str
    summary: str
    impact_level: int  # 1-5
    tech_area: str
    keywords: List[str]

@dataclass
class FocusSynthesis:
    """Synthèse complète du mode focus"""
    mode: FocusMode
    insights: List[FocusInsight]
    key_trends: List[str]
    critical_alerts: List[str]
    innovation_highlights: List[str]
    generation_time: float
    sources_analyzed: int
    confidence_score: float
    timestamp: datetime

class FocusModeGenerator:
    """Générateur de synthèses rapides et structurées"""
    
    def __init__(self):
        self.settings = get_settings()
        self.mcp_client: Optional[MCPCrawl4AIClient] = None
        
        # Configuration optimisée par mode
        self.focus_configs = {
            FocusMode.QUICK_SCAN: {
                "max_sources": 5,
                "max_insights": 3,
                "target_time": 30,
                "keywords": ["breaking", "nouveau", "tendance"],
                "areas": ["AI/ML", "Cloud", "Security"]
            },
            FocusMode.TECH_PULSE: {
                "max_sources": 8,
                "max_insights": 5,
                "target_time": 60,
                "keywords": ["adoption", "innovation", "performance"],
                "areas": ["Frontend", "Backend", "DevOps", "Mobile"]
            },
            FocusMode.CRITICAL_ALERTS: {
                "max_sources": 6,
                "max_insights": 4,
                "target_time": 45,
                "keywords": ["critique", "sécurité", "urgent", "breaking"],
                "areas": ["Security", "Infrastructure"]
            },
            FocusMode.INNOVATION_RADAR: {
                "max_sources": 10,
                "max_insights": 6,
                "target_time": 90,
                "keywords": ["innovation", "emerging", "future", "disruptive"],
                "areas": ["Emerging Tech", "AI/ML", "Blockchain", "IoT"]
            }
        }
    
    async def initialize(self):
        """Initialise le client MCP"""
        try:
            self.mcp_client = MCPCrawl4AIClient()
            await self.mcp_client.connect()
            logger.info("FocusModeGenerator initialisé")
        except Exception as e:
            logger.error("Erreur initialisation FocusModeGenerator", error=str(e))
            raise
    
    async def generate_focus_synthesis(
        self,
        mode: FocusMode = FocusMode.TECH_PULSE,
        custom_query: Optional[str] = None
    ) -> FocusSynthesis:
        """Génère une synthèse focus selon le mode sélectionné"""
        start_time = time.time()
        config = self.focus_configs[mode]
        
        try:
            logger.info(
                "Génération synthèse focus",
                mode=mode.value,
                target_time=f"{config['target_time']}s"
            )
            
            # Récupération des sources
            sources_response = await self.mcp_client.get_available_sources()
            if not sources_response.success:
                raise Exception(f"Erreur sources MCP: {sources_response.error}")
            
            total_sources = len(sources_response.data.get("sources", []))
            
            # Génération parallèle avec timeout
            timeout = config["target_time"] - 5
            tasks = [
                self._generate_insights(mode, config, custom_query),
                self._extract_trends(config),
                self._detect_alerts(config),
                self._identify_innovations(config)
            ]
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
                
                insights, trends, alerts, innovations = results
                
                # Gestion des erreurs
                insights = insights if not isinstance(insights, Exception) else []
                trends = trends if not isinstance(trends, Exception) else []
                alerts = alerts if not isinstance(alerts, Exception) else []
                innovations = innovations if not isinstance(innovations, Exception) else []
                
            except asyncio.TimeoutError:
                logger.warning("Timeout synthèse focus", mode=mode.value)
                insights, trends, alerts, innovations = [], [], [], []
            
            generation_time = time.time() - start_time
            confidence = self._calculate_confidence(
                insights, trends, alerts, innovations, 
                generation_time, config["target_time"]
            )
            
            synthesis = FocusSynthesis(
                mode=mode,
                insights=insights,
                key_trends=trends,
                critical_alerts=alerts,
                innovation_highlights=innovations,
                generation_time=generation_time,
                sources_analyzed=total_sources,
                confidence_score=confidence,
                timestamp=datetime.now()
            )
            
            logger.info(
                "Synthèse focus générée",
                mode=mode.value,
                insights=len(insights),
                time=f"{generation_time:.1f}s",
                confidence=f"{confidence:.2f}"
            )
            
            return synthesis
            
        except Exception as e:
            logger.error("Erreur génération synthèse focus", error=str(e))
            raise
    
    async def _generate_insights(
        self,
        mode: FocusMode,
        config: Dict[str, Any],
        custom_query: Optional[str] = None
    ) -> List[FocusInsight]:
        """Génère les insights principaux"""
        try:
            query = custom_query or " OR ".join(config["keywords"])
            
            rag_request = RAGQueryRequest(
                query=query,
                match_count=config["max_sources"]
            )
            
            response = await self.mcp_client.perform_rag_query(rag_request)
            
            if response.success and response.data:
                results = response.data.get("results", [])
                insights = []
                
                for result in results[:config["max_insights"]]:
                    insight = self._create_insight(result, config)
                    if insight:
                        insights.append(insight)
                
                return insights
        
        except Exception as e:
            logger.warning("Erreur génération insights", error=str(e))
        
        return []
    
    def _create_insight(self, result: Dict[str, Any], config: Dict[str, Any]) -> Optional[FocusInsight]:
        """Crée un insight à partir d'un résultat MCP"""
        try:
            content = result.get("content", "")
            
            # Titre condensé
            title = content.split('.')[0][:80] + "..." if len(content) > 80 else content.split('.')[0]
            
            # Résumé ultra-court
            summary = content[:100] + "..." if len(content) > 100 else content
            
            # Niveau d'impact
            impact = self._calculate_impact(content, config["keywords"])
            
            # Aire technologique
            tech_area = self._detect_tech_area(content, config["areas"])
            
            # Mots-clés
            keywords = [kw for kw in config["keywords"] if kw.lower() in content.lower()][:3]
            
            return FocusInsight(
                title=title,
                summary=summary,
                impact_level=impact,
                tech_area=tech_area,
                keywords=keywords
            )
            
        except Exception as e:
            logger.warning("Erreur création insight", error=str(e))
            return None
    
    async def _extract_trends(self, config: Dict[str, Any]) -> List[str]:
        """Extrait les tendances clés"""
        try:
            rag_request = RAGQueryRequest(
                query="tendances émergentes innovation adoption",
                match_count=3
            )
            
            response = await self.mcp_client.perform_rag_query(rag_request)
            
            if response.success and response.data:
                results = response.data.get("results", [])
                trends = []
                
                for result in results:
                    content = result.get("content", "")
                    sentences = content.split('.')
                    for sentence in sentences:
                        if any(word in sentence.lower() for word in ["tendance", "adoption", "croissance"]):
                            trends.append(sentence.strip()[:100] + "...")
                            break
                
                return trends[:3]
        
        except Exception as e:
            logger.warning("Erreur extraction tendances", error=str(e))
        
        return []
    
    async def _detect_alerts(self, config: Dict[str, Any]) -> List[str]:
        """Détecte les alertes critiques"""
        try:
            rag_request = RAGQueryRequest(
                query="critique urgent sécurité breaking vulnérabilité",
                match_count=3
            )
            
            response = await self.mcp_client.perform_rag_query(rag_request)
            
            if response.success and response.data:
                results = response.data.get("results", [])
                alerts = []
                
                for result in results:
                    content = result.get("content", "")
                    source = result.get("source", "")
                    
                    if any(word in content.lower() for word in ["critique", "urgent", "sécurité"]):
                        alert = f"{content[:80]}... (Source: {source})"
                        alerts.append(alert)
                
                return alerts[:2]
        
        except Exception as e:
            logger.warning("Erreur détection alertes", error=str(e))
        
        return []
    
    async def _identify_innovations(self, config: Dict[str, Any]) -> List[str]:
        """Identifie les innovations"""
        try:
            rag_request = RAGQueryRequest(
                query="innovation breakthrough nouveau révolutionnaire",
                match_count=3
            )
            
            response = await self.mcp_client.perform_rag_query(rag_request)
            
            if response.success and response.data:
                results = response.data.get("results", [])
                innovations = []
                
                for result in results:
                    content = result.get("content", "")
                    sentences = content.split('.')
                    for sentence in sentences:
                        if any(word in sentence.lower() for word in ["innovation", "nouveau", "révolutionnaire"]):
                            innovations.append(sentence.strip()[:100] + "...")
                            break
                
                return innovations[:3]
        
        except Exception as e:
            logger.warning("Erreur identification innovations", error=str(e))
        
        return []
    
    def _calculate_impact(self, content: str, keywords: List[str]) -> int:
        """Calcule le niveau d'impact (1-5)"""
        content_lower = content.lower()
        score = 0
        
        high_impact = ["critique", "breaking", "révolutionnaire", "majeur"]
        medium_impact = ["important", "significatif", "notable"]
        
        for word in high_impact:
            if word in content_lower:
                score += 2
        
        for word in medium_impact:
            if word in content_lower:
                score += 1
        
        for keyword in keywords:
            if keyword.lower() in content_lower:
                score += 1
        
        return min(max(score, 1), 5)
    
    def _detect_tech_area(self, content: str, areas: List[str]) -> str:
        """Détecte l'aire technologique"""
        content_lower = content.lower()
        
        area_keywords = {
            "AI/ML": ["intelligence artificielle", "machine learning", "ia", "ml"],
            "Cloud": ["cloud", "aws", "azure", "kubernetes"],
            "Security": ["sécurité", "cybersecurity", "vulnerability"],
            "Frontend": ["react", "vue", "angular", "javascript"],
            "Backend": ["api", "database", "server"],
            "DevOps": ["ci/cd", "deployment", "infrastructure"],
            "Mobile": ["ios", "android", "mobile"]
        }
        
        for area in areas:
            if area in area_keywords:
                keywords = area_keywords[area]
                if any(keyword in content_lower for keyword in keywords):
                    return area
        
        return areas[0] if areas else "General"
    
    def _calculate_confidence(
        self, insights, trends, alerts, innovations, 
        generation_time: float, target_time: int
    ) -> float:
        """Calcule le score de confiance"""
        completeness = 0.0
        if insights: completeness += 0.4
        if trends: completeness += 0.2
        if alerts: completeness += 0.2
        if innovations: completeness += 0.2
        
        time_score = max(0.0, 1.0 - (generation_time / target_time))
        return min((completeness * 0.7) + (time_score * 0.3), 1.0)
    
    def format_summary(self, synthesis: FocusSynthesis) -> str:
        """Formate la synthèse en texte"""
        lines = [
            f"🎯 MODE FOCUS: {synthesis.mode.value.upper()}",
            f"⏱️ {synthesis.generation_time:.1f}s | Confiance: {synthesis.confidence_score:.0%}",
            "",
            "📊 INSIGHTS CLÉS:"
        ]
        
        for i, insight in enumerate(synthesis.insights, 1):
            impact_emoji = "🔥" if insight.impact_level >= 4 else "⚡" if insight.impact_level >= 3 else "💡"
            lines.append(f"{i}. {impact_emoji} [{insight.tech_area}] {insight.title}")
        
        if synthesis.key_trends:
            lines.extend(["", "📈 TENDANCES:"] + [f"• {trend}" for trend in synthesis.key_trends])
        
        if synthesis.critical_alerts:
            lines.extend(["", "🚨 ALERTES:"] + [f"• {alert}" for alert in synthesis.critical_alerts])
        
        if synthesis.innovation_highlights:
            lines.extend(["", "🚀 INNOVATIONS:"] + [f"• {innovation}" for innovation in synthesis.innovation_highlights])
        
        return "\n".join(lines)
    
    async def cleanup(self):
        """Nettoie les ressources"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
        logger.info("FocusModeGenerator nettoyé")

# Instance globale
_focus_generator: Optional[FocusModeGenerator] = None

async def get_focus_mode_generator() -> FocusModeGenerator:
    """Récupère l'instance globale"""
    global _focus_generator
    
    if _focus_generator is None:
        _focus_generator = FocusModeGenerator()
        await _focus_generator.initialize()
    
    return _focus_generator 