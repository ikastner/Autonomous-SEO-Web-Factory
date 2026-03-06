"""
agents/seo_agent.py — SEO Node (2e nœud du pipeline LangGraph).

Responsabilité : Traduire les données marketing en stratégie de référencement implacable.

Workflow :
    1. Lit le `market_context` compressé (produit par Scout Node)
    2. Utilise un LLM Expert SEO pour générer :
       - Mots-clés (primary + secondary)
       - Search intent
       - Métas SEO optimisés (title + description validés par Pydantic)
       - Semantic outline (sections obligatoires pour le SEO)
    3. Retourne `{"seo_silo": SeoStrategy}` fusionné dans le State

Règle critique :
    - Les métas (title/description) DOIVENT respecter les longueurs Google.
    - Si Pydantic lève une ValidationError → renvoi vers l'Arbitre pour retry.
    - Cet agent ne rédige PAS de contenu, il définit la STRATÉGIE sémantique
      qui guidera l'UX Node et le Copywriter Node.
"""

from __future__ import annotations

import logging
import re
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


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _truncate_meta_title(value: str, max_length: int = 60) -> str:
    normalized = _normalize_whitespace(value)
    if len(normalized) <= max_length:
        return normalized

    separators = (" | ", " — ", " - ", ": ")
    for separator in separators:
        if separator in normalized:
            left_part = normalized.split(separator, 1)[0].strip()
            if 30 <= len(left_part) <= max_length:
                return left_part

    truncated = normalized[:max_length].rstrip(" ,;:-|—")
    if len(truncated) < 30:
        return normalized[:max_length].strip()
    return truncated


