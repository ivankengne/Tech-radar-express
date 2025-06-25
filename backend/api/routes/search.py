"""
Tech Radar Express - Routes API Recherche Conversationnelle
Endpoints recherche RAG et interface chat avec proxy MCP crawl4ai-rag
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from sse_starlette.sse import EventSourceResponse
import structlog

from core.mcp_client import (
    MCPCrawl4AIClient,
    get_mcp_client,
    RAGQueryRequest,
    CodeSearchRequest,
    MCPResponse
)
from core.config_manager import get_settings

# Configuration du logger
logger = structlog.get_logger(__name__)

# Router principal pour les recherches
router = APIRouter(
    prefix="/api/v1/search",
    tags=["Recherche Conversationnelle"],
    responses={
        404: {"description": "Résultats non trouvés"},
        500: {"description": "Erreur serveur de recherche"},
        503: {"description": "Service MCP indisponible"}
    }
)

# ===================================
# MODÈLES DE REQUÊTE ET RÉPONSE
# ===================================

class SearchQuery(BaseModel):
    """Modèle pour les requêtes de recherche conversationnelle"""
    query: str = Field(..., min_length=1, max_length=1000, description="Question ou recherche de l'utilisateur")
    search_type: str = Field(default="rag", pattern="^(rag|code|hybrid)$", description="Type de recherche (rag|code|hybrid)")
    source_filter: Optional[str] = Field(default=None, description="Filtre par source/domaine (optionnel)")
    max_results: int = Field(default=5, ge=1, le=20, description="Nombre maximum de résultats")
    include_citations: bool = Field(default=True, description="Inclure les citations cliquables")
    streaming: bool = Field(default=False, description="Réponse en streaming SSE")
    think_mode: bool = Field(default=False, description="Mode raisonnement approfondi")
    
    @validator('query')
    def validate_query(cls, v):
        """Validation et nettoyage de la requête"""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("La requête ne peut pas être vide")
        return cleaned

class SearchResult(BaseModel):
    """Résultat de recherche individuel"""
    id: str = Field(description="Identifiant unique du résultat")
    title: str = Field(description="Titre du contenu")
    content: str = Field(description="Extrait du contenu")
    source: str = Field(description="Source/domaine d'origine")
    type: str = Field(default="document", description="Type de contenu (document|code)")
    url: Optional[str] = Field(description="URL originale si disponible")
    score: float = Field(description="Score de pertinence (0-1)")
    chunk_id: str = Field(default="", description="ID du chunk pour citations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")

class SearchResponse(BaseModel):
    """Réponse complète de recherche"""
    success: bool = Field(description="Succès de la recherche")
    query: str = Field(description="Requête originale")
    search_type: str = Field(description="Type de recherche effectuée")
    results: List[SearchResult] = Field(description="Liste des résultats")
    total_results: int = Field(description="Nombre total de résultats trouvés")
    execution_time: float = Field(description="Temps d'exécution en secondes")
    sources_used: List[str] = Field(description="Sources consultées")
    error: Optional[str] = Field(description="Message d'erreur si échec")
    
class CitationLink(BaseModel):
    """Lien de citation cliquable"""
    id: str = Field(description="Identifiant de la citation")
    text: str = Field(description="Texte de la citation")
    url: str = Field(description="URL de la source")
    source: str = Field(description="Nom de la source")

class StreamResponse(BaseModel):
    """Réponse streaming pour SSE"""
    event: str = Field(description="Type d'événement")
    data: str = Field(description="Données JSON")

class ConversationalResponse(BaseModel):
    """Réponse conversationnelle enrichie"""
    answer: str = Field(description="Réponse synthétisée")
    confidence: float = Field(description="Niveau de confiance (0-1)")
    search_results: List[SearchResult] = Field(description="Résultats de recherche source")
    citations: List[Dict[str, Any]] = Field(description="Citations avec permaliens")
    suggested_followups: List[str] = Field(description="Questions de suivi suggérées")
    reasoning: Optional[str] = Field(description="Raisonnement détaillé (mode think)")
    sources: List[str] = Field(default_factory=list, description="Sources utilisées")
    think: Optional[str] = Field(description="Raisonnement détaillé (mode think)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées")

# ===================================
# ENDPOINTS RECHERCHE PRINCIPALE
# ===================================

@router.post(
    "/query",
    response_model=ConversationalResponse,
    summary="Recherche conversationnelle principale",
    description="""
    Endpoint principal pour la recherche conversationnelle avec proxy vers MCP crawl4ai-rag.
    
    Fonctionnalités:
    - Recherche RAG vectorielle via MCP
    - Recherche de code si demandé
    - Synthèse conversationnelle des résultats
    - Citations cliquables avec permaliens
    - Mode raisonnement approfondi (/think)
    - Support streaming SSE
    """
)
async def search_query(
    request: SearchQuery,
    background_tasks: BackgroundTasks,
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> ConversationalResponse:
    """
    Endpoint principal de recherche conversationnelle avec proxy MCP
    """
    start_time = time.time()
    
    try:
        logger.info(
            "Début recherche conversationnelle",
            query=request.query,
            search_type=request.search_type,
            think_mode=request.think_mode,
            source_filter=request.source_filter
        )
        
        # Préparation des requêtes selon le type de recherche
        search_results = []
        sources_used = []
        
        if request.search_type in ["rag", "hybrid"]:
            # Recherche RAG via MCP
            rag_request = RAGQueryRequest(
                query=request.query,
                source=request.source_filter,
                match_count=request.max_results
            )
            
            rag_response = await mcp_client.perform_rag_query(rag_request)
            
            if rag_response.success and rag_response.data:
                search_results.extend(_format_rag_results(rag_response.data))
                sources_used.extend(_extract_sources(rag_response.data))
        
        if request.search_type in ["code", "hybrid"]:
            # Recherche de code via MCP
            code_request = CodeSearchRequest(
                query=request.query,
                source_id=request.source_filter,
                match_count=min(request.max_results, 5)
            )
            
            code_response = await mcp_client.search_code_examples(code_request)
            
            if code_response.success and code_response.data:
                search_results.extend(_format_code_results(code_response.data))
                sources_used.extend(_extract_sources(code_response.data))
        
        # Déduplication et tri par score
        search_results = _deduplicate_results(search_results)
        search_results = sorted(search_results, key=lambda x: x.score, reverse=True)
        search_results = search_results[:request.max_results]
        
        # Génération de la réponse conversationnelle
        conversational_response = await _generate_conversational_response(
            request.query,
            search_results,
            request.think_mode
        )
        
        # Génération des citations si demandées
        citations = []
        if request.include_citations:
            citations = _generate_citations(search_results)
        
        execution_time = time.time() - start_time
        
        logger.info(
            "Recherche conversationnelle terminée",
            query=request.query,
            results_count=len(search_results),
            execution_time=f"{execution_time:.2f}s"
        )
        
        return ConversationalResponse(
            answer=conversational_response["answer"],
            confidence=conversational_response["confidence"],
            search_results=search_results,
            citations=citations,
            suggested_followups=conversational_response.get("followups", []),
            reasoning=conversational_response.get("reasoning") if request.think_mode else None
        )
        
    except Exception as e:
        logger.error(
            "Erreur lors de la recherche conversationnelle",
            query=request.query,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )

@router.get(
    "/stream/{query}",
    summary="Recherche en streaming SSE",
    description="Version streaming de la recherche conversationnelle avec Server-Sent Events"
)
async def search_stream(
    query: str = Path(..., min_length=1, max_length=1000),
    search_type: str = Query(default="rag", pattern="^(rag|code|hybrid)$"),
    source_filter: Optional[str] = Query(default=None),
    max_results: int = Query(default=5, ge=1, le=20),
    think_mode: bool = Query(default=False),
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
):
    """Recherche conversationnelle en streaming avec SSE"""
    
    async def generate_search_stream():
        """Générateur pour le streaming de la recherche"""
        try:
            yield {"event": "search_start", "data": json.dumps({"query": query, "timestamp": time.time()})}
            
            # Phase 1: Recherche des résultats
            yield {"event": "phase", "data": json.dumps({"phase": "searching", "message": "Recherche en cours..."})}
            
            search_request = SearchQuery(
                query=query,
                search_type=search_type,
                source_filter=source_filter,
                max_results=max_results,
                think_mode=think_mode,
                streaming=True
            )
            
            # Exécution de la recherche (réutilisation de la logique principale)
            response = await search_query(search_request, BackgroundTasks(), mcp_client)
            
            # Streaming des résultats par chunks
            yield {"event": "results_found", "data": json.dumps({"count": len(response.search_results)})}
            
            for i, result in enumerate(response.search_results):
                yield {
                    "event": "result",
                    "data": json.dumps({
                        "index": i,
                        "result": result.dict()
                    })
                }
                await asyncio.sleep(0.1)  # Délai pour le streaming
            
            # Phase 2: Génération de la réponse
            if think_mode:
                yield {"event": "phase", "data": json.dumps({"phase": "thinking", "message": "Analyse approfondie..."})}
                
                if response.reasoning:
                    # Stream le raisonnement par chunks
                    reasoning_chunks = response.reasoning.split('. ')
                    for chunk in reasoning_chunks:
                        yield {"event": "reasoning", "data": json.dumps({"chunk": chunk + ". "})}
                        await asyncio.sleep(0.2)
            
            yield {"event": "phase", "data": json.dumps({"phase": "generating", "message": "Génération de la réponse..."})}
            
            # Stream de la réponse finale par mots
            answer_words = response.answer.split(' ')
            for i, word in enumerate(answer_words):
                yield {
                    "event": "answer_chunk",
                    "data": json.dumps({
                        "word": word + " ",
                        "progress": (i + 1) / len(answer_words)
                    })
                }
                await asyncio.sleep(0.05)
            
            # Finalisation
            yield {
                "event": "search_complete",
                "data": json.dumps({
                    "citations": [c for c in response.citations],
                    "followups": response.suggested_followups,
                    "confidence": response.confidence
                })
            }
            
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
    
    return EventSourceResponse(generate_search_stream())

# ===================================
# ENDPOINTS AUXILIAIRES
# ===================================

@router.get(
    "/suggestions",
    summary="Suggestions de recherche",
    description="Génère des suggestions de recherche basées sur les sources disponibles"
)
async def get_search_suggestions(
    partial_query: str = Query(default="", description="Début de requête pour suggestions"),
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> Dict[str, Any]:
    """Génère des suggestions de recherche"""
    try:
        # Récupération des sources disponibles
        sources_response = await mcp_client.get_available_sources()
        
        suggestions = []
        if sources_response.success and sources_response.data:
            # Génération de suggestions basées sur les sources et thématiques
            suggestions = _generate_search_suggestions(
                partial_query,
                sources_response.data
            )
        
        return {
            "suggestions": suggestions,
            "total_sources": len(sources_response.data) if sources_response.data else 0
        }
        
    except Exception as e:
        logger.error("Erreur génération suggestions", error=str(e))
        return {"suggestions": [], "error": str(e)}

@router.get(
    "/history",
    summary="Historique des recherches",
    description="Récupère l'historique des recherches récentes"
)
async def get_search_history(
    limit: int = Query(default=10, ge=1, le=50),
    user_id: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    """Récupère l'historique des recherches (implémentation future)"""
    # TODO: Implémenter avec Redis pour persistence
    return {
        "history": [],
        "message": "Historique non encore implémenté"
    }

