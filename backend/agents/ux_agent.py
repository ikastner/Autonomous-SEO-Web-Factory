"""
agents/ux_agent.py — UX Node (3e nœud du pipeline LangGraph, s'exécute en parallèle avec Copywriter).

Responsabilité : Convertir le plan sémantique SEO en wireframe UX/UI optimisé pour la conversion.

Workflow :
    1. Lit `market_context` et `seo_silo` (notamment le `semantic_outline`)
    2. Utilise un LLM Expert UX/UI pour mapper chaque section du semantic_outline
       vers un composant UI concret du catalogue shadcn/ui
    3. Retourne `{"wireframe": WireframePlan}` fusionné dans le State

Règle critique :
    - Chaque section du wireframe DOIT mapper vers un `component_name` existant
      dans generative_ui.py : HeroSection, FeatureGrid, ContentBlock, FAQ, CTABanner
    - Le wireframe définit la STRUCTURE, pas le contenu (c'est le Copywriter)
    - L'ordre des sections est stratégique pour le parcours utilisateur
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, ValidationError, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.state import GraphState
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()


# ===========================================================================
# Schéma de validation Pydantic — Wireframe Plan
# ===========================================================================

ComponentName = Literal["HeroSection", "FeatureGrid", "ContentBlock", "FAQ", "CTABanner"]


class WireframeSection(BaseModel):
    """Une section individuelle du wireframe.

    Définit quel composant UI utiliser et pourquoi (stratégie UX).
    """

    component_name: ComponentName = Field(
        ...,
        description=(
            "Nom exact du composant UI à utiliser (doit matcher generative_ui.py). "
            "Valeurs autorisées : 'HeroSection', 'FeatureGrid', 'ContentBlock', 'FAQ', 'CTABanner'."
        ),
    )

    purpose: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description=(
            "Raison stratégique de placer ce composant ici dans le parcours utilisateur. "
            "Ex: 'Capter l'attention avec la promesse principale', "
            "'Prouver la valeur via des bénéfices concrets', "
            "'Lever les objections via FAQ People Also Ask'."
        ),
    )

    expected_content_type: str = Field(
        ...,
        min_length=5,
        max_length=150,
        description=(
            "Type de contenu attendu pour cette section. "
            "Ex: 'H1 + sous-titre + 2 CTAs', "
            "'Grille 3 colonnes avec icônes Lucide', "
            "'Bloc texte 400 mots avec image droite', "
            "'5-7 paires question/réponse FAQ'."
        ),
    )

    seo_target: str = Field(
        ...,
        max_length=100,
        description=(
            "Quel élément du semantic_outline SEO cette section adresse. "
            "Ex: 'Primary keyword dans le H1', "
            "'LSI keywords dans les titres de features', "
            "'People Also Ask dans la FAQ'."
        ),
    )


class WireframePlan(BaseModel):
    """Plan complet du wireframe de la page.

    Définit la structure UX optimisée pour la conversion, basée sur le semantic_outline SEO.
    """

    sections: list[WireframeSection] = Field(
        ...,
        min_length=3,
        max_length=8,
        description=(
            "Liste ordonnée des sections de la page. "
            "Doit commencer par un HeroSection (convention UX). "
            "Recommandé : 4-6 sections pour une landing page performante."
        ),
    )

    @field_validator("sections")
    @classmethod
    def hero_must_be_first(cls, v: list[WireframeSection]) -> list[WireframeSection]:
        """La première section DOIT être un HeroSection (best practice UX/conversion)."""
        if not v:
            raise ValueError("Le wireframe doit contenir au moins une section")
        if v[0].component_name != "HeroSection":
            raise ValueError(
                f"La première section doit être 'HeroSection'. Reçu : '{v[0].component_name}'"
            )
        return v

    @field_validator("sections")
    @classmethod
    def no_duplicate_hero_or_cta(cls, v: list[WireframeSection]) -> list[WireframeSection]:
        """Interdit les doublons de HeroSection et CTABanner (dilue la conversion)."""
        hero_count = sum(1 for s in v if s.component_name == "HeroSection")
        cta_count = sum(1 for s in v if s.component_name == "CTABanner")

        if hero_count > 1:
            raise ValueError(
                f"Une seule 'HeroSection' autorisée par page. Trouvé : {hero_count}"
            )
        if cta_count > 1:
            raise ValueError(
                f"Un seul 'CTABanner' autorisé par page. Trouvé : {cta_count}"
            )
        return v


# ===========================================================================
# Prompt System — Expert UX/UI Senior
# ===========================================================================

UX_EXPERT_SYSTEM_PROMPT = """Tu es un Expert UX/UI Senior spécialisé en landing pages à haute conversion.

CONTEXTE :
Tu reçois un plan sémantique SEO (semantic_outline) généré par un expert SEO.
Ce plan liste les sections OBLIGATOIRES d'un point de vue référencement.
Ta mission est de traduire ce plan SEO en wireframe UX concret.

TA MISSION :
Générer un wireframe structuré en JSON contenant une liste de sections.
Chaque section du wireframe doit :
1. Mapper vers un composant UI existant dans notre catalogue shadcn/ui
2. Respecter les best practices UX/conversion (parcours AIDA : Attention, Intérêt, Désir, Action)
3. Intégrer les contraintes SEO du semantic_outline

