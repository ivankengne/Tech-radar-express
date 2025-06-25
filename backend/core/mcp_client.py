"""
Tech Radar Express - Client MCP crawl4ai-rag
Intégration des 8 outils MCP pour le crawling et RAG avancé
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import httpx
from pydantic import BaseModel, Field
import structlog

from .config_manager import get_settings

# Configuration du logger structuré
logger = structlog.get_logger(__name__)

class MCPTransportType(str, Enum):
    """Types de transport MCP supportés"""
    SSE = "sse"
    STDIO = "stdio"
    WEBSOCKET = "websocket"

@dataclass
class MCPResponse:
    """Réponse standardisée des outils MCP"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    tool_name: str = ""
    execution_time: float = 0.0

class CrawlRequest(BaseModel):
    """Modèle pour les requêtes de crawling selon documentation MCP"""
    url: str = Field(..., description="URL à crawler")
    max_depth: int = Field(default=3, ge=1, le=5, description="Profondeur maximale de crawling récursif")
    max_concurrent: int = Field(default=10, ge=1, le=20, description="Nombre max de sessions browser parallèles")
    chunk_size: int = Field(default=5000, ge=1000, le=10000, description="Taille max des chunks en caractères")

class RAGQueryRequest(BaseModel):
    """Modèle pour les requêtes RAG selon documentation MCP"""
    query: str = Field(..., min_length=1, max_length=1000, description="Requête de recherche")
    source: Optional[str] = Field(default=None, description="Filtre par domaine source (ex: 'example.com')")
    match_count: int = Field(default=5, ge=1, le=20, description="Nombre max de résultats")

class CodeSearchRequest(BaseModel):
    """Modèle pour la recherche de code selon documentation MCP"""
    query: str = Field(..., min_length=1, max_length=500, description="Requête de recherche de code")
    source_id: Optional[str] = Field(default=None, description="Filtre par source_id (ex: 'github.com')")
    match_count: int = Field(default=5, ge=1, le=10, description="Nombre max de résultats")

class KnowledgeGraphQuery(BaseModel):
    """Modèle pour les requêtes knowledge graph selon documentation MCP"""
    command: str = Field(..., min_length=1, max_length=500, description="Commande: repos, classes, method <name>, query <cypher>")

class GitHubParseRequest(BaseModel):
    """Modèle pour parser un repository GitHub selon documentation MCP"""
    repo_url: str = Field(..., pattern=r"^https://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?$", 
                         description="URL GitHub du repository (doit finir par .git)")