@router.post(
    "/test-mcp",
    summary="Test direct MCP crawl4ai-rag",
    description="Endpoint de test pour valider l'intégration MCP perform_rag_query et search_code_examples"
)
async def test_mcp_integration(
    query: str = Query(..., description="Requête de test"),
    search_type: str = Query(default="rag", pattern="^(rag|code|both)$"),
    source_filter: Optional[str] = Query(default=None),
    mcp_client: MCPCrawl4AIClient = Depends(get_mcp_client)
) -> Dict[str, Any]:
    """Test direct des fonctions MCP pour validation de l'intégration"""
    
    results = {
        "query": query,
        "search_type": search_type,
        "source_filter": source_filter,
        "timestamp": time.time(),
        "results": {}
    }
    
    try:
        if search_type in ["rag", "both"]:
            # Test perform_rag_query
            rag_request = RAGQueryRequest(
                query=query,
                source=source_filter,
                match_count=3
            )
            
            rag_response = await mcp_client.perform_rag_query(rag_request)
            results["results"]["rag"] = {
                "success": rag_response.success,
                "raw_data": rag_response.data,
                "error": rag_response.error,
                "execution_time": rag_response.execution_time,
                "formatted_results": _format_rag_results(rag_response.data) if rag_response.success else []
            }
        
        if search_type in ["code", "both"]:
            # Test search_code_examples
            code_request = CodeSearchRequest(
                query=query,
                source_id=source_filter,
                match_count=2
            )
            
            code_response = await mcp_client.search_code_examples(code_request)
            results["results"]["code"] = {
                "success": code_response.success,
                "raw_data": code_response.data,
                "error": code_response.error,
                "execution_time": code_response.execution_time,
                "formatted_results": _format_code_results(code_response.data) if code_response.success else []
            }
        
        # Test des sources disponibles
        sources_response = await mcp_client.get_available_sources()
        results["available_sources"] = {
            "success": sources_response.success,
            "count": len(sources_response.data) if sources_response.data else 0,
            "sources": [s.get("source_id", "unknown") for s in (sources_response.data or [])[:5]]
        }
        
        return results
        
    except Exception as e:
        logger.error("Erreur lors du test MCP", error=str(e))
        return {
            **results,
            "error": str(e),
            "status": "failed"
        }

