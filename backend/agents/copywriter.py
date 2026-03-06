"""
agents/copywriter.py — Copywriter Node (4e nœud du pipeline, s'exécute en parallèle avec UX).

Responsabilité : Rédiger tout le contenu persuasif de la page basé sur la stratégie SEO.

Workflow :
    1. Lit `market_context` et `seo_silo` via build_copywriter_context() (compression)
    2. Utilise un LLM Copywriter Senior (Direct Response) pour rédiger :
       - Headlines (H1 + sous-titres)
       - Key benefits (bénéfices orientés résultat)
       - CTAs (calls-to-action)
       - FAQ (questions/réponses)
       - Tout autre contenu textuel nécessaire
    3. Intègre NATURELLEMENT le primary_keyword et les secondary_keywords
    4. Respecte strictement le tone_of_voice défini dans market_context
    5. Retourne `{"copy_draft": CopyDraft}` fusionné dans le State

Règle critique :
    - Le contenu DOIT intégrer les keywords SEO de façon naturelle (pas de keyword stuffing)
    - Le ton DOIT matcher le tone_of_voice (professionnel, décontracté, technique, etc.)
    - Orientation Direct Response : chaque phrase doit pousser vers l'action
    - Le Copywriter ne sait PAS encore dans quels composants UI ce contenu ira
      (c'est le rôle de l'Architect qui viendra après)
"""

from __future__ import annotations

import logging
import re
from typing import Any

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


def _contains_keyword(text: str, keyword: str) -> bool:
    normalized_text = _normalize_whitespace(text).lower()
    normalized_keyword = _normalize_whitespace(keyword).lower()
    return bool(normalized_keyword) and normalized_keyword in normalized_text


def _ensure_primary_keyword_in_headline(headline: str, primary_keyword: str) -> str:
    normalized_headline = _normalize_whitespace(headline)
    normalized_keyword = _normalize_whitespace(primary_keyword)

    if not normalized_keyword:
        return normalized_headline

    if _contains_keyword(normalized_headline, normalized_keyword):
        return normalized_headline

    candidate = f"{normalized_keyword} — {normalized_headline}".strip()
    if len(candidate) <= 100:
        return candidate

    remaining = max(0, 100 - len(normalized_keyword) - 3)
    trimmed_headline = normalized_headline[:remaining].rstrip(" ,;:-|—")
    return f"{normalized_keyword} — {trimmed_headline}".strip()


def _normalize_copy_payload(payload: dict[str, Any], primary_keyword: str) -> dict[str, Any]:
    normalized = dict(payload)

    main_headline = normalized.get("main_headline")
    if isinstance(main_headline, str):
        normalized["main_headline"] = _ensure_primary_keyword_in_headline(
            main_headline,
            primary_keyword,
        )

    for key in ("subheadline", "social_proof_statement", "value_proposition_long"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = _normalize_whitespace(value)

    for key in ("key_benefits", "call_to_actions"):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = [
                _normalize_whitespace(item)
                for item in value
                if isinstance(item, str) and _normalize_whitespace(item)
            ]

    faq_items = normalized.get("faq_items")
    if isinstance(faq_items, list):
        cleaned_faq_items: list[dict[str, Any]] = []
        for item in faq_items:
            if not isinstance(item, dict):
                continue
            question = item.get("question")
            answer = item.get("answer")
            if isinstance(question, str) and isinstance(answer, str):
                cleaned_faq_items.append(
                    {
                        "question": _normalize_whitespace(question),
                        "answer": _normalize_whitespace(answer),
                    }
                )
        normalized["faq_items"] = cleaned_faq_items

    return normalized


# ===========================================================================
# Schéma de validation Pydantic — Copy Draft
# ===========================================================================

class FAQItemDraft(BaseModel):
    """Une paire question/réponse pour la section FAQ."""

    question: str = Field(
        ...,
        min_length=10,
        max_length=150,
        description=(
            "Question formulée comme un utilisateur la poserait dans Google. "
            "Doit cibler une requête People Also Ask ou une objection client. "
            "Ex: 'Combien coûte le SEO en moyenne ?', 'Combien de temps pour voir des résultats ?'."
        ),
    )

    answer: str = Field(
        ...,
        min_length=40,
        max_length=500,
        description=(
            "Réponse concise et directe. La première phrase DOIT répondre directement. "
            "Ensuite développer avec preuve ou exemple. Ton orienté réassurance."
        ),
    )


class CopyDraft(BaseModel):
    """Contenu textuel complet de la page.

    Rédigé par le Copywriter avant mapping vers les composants UI (rôle de l'Architect).
    """

    main_headline: str = Field(
        ...,
        min_length=10,
        max_length=100,
        description=(
            "Titre principal H1 de la page. DOIT contenir le primary_keyword. "
            "Formule orientée bénéfice client (pas feature produit). "
            "Ex: 'Doublez votre trafic organique en 6 mois' (pas 'Nos services SEO')."
        ),
    )

    subheadline: str = Field(
        ...,
        min_length=20,
        max_length=200,
        description=(
            "Sous-titre H2 qui clarifie la promesse du headline. "
            "Répond à 'Pour qui ?' et 'Quel résultat concret ?'. "
            "Ex: 'Acme SEO accompagne les PME parisiennes avec une stratégie data-driven et des contenus optimisés.'"
        ),
    )

    key_benefits: list[str] = Field(
        ...,
        min_length=3,
        max_length=6,
        description=(
            "Liste de 3-6 bénéfices clés orientés RÉSULTAT client (pas caractéristiques produit). "
            "Chaque bénéfice = 1 phrase courte (8-15 mots). "
            "Doit intégrer naturellement les secondary_keywords SEO. "
            "Ex: ['Audit SEO technique complet en 48h', "
            "'Suivi de positions temps réel sur vos mots-clés', "
            "'Contenus optimisés qui convertent ET rankent']."
        ),
    )

    call_to_actions: list[str] = Field(
        ...,
        min_length=2,
        max_length=4,
        description=(
            "Liste de 2-4 CTAs (calls-to-action) utilisables dans la page. "
            "Chaque CTA = verbe d'action + bénéfice implicite (3-6 mots max). "
            "Ex: ['Démarrer gratuitement', 'Demander un audit SEO', 'Voir nos résultats', 'Parler à un expert']."
        ),
    )

    faq_items: list[FAQItemDraft] = Field(
        ...,
        min_length=3,
        max_length=8,
        description=(
            "Liste de 3-8 paires question/réponse pour la section FAQ. "
            "Questions = requêtes People Also Ask ou objections clients classiques. "
            "Réponses = concises, directes, réassurantes."
        ),
    )

    social_proof_statement: str = Field(
        ...,
        max_length=100,
        description=(
            "Courte phrase de preuve sociale à placer sous le CTA principal. "
            "Ex: 'Rejoignez 2 000+ marketeurs qui nous font confiance', "
            "'Note moyenne 4.9/5 sur Google (200+ avis)', "
            "'500+ sites propulsés en première page Google'."
        ),
    )

    value_proposition_long: str = Field(
        ...,
        min_length=100,
        max_length=600,
        description=(
            "Paragraphe de contenu longue-forme (2-4 phrases) développant la proposition de valeur. "
            "Utilisé dans un ContentBlock pour le SEO on-page. "
            "DOIT intégrer naturellement le primary_keyword ET 1-2 secondary_keywords. "
            "Ton orienté bénéfice + preuve sociale ou cas d'usage concret."
        ),
    )

    @field_validator("key_benefits")
    @classmethod
    def benefits_not_empty(cls, v: list[str]) -> list[str]:
        """Filtre les bénéfices vides et valide le format."""
        cleaned = [b.strip() for b in v if b.strip()]
        if len(cleaned) < 3:
            raise ValueError(f"Au moins 3 key_benefits requis. Reçu : {len(cleaned)}")
        return cleaned

    @field_validator("call_to_actions")
    @classmethod
    def ctas_not_empty(cls, v: list[str]) -> list[str]:
        """Filtre les CTAs vides."""
        cleaned = [cta.strip() for cta in v if cta.strip()]
        if len(cleaned) < 2:
            raise ValueError(f"Au moins 2 CTAs requis. Reçu : {len(cleaned)}")
        return cleaned


# ===========================================================================
# Prompt System — Copywriter Senior (Direct Response)
# ===========================================================================

COPYWRITER_SYSTEM_PROMPT = """Tu es un Copywriter Senior spécialisé en Direct Response et en SEO copywriting.

CONTEXTE :
Tu reçois :
1. Un résumé marketing (USP, niche, audience cible, ton de voix)
2. Une stratégie SEO (mots-clés à intégrer naturellement, search intent)

TA MISSION :
Rédiger TOUT le contenu textuel d'une landing page optimisée pour :
- La CONVERSION (chaque phrase pousse vers l'action)
- Le SEO (intégration naturelle des keywords, pas de keyword stuffing)
- La COHÉRENCE de ton (strictement respecter le tone_of_voice fourni)

TU DOIS RÉDIGER :

1. **main_headline** (H1) :
   - Formule orientée BÉNÉFICE client (pas feature produit)
   - DOIT contenir le primary_keyword
   - 10-100 caractères
   - Ex: "Agence SEO Paris — Doublez votre trafic en 6 mois"

2. **subheadline** (H2) :
   - Clarifie la promesse du headline
   - Répond à "Pour qui ?" et "Quel résultat ?"
   - 20-200 caractères
   - Ex: "Acme SEO accompagne les PME avec une stratégie data-driven et des contenus qui convertissent."

3. **key_benefits** (3-6 items) :
   - Bénéfices orientés RÉSULTAT (pas caractéristiques)
   - Intègre naturellement les secondary_keywords
   - 8-15 mots par bénéfice
   - Ex: "Audit SEO technique complet en 48h"

4. **call_to_actions** (2-4 CTAs) :
   - Verbe d'action + bénéfice implicite
   - 3-6 mots max
   - Ex: "Démarrer gratuitement", "Demander un audit", "Voir nos cas clients"

5. **faq_items** (3-8 paires Q&R) :
   - Questions = People Also Ask ou objections clients
   - Réponses = concises (40-500 chars), directes, réassurantes
   - Ex Q: "Combien de temps pour voir des résultats SEO ?"
   - Ex R: "Les premiers résultats apparaissent entre 3 et 6 mois selon la concurrence. Nos clients constatent en moyenne +40% de trafic après 4 mois."

6. **social_proof_statement** :
   - Courte preuve sociale sous le CTA
   - Max 100 caractères
   - Ex: "Rejoignez 2 000+ entreprises qui nous font confiance"

7. **value_proposition_long** :
   - Paragraphe 2-4 phrases (100-600 chars)
   - Développe la proposition de valeur
   - DOIT intégrer primary_keyword + 1-2 secondary_keywords NATURELLEMENT
   - Ton orienté bénéfice + preuve ou cas d'usage

RÈGLES STRICTES :
- **Ton de voix** : RESPECTE STRICTEMENT le tone_of_voice fourni (professionnel, décontracté, technique, etc.)
- **SEO** : Intègre les keywords NATURELLEMENT (pas de répétition forcée, pas de keyword stuffing)
- **Direct Response** : Chaque phrase doit créer du désir ou pousser vers l'action
- **Clarté** : Phrases courtes et percutantes. Pas de jargon inutile.
- **Orientation client** : Bénéfices avant features. "Vous doublez" avant "Nous faisons".
- **CRÉATIVITÉ ET VARIÉTÉ** : Lorsque tu génères des listes (ex: key_benefits, faq_items), tu dois être CRÉATIF et VARIÉ. Les titres et les descriptions ne doivent JAMAIS être identiques. Pour les FeatureGrid, développe toujours la description avec un argument supplémentaire différent du titre.

OUTPUT FORMAT :
Retourne UNIQUEMENT un objet JSON conforme au schéma CopyDraft.
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
async def copywriter_node(state: GraphState) -> dict[str, Any]:
    """Nœud LangGraph : Rédaction contenu persuasif → CopyDraft.

    Returns:
        dict avec clé "copy_draft" (CopyDraft serialisé)
        OU clé "arbitre_errors" si échec (seo_silo vide, ValidationError).
    """
    market_context = state.get("market_context", {})
    seo_silo = state.get("seo_silo", {})

    if not seo_silo or not market_context:
        logger.error("❌ Copywriter Node appelé sans market_context ou seo_silo")
        return {
            "arbitre_errors": ["Copywriter Node : market_context ou seo_silo manquant dans le State"],
            "copy_draft": {},
        }

    logger.info("✍️ Copywriter Node démarré — Rédaction contenu persuasif...")

    usp = market_context.get("usp", "")
    niche = market_context.get("niche", "")
    target_audience = market_context.get("target_audience", "")
    tone_of_voice = market_context.get("tone_of_voice", "professionnel")
    main_offers = market_context.get("main_offers", [])

    primary_keyword = seo_silo.get("primary_keyword", "")
    secondary_keywords = seo_silo.get("secondary_keywords", [])
    search_intent = seo_silo.get("search_intent", "commercial")

    logger.info(
        f"📝 Context → Niche: '{niche}', Tone: '{tone_of_voice}', "
        f"Primary KW: '{primary_keyword}', Intent: '{search_intent}'"
    )

    llm = ChatOpenAI(
        model=_settings.openai_model,
        temperature=_settings.llm_temperature,
        timeout=_settings.llm_timeout_seconds,
        max_retries=_settings.llm_max_retries,
        base_url=_settings.openai_api_base,
        api_key=_settings.effective_api_key,
    )

    parser = JsonOutputParser(pydantic_object=CopyDraft)

    prompt_messages = [
        SystemMessage(content=COPYWRITER_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Données marketing et SEO pour la rédaction :\n\n"
                f"MARKETING :\n"
                f"- Niche : {niche}\n"
                f"- USP : {usp}\n"
                f"- Audience cible : {target_audience}\n"
                f"- Ton de voix : {tone_of_voice} (RESPECTE STRICTEMENT ce ton)\n"
                f"- Offres principales : {', '.join(main_offers)}\n\n"
                f"SEO (keywords à intégrer NATURELLEMENT) :\n"
                f"- Primary keyword : {primary_keyword}\n"
                f"- Secondary keywords : {', '.join(secondary_keywords)}\n"
                f"- Search intent : {search_intent}\n\n"
                f"Retourne le JSON CopyDraft conforme au schéma : {parser.get_format_instructions()}"
            )
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        copy_json = parser.parse(response.content)
    except Exception as exc:
        logger.error(f"❌ Échec de la génération LLM Copywriter : {exc}")
        return {
            "arbitre_errors": [f"Copywriter Node LLM generation failed: {exc}"],
            "copy_draft": {},
        }

    try:
        normalized_copy = _normalize_copy_payload(copy_json, primary_keyword)
        validated_copy = CopyDraft(**normalized_copy)
    except ValidationError as exc:
        logger.error(f"❌ Validation Pydantic Copywriter échouée : {exc}")
        errors_summary = "; ".join([f"{e['loc']}: {e['msg']}" for e in exc.errors()])
        return {
            "arbitre_errors": [f"Copywriter validation failed: {errors_summary}"],
            "copy_draft": {},
        }

    logger.info(
        f"✅ Copy validé. "
        f"Headline: '{validated_copy.main_headline[:60]}...', "
        f"{len(validated_copy.key_benefits)} benefits, "
        f"{len(validated_copy.faq_items)} FAQ items"
    )

    return {
        "copy_draft": validated_copy.model_dump(),
        "arbitre_errors": [],
    }
