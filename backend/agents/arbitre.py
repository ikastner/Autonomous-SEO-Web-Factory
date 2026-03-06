"""
agents/arbitre.py — Arbitre Node (Gatekeeper / Directeur Qualité).

Responsabilité : Inspecter le State complet et décider si on avance ou recule.

Workflow :
    1. Vérifie si `arbitre_errors` contient déjà des erreurs (issues des validateurs Pydantic)
       → Si oui, pas besoin de LLM : route directement vers le nœud fautif
    2. Vérifie `retry_count` > MAX_RETRY
       → Si oui, fail-safe : route vers "END" pour éviter boucles infinies coûteuses
    3. Sinon, appelle un LLM Directeur Qualité pour valider la cohérence :
       - Wireframe (UX) vs CopyDraft : le texte rentre-t-il dans les blocs prévus ?
       - SEO keywords : sont-ils présents dans le copy ?
       - Cohérence globale marque/ton/cible

Règle critique :
    - L'Arbitre est IMPITOYABLE : si une incohérence est détectée, il rejette.
    - Chaque rejet incrémente `retry_count` et route vers le nœud fautif.
    - Après MAX_RETRY rejets, il laisse passer (fail-safe) pour éviter les coûts API explosifs.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.state import GraphState, has_exceeded_retries, is_arbitre_ok, MAX_RETRY
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _contains_primary_keyword(main_headline: str, primary_keyword: str) -> bool:
    normalized_headline = _normalize_whitespace(main_headline).casefold()
    normalized_keyword = _normalize_whitespace(primary_keyword).casefold()
    return bool(normalized_keyword) and normalized_keyword in normalized_headline


# ===========================================================================
# Schéma de validation Pydantic — Décision de l'Arbitre
# ===========================================================================

class ArbitreDecision(BaseModel):
    """Décision de validation du Directeur Qualité.

    Détermine si le pipeline peut avancer vers l'Architect ou doit revenir
    à un nœud précédent pour correction.
    """

    is_approved: bool = Field(
        ...,
        description=(
            "True si le State est cohérent et peut passer à l'Architect. "
            "False si des incohérences nécessitent un retry d'un nœud spécifique."
        ),
    )

    feedback_reason: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description=(
            "Raison détaillée de l'approbation ou du rejet. "
            "Si rejeté, DOIT expliquer précisément quelle incohérence a été détectée. "
            "Ex: 'Le wireframe prévoit une FeatureGrid à 3 colonnes, mais le copy ne fournit que 2 bénéfices.' "
            "Ex: 'Le primary_keyword \"agence seo paris\" est absent du main_headline du copy.'"
        ),
    )

    route_to: Literal["SEO", "UX", "Copywriter", "Architect", "END"] = Field(
        ...,
        description=(
            "Où le graphe doit router ensuite. "
            "- 'Architect' si approuvé (is_approved=True). "
            "- 'SEO' / 'UX' / 'Copywriter' si rejeté (nœud fautif à re-exécuter). "
            "- 'END' si max retries atteint (fail-safe)."
        ),
    )


# ===========================================================================
# Prompt System — Directeur Qualité & Conversion
# ===========================================================================

ARBITRE_SYSTEM_PROMPT = """Tu es un Directeur Qualité et Conversion ultra-exigeant.

CONTEXTE :
Trois agents IA ont travaillé en parallèle :
1. **SEO Agent** : a défini la stratégie sémantique (keywords, meta tags, semantic_outline)
2. **UX Agent** : a créé un wireframe (structure des sections UI)
3. **Copywriter Agent** : a rédigé le contenu textuel persuasif

Tu reçois l'output des trois agents. Ta mission est de vérifier leur COHÉRENCE.

TA MISSION :
Inspecter le State et détecter toute incohérence entre SEO / UX / Copy qui pourrait :
- Nuire au référencement (keywords manquants ou mal intégrés)
- Casser le parcours utilisateur (texte ne rentrant pas dans les blocs UX)
- Diluer la conversion (CTAs incohérents, ton discordant)

VÉRIFICATIONS OBLIGATOIRES :