# ===================================
# FONCTIONS UTILITAIRES
# ===================================

def _format_rag_results(rag_data: Any) -> List[SearchResult]:
    """Formate les résultats RAG MCP en SearchResult selon le format réel"""
    results = []
    
    if isinstance(rag_data, dict) and "results" in rag_data:
        for i, item in enumerate(rag_data["results"]):
            # Extraction du titre depuis les métadonnées ou URL
            title = "Document non titré"
            if "metadata" in item and item["metadata"]:
                if "headers" in item["metadata"]:
                    # Extraire le premier header comme titre
                    headers = item["metadata"]["headers"]
                    if headers and "#" in headers:
                        title = headers.split("#")[1].split(";")[0].strip() if "#" in headers else title
                elif "url" in item:
                    # Utiliser le domaine de l'URL comme titre
                    url_parts = item["url"].split("/")
                    title = f"Document de {url_parts[2] if len(url_parts) > 2 else 'source inconnue'}"
            
            # Génération d'un ID unique si manquant
            result_id = item.get("id", f"rag_{i}_{hash(item.get('content', ''))}")
            
            results.append(SearchResult(
                id=result_id,
                title=title,
                content=item.get("content", ""),
                source=item.get("metadata", {}).get("source", "source_inconnue"),
                url=item.get("url"),
                score=float(item.get("similarity", 0.0)),
                chunk_id=f"chunk_{i}_{result_id}",
                metadata={
                    **item.get("metadata", {}),
                    "rerank_score": item.get("rerank_score", 0.0),
                    "word_count": item.get("metadata", {}).get("word_count", 0),
                    "char_count": item.get("metadata", {}).get("char_count", 0)
                }
            ))
    
    return results

