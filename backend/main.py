"""
main.py — Point d'entrée FastAPI + initialisation du graphe LangGraph.

Autonomous SEO Web Factory — Pipeline agentique de génération de landing pages SEO.

Architecture du graphe :
    START → Scout → SEO → (UX + Copywriter en parallèle) → Arbitre ⇄ retry → Architect → END
                                                               ↓
                                                    (routing conditionnel selon validation)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
import json
from datetime import datetime

from backend.core.config import get_settings
from backend.core.state import GraphState
from backend.agents.scout import scout_node
from backend.agents.seo_agent import seo_node
from backend.agents.ux_agent import ux_node
from backend.agents.art_director import art_director_node
from backend.agents.copywriter import copywriter_node
from backend.agents.arbitre import arbitre_node, route_after_arbitre
from backend.agents.architect import architect_node

from langgraph.graph import StateGraph, START, END

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ===========================================================================
# Graphe LangGraph — Autonomous SEO Web Factory
# ===========================================================================

def build_factory_graph() -> Any:
    """Construit et compile le graphe LangGraph complet du pipeline.

    Topologie du graphe :
        1. START → scout_node : Extraction et compression du contenu web
        2. scout_node → seo_node : Définition de la stratégie sémantique SEO
        3. seo_node → [ux_node, art_director_node, copywriter_node] : Exécution PARALLÈLE
            - ux_node : Conception du wireframe (structure UI)
            - art_director_node : Génération des design tokens (vibe, typo, couleurs)
            - copywriter_node : Rédaction du contenu persuasif
        4. [ux_node, art_director_node, copywriter_node] → arbitre_node : Point de jonction (attend les 3)
        5. arbitre_node → {routing conditionnel} :
            - Si approuvé → architect_node
            - Si rejeté → seo_node | ux_node | copywriter_node (retry)
            - Si max retry → architect_node (fail-safe)
        6. architect_node → END : Compilation du GenerativeUISchema final

    Returns:
        CompiledGraph prêt pour exécution via ainvoke()
    """
    logger.info("🏗️ Construction du graphe LangGraph...")

    builder = StateGraph(GraphState)

    # -----------------------------------------------------------------------
    # Ajout des nœuds
    # -----------------------------------------------------------------------
    builder.add_node("scout_node", scout_node)
    builder.add_node("seo_node", seo_node)
    builder.add_node("ux_node", ux_node)
    builder.add_node("art_director_node", art_director_node)
    builder.add_node("copywriter_node", copywriter_node)
    builder.add_node("arbitre_node", arbitre_node)
    builder.add_node("architect_node", architect_node)

    # -----------------------------------------------------------------------
    # Point d'entrée
    # -----------------------------------------------------------------------
    builder.add_edge(START, "scout_node")

    # -----------------------------------------------------------------------
    # Flux séquentiel : Scout → SEO
    # -----------------------------------------------------------------------
    builder.add_edge("scout_node", "seo_node")

    # -----------------------------------------------------------------------
    # PARALLÉLISATION : SEO → (UX + Art Director + Copywriter)
    # -----------------------------------------------------------------------
    # LangGraph lancera les trois nœuds en parallèle dès que seo_node termine
    builder.add_edge("seo_node", "ux_node")
    builder.add_edge("seo_node", "art_director_node")
    builder.add_edge("seo_node", "copywriter_node")

    # -----------------------------------------------------------------------
    # Point de jonction : (UX + Art Director + Copywriter) → Arbitre
    # -----------------------------------------------------------------------
    # LangGraph attend automatiquement que TOUS les nœuds pointant vers
    # arbitre_node soient terminés avant de le lancer
    builder.add_edge("ux_node", "arbitre_node")
    builder.add_edge("art_director_node", "arbitre_node")
    builder.add_edge("copywriter_node", "arbitre_node")

    # -----------------------------------------------------------------------
    # Routing conditionnel : Arbitre → {SEO | UX | Copywriter | Architect}
    # -----------------------------------------------------------------------
    builder.add_conditional_edges(
        "arbitre_node",
        route_after_arbitre,  # Fonction de routing définie dans arbitre.py
        {
            "scout_node": "scout_node",      # Retry Scout si URL invalide
            "seo_node": "seo_node",          # Retry SEO si stratégie incohérente
            "ux_node": "ux_node",            # Retry UX si wireframe invalide
            "copywriter_node": "copywriter_node",  # Retry Copy si texte manquant
            "architect_node": "architect_node",    # Approuvé ou fail-safe
            "END": END,                      # Abandon si erreur critique
        },
    )

    # -----------------------------------------------------------------------
    # Sortie : Architect → END
    # -----------------------------------------------------------------------
    builder.add_edge("architect_node", END)

    logger.info("✅ Graphe compilé avec succès")
    return builder.compile()


# Compilation du graphe au démarrage de l'application
factory_graph = build_factory_graph()


# ===========================================================================
# FastAPI Application
# ===========================================================================

settings = get_settings()

app = FastAPI(
    title="Autonomous SEO Web Factory",
    description=(
        "API de génération automatique de landing pages SEO-optimisées via pipeline agentique LangGraph. "
        "Entrée : URL cible. Sortie : JSON GenerativeUISchema prêt pour Next.js."
    ),
    version="1.0.0",
    debug=settings.api_debug,
)

# CORS pour autoriser les requêtes depuis le frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Schémas Pydantic pour l'API
# ===========================================================================

class GenerateSiteRequest(BaseModel):
    """Requête pour générer un site à partir d'une URL cible."""

    target_url: HttpUrl

    class Config:
        json_schema_extra = {
            "example": {
                "target_url": "https://www.example-agence-seo.com"
            }
        }


