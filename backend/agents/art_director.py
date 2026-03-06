"""
agents/art_director.py — Art Director Node (Directeur Artistique Senior).

Responsabilité : Analyser le market_context et générer les ArtDirectionTokens
pour transformer les sites génériques en expériences visuelles niveau Awwwards.

Workflow :
    1. Lit `market_context` via le State
    2. Analyse la niche, le tone_of_voice et l'USP pour déterminer la vibe visuelle
    3. Utilise un LLM Directeur Artistique pour choisir :
       - design_vibe (swiss_editorial, neo_brutalism, minimalist_tech, organic_elegant)
       - typography_style (sans_serif_heavy, serif_elegant, monospaced_tech)
       - animation_feeling (snappy_springs, smooth_ease, none)
       - color_palette_hex (3-5 couleurs générées mathématiquement)
    4. Retourne `{"art_direction": ArtDirectionTokens}` fusionné dans le State

Règle critique :
    - L'Art Director s'exécute en PARALLÈLE de UX et Copywriter
    - Il ne génère JAMAIS de code CSS/Tailwind, uniquement des tokens JSON
    - Les choix doivent être radicaux et assumés (pas de "safe design")
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.state import GraphState
from backend.core.config import get_settings
from backend.schemas.generative_ui import ArtDirectionTokens

logger = logging.getLogger(__name__)

_settings = get_settings()


# ===========================================================================
# Prompt System — Directeur Artistique Senior (Awwwards Jury)
# ===========================================================================

ART_DIRECTOR_SYSTEM_PROMPT = """Tu es un Directeur Artistique Senior, membre du jury Awwwards et SiteInspire.

CONTEXTE :
Tu reçois un brief marketing (niche, USP, tone_of_voice, audience cible).
Ta mission est de définir l'identité visuelle RADICALE du site web généré.

⚠️ RÈGLE D'OR ABSOLUE :
Tu NE fais PAS de l'UI classique "Boring SaaS". Tu crées des identités de marque
qui marquent les esprits, qui cassent les codes, qui sont mémorables.

TA MISSION :
Générer les ArtDirectionTokens qui définiront TOUTE l'identité visuelle du site :
1. **design_vibe** : La vibe globale (swiss_editorial, neo_brutalism, minimalist_tech, organic_elegant)
2. **typography_style** : Le style typographique (sans_serif_heavy, serif_elegant, monospaced_tech)
3. **animation_feeling** : L'approche des animations (snappy_springs, smooth_ease, none)
4. **color_palette_hex** : 3-5 couleurs HEX générées mathématiquement

GUIDE DE DÉCISION (EXEMPLES CONCRETS) :

**SaaS B2B Technique (ex: Vercel, Linear, Raycast)** :
- design_vibe: "minimalist_tech"
- typography_style: "sans_serif_heavy"
- animation_feeling: "snappy_springs"
- color_palette_hex: ["#0A0A0A", "#FAFAFA", "#3B82F6", "#E5E5E5"]
→ Monochrome, grilles parfaites, micro-interactions subtiles, glassmorphism

**Agence Créative / Studio Design (ex: Stripe, Figma)** :
- design_vibe: "swiss_editorial"
- typography_style: "sans_serif_heavy"
- animation_feeling: "smooth_ease"
- color_palette_hex: ["#000000", "#FFFFFF", "#0066FF", "#F5F5F5"]
→ Grilles strictes, typographie suisse, layouts asymétriques, espaces blancs généreux

**Produit Grand Public Playful (ex: Gumroad, Notion)** :
- design_vibe: "neo_brutalism"
- typography_style: "sans_serif_heavy"
- animation_feeling: "snappy_springs"
- color_palette_hex: ["#FF6B35", "#004E89", "#FFEB3B", "#000000", "#FFFFFF"]
→ Bordures épaisses noires, ombres portées dures, couleurs saturées, anti-design assumé

**Restaurant / Lifestyle / Premium (ex: Airbnb, Kinfolk)** :
- design_vibe: "organic_elegant"
- typography_style: "serif_elegant"
- animation_feeling: "smooth_ease"
- color_palette_hex: ["#2D3748", "#F7FAFC", "#D69E2E", "#EDF2F7"]
→ Courbes douces, dégradés subtils, typographie serif, animations fluides

RÈGLES STRICTES :