def _normalize_seo_strategy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    meta_title = normalized.get("meta_title")
    if isinstance(meta_title, str):
        normalized["meta_title"] = _truncate_meta_title(meta_title)

    meta_description = normalized.get("meta_description")
    if isinstance(meta_description, str):
        normalized["meta_description"] = _normalize_whitespace(meta_description)

    semantic_outline = normalized.get("semantic_outline")
    if isinstance(semantic_outline, list):
        normalized["semantic_outline"] = [
            _normalize_whitespace(section)
            for section in semantic_outline
            if isinstance(section, str) and _normalize_whitespace(section)
        ]

    secondary_keywords = normalized.get("secondary_keywords")
    if isinstance(secondary_keywords, list):
        normalized["secondary_keywords"] = [
            _normalize_whitespace(keyword)
            for keyword in secondary_keywords
            if isinstance(keyword, str) and _normalize_whitespace(keyword)
        ]

    for key in ("primary_keyword", "search_intent"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = _normalize_whitespace(value)

    return normalized


# ===========================================================================
# Schéma de validation Pydantic — Stratégie SEO stricte
# ===========================================================================

class SeoStrategy(BaseModel):
    """Stratégie SEO complète pour une Landing Page.

    Validé par Pydantic avant injection dans le State.
    Les validateurs garantissent le respect des best practices Google.
    """

    primary_keyword: str = Field(
        ...,
        min_length=2,
        max_length=80,
        description=(
            "Mot-clé principal ciblé pour cette page. "
            "Doit être une requête exacte issue de la recherche utilisateur. "
            "Ex: 'agence seo paris', 'logiciel crm pme', 'formation marketing digital'."
        ),
    )

    secondary_keywords: list[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description=(
            "Liste de 3 à 5 mots-clés secondaires (LSI keywords, longue traîne). "
            "Doivent être sémantiquement liés au primary_keyword. "
            "Ex: ['référencement naturel paris', 'consultant seo ile de france', 'audit seo gratuit']."
        ),
    )

    search_intent: Literal["informational", "navigational", "commercial", "transactional"] = Field(
        ...,
        description=(
            "Intention de recherche dominante du primary_keyword. "
            "- informational: l'utilisateur cherche à s'informer (guide, tutoriel). "
            "- navigational: l'utilisateur cherche une marque/site spécifique. "
            "- commercial: l'utilisateur compare des solutions avant achat. "
            "- transactional: l'utilisateur est prêt à acheter/s'inscrire maintenant."
        ),
    )

    meta_title: str = Field(
        ...,
        description=(
            "Balise <title> SEO de la page. "
            "DOIT contenir le primary_keyword en début de titre (idéalement dans les 30 premiers caractères). "
            "Format recommandé : '[Primary Keyword] — [Bénéfice] | [Brand]'. "
            "Longueur STRICTEMENT entre 30 et 60 caractères pour affichage optimal dans les SERPs."
        ),
    )

    meta_description: str = Field(
        ...,
        description=(
            "Balise <meta name='description'> SEO de la page. "
            "DOIT inclure le primary_keyword ET un appel à l'action implicite. "
            "Format recommandé : '[Accroche bénéfice]. [Preuve sociale ou USP]. [CTA soft]'. "
            "Longueur STRICTEMENT entre 120 et 160 caractères pour éviter la troncature Google."
        ),
    )

    semantic_outline: list[str] = Field(
        ...,
        min_length=4,
        max_length=8,
        description=(
            "Liste ordonnée des sections OBLIGATOIRES d'un point de vue SEO. "
            "Chaque item décrit une section de contenu stratégique pour le référencement. "
            "Ex: ['Hero optimisé pour le mot-clé principal', "
            "'Grille de fonctionnalités ciblant la longue traîne', "
            "'Bloc de contenu pour les requêtes LSI', "
            "'FAQ pour cibler les People Also Ask (PAA)']."
        ),
    )

    @field_validator("meta_title")
    @classmethod
    def validate_meta_title_length(cls, v: str) -> str:
        """Valide que le meta_title respecte les contraintes Google Search Central."""
        char_count = len(v)
        if char_count < 30:
            raise ValueError(
                f"meta_title trop court ({char_count} chars). "
                f"Minimum 30 caractères pour optimiser le CTR dans les SERPs."
            )
        if char_count > 60:
            raise ValueError(
                f"meta_title trop long ({char_count} chars). "
                f"Maximum 60 caractères pour éviter la troncature '...' dans Google."
            )
        return v

    @field_validator("meta_description")
    @classmethod
    def validate_meta_description_length(cls, v: str) -> str:
        """Valide que la meta_description respecte les contraintes Google."""
        char_count = len(v)
        if char_count < 120:
            raise ValueError(
                f"meta_description trop courte ({char_count} chars). "
                f"Minimum 120 caractères pour exploiter l'espace SERP disponible."
            )
        if char_count > 160:
            raise ValueError(
                f"meta_description trop longue ({char_count} chars). "
                f"Maximum 160 caractères pour éviter la troncature dans les résultats de recherche."
            )
        return v

    @field_validator("secondary_keywords")
    @classmethod
    def secondary_keywords_not_empty_strings(cls, v: list[str]) -> list[str]:
        """Filtre les chaînes vides ou whitespace dans les mots-clés secondaires."""
        cleaned = [kw.strip() for kw in v if kw.strip()]
        if len(cleaned) < 3:
            raise ValueError(
                f"Au moins 3 secondary_keywords valides requis. Reçu : {len(cleaned)}"
            )
        return cleaned


# ===========================================================================
# Prompt System — Expert SEO Technique Senior
# ===========================================================================

SEO_EXPERT_SYSTEM_PROMPT = """Tu es un Expert SEO Technique Senior avec 15 ans d'expérience.

CONTEXTE :
Tu reçois un résumé marketing dense d'une marque (USP, niche, cible, ton de voix, offres).
Tu dois traduire ces données marketing en une stratégie de référencement implacable pour une Landing Page optimisée SEO.

TA MISSION :
Générer un document JSON structuré contenant :

1. **primary_keyword** : Le mot-clé principal à cibler (volume élevé, intention claire).
   - Choisis une requête générique avec volume de recherche significatif.
   - Exemple : Si niche = "Agence SEO Paris" → primary_keyword = "agence seo paris".

2. **secondary_keywords** : 3 à 5 mots-clés LSI (Latent Semantic Indexing) ou longue traîne.
   - Requêtes sémantiquement liées au primary_keyword.
   - Ciblent des micro-intentions ou des questions spécifiques.
   - Exemple : ["référencement naturel paris", "consultant seo freelance", "audit seo technique gratuit"].

3. **search_intent** : L'intention de recherche dominante du primary_keyword.
   - informational (guide, définition)
   - navigational (nom de marque)
   - commercial (comparatif, "meilleur X")
   - transactional (achat, inscription)

4. **meta_title** : Balise <title> SEO ultra-optimisée.
   - DOIT inclure le primary_keyword dans les 30 premiers caractères.
   - Format : "[Primary Keyword] — [Bénéfice unique] | [Brand]"
   - Longueur STRICTE : entre 30 et 60 caractères (compte chaque caractère, espaces inclus).
   - Exemple : "Agence SEO Paris — Doublez votre trafic | Acme"

5. **meta_description** : Balise <meta description> optimisée.
   - DOIT inclure le primary_keyword ET un CTA soft.
   - Format : "[Accroche bénéfice]. [Preuve sociale]. [CTA]."
   - Longueur STRICTE : entre 120 et 160 caractères.
   - Exemple : "Acme SEO, agence spécialisée à Paris. +200% de trafic organique en 6 mois pour nos clients. Audit gratuit en 48h."

6. **semantic_outline** : Structure sémantique SEO de la page (4-8 sections).
   - Liste ordonnée des blocs de contenu OBLIGATOIRES pour le SEO.
   - Chaque section cible une intention sémantique spécifique (primary keyword, LSI, PAA, etc.).
   - Exemple :
     [
       "Hero optimisé pour 'agence seo paris' (H1 + CTA)",
       "Grille de fonctionnalités ciblant les LSI keywords",
       "Bloc de contenu longue-forme pour 'référencement naturel paris'",
       "FAQ ciblant les People Also Ask : 'Combien coûte le SEO ?', 'Combien de temps pour ranker ?'"
     ]

RÈGLES STRICTES (TRÈS IMPORTANT) :
- Le meta_title DOIT faire entre 30 et 60 caractères. Compte manuellement avant de répondre.
- La meta_description DOIT faire entre 120 et 160 caractères. Si tu dépasses ou si tu es trop court, RECOMMENCE.
- Les secondary_keywords doivent être différents du primary_keyword (pas de duplication).
- Le JSON final DOIT être conforme au schéma Pydantic SeoStrategy fourni.

OUTPUT FORMAT :
Retourne UNIQUEMENT un objet JSON valide (pas de markdown, pas de texte explicatif autour).
"""


# ===========================================================================
# Nœud LangGraph
# ===========================================================================

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    reraise=True,
)
async def seo_node(state: GraphState) -> dict[str, Any]:
    """Nœud LangGraph : Analyse SEO → SeoStrategy.

    Returns:
        dict avec clé "seo_silo" (SeoStrategy serialisé)
        OU clé "arbitre_errors" si échec (market_context vide, ValidationError).
    """
    market_context = state.get("market_context", {})

    if not market_context:
        logger.error("❌ SEO Node appelé sans market_context dans le State")
        return {
            "arbitre_errors": ["SEO Node : market_context vide ou absent dans le State"],
            "seo_silo": {},
        }

    logger.info("🎯 SEO Node démarré — Analyse stratégie sémantique...")

    usp = market_context.get("usp", "Non identifié")
    niche = market_context.get("niche", "Non identifié")
    target_audience = market_context.get("target_audience", "Non identifié")
    tone_of_voice = market_context.get("tone_of_voice", "professionnel")
    main_offers = market_context.get("main_offers", [])

    logger.info(f"📊 Market Context → Niche: '{niche}', USP: '{usp[:50]}...'")

    llm = ChatOpenAI(
        model=_settings.openai_model,
        temperature=_settings.llm_temperature,
        timeout=_settings.llm_timeout_seconds,
        max_retries=_settings.llm_max_retries,
        base_url=_settings.openai_api_base,
        api_key=_settings.effective_api_key,
    )

    parser = JsonOutputParser(pydantic_object=SeoStrategy)

    prompt_messages = [
        SystemMessage(content=SEO_EXPERT_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Données marketing à transformer en stratégie SEO :\n\n"
                f"- Niche : {niche}\n"
                f"- USP : {usp}\n"
                f"- Audience cible : {target_audience}\n"
                f"- Ton de voix : {tone_of_voice}\n"
                f"- Offres principales : {', '.join(main_offers)}\n\n"
                f"Retourne le JSON SeoStrategy conforme au schéma : {parser.get_format_instructions()}"
            )
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        seo_strategy_json = parser.parse(response.content)
    except Exception as exc:
        logger.error(f"❌ Échec de la génération LLM SEO : {exc}")
        return {
            "arbitre_errors": [f"SEO Node LLM generation failed: {exc}"],
            "seo_silo": {},
        }

    try:
        normalized_strategy = _normalize_seo_strategy_payload(seo_strategy_json)
        validated_strategy = SeoStrategy(**normalized_strategy)
    except ValidationError as exc:
        logger.error(f"❌ Validation Pydantic SEO échouée : {exc}")
        errors_summary = "; ".join([f"{e['loc'][0]}: {e['msg']}" for e in exc.errors()])
        return {
            "arbitre_errors": [f"SEO validation failed: {errors_summary}"],
            "seo_silo": {},
        }

    logger.info(
        f"✅ SEO Strategy validée. "
        f"Primary KW: '{validated_strategy.primary_keyword}', "
        f"Intent: '{validated_strategy.search_intent}', "
        f"Meta title: {len(validated_strategy.meta_title)} chars"
    )

    return {"seo_silo": validated_strategy.model_dump()}