def _format_code_results(code_data: Any) -> List[SearchResult]:
    """Formate les résultats de recherche de code en SearchResult selon le format réel"""
    results = []
    
    if isinstance(code_data, dict) and "results" in code_data:
        for i, item in enumerate(code_data["results"]):
            # Pour les résultats de code, le format diffère légèrement
            # Le code est dans 'code' et non 'code_snippet'
            code_content = item.get("code", item.get("code_snippet", ""))
            
            # Extraction du nom de fichier ou classe depuis l'URL ou métadonnées
            title = "Code"
            if "url" in item and item["url"]:
                url_parts = item["url"].split("/")
                if len(url_parts) > 0:
                    title = f"Code de {url_parts[-1] if url_parts[-1] else url_parts[-2]}"
            
            # Génération d'un ID unique si manquant
            result_id = item.get("id", f"code_{i}_{hash(code_content[:100])}")
            
            results.append(SearchResult(
                id=result_id,
                title=title,
                content=code_content,
                source=item.get("source_id", item.get("metadata", {}).get("source", "code_source")),
                type="code",  # Type explicite pour le code
                url=item.get("url"),
                score=float(item.get("similarity", item.get("relevance_score", 0.0))),
                chunk_id=f"code_chunk_{i}_{result_id}",
                metadata={
                    **item.get("metadata", {}),
                    "type": "code",
                    "rerank_score": item.get("rerank_score", 0.0),
                    "summary": item.get("summary", ""),
                    "word_count": item.get("metadata", {}).get("word_count", 0),
                    "char_count": item.get("metadata", {}).get("char_count", 0)
                }
            ))
    
    return results

