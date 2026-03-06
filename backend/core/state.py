"""
core/state.py — Définition du GraphState LangGraph.

Chaque clé du TypedDict est annotée avec un reducer explicite pour éviter
l'amnésie LLM et garantir des fusions déterministes lors des mises à jour
parallèles (UX + Copywriter nodes).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


# ---------------------------------------------------------------------------
# Reducers
# ---------------------------------------------------------------------------

def _overwrite(current: Any, update: Any) -> Any:
    """Reducer : écrase purement et simplement la valeur existante."""
    return update


def _merge_dict(current: dict, update: dict) -> dict:
    """Reducer : fusionne deux dicts (update a priorité sur current)."""
    if not isinstance(current, dict):
        return update
    return {**current, **update}


def _append_errors(current: list[str], update: list[str]) -> list[str]:
    """Reducer : accumule les messages d'erreur de l'Arbitre."""
    if not isinstance(update, list):
        return current if isinstance(current, list) else []
    return update


def _increment_retry(current: int, update: int) -> int:
    """Reducer : additionne les tentatives de retry (Arbitre → nœud fautif)."""
    return current + update


# ---------------------------------------------------------------------------
# Sub-structures (pas des nœuds TypedDict imbriqués, juste des type aliases
# documentés pour guider les agents)
# ---------------------------------------------------------------------------

# MarketContext  → produit par Scout Node
# { "niche": str, "competitors": list[str], "raw_text": str }
MarketContext = dict[str, Any]

# BrandDNA       → produit par Data Miner Node
# { "brand_name": str, "tone": str, "usp": str, "target_audience": str }
BrandDNA = dict[str, Any]

# SeoSilo        → produit par SEO Node
# { "pillar_page": str, "cluster_pages": list[str], "keywords": list[str] }
SeoSilo = dict[str, Any]

# Wireframe      → produit par UX Node
# { "sections": list[{ "id": str, "type": str, "props": dict }] }
Wireframe = dict[str, Any]

# ArtDirection   → produit par Art Director Node
# { "design_vibe": str, "typography_style": str, "animation_feeling": str, "color_palette_hex": list[str] }
ArtDirection = dict[str, Any]

# CopyDraft      → produit par Copywriter Node
# { "hero": str, "sections": dict[str, str] }
CopyDraft = dict[str, Any]

# GenerativeUISchema → produit par Architect Node (contrat Pydantic final)
GenerativeUISchema = dict[str, Any]


# ---------------------------------------------------------------------------
# GraphState
# ---------------------------------------------------------------------------

class GraphState(TypedDict):
    """État global partagé entre tous les nœuds du graphe LangGraph.

    Règles :
    - Toute clé DOIT avoir un reducer via `Annotated`.
    - Les agents ne lisent que les clés dont ils ont besoin.
    - L'Arbitre inspecte `arbitre_errors` avant de router.
    """

    # --- Entrée utilisateur ---
    target_url: Annotated[str, _overwrite]
    """URL cible fournie par l'utilisateur pour lancer le pipeline."""

    # --- Scout Node ---
    market_context: Annotated[MarketContext, _merge_dict]
    """Données brutes extraites par Crawl4AI + analyse concurrentielle."""

    # --- Data Miner Node ---
    brand_dna: Annotated[BrandDNA, _merge_dict]
    """ADN de marque extrait : ton, USP, audience cible."""

    # --- SEO Node ---
    seo_silo: Annotated[SeoSilo, _merge_dict]
    """Arborescence Silo SEO : page pilier, clusters, mots-clés."""

    # --- UX Node ---
    wireframe: Annotated[Wireframe, _merge_dict]
    """Structure de la page : sections ordonnées avec types de composants."""

    # --- Art Director Node ---
    art_direction: Annotated[ArtDirection, _merge_dict]
    """Tokens de direction artistique : vibe, typographie, animations, palette de couleurs."""

    # --- Copywriter Node ---
    copy_draft: Annotated[CopyDraft, _merge_dict]
    """Textes rédigés pour chaque section du wireframe."""

    # --- Arbitre Node ---
    arbitre_errors: Annotated[list[str], _append_errors]
    """Messages d'erreur émis par l'Arbitre. Vide = tout est validé."""

    retry_count: Annotated[int, _increment_retry]
    """Nombre de renvois opérés par l'Arbitre vers un nœud fautif."""

    faulty_node: Annotated[Optional[str], _overwrite]
    """Nom du dernier nœud identifié comme fautif par l'Arbitre."""

    # --- Architect Node ---
    generative_ui_schema: Annotated[GenerativeUISchema, _overwrite]
    """JSON final validé par Pydantic, prêt à être consommé par le frontend."""

    # --- Historique LLM (messages inter-nœuds, format LangChain) ---
    messages: Annotated[list, add_messages]
    """Fil de messages LangChain utilisé pour le débogage et le tracing."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_RETRY = 3
"""Nombre maximum de tentatives autorisées par l'Arbitre avant abandon."""


def build_copywriter_context(state: GraphState) -> dict[str, Any]:
    """Compression du contexte pour le Copywriter Node.

    Filtre le State complet et ne transmet que le strict minimum nécessaire
    (wireframe + mots-clés SEO) afin d'éviter la surcharge du contexte LLM.
    """
    return {
        "wireframe": state.get("wireframe", {}),
        "keywords": state.get("seo_silo", {}).get("keywords", []),
        "tone": state.get("brand_dna", {}).get("tone", ""),
        "usp": state.get("brand_dna", {}).get("usp", ""),
    }


def is_arbitre_ok(state: GraphState) -> bool:
    """Retourne True si l'Arbitre n'a signalé aucune erreur."""
    return len(state.get("arbitre_errors", [])) == 0


def has_exceeded_retries(state: GraphState) -> bool:
    """Retourne True si le nombre max de retries est atteint."""
    return state.get("retry_count", 0) >= MAX_RETRY
