"""
Tech Radar Express - Générateur de Résumé Quotidien
Génération automatisée de résumés intelligents via LLM avec données MCP
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import structlog

from .config_manager import get_settings
from .mcp_client import MCPCrawl4AIClient, RAGQueryRequest

logger = structlog.get_logger(__name__)

class SummaryScope(str, Enum):
    """Portée du résumé"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

@dataclass
class SummarySection:
    """Section d'un résumé"""
    title: str
    content: str
    priority: int = 50
    source_count: int = 0

@dataclass
class DailySummary:
    """Résumé quotidien complet"""
    date: datetime
    sections: List[SummarySection]
    total_sources: int
    generation_time: float
    metadata: Dict[str, Any]

class DailySummaryGenerator:
    """Générateur de résumés quotidiens intelligents"""
    
    def __init__(self):
        self.settings = get_settings()
        self.mcp_client: Optional[MCPCrawl4AIClient] = None
        
        # Configuration par défaut
        self.tech_axes = [
            "Frontend & UX", "Backend & API", "DevOps & Infrastructure",
            "Data & AI/ML", "Mobile", "Security", "Cloud", "Emerging Tech"
        ]
        
        self.priority_keywords = [
            "breaking", "nouveau", "important", "critique", "innovation",
            "tendance", "adoption", "sécurité", "performance", "migration"
        ]
    
    async def initialize(self):
        """Initialise le client MCP"""
        try:
            self.mcp_client = MCPCrawl4AIClient()
            await self.mcp_client.connect()
            logger.info("DailySummaryGenerator initialisé")
        except Exception as e:
            logger.error("Erreur initialisation DailySummaryGenerator", error=str(e))
            raise
    
    async def generate_daily_summary(
        self,
        date: Optional[datetime] = None,
        scope: SummaryScope = SummaryScope.DAILY
    ) -> DailySummary:
        """Génère un résumé quotidien complet"""
        start_time = asyncio.get_event_loop().time()
        
        if not date:
            date = datetime.now() - timedelta(days=1)
        
        try:
            logger.info("Génération résumé quotidien", date=date.strftime("%Y-%m-%d"))
            
            # 1. Récupération des sources disponibles
            sources_response = await self.mcp_client.get_available_sources()
            if not sources_response.success:
                raise Exception(f"Erreur sources: {sources_response.error}")
            
            sources_data = sources_response.data
            total_sources = len(sources_data.get("sources", []))
            
            # 2. Génération des sections
            sections = []
            
            # Section tendances générales
            trends_section = await self._generate_trends_section(date)
            if trends_section:
                sections.append(trends_section)
            
            # Sections par axe technologique
            for axis in self.tech_axes[:4]:  # Limité à 4 axes pour le moment
                section = await self._generate_axis_section(axis, date)
                if section:
                    sections.append(section)
            
            # Section alertes
            alerts_section = await self._generate_alerts_section(date)
            if alerts_section:
                sections.append(alerts_section)
            
            # Tri par priorité
            sections.sort(key=lambda x: x.priority, reverse=True)
            
            generation_time = asyncio.get_event_loop().time() - start_time
            
            summary = DailySummary(
                date=date,
                sections=sections,
                total_sources=total_sources,
                generation_time=generation_time,
                metadata={
                    "scope": scope.value,
                    "generation_timestamp": datetime.now().isoformat(),
                    "version": "1.0"
                }
            )
            
            logger.info(
                "Résumé généré",
                sections=len(sections),
                sources=total_sources,
                time=f"{generation_time:.2f}s"
            )
            
            return summary
            
        except Exception as e:
            logger.error("Erreur génération résumé", error=str(e))
            raise
    
    async def _generate_trends_section(self, date: datetime) -> Optional[SummarySection]:
        """Génère la section tendances"""
        try:
            query = f"tendances émergentes innovation technologie {date.strftime('%Y-%m')}"
            
            rag_request = RAGQueryRequest(
                query=query,
                match_count=10
            )
            
            response = await self.mcp_client.perform_rag_query(rag_request)
            
            if response.success and response.data:
                results = response.data.get("results", [])
                
                if results:
                    # Génération d'un résumé simple basé sur les résultats
                    content = self._create_section_content(results, "tendances")
                    
                    return SummarySection(
                        title="📈 Tendances & Innovations",
                        content=content,
                        priority=90,
                        source_count=len(results)
                    )
        
        except Exception as e:
            logger.warning("Erreur section tendances", error=str(e))
        
        return None
    
    async def _generate_axis_section(self, axis: str, date: datetime) -> Optional[SummarySection]:
        """Génère une section pour un axe technologique"""
        try:
            query = f"{axis.lower()} nouveautés mise à jour innovation"
            
            rag_request = RAGQueryRequest(
                query=query,
                match_count=8
            )
            
            response = await self.mcp_client.perform_rag_query(rag_request)
            
            if response.success and response.data:
                results = response.data.get("results", [])
                
                if results:
                    content = self._create_section_content(results, axis.lower())
                    priority = self._calculate_priority(axis, results)
                    
                    return SummarySection(
                        title=f"🚀 {axis}",
                        content=content,
                        priority=priority,
                        source_count=len(results)
                    )
        
        except Exception as e:
            logger.warning(f"Erreur section {axis}", error=str(e))
        
        return None
    
    async def _generate_alerts_section(self, date: datetime) -> Optional[SummarySection]:
        """Génère la section alertes"""
        try:
            alert_keywords = " OR ".join(self.priority_keywords[:5])
            query = f"({alert_keywords}) sécurité critique urgent"
            
            rag_request = RAGQueryRequest(
                query=query,
                match_count=5
            )
            
            response = await self.mcp_client.perform_rag_query(rag_request)
            
            if response.success and response.data:
                results = response.data.get("results", [])
                
                if results:
                    content = self._create_section_content(results, "alertes")
                    
                    return SummarySection(
                        title="🚨 Alertes & Points Critiques",
                        content=content,
                        priority=100,
                        source_count=len(results)
                    )
        
        except Exception as e:
            logger.warning("Erreur section alertes", error=str(e))
        
        return None
    
    def _create_section_content(self, results: List[Dict], section_type: str) -> str:
        """Crée le contenu d'une section basé sur les résultats MCP"""
        content_parts = []
        
        # Extraction des points clés des résultats
        for i, result in enumerate(results[:5]):  # Limité à 5 résultats
            content = result.get("content", "")
            source = result.get("source", "source inconnue")
            
            # Extraction d'un extrait pertinent (première phrase ou 100 premiers caractères)
            excerpt = content[:150] + "..." if len(content) > 150 else content
            excerpt = excerpt.split('.')[0] + '.' if '.' in excerpt else excerpt
            
            content_parts.append(f"• {excerpt} *(Source: {source})*")
        
        if not content_parts:
            return f"Aucune information récente trouvée pour {section_type}."
        
        return "\n".join(content_parts)
    
    def _calculate_priority(self, axis: str, results: List[Dict]) -> int:
        """Calcule la priorité d'une section"""
        base_priority = 50
        
        # Bonus selon l'axe
        axis_priorities = {
            "Security": 15,
            "Data & AI/ML": 10,
            "Emerging Tech": 10,
            "Cloud": 8
        }
        
        axis_bonus = axis_priorities.get(axis, 5)
        
        # Bonus selon les mots-clés trouvés
        keyword_bonus = 0
        for result in results:
            content = result.get("content", "").lower()
            for keyword in self.priority_keywords:
                if keyword.lower() in content:
                    keyword_bonus += 2
                    break
        
        return min(base_priority + axis_bonus + keyword_bonus, 95)
    
    def format_as_markdown(self, summary: DailySummary) -> str:
        """Formate le résumé en Markdown"""
        lines = [
            f"# 📊 Tech Radar Express - Résumé Quotidien",
            f"**Date:** {summary.date.strftime('%d/%m/%Y')}",
            f"**Généré le:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            f"**Sources analysées:** {summary.total_sources}",
            "",
            "---",
            ""
        ]
        
        for section in summary.sections:
            lines.extend([
                f"## {section.title}",
                "",
                section.content,
                "",
                f"*{section.source_count} sources analysées*",
                ""
            ])
        
        lines.extend([
            "---",
            f"*Résumé généré en {summary.generation_time:.1f}s*"
        ])
        
        return "\n".join(lines)
    
    async def cleanup(self):
        """Nettoie les ressources"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
        logger.info("DailySummaryGenerator nettoyé")

# Instance globale
_daily_summary_generator: Optional[DailySummaryGenerator] = None

async def get_daily_summary_generator() -> DailySummaryGenerator:
    """Récupère l'instance globale du générateur"""
    global _daily_summary_generator
    
    if _daily_summary_generator is None:
        _daily_summary_generator = DailySummaryGenerator()
        await _daily_summary_generator.initialize()
    
    return _daily_summary_generator 