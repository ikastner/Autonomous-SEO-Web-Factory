"""
agents/scout.py — Scout Node (1er nœud du pipeline LangGraph).

Responsabilité : Extraire et COMPRESSER le contenu web de l'URL cible.

Workflow :
    1. Crawl de l'URL via CrawlerService → Markdown brut (peut faire 50k+ chars)
    2. COMPRESSION via LLM : synthétise le markdown en un résumé structuré JSON
    3. Retourne uniquement le résumé compressé dans le State (pas le markdown brut)

Règle critique (Context Window Management) :
    ⚠️ Le markdown brut ne DOIT JAMAIS entrer dans le GraphState.
    Sinon, chaque nœud suivant (SEO, UX, Copywriter) reçoit 50k+ tokens inutiles
    → explosion de la fenêtre de contexte → amnésie LLM → echec de pipeline.

Stratégie de compression :
    - Le LLM lit le markdown complet en ONE-SHOT.
    - Il extrait UNIQUEMENT : USP, Cible, Ton de voix, Offres principales.
    - Le résumé JSON fait <1000 tokens max.
    - Ce résumé suffit pour tous les nœuds en aval.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.state import GraphState
from backend.core.config import get_settings
from backend.services.crawler import CrawlerService

logger = logging.getLogger(__name__)

_settings = get_settings()
_crawler = CrawlerService()


# ===========================================================================
# Schéma de sortie LLM — Ce qui entre dans le State (compressé)
# ===========================================================================

class MarketContextCompressed(BaseModel):
    """Résumé synthétique du contenu crawlé (sortie du LLM de compression).

    Ce modèle Pydantic guide le LLM via JSON mode.
    Il représente le strict minimum nécessaire pour les nœuds en aval.
    """

    usp: str = Field(
        ...,
        description=(
            "Unique Selling Proposition — Proposition de valeur unique de la marque. "
            "1-2 phrases max. Ex: 'Agence SEO spécialisée e-commerce avec garantie ROI 6 mois'."
        ),
    )
    target_audience: str = Field(
        ...,
        description=(
            "Audience cible principale identifiée sur la page. "
            "Ex: 'PME e-commerce B2C, 10-50 employés, France métropolitaine'."
        ),
    )
    tone_of_voice: str = Field(
        ...,
        description=(
            "Ton de voix dominant détecté dans le contenu. "
            "Choisir parmi : 'professionnel', 'décontracté', 'technique', 'inspirant', 'corporate', 'startup'."
        ),
    )
    main_offers: list[str] = Field(
        ...,
        max_length=5,
        description=(
            "Liste de 3 à 5 offres/services/produits principaux mentionnés. "
            "Phrases courtes (5-10 mots max par item). "
            "Ex: ['Audit SEO technique', 'Rédaction de contenus SEO', 'Netlinking white-hat']."
        ),
    )
    niche: str = Field(
        ...,
        description=(
            "Niche ou secteur d'activité identifié. "
            "1-3 mots. Ex: 'SEO B2B', 'SaaS Marketing', 'E-commerce Mode'."
        ),
    )
    url_source: str = Field(
        ...,
        description="URL crawlée (conservée pour traçabilité).",
    )


# ===========================================================================
# Prompt de compression (System)
# ===========================================================================

COMPRESSION_SYSTEM_PROMPT = """Tu es un analyste expert en marketing digital et brand positioning.

CONTEXTE :
Un utilisateur te fournit le contenu brut d'une page web (en Markdown).
Cette page peut faire des dizaines de milliers de caractères (homepage, landing page, about page, etc.).

TA MISSION :
Extraire UNIQUEMENT les informations critiques suivantes (en JSON strict) :
1. **USP** (Unique Selling Proposition) : la promesse centrale de la marque en 1-2 phrases.
2. **Audience cible** : qui est le client type visé ? (démographie, secteur, taille entreprise, géographie).
3. **Ton de voix** : professionnel, décontracté, technique, inspirant, corporate, ou startup.
4. **Offres principales** : liste de 3-5 produits/services clés mentionnés (phrases courtes).
5. **Niche** : le secteur d'activité en 1-3 mots (ex: "SEO B2B", "SaaS CRM", "E-commerce Luxe").

RÈGLES STRICTES :
- Sois SYNTHÉTIQUE. Chaque champ doit être concis (pas de paraphrase du contenu original).
- Si une info est absente ou ambiguë, déduis-la du contexte ou mets "Non identifié".
- NE répète PAS le contenu brut. Ton output JSON doit faire <500 tokens.
- Le JSON DOIT être conforme au schéma Pydantic fourni (pas de champs supplémentaires).

OUTPUT FORMAT :
Retourne UNIQUEMENT un objet JSON valide (pas de markdown, pas de texte autour).
"""


# ===========================================================================
# Nœud LangGraph
# ===========================================================================

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    reraise=True,
)
async def scout_node(state: GraphState) -> dict[str, Any]:
    """Nœud LangGraph : Crawl + Compression LLM → MarketContext compressé.

    Returns:
        dict avec clé "market_context" (MarketContextCompressed serialisé)
        OU clé "arbitre_errors" si échec critique (URL invalide, crawl failed).
    """
    target_url = state.get("target_url", "")

    if not target_url:
        logger.error("❌ Scout Node appelé sans target_url dans le State")
        return {
            "arbitre_errors": ["Scout Node : aucune URL cible fournie dans le State"],
            "market_context": {},
        }

    logger.info(f"🔍 Scout Node démarré pour URL : {target_url}")

    try:
        raw_markdown = await _crawler.extract_markdown(target_url)
    except (ValueError, RuntimeError) as exc:
        logger.error(f"❌ Échec du crawl pour {target_url}: {exc}")
        return {
            "arbitre_errors": [f"Scout failed to reach URL '{target_url}': {exc}"],
            "market_context": {},
        }

    char_count = len(raw_markdown)
    logger.info(f"📄 Markdown extracted: {char_count} chars")

    logger.info("🧠 Context compression démarrée (LLM synthesis)...")

    llm = ChatOpenAI(
        model=_settings.fast_model,
        temperature=_settings.llm_temperature,
        timeout=_settings.llm_timeout_seconds,
        max_retries=_settings.llm_max_retries,
        base_url=_settings.openai_api_base,
        api_key=_settings.effective_api_key,
    )

    parser = JsonOutputParser(pydantic_object=MarketContextCompressed)

    prompt_messages = [
        SystemMessage(content=COMPRESSION_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"URL source : {target_url}\n\n"
                f"Contenu Markdown à analyser :\n\n{raw_markdown}\n\n"
                f"Retourne le JSON conforme au schéma : {parser.get_format_instructions()}"
            )
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        compressed_json = parser.parse(response.content)
    except Exception as exc:
        logger.error(f"❌ Échec de la compression LLM : {exc}")
        return {
            "arbitre_errors": [f"Scout LLM compression failed: {exc}"],
            "market_context": {},
        }

    compressed_json["url_source"] = target_url

    logger.info(
        f"✅ Context compressed successfully. "
        f"USP: '{compressed_json.get('usp', '')[:60]}...', "
        f"Niche: '{compressed_json.get('niche', '')}'"
    )

    return {"market_context": compressed_json}