class GenerateSiteResponse(BaseModel):
    """Réponse contenant le schéma UI généré et les métadonnées du pipeline."""

    success: bool
    generative_ui_schema: dict[str, Any]
    arbitre_errors: list[str]
    retry_count: int
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "generative_ui_schema": {
                    "page_slug": "agence-seo-paris",
                    "brand_name": "Acme SEO",
                    "seo_metadata": {"title": "Agence SEO Paris...", "description": "..."},
                    "sections": [{"component_type": "HeroSection", "headline": "..."}],
                },
                "arbitre_errors": [],
                "retry_count": 0,
                "message": "Site généré avec succès",
            }
        }


# ===========================================================================
# Endpoints
# ===========================================================================

@app.post("/generate-site")
async def generate_site(request: GenerateSiteRequest):
    """
    Génère une landing page SEO complète à partir d'une URL cible avec streaming SSE.

    Pipeline :
        1. Scout : Crawl + compression LLM du contenu web
        2. SEO : Définition stratégie sémantique (keywords, meta tags)
        3. UX + Art Director + Copywriter (parallèle) : Wireframe + Design + Rédaction
        4. Arbitre : Validation cohérence UX/SEO/Copy
        5. Architect : Compilation du GenerativeUISchema final

    Args:
        request: URL cible à analyser

    Returns:
        StreamingResponse avec Server-Sent Events (SSE)

    Raises:
        HTTPException 500: Si le pipeline échoue après les retries
    """
    logger.info(f"📥 Nouvelle requête /generate-site : {request.target_url}")

    def json_serializer(obj):
        """Encoder JSON personnalisé pour gérer les datetime."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    async def event_generator():
        """Générateur d'événements SSE pour le streaming."""
        # État initial du graphe
        initial_state: GraphState = {
            "target_url": str(request.target_url),
            "market_context": {},
            "brand_dna": {},
            "seo_silo": {},
            "wireframe": {},
            "art_direction": {},
            "copy_draft": {},
            "arbitre_errors": [],
            "retry_count": 0,
            "faulty_node": None,
            "generative_ui_schema": {},
            "messages": [],
        }

        try:
            logger.info("🚀 Lancement du pipeline agentique...")
            
            # Yield événement de démarrage
            yield f"data: {json.dumps({'status': 'started', 'message': 'Pipeline démarré'}, default=json_serializer)}\n\n"

            final_state = None
            
            # Stream des événements du graphe
            async for output in factory_graph.astream(initial_state):
                # output est un dict avec le nom du nœud comme clé
                for node_name, node_output in output.items():
                    logger.info(f"📡 Nœud en cours : {node_name}")
                    
                    # Yield événement de progression
                    event_data = {
                        "status": "running",
                        "node": node_name,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(event_data, default=json_serializer)}\n\n"
                    
                    # Stocker le dernier état
                    final_state = node_output

            # Yield événement de complétion avec le schéma final
            if final_state:
                generative_ui_schema = final_state.get("generative_ui_schema", {})
                arbitre_errors = final_state.get("arbitre_errors", [])
                retry_count = final_state.get("retry_count", 0)
                
                completion_event = {
                    "status": "complete",
                    "generative_ui_schema": generative_ui_schema,
                    "arbitre_errors": arbitre_errors,
                    "retry_count": retry_count,
                    "success": bool(generative_ui_schema) and not arbitre_errors
                }
                yield f"data: {json.dumps(completion_event, default=json_serializer)}\n\n"
                logger.info("✅ Pipeline terminé")
            else:
                # Erreur : aucun état final
                error_event = {
                    "status": "error",
                    "message": "Aucun état final retourné par le pipeline"
                }
                yield f"data: {json.dumps(error_event, default=json_serializer)}\n\n"

        except Exception as exc:
            logger.error(f"❌ Échec critique du pipeline : {exc}")
            error_event = {
                "status": "error",
                "message": f"Pipeline execution failed: {str(exc)}"
            }
            yield f"data: {json.dumps(error_event, default=json_serializer)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Autonomous SEO Web Factory",
        "version": "1.0.0",
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Endpoint racine avec informations sur l'API."""
    return {
        "name": "Autonomous SEO Web Factory API",
        "version": "1.0.0",
        "description": "Pipeline agentique de génération de landing pages SEO",
        "endpoints": {
            "generate_site": "POST /generate-site",
            "health": "GET /health",
            "docs": "GET /docs",
        },
    }


# ===========================================================================
# Démarrage de l'application
# ===========================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.api_debug,
        log_level="info",
    )