class MCPCrawl4AIClient:
    """
    Client pour l'intégration MCP crawl4ai-rag avec les 8 outils
    Gestion robuste des connexions, retry et monitoring
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.transport = MCPTransportType(self.settings.MCP_TRANSPORT)
        self.base_url = f"http://{self.settings.MCP_SERVER_HOST}:{self.settings.MCP_SERVER_PORT}"
        self.session: Optional[httpx.AsyncClient] = None
        self.connected = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0
        }
        
    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()
        
    async def connect(self) -> bool:
        """Établit la connexion avec le serveur MCP"""
        try:
            # Configuration client HTTP avec retry et timeout
            timeout = httpx.Timeout(
                connect=self.settings.MCP_TIMEOUT_CONNECT,
                read=self.settings.MCP_TIMEOUT_READ,
                write=self.settings.MCP_TIMEOUT_WRITE,
                pool=self.settings.MCP_TIMEOUT_POOL
            )
            
            self.session = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100
                ),
                headers={
                    "User-Agent": "TechRadarExpress/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
            
            # Test de connexion
            response = await self.session.get("/health")
            if response.status_code == 200:
                self.connected = True
                logger.info("MCP Client connecté avec succès", server=self.base_url)
                return True
            else:
                logger.error("Échec connexion MCP", status=response.status_code)
                return False
                
        except Exception as e:
            logger.error("Erreur connexion MCP", error=str(e))
            return False
    
    async def disconnect(self):
        """Ferme la connexion MCP"""
        if self.session:
            await self.session.aclose()
            self.connected = False
            logger.info("MCP Client déconnecté")
    
    async def _execute_tool(self, tool_name: str, **kwargs) -> MCPResponse:
        """Exécute un outil MCP avec gestion d'erreurs et retry"""
        if not self.connected:
            await self.connect()
            
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.stats["total_requests"] += 1
            
            # Construction de la requête
            payload = {
                "tool": tool_name,
                "parameters": kwargs
            }
            
            # Exécution avec retry automatique
            for attempt in range(self.settings.MCP_MAX_RETRIES):
                try:
                    response = await self.session.post("/tools/execute", json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        execution_time = asyncio.get_event_loop().time() - start_time
                        
                        # Mise à jour des stats
                        self.stats["successful_requests"] += 1
                        self._update_avg_response_time(execution_time)
                        
                        logger.info(
                            "Outil MCP exécuté avec succès",
                            tool=tool_name,
                            execution_time=f"{execution_time:.2f}s",
                            attempt=attempt + 1
                        )
                        
                        return MCPResponse(
                            success=True,
                            data=result.get("data"),
                            metadata=result.get("metadata", {}),
                            tool_name=tool_name,
                            execution_time=execution_time
                        )
                    
                    elif response.status_code == 429:  # Rate limiting
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limiting, attente {wait_time}s", tool=tool_name)
                        await asyncio.sleep(wait_time)
                        continue
                        
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error("Erreur HTTP outil MCP", tool=tool_name, error=error_msg)
                        break
                        
                except httpx.TimeoutException:
                    logger.warning(f"Timeout outil MCP (tentative {attempt + 1})", tool=tool_name)
                    if attempt < self.settings.MCP_MAX_RETRIES - 1:
                        await asyncio.sleep(1)
                        continue
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Erreur outil MCP (tentative {attempt + 1})", tool=tool_name, error=str(e))
                    if attempt < self.settings.MCP_MAX_RETRIES - 1:
                        await asyncio.sleep(1)
                        continue
                    else:
                        break
            
            # Échec après tous les retry
            self.stats["failed_requests"] += 1
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return MCPResponse(
                success=False,
                error=f"Échec outil {tool_name} après {self.settings.MCP_MAX_RETRIES} tentatives",
                tool_name=tool_name,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error("Erreur critique outil MCP", tool=tool_name, error=str(e))
            
            return MCPResponse(
                success=False,
                error=f"Erreur critique: {str(e)}",
                tool_name=tool_name,
                execution_time=execution_time
            )
    
    def _update_avg_response_time(self, execution_time: float):
        """Met à jour le temps de réponse moyen"""
        if self.stats["successful_requests"] == 1:
            self.stats["avg_response_time"] = execution_time
        else:
            total_time = self.stats["avg_response_time"] * (self.stats["successful_requests"] - 1)
            self.stats["avg_response_time"] = (total_time + execution_time) / self.stats["successful_requests"]
    
    # ===================================
    # OUTIL 1: Smart Crawl URL
    # ===================================
    async def smart_crawl_url(self, request: CrawlRequest) -> MCPResponse:
        """
        Crawling intelligent avec détection automatique du type d'URL
        Supporte sitemaps, fichiers texte et pages web avec crawl récursif
        """
        return await self._execute_tool(
            "smart_crawl_url",
            url=request.url,
            max_depth=request.max_depth,
            max_concurrent=request.max_concurrent,
            chunk_size=request.chunk_size
        )
    
    # ===================================
    # OUTIL 2: Crawl Single Page  
    # ===================================
    async def crawl_single_page(self, url: str) -> MCPResponse:
        """Crawl d'une page unique sans suivre les liens"""
        return await self._execute_tool("crawl_single_page", url=url)
    
    # ===================================
    # OUTIL 3: Get Available Sources
    # ===================================
    async def get_available_sources(self) -> MCPResponse:
        """Récupère la liste des sources disponibles dans la base"""
        return await self._execute_tool("get_available_sources", random_string="fetch")
    
    # ===================================
    # OUTIL 4: Perform RAG Query
    # ===================================
    async def perform_rag_query(self, request: RAGQueryRequest) -> MCPResponse:
        """
        Effectue une recherche RAG vectorielle avec filtrage optionnel par source
        Utilise la recherche hybride (vector + keyword + reranking)
        """
        params = {
            "query": request.query,
            "match_count": request.match_count
        }
        if request.source:
            params["source"] = request.source
            
        return await self._execute_tool("perform_rag_query", **params)
    
    # ===================================
    # OUTIL 5: Search Code Examples
    # ===================================
    async def search_code_examples(self, request: CodeSearchRequest) -> MCPResponse:
        """Recherche d'exemples de code pertinents avec filtrage par source"""
        params = {
            "query": request.query,
            "match_count": request.match_count
        }
        if request.source_id:
            params["source_id"] = request.source_id
            
        return await self._execute_tool("search_code_examples", **params)
    
    # ===================================
    # OUTIL 6: Check AI Script Hallucinations
    # ===================================
    async def check_ai_script_hallucinations(self, script_path: str) -> MCPResponse:
        """
        Vérifie un script Python généré par IA contre le knowledge graph
        Détecte imports, méthodes et paramètres hallucinés
        """
        return await self._execute_tool("check_ai_script_hallucinations", script_path=script_path)
    
    # ===================================
    # OUTIL 7: Query Knowledge Graph
    # ===================================
    async def query_knowledge_graph(self, request: KnowledgeGraphQuery) -> MCPResponse:
        """
        Effectue des requêtes sur le knowledge graph Neo4j
        Supporte les commandes: repos, classes, method, explore, query
        """
        return await self._execute_tool("query_knowledge_graph", command=request.command)
    
    # ===================================
    # OUTIL 8: Parse GitHub Repository
    # ===================================
    async def parse_github_repository(self, request: GitHubParseRequest) -> MCPResponse:
        """
        Parse un repository GitHub et stocke la structure dans Neo4j
        Analyse classes, méthodes, fonctions et imports Python
        """
        return await self._execute_tool("parse_github_repository", repo_url=request.repo_url)
    
    # ===================================
    # MÉTHODES UTILITAIRES ET MONITORING
    # ===================================
    async def get_health_status(self) -> Dict[str, Any]:
        """Retourne le statut de santé du client MCP"""
        try:
            if not self.session:
                return {"status": "disconnected", "error": "No session"}
                
            response = await self.session.get("/health")
            server_healthy = response.status_code == 200
            
            return {
                "status": "healthy" if server_healthy and self.connected else "unhealthy",
                "connected": self.connected,
                "server_status": response.status_code if server_healthy else "unreachable",
                "stats": self.stats,
                "base_url": self.base_url,
                "transport": self.transport.value
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": self.connected,
                "error": str(e),
                "stats": self.stats
            }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation détaillées"""
        success_rate = 0.0
        if self.stats["total_requests"] > 0:
            success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100
            
        return {
            **self.stats,
            "success_rate": f"{success_rate:.1f}%",
            "connection_status": "connected" if self.connected else "disconnected",
            "transport_type": self.transport.value
        }
    
    async def reset_statistics(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0
        }
        logger.info("Statistiques MCP Client remises à zéro")

# Instance globale du client MCP
mcp_client = MCPCrawl4AIClient()

# Helper functions pour utilisation simplifiée
async def get_mcp_client() -> MCPCrawl4AIClient:
    """Dependency injection pour FastAPI"""
    if not mcp_client.connected:
        await mcp_client.connect()
    return mcp_client

async def execute_smart_crawl(url: str, max_depth: int = 3, chunk_size: int = 5000) -> MCPResponse:
    """Helper pour crawling intelligent"""
    async with mcp_client:
        request = CrawlRequest(url=url, max_depth=max_depth, chunk_size=chunk_size)
        return await mcp_client.smart_crawl_url(request)

async def execute_rag_search(query: str, source: str = None, match_count: int = 5) -> MCPResponse:
    """Helper pour recherche RAG"""
    async with mcp_client:
        request = RAGQueryRequest(query=query, source=source, match_count=match_count)
        return await mcp_client.perform_rag_query(request)