1. **Cohérence UX ↔ Copy** :
   - Le wireframe définit X sections de type Y. Le copy fournit-il le bon type de contenu pour chaque section ?
   - Ex: Si wireframe = "FeatureGrid 3 colonnes" → le copy doit avoir 3+ key_benefits.
   - Ex: Si wireframe = "FAQ" → le copy doit avoir faq_items.

2. **Cohérence SEO ↔ Copy** :
   - Le primary_keyword est-il présent dans le main_headline du copy ?
     IMPORTANT : Pour vérifier la présence d'un mot-clé, sois insensible à la casse, aux majuscules ou aux légères variations d'accents. Si le sens et les mots sont là, valide.
   - Les secondary_keywords sont-ils intégrés naturellement dans les key_benefits ou value_proposition_long ?
   - Les meta_title et meta_description SEO sont-ils cohérents avec le copy rédigé ?

3. **Cohérence globale marque** :
   - Le tone_of_voice défini dans market_context est-il respecté dans le copy ?
   - L'USP de la marque est-elle clairement exprimée dans le subheadline ou value_proposition_long ?

RÈGLES DE DÉCISION :
- **SOIS IMPITOYABLE** : la moindre incohérence = REJET.
- Si une section UX n'a pas de contenu correspondant dans le copy → REJETER vers "Copywriter".
- Si le primary_keyword SEO est absent du headline → REJETER vers "Copywriter".
- Si le wireframe définit 4 sections mais le copy en oublie → REJETER vers "UX" ou "Copywriter" (selon ce qui manque).
- Si TOUT est cohérent → APPROUVER et router vers "Architect".