def _extract_sources(data: Any) -> List[str]:
    """Extrait la liste des sources utilisées selon le format réel MCP"""
    sources = set()
    
    if isinstance(data, dict) and "results" in data:
        for item in data["results"]:
            # Extraction depuis metadata.source pour RAG
            if "metadata" in item and item["metadata"]:
                if "source" in item["metadata"]:
                    sources.add(item["metadata"]["source"])
            
            # Extraction depuis source_id pour code
            if "source_id" in item:
                sources.add(item["source_id"])
                
            # Extraction depuis URL comme fallback
            if "url" in item and item["url"]:
                url_parts = item["url"].split("/")
                if len(url_parts) > 2:
                    sources.add(url_parts[2])  # Domaine
    
    return list(sources)

def _deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """Supprime les doublons basés sur le contenu"""
    seen = set()
    unique_results = []
    
    for result in results:
        # Clé de déduplication basée sur le contenu tronqué
        dedup_key = (result.source, result.content[:100])
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique_results.append(result)
    
    return unique_results

async def _generate_conversational_response(
    query: str,
    search_results: List[SearchResult],
    think_mode: bool = False
) -> Dict[str, Any]:
    """Génère une réponse conversationnelle enrichie basée sur les résultats MCP"""
    
    if not search_results:
        return {
            "answer": "Je n'ai pas trouvé d'informations pertinentes pour votre question. Pourriez-vous reformuler ou être plus précis ?",
            "confidence": 0.0,
            "followups": [
                "Pouvez-vous être plus spécifique ?",
                "Cherchez-vous des informations techniques ?",
                "Souhaitez-vous explorer d'autres sources ?"
            ]
        }
    
    # Synthèse intelligente avec métadonnées MCP
    top_result = search_results[0]
    sources_used = set(r.source for r in search_results)
    
    # Construction de la réponse basée sur le type de contenu
    has_code = any(r.metadata.get("type") == "code" for r in search_results)
    
    answer = f"Basé sur l'analyse de {len(search_results)} résultats"
    if len(sources_used) > 1:
        answer += f" provenant de {len(sources_used)} sources ({', '.join(list(sources_used)[:3])}{'...' if len(sources_used) > 3 else ''})"
    else:
        answer += f" de {top_result.source}"
    
    answer += f", voici ce que j'ai trouvé concernant '{query}':\n\n"
    
    # Ajout du contenu principal
    content_preview = top_result.content[:400]
    if len(top_result.content) > 400:
        content_preview += "..."
    answer += content_preview
    
    # Informations sur la qualité des résultats
    if len(search_results) > 1:
        avg_score = sum(r.score for r in search_results) / len(search_results)
        answer += f"\n\n📊 **Analyse de pertinence** : {len(search_results)} résultats avec un score de confiance moyen de {avg_score:.1%}"
        
        if has_code:
            code_results = [r for r in search_results if r.metadata.get("type") == "code"]
            answer += f" (incluant {len(code_results)} exemple{'s' if len(code_results) > 1 else ''} de code)"
    
    # Calcul de confiance basé sur les scores MCP
    confidence = top_result.score
    if len(search_results) > 1:
        # Bonus si plusieurs sources concordent
        confidence = min(confidence + 0.1, 0.95)
    
    # Suggestions de suivi intelligentes
    followups = []
    
    if has_code:
        followups.append("Montrer plus d'exemples de code")
    
    if len(sources_used) > 1:
        for source in list(sources_used)[:2]:
            followups.append(f"Focus sur les résultats de {source}")
    
    # Suggestions génériques
    followups.extend([
        "Recherche plus approfondie sur ce sujet",
        "Sources alternatives pour cette thématique"
    ])
    
    response = {
        "answer": answer,
        "confidence": confidence,
        "followups": followups[:4]  # Maximum 4 suggestions
    }
    
    if think_mode:
        reasoning = f"🔍 **Analyse détaillée de la requête** '{query}':\n\n"
        reasoning += f"**📈 Résultats quantitatifs :**\n"
        reasoning += f"- {len(search_results)} documents analysés\n"
        reasoning += f"- {len(sources_used)} sources distinctes consultées\n"
        reasoning += f"- Score de pertinence le plus élevé : {top_result.score:.1%}\n"
        reasoning += f"- Score de confiance moyen : {sum(r.score for r in search_results) / len(search_results):.1%}\n\n"
        
        reasoning += f"**🔗 Sources principales :**\n"
        for i, source in enumerate(list(sources_used)[:3], 1):
            source_results = [r for r in search_results if r.source == source]
            reasoning += f"{i}. {source} ({len(source_results)} résultat{'s' if len(source_results) > 1 else ''})\n"
        
        if any("rerank_score" in r.metadata for r in search_results):
            reasoning += f"\n**🎯 Reranking MCP :**\n"
            rerank_scores = [r.metadata.get("rerank_score", 0) for r in search_results if "rerank_score" in r.metadata]
            if rerank_scores:
                reasoning += f"- Score de reranking le plus élevé : {max(rerank_scores):.2f}\n"
                reasoning += f"- Le système de reranking MCP a optimisé l'ordre des résultats\n"
        
        reasoning += f"\n**💡 Stratégie de réponse :**\n"
        reasoning += f"- Contenu principal extrait du résultat le plus pertinent ({top_result.source})\n"
        reasoning += f"- Synthèse enrichie avec les métadonnées MCP\n"
        if has_code:
            reasoning += f"- Détection automatique d'exemples de code intégrés\n"
        
        response["reasoning"] = reasoning
    
    return response