COMPOSANTS UI DISPONIBLES (component_name) :
- **HeroSection** : Hero principal (H1 + sous-titre + CTAs). Toujours en premier.
- **FeatureGrid** : Grille de fonctionnalités/bénéfices (2-3 colonnes, icônes Lucide).
- **ContentBlock** : Bloc de contenu longue-forme (texte + image optionnelle).
- **FAQ** : Accordion de questions/réponses (People Also Ask, objections).
- **CTABanner** : Bandeau CTA secondaire (avant footer, rappel de l'offre).

RÈGLES STRICTES :
1. La première section DOIT être "HeroSection" (convention UX).
2. Un seul "HeroSection", un seul "ContentBlock" et un seul "CTABanner" par page (pas de dilution, pas de redondance).
3. Nombre de sections recommandé : 4-6 pour une landing page performante.
4. Chaque section doit avoir un `purpose` UX clair (ex: "Capter attention", "Prouver valeur", "Lever objections").
5. Le `seo_target` doit indiquer quel élément du semantic_outline SEO est adressé.
6. LIMITE STRICTE : Maximum 1 ContentBlock et 1 CTABanner par wireframe pour éviter la duplication de contenu.

PARCOURS UTILISATEUR TYPE (recommandé) :
1. HeroSection → Capter attention avec promesse principale (primary keyword en H1)
2. FeatureGrid → Prouver la valeur (3-4 bénéfices clés, LSI keywords)
3. ContentBlock → Approfondir avec preuve sociale ou cas d'usage (contenu SEO dense)
4. FAQ → Lever objections (People Also Ask, requêtes longue traîne)
5. CTABanner → Conversion finale (rappel offre + CTA)

OUTPUT FORMAT :
Retourne UNIQUEMENT un objet JSON conforme au schéma WireframePlan.
Pas de markdown, pas de texte explicatif autour.
"""


# ===========================================================================
# Nœud LangGraph
# ===========================================================================

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    reraise=True,
)
async def ux_node(state: GraphState) -> dict[str, Any]:
    """Nœud LangGraph : Conception wireframe UX → WireframePlan.

    Returns:
        dict avec clé "wireframe" (WireframePlan serialisé)
        OU clé "arbitre_errors" si échec (seo_silo vide, ValidationError).
    """
    market_context = state.get("market_context", {})
    seo_silo = state.get("seo_silo", {})

    if not seo_silo or not seo_silo.get("semantic_outline"):
        logger.error("❌ UX Node appelé sans semantic_outline dans seo_silo")
        return {
            "arbitre_errors": ["UX Node : semantic_outline SEO absent ou vide dans le State"],
            "wireframe": {},
        }

    logger.info("🎨 UX Node démarré — Conception wireframe optimisé conversion...")

    semantic_outline = seo_silo.get("semantic_outline", [])
    primary_keyword = seo_silo.get("primary_keyword", "")
    search_intent = seo_silo.get("search_intent", "commercial")
    niche = market_context.get("niche", "")
    target_audience = market_context.get("target_audience", "")

    logger.info(f"📐 Semantic outline → {len(semantic_outline)} sections SEO à mapper")

    llm = ChatOpenAI(
        model=_settings.creative_model,
        temperature=_settings.llm_temperature,
        timeout=_settings.llm_timeout_seconds,
        max_retries=_settings.llm_max_retries,
        base_url=_settings.openai_api_base,
        api_key=_settings.effective_api_key,
    )

    parser = JsonOutputParser(pydantic_object=WireframePlan)

    prompt_messages = [
        SystemMessage(content=UX_EXPERT_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Données à transformer en wireframe UX :\n\n"
                f"- Niche : {niche}\n"
                f"- Audience cible : {target_audience}\n"
                f"- Primary keyword : {primary_keyword}\n"
                f"- Search intent : {search_intent}\n"
                f"- Semantic outline SEO (à respecter) :\n"
                + "\n".join([f"  {i+1}. {section}" for i, section in enumerate(semantic_outline)])
                + f"\n\nRetourne le JSON WireframePlan conforme au schéma : {parser.get_format_instructions()}"
            )
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        wireframe_json = parser.parse(response.content)
    except Exception as exc:
        logger.error(f"❌ Échec de la génération LLM UX : {exc}")
        return {
            "arbitre_errors": [f"UX Node LLM generation failed: {exc}"],
            "wireframe": {},
        }

    try:
        validated_wireframe = WireframePlan(**wireframe_json)
    except ValidationError as exc:
        logger.error(f"❌ Validation Pydantic UX échouée : {exc}")
        errors_summary = "; ".join([f"{e['loc']}: {e['msg']}" for e in exc.errors()])
        return {
            "arbitre_errors": [f"UX validation failed: {errors_summary}"],
            "wireframe": {},
        }

    logger.info(
        f"✅ Wireframe validé. "
        f"{len(validated_wireframe.sections)} sections : "
        f"{[s.component_name for s in validated_wireframe.sections]}"
    )

    return {"wireframe": validated_wireframe.model_dump()}