OUTPUT FORMAT :
Retourne UNIQUEMENT un objet JSON conforme au schéma ArbitreDecision.
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
async def arbitre_node(state: GraphState) -> dict[str, Any]:
    """Nœud LangGraph : Validation cohérence → Routing conditionnel.

    Returns:
        dict avec clés :
        - "faulty_node" : str | None (où router si rejeté)
        - "retry_count" : int (incrémenté si rejeté)
        - "arbitre_errors" : list[str] (feedback de l'Arbitre)
    """
    existing_errors = state.get("arbitre_errors", [])
    retry_count = state.get("retry_count", 0)

    # -----------------------------------------------------------------------
    # CAS 1 : Des erreurs Pydantic existent déjà (issues des nœuds précédents)
    # -----------------------------------------------------------------------
    if existing_errors:
        logger.warning(f"⚠️ Arbitre détecte {len(existing_errors)} erreur(s) Pydantic pré-existantes")

        # Déterminer le nœud fautif depuis le message d'erreur
        faulty_node = "architect_node"  # Par défaut
        for error in existing_errors:
            if "Scout" in error:
                faulty_node = "scout_node"
                break
            elif "SEO" in error:
                faulty_node = "seo_node"
                break
            elif "UX" in error:
                faulty_node = "ux_node"
                break
            elif "Copywriter" in error:
                faulty_node = "copywriter_node"
                break

        # Fail-safe : max retries atteint
        if has_exceeded_retries(state):
            logger.error(
                f"🔴 MAX_RETRY={MAX_RETRY} atteint. Passage forcé vers Architect malgré les erreurs."
            )
            return {
                "faulty_node": "architect_node",
                "retry_count": 0,
                "arbitre_errors": [f"[FAIL-SAFE] {e}" for e in existing_errors],
            }

        logger.error(f"🔴 REJECTED (Pydantic errors) → {faulty_node} (retry #{retry_count + 1})")
        return {
            "faulty_node": faulty_node,
            "retry_count": 1,
            "arbitre_errors": existing_errors,
        }

    # -----------------------------------------------------------------------
    # CAS 2 : Fail-safe — max retries atteint sans erreurs explicites
    # -----------------------------------------------------------------------
    if has_exceeded_retries(state):
        logger.warning(
            f"⚠️ MAX_RETRY={MAX_RETRY} atteint sans erreurs explicites. Passage forcé vers Architect."
        )
        return {
            "faulty_node": "architect_node",
            "retry_count": 0,
            "arbitre_errors": [],
        }

    # -----------------------------------------------------------------------
    # CAS 3 : Validation LLM (pas d'erreurs Pydantic, pas de max retry)
    # -----------------------------------------------------------------------
    logger.info("⚖️ Arbitre démarre l'analyse de cohérence LLM...")

    market_context = state.get("market_context", {})
    seo_silo = state.get("seo_silo", {})
    wireframe = state.get("wireframe", {})
    copy_draft = state.get("copy_draft", {})

    # Vérification basique : si un élément clé manque, rejet immédiat
    if not seo_silo or not wireframe or not copy_draft:
        logger.error("❌ State incomplet : seo_silo, wireframe ou copy_draft manquant")
        return {
            "faulty_node": "END",
            "retry_count": 0,
            "arbitre_errors": ["State incomplet : données manquantes pour validation"],
        }

    primary_keyword = seo_silo.get("primary_keyword", "")
    main_headline = copy_draft.get("main_headline", "")

    if isinstance(primary_keyword, str) and isinstance(main_headline, str):
        if not _contains_primary_keyword(main_headline, primary_keyword):
            logger.error(
                "🔴 REJECTED (deterministic check) → Copywriter | "
                "Le primary_keyword est absent du main_headline"
            )
            return {
                "faulty_node": "copywriter_node",
                "retry_count": 1,
                "arbitre_errors": [
                    f"Arbitre rejection: Le primary_keyword '{primary_keyword}' est absent du main_headline du copy."
                ],
            }

    llm = ChatOpenAI(
        model=_settings.reasoning_model,
        temperature=0.0,  # Strictement 0.0 pour maximiser le déterminisme
        timeout=_settings.llm_timeout_seconds,
        max_retries=_settings.llm_max_retries,
        base_url=_settings.openai_api_base,
        api_key=_settings.effective_api_key,
    )

    parser = JsonOutputParser(pydantic_object=ArbitreDecision)

    prompt_messages = [
        SystemMessage(content=ARBITRE_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Voici le State complet à valider :\n\n"
                f"MARKET CONTEXT :\n{market_context}\n\n"
                f"SEO STRATEGY :\n{seo_silo}\n\n"
                f"WIREFRAME (UX) :\n{wireframe}\n\n"
                f"COPY DRAFT :\n{copy_draft}\n\n"
                f"Retourne une ArbitreDecision JSON : {parser.get_format_instructions()}"
            )
        ),
    ]

    try:
        response = await llm.ainvoke(prompt_messages)
        decision_json = parser.parse(response.content)
        decision = ArbitreDecision(**decision_json)
    except Exception as exc:
        logger.error(f"❌ Échec de la validation LLM Arbitre : {exc}")
        # En cas d'erreur LLM, passer quand même (fail-safe)
        return {
            "faulty_node": "architect_node",
            "retry_count": 0,
            "arbitre_errors": [f"Arbitre LLM failed (passed anyway): {exc}"],
        }

    # -----------------------------------------------------------------------
    # Décision finale : Approuvé ou Rejeté
    # -----------------------------------------------------------------------
    if decision.is_approved:
        logger.info(f"🟢 APPROVED → Architect | Raison : {decision.feedback_reason}")
        return {
            "faulty_node": "architect_node",
            "retry_count": 0,
            "arbitre_errors": [],
        }
    else:
        # Mapping du route_to vers le nom de nœud LangGraph
        node_mapping = {
            "SEO": "seo_node",
            "UX": "ux_node",
            "Copywriter": "copywriter_node",
            "Architect": "architect_node",
            "END": "END",
        }
        target_node = node_mapping.get(decision.route_to, "architect_node")

        logger.error(
            f"🔴 REJECTED → {decision.route_to} (retry #{retry_count + 1}) | "
            f"Raison : {decision.feedback_reason}"
        )
        return {
            "faulty_node": target_node,
            "retry_count": 1,
            "arbitre_errors": [f"Arbitre rejection: {decision.feedback_reason}"],
        }


# ===========================================================================
# Fonction de routing pour LangGraph
# ===========================================================================

def route_after_arbitre(state: GraphState) -> str:
    """Fonction de routing conditionnel post-Arbitre pour LangGraph.

    Retourne le nom du prochain nœud à exécuter selon la décision de l'Arbitre.
    """
    faulty_node = state.get("faulty_node")

    if not faulty_node or faulty_node == "architect_node":
        return "architect_node"

    if faulty_node == "END":
        return "END"

    # Retourne le nœud fautif identifié par l'Arbitre
    return faulty_node