def _generate_citations(search_results: List[SearchResult]) -> List[Dict[str, Any]]:
    """Génère des citations cliquables avec permaliens"""
    citations = []
    
    for i, result in enumerate(search_results):
        citation = {
            "id": f"cite_{i+1}",
            "title": result.title,
            "source": result.source,
            "url": result.url,
            "chunk_id": result.chunk_id,
            "permalink": f"/search/citation/{result.chunk_id}",
            "preview": result.content[:150] + "..." if len(result.content) > 150 else result.content
        }
        citations.append(citation)
    
    return citations

def _generate_search_suggestions(partial_query: str, sources_data: Any) -> List[str]:
    """Génère des suggestions de recherche basées sur les sources"""
    suggestions = []
    
    # Suggestions génériques
    base_suggestions = [
        "Quelles sont les dernières tendances en",
        "Comment implémenter",
        "Quels sont les avantages de",
        "Comparaison entre",
        "Guide d'installation pour",
        "Meilleures pratiques pour"
    ]
    
    # Suggestions basées sur les sources disponibles
    if sources_data:
        for suggestion in base_suggestions[:4]:
            suggestions.append(f"{suggestion} {partial_query}")
    
    # Suggestions de domaines techniques
    tech_domains = ["IA", "blockchain", "cloud", "DevOps", "sécurité", "microservices"]
    for domain in tech_domains[:2]:
        suggestions.append(f"{partial_query} en {domain}")
    
    return suggestions[:6]