1. **Cohérence Totale** :
   - Si tu choisis "neo_brutalism", la palette DOIT être saturée et contrastée
   - Si tu choisis "minimalist_tech", la palette DOIT être monochrome
   - Si tu choisis "organic_elegant", la palette DOIT être douce et naturelle

2. **Contraste WCAG AA** :
   - Toutes les couleurs doivent respecter un ratio de contraste 4.5:1 minimum
   - Vérifie que primary/secondary sont lisibles sur neutral_light/dark

3. **Mathématiques des Couleurs** :
   - Utilise des harmonies de couleurs (complémentaires, triadiques, analogues)
   - Pas de couleurs aléatoires : chaque couleur doit avoir une raison d'être

4. **Radicalité Assumée** :
   - Ne choisis JAMAIS "safe design" par défaut
   - Si la marque est technique → assume le monochrome radical
   - Si la marque est créative → assume l'asymétrie et les couleurs vives
   - Si la marque est premium → assume le serif et les espaces blancs généreux

OUTPUT FORMAT :
Retourne UNIQUEMENT un objet JSON conforme au schéma ArtDirectionTokens.
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
async def art_director_node(state: GraphState) -> dict[str, Any]:
    """Nœud LangGraph : Génération des ArtDirectionTokens → Design System.

    Returns:
        dict avec clé "art_direction" (ArtDirectionTokens serialisé)
        OU clé "arbitre_errors" si échec (market_context vide, ValidationError).
    """
    market_context = state.get("market_context", {})

    if not market_context:
        logger.error("❌ Art Director Node appelé sans market_context dans le State")
        return {
            "arbitre_errors": ["Art Director Node : market_context vide ou absent dans le State"],
            "art_direction": {},
        }

    logger.info("🎨 Art Director Node démarré — Génération de l'identité visuelle...")

    niche = market_context.get("niche", "Non identifié")
    usp = market_context.get("usp", "Non identifié")
    target_audience = market_context.get("target_audience", "Non identifié")
    tone_of_voice = market_context.get("tone_of_voice", "professionnel")
    main_offers = market_context.get("main_offers", [])

    logger.info(
        f"🎨 Context → Niche: '{niche}', Tone: '{tone_of_voice}', "
        f"USP: '{usp[:50]}...'"
    )

    llm = ChatOpenAI(
        model=_settings.openai_model,
        temperature=0.3,  # Légèrement créatif mais cohérent
        timeout=_settings.llm_timeout_seconds,
        max_retries=_settings.llm_max_retries,
        base_url=_settings.openai_api_base,
        api_key=_settings.effective_api_key,
    )

    parser = JsonOutputParser(pydantic_object=ArtDirectionTokens)

    prompt_messages = [
        SystemMessage(content=ART_DIRECTOR_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Brief marketing pour la direction artistique :\n\n"
                f"MARQUE :\n"
                f"- Niche : {niche}\n"
                f"- USP : {usp}\n"
                f"- Audience cible : {target_audience}\n"
                f"- Ton de voix : {tone_of_voice}\n"
                f"- Offres principales : {', '.join(main_offers)}\n\n"
                f"Génère les ArtDirectionTokens pour créer une identité visuelle "
                f"RADICALE et MÉMORABLE qui correspond parfaitement à cette marque.\n\n"
                f"Retourne le JSON ArtDirectionTokens conforme au schéma : {parser.get_format_instructions()}"
            )
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        art_direction_json = parser.parse(response.content)
    except Exception as exc:
        logger.error(f"❌ Échec de la génération LLM Art Director : {exc}")
        return {
            "arbitre_errors": [f"Art Director Node LLM generation failed: {exc}"],
            "art_direction": {},
        }

    try:
        validated_tokens = ArtDirectionTokens(**art_direction_json)
    except ValidationError as exc:
        logger.error(f"❌ Validation Pydantic Art Director échouée : {exc}")
        errors_summary = "; ".join([f"{e['loc'][0]}: {e['msg']}" for e in exc.errors()])
        return {
            "arbitre_errors": [f"Art Director validation failed: {errors_summary}"],
            "art_direction": {},
        }

    logger.info(
        f"✅ ArtDirectionTokens validés. "
        f"Vibe: '{validated_tokens.design_vibe}', "
        f"Typo: '{validated_tokens.typography_style}', "
        f"Anim: '{validated_tokens.animation_feeling}', "
        f"Palette: {validated_tokens.color_palette_hex}"
    )

    return {"art_direction": validated_tokens.model_dump()}
