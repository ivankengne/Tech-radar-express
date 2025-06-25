"""
Tech Radar Express - Routes API MCP crawl4ai-rag
Exposition des 8 outils MCP via l'API REST FastAPI
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import structlog
import asyncio
import json

from core.mcp_client import (
    MCPCrawl4AIClient, 
    get_mcp_client,
    CrawlRequest,
    RAGQueryRequest, 
    CodeSearchRequest,
    KnowledgeGraphQuery,
    GitHubParseRequest,
    MCPResponse
)
from core.config_manager import get_settings

# Configuration du logger
logger = structlog.get_logger(__name__)

# Router principal pour les routes MCP
router = APIRouter(
    prefix="/api/v1/mcp",
    tags=["MCP crawl4ai-rag"],
    responses={
        404: {"description": "Outil MCP non trouvé"},
        500: {"description": "Erreur serveur MCP"},
        503: {"description": "Service MCP indisponible"}
    }
)

# ===================================
# MODÈLES DE RÉPONSE
# ===================================

class MCPHealthResponse(BaseModel):
    """Réponse de santé du serveur MCP"""
    status: str = Field(description="Statut du serveur (healthy/unhealthy/error)")
    connected: bool = Field(description="État de la connexion")
    server_status: str = Field(description="Code de statut du serveur")
    stats: Dict[str, Any] = Field(description="Statistiques d'utilisation")
    base_url: str = Field(description="URL du serveur MCP")
    transport: str = Field(description="Type de transport utilisé")

class MCPStatisticsResponse(BaseModel):
    """Statistiques détaillées du client MCP"""
    total_requests: int = Field(description="Nombre total de requêtes")
    successful_requests: int = Field(description="Nombre de requêtes réussies")
    failed_requests: int = Field(description="Nombre de requêtes échouées")
    avg_response_time: float = Field(description="Temps de réponse moyen")
    success_rate: str = Field(description="Taux de succès en pourcentage")
    connection_status: str = Field(description="Statut de connexion")
    transport_type: str = Field(description="Type de transport")

class CrawlResult(BaseModel):
    """Résultat de crawling"""
    success: bool = Field(description="Succès de l'opération")
    data: Optional[Dict[str, Any]] = Field(description="Données extraites")
    error: Optional[str] = Field(description="Message d'erreur si échec")
    metadata: Optional[Dict[str, Any]] = Field(description="Métadonnées de l'opération")
    execution_time: float = Field(description="Temps d'exécution en secondes")

class RAGResult(BaseModel):
    """Résultat de recherche RAG"""
    success: bool = Field(description="Succès de la recherche")
    results: Optional[List[Dict[str, Any]]] = Field(description="Résultats de recherche")
    query: str = Field(description="Requête originale")
    match_count: int = Field(description="Nombre de résultats retournés")
    execution_time: float = Field(description="Temps d'exécution en secondes")
    error: Optional[str] = Field(description="Message d'erreur si échec")

class SourcesResult(BaseModel):
    """Liste des sources disponibles"""
    success: bool = Field(description="Succès de l'opération")
    sources: Optional[List[Dict[str, Any]]] = Field(description="Liste des sources")
    total_sources: int = Field(description="Nombre total de sources")
    execution_time: float = Field(description="Temps d'exécution en secondes")

# ===================================
# ENDPOINT SANTÉ ET MONITORING
# ===================================

@router.get(
    "/health",
    response_model=MCPHealthResponse,
    summary="Vérifier la santé du serveur MCP",
    description="Retourne l'état de santé du serveur MCP crawl4ai-rag et les statistiques de connexion"
)
async def get_mcp_health(
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> MCPHealthResponse:
    """Endpoint de santé pour le serveur MCP"""
    try:
        health_data = await mcp_client.get_health_status()
        return MCPHealthResponse(**health_data)
    except Exception as e:
        logger.error("Erreur lors de la vérification de santé MCP", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service MCP indisponible: {str(e)}"
        )

@router.get(
    "/statistics",
    response_model=MCPStatisticsResponse,
    summary="Obtenir les statistiques d'utilisation MCP",
    description="Retourne les statistiques détaillées d'utilisation du client MCP"
)
async def get_mcp_statistics(
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> MCPStatisticsResponse:
    """Endpoint pour les statistiques du client MCP"""
    try:
        stats_data = await mcp_client.get_statistics()
        return MCPStatisticsResponse(**stats_data)
    except Exception as e:
        logger.error("Erreur lors de la récupération des statistiques MCP", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )

@router.post(
    "/statistics/reset",
    summary="Remettre à zéro les statistiques",
    description="Remet à zéro toutes les statistiques du client MCP"
)
async def reset_mcp_statistics(
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
):
    """Reset des statistiques MCP"""
    try:
        await mcp_client.reset_statistics()
        return {"status": "success", "message": "Statistiques remises à zéro"}
    except Exception as e:
        logger.error("Erreur lors du reset des statistiques MCP", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du reset: {str(e)}"
        )

# ===================================
# OUTILS DE CRAWLING
# ===================================

@router.post(
    "/crawl/smart",
    response_model=CrawlResult,
    summary="Crawling intelligent d'URL",
    description="""
    Effectue un crawling intelligent avec détection automatique du type d'URL.
    Supporte:
    - Sitemaps XML (crawl de toutes les URLs)
    - Fichiers texte (extraction directe du contenu)
    - Pages web (crawl récursif avec profondeur configurable)
    """
)
async def smart_crawl_url(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> CrawlResult:
    """Endpoint pour le crawling intelligent d'URLs"""
    try:
        logger.info(
            "Début crawling intelligent",
            url=request.url,
            max_depth=request.max_depth,
            chunk_size=request.chunk_size
        )
        
        result = await mcp_client.smart_crawl_url(request)
        
        # Log du résultat
        if result.success:
            logger.info(
                "Crawling intelligent réussi",
                url=request.url,
                execution_time=result.execution_time
            )
        else:
            logger.error(
                "Échec crawling intelligent",
                url=request.url,
                error=result.error
            )
        
        return CrawlResult(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error("Erreur crawling intelligent", url=request.url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du crawling: {str(e)}"
        )

class SinglePageRequest(BaseModel):
    """Requête pour le crawl d'une page unique"""
    url: str = Field(..., description="URL de la page à crawler")

@router.post(
    "/crawl/single",
    response_model=CrawlResult,
    summary="Crawl d'une page unique",
    description="Effectue le crawl d'une page unique sans suivre les liens"
)
async def crawl_single_page(
    request: SinglePageRequest,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> CrawlResult:
    """Endpoint pour le crawl d'une page unique"""
    try:
        logger.info("Début crawl page unique", url=request.url)
        
        result = await mcp_client.crawl_single_page(request.url)
        
        return CrawlResult(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error("Erreur crawl page unique", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du crawl: {str(e)}"
        )

# ===================================
# GESTION DES SOURCES
# ===================================

@router.get(
    "/sources",
    response_model=SourcesResult,
    summary="Lister les sources disponibles",
    description="Retourne la liste de toutes les sources crawlées disponibles dans la base de données"
)
async def get_available_sources(
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> SourcesResult:
    """Endpoint pour lister les sources disponibles"""
    try:
        logger.info("Récupération des sources disponibles")
        
        result = await mcp_client.get_available_sources()
        
        if result.success and result.data:
            sources = result.data.get("sources", [])
            total_sources = len(sources)
        else:
            sources = []
            total_sources = 0
        
        return SourcesResult(
            success=result.success,
            sources=sources,
            total_sources=total_sources,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error("Erreur récupération sources", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des sources: {str(e)}"
        )

# ===================================
# RECHERCHE ET RAG
# ===================================

@router.post(
    "/search/rag",
    response_model=RAGResult,
    summary="Recherche RAG vectorielle",
    description="""
    Effectue une recherche RAG (Retrieval Augmented Generation) avec:
    - Recherche vectorielle dans les embeddings
    - Recherche par mots-clés
    - Reranking des résultats
    - Filtrage optionnel par source
    """
)
async def perform_rag_query(
    request: RAGQueryRequest,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> RAGResult:
    """Endpoint pour la recherche RAG"""
    try:
        logger.info(
            "Début recherche RAG",
            query=request.query[:100],  # Tronquer pour les logs
            source=request.source,
            match_count=request.match_count
        )
        
        result = await mcp_client.perform_rag_query(request)
        
        if result.success and result.data:
            results = result.data.get("results", [])
            match_count = len(results)
        else:
            results = []
            match_count = 0
        
        return RAGResult(
            success=result.success,
            results=results,
            query=request.query,
            match_count=match_count,
            execution_time=result.execution_time,
            error=result.error
        )
        
    except Exception as e:
        logger.error("Erreur recherche RAG", query=request.query[:50], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche RAG: {str(e)}"
        )

@router.post(
    "/search/code",
    response_model=RAGResult,
    summary="Recherche d'exemples de code",
    description="Recherche d'exemples de code pertinents avec filtrage optionnel par source"
)
async def search_code_examples(
    request: CodeSearchRequest,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> RAGResult:
    """Endpoint pour la recherche d'exemples de code"""
    try:
        logger.info(
            "Début recherche code",
            query=request.query[:100],
            source_id=request.source_id,
            match_count=request.match_count
        )
        
        result = await mcp_client.search_code_examples(request)
        
        if result.success and result.data:
            results = result.data.get("results", [])
            match_count = len(results)
        else:
            results = []
            match_count = 0
        
        return RAGResult(
            success=result.success,
            results=results,
            query=request.query,
            match_count=match_count,
            execution_time=result.execution_time,
            error=result.error
        )
        
    except Exception as e:
        logger.error("Erreur recherche code", query=request.query[:50], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche de code: {str(e)}"
        )

# ===================================
# KNOWLEDGE GRAPH
# ===================================

@router.post(
    "/knowledge-graph/query",
    summary="Requête sur le knowledge graph",
    description="""
    Effectue des requêtes sur le knowledge graph Neo4j.
    Commandes supportées:
    - `repos` : Lister les repositories
    - `classes` : Lister les classes
    - `method <name>` : Rechercher une méthode
    - `explore <repo>` : Explorer un repository
    - `query <cypher>` : Requête Cypher personnalisée
    """
)
async def query_knowledge_graph(
    request: KnowledgeGraphQuery,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
):
    """Endpoint pour les requêtes knowledge graph"""
    try:
        logger.info("Début requête knowledge graph", command=request.command[:100])
        
        result = await mcp_client.query_knowledge_graph(request)
        
        return {
            "success": result.success,
            "data": result.data,
            "command": request.command,
            "execution_time": result.execution_time,
            "error": result.error
        }
        
    except Exception as e:
        logger.error("Erreur requête knowledge graph", command=request.command[:50], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la requête knowledge graph: {str(e)}"
        )

@router.post(
    "/knowledge-graph/parse-repo",
    summary="Parser un repository GitHub",
    description="""
    Parse un repository GitHub et stocke sa structure dans le knowledge graph Neo4j.
    Analyse:
    - Classes et leurs méthodes
    - Fonctions globales
    - Imports et dépendances
    - Structure des modules
    """
)
async def parse_github_repository(
    request: GitHubParseRequest,
    background_tasks: BackgroundTasks,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
):
    """Endpoint pour parser un repository GitHub"""
    try:
        logger.info("Début parsing repository GitHub", repo_url=request.repo_url)
        
        # Execution en arrière-plan pour les gros repos
        result = await mcp_client.parse_github_repository(request)
        
        return {
            "success": result.success,
            "data": result.data,
            "repo_url": request.repo_url,
            "execution_time": result.execution_time,
            "error": result.error
        }
        
    except Exception as e:
        logger.error("Erreur parsing repository", repo_url=request.repo_url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du parsing: {str(e)}"
        )

# ===================================
# VÉRIFICATION HALLUCINATIONS IA
# ===================================

class HallucinationCheckRequest(BaseModel):
    """Requête pour la vérification des hallucinations"""
    script_path: str = Field(..., description="Chemin vers le script Python à vérifier")

@router.post(
    "/ai/check-hallucinations",
    summary="Vérifier les hallucinations dans un script IA",
    description="""
    Vérifie un script Python généré par IA contre le knowledge graph pour détecter:
    - Imports inexistants
    - Méthodes hallucinées
    - Paramètres incorrects
    - Classes inexistantes
    """
)
async def check_ai_script_hallucinations(
    request: HallucinationCheckRequest,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
):
    """Endpoint pour vérifier les hallucinations IA"""
    try:
        logger.info("Début vérification hallucinations", script_path=request.script_path)
        
        result = await mcp_client.check_ai_script_hallucinations(request.script_path)
        
        return {
            "success": result.success,
            "data": result.data,
            "script_path": script_path,
            "execution_time": result.execution_time,
            "error": result.error
        }
        
    except Exception as e:
        logger.error("Erreur vérification hallucinations", script_path=script_path, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )