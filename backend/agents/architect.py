"""
agents/architect.py — Architect Node (Builder final / JSON Compiler).

Responsabilité : Assembler le GenerativeUISchema final pour Next.js.

Workflow :
    1. Lit le State validé par l'Arbitre (seo_silo, wireframe, copy_draft, market_context)
    2. Utilise un LLM "JSON Compiler" pour mapper les données vers le GenerativeUISchema
    3. Le LLM NE génère AUCUN contenu nouveau : il MAPPE uniquement les données existantes
    4. Valide le schéma final avec Pydantic (Discriminated Unions strictes)
    5. Retourne `{"generative_ui_schema": GenerativeUISchema}` prêt pour Next.js

Règle critique :
    - L'Architect ne CRÉE rien, il ASSEMBLE.
    - Il prend le WireframePlan (component_name) et remplit chaque UIComponent
      avec les textes du CopyDraft correspondants.
    - Toute ValidationError Pydantic ici est GRAVE → retour à arbitre_errors.
    - Le JSON final DOIT être conforme aux Discriminated Unions de generative_ui.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.state import GraphState
from backend.core.config import get_settings
from backend.schemas.generative_ui import (
    GenerativeUISchema,
    PageMetadata,
    HeroSectionSchema,
    FeatureGridSchema,
    FeatureItem,
    ContentBlockSchema,
    FAQSchema,
    FAQItem,
    CTASchema,
)

logger = logging.getLogger(__name__)

_settings = get_settings()


# ===========================================================================
# Prompt System — Ingénieur Frontend (JSON Compiler)
# ===========================================================================

ARCHITECT_SYSTEM_PROMPT = """Tu es un Ingénieur Frontend spécialisé en compilation de données structurées.

CONTEXTE :
Tu reçois un State validé contenant :
1. **SEO Strategy** : mots-clés, meta tags, semantic outline
2. **Wireframe (UX)** : structure de la page avec liste de composants UI
3. **Copy Draft** : tous les textes rédigés (headlines, benefits, CTAs, FAQ, etc.)
4. **Market Context** : niche, brand name, tone, USP

TA MISSION :
Générer un objet JSON final de type `GenerativeUISchema` en MAPPANT les données existantes.

⚠️ RÈGLE D'OR ABSOLUE :
- Tu NE génères AUCUN contenu nouveau.
- Tu NE rédiges AUCUN texte.
- Tu NE crées AUCUN code React/TSX.
- Tu es un COMPILATEUR : tu prends les données du State et tu les MAPPES vers la structure JSON finale.

⚠️ NE DUPLIQUE JAMAIS DE CONTENU :
- Si le Wireframe (UX) te demande 3 ContentBlocks mais que le CopyDraft ne contient qu'un seul texte de proposition de valeur (value_proposition_long), remplis UNIQUEMENT le premier ContentBlock avec ce texte.
- IGNORE et SUPPRIME les blocs excédentaires du Wireframe.
- Même règle pour tous les composants : 1 donnée source = 1 composant maximum. Pas de duplication.

STRUCTURE DU JSON FINAL (GenerativeUISchema) :

1. **page_slug** : slug kebab-case de la page (dérivé du primary_keyword SEO)
   Ex: "agence-seo-paris"

2. **brand_name** : nom de la marque (depuis market_context)

3. **seo_metadata** (PageMetadata) :
   - title : meta_title du SEO Strategy
   - description : meta_description du SEO Strategy
   - keywords : secondary_keywords du SEO Strategy
   - og_title, og_description, og_image_url : optionnels

4. **sections** : liste de UIComponents discriminés sur `component_type`
   Pour chaque section du Wireframe :
   - Lit le `component_name` (HeroSection, FeatureGrid, etc.)
   - Mappe vers le bon schéma Pydantic (Discriminated Union)
   - Remplit les champs avec les textes du CopyDraft correspondants

5. **generated_at** : timestamp UTC ISO 8601
6. **pipeline_version** : "1.0.0"

MAPPING WIREFRAME → COMPOSANTS UI :

- **component_name = "HeroSection"** →
  component_type: "HeroSection"
  headline: copy_draft.main_headline
  subheadline: copy_draft.subheadline
  cta_primary_label: copy_draft.call_to_actions[0]
  cta_primary_url: "/contact" (default)
  social_proof_label: copy_draft.social_proof_statement

- **component_name = "FeatureGrid"** →
  component_type: "FeatureGrid"
  section_title: "Nos avantages" (generic ou depuis copy)
  features: mapper copy_draft.key_benefits vers FeatureItem[]
    Chaque benefit → { icon_name: "Zap", title: benefit, description: benefit }

- **component_name = "ContentBlock"** →
  component_type: "ContentBlock"
  heading: "Pourquoi nous choisir ?" (generic)
  body_markdown: copy_draft.value_proposition_long
  image_url: null (optionnel)

- **component_name = "FAQ"** →
  component_type: "FAQ"
  section_title: "Questions fréquentes"
  items: mapper copy_draft.faq_items vers FAQItem[]

- **component_name = "CTABanner"** →
  component_type: "CTABanner"
  headline: "Prêt à passer à l'action ?" (generic ou depuis copy)
  cta_label: copy_draft.call_to_actions[1] ou [0] si un seul
  cta_url: "/contact"

RÈGLES STRICTES :
1. Chaque section DOIT avoir un `component_type` valide (HeroSection, FeatureGrid, ContentBlock, FAQ, CTABanner).
2. La première section DOIT être `component_type: "HeroSection"`.
3. Pas plus d'un HeroSection et un CTABanner par page.
4. Les champs DOIVENT être remplis avec les données EXACTES du State (pas d'invention).
5. Si une donnée manque, utilise une valeur par défaut raisonnable (ex: cta_url = "/contact").

OUTPUT FORMAT :
Retourne UNIQUEMENT un objet JSON conforme au schéma GenerativeUISchema.
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
async def architect_node(state: GraphState) -> dict[str, Any]:
    """Nœud LangGraph : Assemblage final → GenerativeUISchema.

    Returns:
        dict avec clé "generative_ui_schema" (GenerativeUISchema serialisé)
        OU clé "arbitre_errors" si ValidationError critique.
    """
    market_context = state.get("market_context", {})
    seo_silo = state.get("seo_silo", {})
    wireframe = state.get("wireframe", {})
    art_direction = state.get("art_direction", {})
    copy_draft = state.get("copy_draft", {})

    if not seo_silo or not wireframe or not art_direction or not copy_draft:
        logger.error("❌ Architect Node appelé sans données complètes dans le State")
        return {
            "arbitre_errors": ["Architect Node : State incomplet (seo_silo, wireframe, art_direction ou copy_draft manquant)"],
            "generative_ui_schema": {},
        }

    logger.info("🏗️ Architect Node démarré — Compilation du JSON final...")

    llm = ChatOpenAI(
        model=_settings.fast_model,
        temperature=0.1,  # Très bas : c'est du mapping strict, pas de créativité
        timeout=_settings.llm_timeout_seconds,
        max_retries=_settings.llm_max_retries,
        base_url=_settings.openai_api_base,
        api_key=_settings.effective_api_key,
    )

    parser = JsonOutputParser(pydantic_object=GenerativeUISchema)

    prompt_messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Voici le State validé à compiler en GenerativeUISchema :\n\n"
                f"MARKET CONTEXT :\n{market_context}\n\n"
                f"SEO STRATEGY :\n{seo_silo}\n\n"
                f"WIREFRAME (UX) :\n{wireframe}\n\n"
                f"ART DIRECTION (Design Tokens) :\n{art_direction}\n\n"
                f"COPY DRAFT :\n{copy_draft}\n\n"
                f"Retourne le JSON GenerativeUISchema conforme au schéma : {parser.get_format_instructions()}"
            )
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        schema_json = parser.parse(response.content)
    except Exception as exc:
        logger.error(f"❌ Échec de la génération LLM Architect : {exc}")
        return {
            "arbitre_errors": [f"Architect Node LLM generation failed: {exc}"],
            "generative_ui_schema": {},
        }

    # -----------------------------------------------------------------------
    # Validation Pydantic STRICTE du schéma final
    # -----------------------------------------------------------------------
    try:
        # Ajout des champs manquants si le LLM les a oubliés
        if "generated_at" not in schema_json:
            schema_json["generated_at"] = datetime.now(tz=timezone.utc)
        if "pipeline_version" not in schema_json:
            schema_json["pipeline_version"] = "1.0.0"
        # Injection directe des ArtDirectionTokens si le LLM les a oubliés
        if "art_direction" not in schema_json and art_direction:
            schema_json["art_direction"] = art_direction

        validated_schema = GenerativeUISchema(**schema_json)
    except ValidationError as exc:
        logger.error(f"❌ Validation Pydantic Architect échouée : {exc}")
        errors_summary = "; ".join([f"{e['loc']}: {e['msg']}" for e in exc.errors()])
        return {
            "arbitre_errors": [f"Architect validation failed (CRITIQUE): {errors_summary}"],
            "generative_ui_schema": {},
        }

    logger.info(
        f"✅ GenerativeUISchema validé. "
        f"Page: '{validated_schema.page_slug}', "
        f"Brand: '{validated_schema.brand_name}', "
        f"{len(validated_schema.sections)} sections : "
        f"{[s.component_type for s in validated_schema.sections]}"
    )

    return {"generative_ui_schema": validated_schema.model_dump()}
