"""
schemas/generative_ui.py — Contrat Pydantic v2 maître Frontend <-> Backend.

Règle d'or : les agents NE génèrent JAMAIS de code .tsx/.jsx/.css.
Ils produisent UNIQUEMENT un objet conforme à GenerativeUISchema.
Le frontend Next.js fait un simple map() sur `sections` et résout
chaque composant depuis son catalogue shadcn/ui via `component_type`.

Architecture Discriminated Union :
    UIComponent = Annotated[Union[Hero, FeatureGrid, ...], discriminator="component_type"]
    -> Pydantic sélectionne et valide le bon modèle à la désérialisation.
    -> L'agent IA sait exactement quels champs remplir grâce aux Field(description=...).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


# ===========================================================================
# 1. MÉTADONNÉES SEO
# ===========================================================================

class PageMetadata(BaseModel):
    """Métadonnées SEO complètes de la page générée.

    Utilisé par Next.js dans le segment `generateMetadata()` de l'App Router.
    Toutes les valeurs sont validées pour respecter les limites recommandées
    par Google Search Central.
    """

    title: str = Field(
        ...,
        min_length=10,
        max_length=70,
        description=(
            "Balise <title> SEO. Doit contenir le mot-clé principal en début de titre. "
            "Entre 50 et 70 caractères pour un affichage optimal dans les SERPs."
        ),
    )
    description: str = Field(
        ...,
        min_length=50,
        max_length=160,
        description=(
            "Balise <meta name='description'>. Doit inclure un appel à l'action implicite "
            "et le mot-clé principal. Entre 120 et 160 caractères."
        ),
    )
    keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Liste des mots-clés SEO ciblés pour cette page. "
            "Le premier élément est le mot-clé principal (head keyword)."
        ),
    )
    canonical_url: Optional[AnyHttpUrl] = Field(
        None,
        description=(
            "URL canonique absolue de la page. Obligatoire si la page est accessible "
            "depuis plusieurs URLs pour éviter le duplicate content."
        ),
    )
    og_title: Optional[str] = Field(
        None,
        max_length=95,
        description="Titre Open Graph pour le partage social. Si absent, reprend `title`.",
    )
    og_description: Optional[str] = Field(
        None,
        max_length=200,
        description="Description Open Graph. Si absent, reprend `description`.",
    )
    og_image_url: Optional[AnyHttpUrl] = Field(
        None,
        description=(
            "URL absolue de l'image Open Graph. Format recommandé : 1200x630px. "
            "Utilisée par Facebook, LinkedIn, Twitter lors du partage."
        ),
    )

    @field_validator("keywords")
    @classmethod
    def keywords_not_empty_strings(cls, v: list[str]) -> list[str]:
        return [kw.strip() for kw in v if kw.strip()]


# ===========================================================================
# 2. ART DIRECTION TOKENS — Design System Génératif
# ===========================================================================

class ArtDirectionTokens(BaseModel):
    """Tokens de direction artistique générés par l'Art Director Agent.
    
    Définit l'identité visuelle complète du site généré : vibe, typographie,
    animations et palette de couleurs. Permet de passer de "Boring UI" à
    "Awwwards-level design" en injectant des intentions créatives dans le frontend.
    """

    design_vibe: Literal[
        "swiss_editorial",
        "neo_brutalism",
        "minimalist_tech",
        "organic_elegant"
    ] = Field(
        ...,
        description=(
            "Vibe visuelle globale du site. Détermine le layout, les espacements, "
            "les bordures et l'approche typographique.\n"
            "- swiss_editorial : Grilles strictes, typographie suisse, layouts asymétriques, "
            "espaces blancs généreux (ex: Stripe, Linear).\n"
            "- neo_brutalism : Bordures épaisses noires, ombres portées dures, couleurs saturées, "
            "layouts cassés, anti-design assumé (ex: Gumroad, Figma Playground).\n"
            "- minimalist_tech : Monochrome, grilles parfaites, micro-interactions subtiles, "
            "glassmorphism, feeling Apple/Vercel (ex: Vercel, Raycast).\n"
            "- organic_elegant : Courbes douces, dégradés subtils, typographie serif, "
            "animations fluides, feeling premium (ex: Airbnb, Notion)."
        ),
    )

    typography_style: Literal[
        "sans_serif_heavy",
        "serif_elegant",
        "monospaced_tech"
    ] = Field(
        ...,
        description=(
            "Style typographique principal.\n"
            "- sans_serif_heavy : Grotesk bold (Inter, Helvetica Now, Suisse), "
            "titres massifs, contrastes de poids forts.\n"
            "- serif_elegant : Serif éditorial (Tiempos, Canela, Freight), "
            "titres raffinés, feeling magazine.\n"
            "- monospaced_tech : Mono technique (JetBrains Mono, IBM Plex Mono), "
            "feeling code/terminal, SaaS technique."
        ),
    )

    animation_feeling: Literal[
        "snappy_springs",
        "smooth_ease",
        "none"
    ] = Field(
        ...,
        description=(
            "Approche des micro-interactions et transitions.\n"
            "- snappy_springs : Animations élastiques rapides (spring physics), "
            "feeling réactif et joueur (ex: Framer Motion springs).\n"
            "- smooth_ease : Easing doux et fluide (cubic-bezier), "
            "transitions longues et élégantes.\n"
            "- none : Pas d'animations, design statique ultra-rapide."
        ),
    )

    color_palette_hex: list[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description=(
            "Palette de couleurs générée mathématiquement (3-5 couleurs en HEX).\n"
            "Ordre : [primary, secondary, accent, neutral_dark, neutral_light].\n"
            "Doit respecter les ratios de contraste WCAG AA (4.5:1 minimum).\n"
            "Exemples :\n"
            "- swiss_editorial : ['#000000', '#FFFFFF', '#0066FF', '#F5F5F5']\n"
            "- neo_brutalism : ['#FF6B35', '#004E89', '#FFEB3B', '#000000', '#FFFFFF']\n"
            "- minimalist_tech : ['#0A0A0A', '#FAFAFA', '#3B82F6', '#E5E5E5']\n"
            "- organic_elegant : ['#2D3748', '#F7FAFC', '#D69E2E', '#EDF2F7']"
        ),
    )

    @field_validator("color_palette_hex")
    @classmethod
    def validate_hex_colors(cls, v: list[str]) -> list[str]:
        """Valide que toutes les couleurs sont au format HEX valide."""
        import re
        hex_pattern = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
        for color in v:
            if not hex_pattern.match(color):
                raise ValueError(
                    f"Couleur invalide '{color}'. Format attendu : #RRGGBB ou #RGB"
                )
        return v


# ===========================================================================
# 3. COMPOSANTS UI — Discriminated Union
# ===========================================================================
# Chaque modèle possède un champ `component_type: Literal["NomDuComposant"]`
# qui sert de discriminant. L'agent IA DOIT renseigner ce champ tel quel.
# Les Field(description=...) servent de prompt implicite pour guider le LLM.
# ===========================================================================


class HeroSectionSchema(BaseModel):
    """Composant Hero — section d'accroche principale de la page.

    Rendu côté frontend : composant <HeroSection> (shadcn/ui + Tailwind).
    Positionnement conseillé : order=0, toujours en premier.
    """

    component_type: Literal["HeroSection"] = "HeroSection"

    headline: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description=(
            "Titre principal H1 de la page. Doit contenir le mot-clé SEO principal. "
            "Formule orientée bénéfice, pas feature. Ex: 'Doublez vos leads en 30 jours'."
        ),
    )
    subheadline: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description=(
            "Sous-titre H2 qui clarifie la proposition de valeur. "
            "Répond à 'pour qui ?' et 'quel résultat ?'."
        ),
    )
    cta_primary_label: str = Field(
        ...,
        max_length=40,
        description=(
            "Texte du bouton CTA principal. Doit être un verbe d'action. "
            "Ex: 'Démarrer gratuitement', 'Voir la démo'."
        ),
    )
    cta_primary_url: str = Field(
        ...,
        description="URL ou ancre href du CTA principal. Ex: '/signup' ou '#contact'.",
    )
    cta_secondary_label: Optional[str] = Field(
        None,
        max_length=40,
        description="Texte du CTA secondaire (lien fantôme). Optionnel.",
    )
    cta_secondary_url: Optional[str] = Field(
        None,
        description="URL ou ancre href du CTA secondaire.",
    )
    background_variant: Literal["gradient", "image", "solid", "mesh"] = Field(
        "gradient",
        description=(
            "Style de fond du Hero. 'gradient' = dégradé de marque, "
            "'image' = image de fond (og_image_url), 'solid' = couleur unie, "
            "'mesh' = fond animé CSS."
        ),
    )
    social_proof_label: Optional[str] = Field(
        None,
        max_length=80,
        description=(
            "Courte preuve sociale sous le CTA. "
            "Ex: 'Rejoignez 2 000+ marketeurs qui nous font confiance'."
        ),
    )
    layout_style: Literal["centered", "split_screen", "asymmetric", "overlapping"] = Field(
        "centered",
        description=(
            "Style de layout du Hero pour casser la grille classique.\n"
            "- centered : Layout centré classique (texte + CTAs centrés).\n"
            "- split_screen : Texte à gauche, visuel/gradient à droite (50/50).\n"
            "- asymmetric : Layout asymétrique avec texte décalé (swiss_editorial vibe).\n"
            "- overlapping : Éléments superposés avec z-index (neo_brutalism vibe)."
        ),
    )


class FeatureItem(BaseModel):
    """Un item individuel dans la FeatureGrid."""

    icon_name: str = Field(
        ...,
        description=(
            "Nom exact d'une icône Lucide React (ex: 'Zap', 'Shield', 'BarChart2'). "
            "Voir https://lucide.dev/icons/ pour la liste complète."
        ),
    )
    title: str = Field(
        ...,
        max_length=60,
        description="Titre court de la feature (3-6 mots). Ex: 'Analyse en temps réel'.",
    )
    description: str = Field(
        ...,
        max_length=160,
        description=(
            "Description de la feature en 1-2 phrases. "
            "Orientée résultat concret, pas spécification technique."
        ),
    )


class FeatureGridSchema(BaseModel):
    """Composant Feature Grid — grille de fonctionnalités ou avantages.

    Rendu côté frontend : composant <FeatureGrid> (grille 2-3 colonnes).
    Idéal pour lister 3 à 6 bénéfices clés avec icône Lucide + texte.
    """

    component_type: Literal["FeatureGrid"] = "FeatureGrid"

    section_title: str = Field(
        ...,
        max_length=80,
        description=(
            "Titre H2 de la section features. Orienté bénéfice global. "
            "Ex: 'Tout ce dont vous avez besoin pour scaler'."
        ),
    )
    section_subtitle: Optional[str] = Field(
        None,
        max_length=160,
        description="Sous-titre optionnel sous le titre de section.",
    )
    features: list[FeatureItem] = Field(
        ...,
        min_length=2,
        max_length=6,
        description=(
            "Liste de 2 à 6 fonctionnalités/avantages. "
            "Chaque item a une icône Lucide, un titre et une description courte."
        ),
    )
    columns: Literal[2, 3] = Field(
        3,
        description="Nombre de colonnes de la grille. 2 ou 3 selon le nombre de features.",
    )
    layout_style: Literal["grid_classic", "bento_box", "masonry", "staggered"] = Field(
        "grid_classic",
        description=(
            "Style de layout de la grille pour casser la monotonie.\n"
            "- grid_classic : Grille uniforme classique (toutes les cartes même taille).\n"
            "- bento_box : Layout type Bento (cartes de tailles variables, style Apple).\n"
            "- masonry : Layout masonry (hauteurs variables, Pinterest-style).\n"
            "- staggered : Cartes décalées verticalement (swiss_editorial vibe)."
        ),
    )


class ContentBlockSchema(BaseModel):
    """Composant Content Block — bloc texte riche avec image optionnelle.

    Rendu côté frontend : composant <ContentBlock> (layout 50/50 ou full-width).
    Utilisé pour les sections de contenu SEO longue-forme (cluster pages).
    """

    component_type: Literal["ContentBlock"] = "ContentBlock"

    heading: str = Field(
        ...,
        max_length=100,
        description=(
            "Titre H2 ou H3 de la section. Doit contenir un mot-clé secondaire (LSI). "
            "Formule sous forme de question ou affirmation forte."
        ),
    )
    body_markdown: str = Field(
        ...,
        min_length=100,
        description=(
            "Contenu principal en Markdown. Supporte **gras**, *italique*, listes, "
            "sous-titres H3/H4. Minimum 100 caractères. Viser 200-400 caractères "
            "par bloc pour la lisibilité. NE PAS inclure de code HTML."
        ),
    )
    image_url: Optional[AnyHttpUrl] = Field(
        None,
        description=(
            "URL absolue d'une image illustrative. Si présent, le layout devient 50/50 "
            "(texte à gauche, image à droite) ou inversé selon `image_position`."
        ),
    )
    image_alt: Optional[str] = Field(
        None,
        max_length=125,
        description=(
            "Texte alternatif de l'image (attribut alt). Obligatoire si image_url est renseigné. "
            "Doit décrire l'image et idéalement contenir un mot-clé."
        ),
    )
    image_position: Literal["left", "right", "none"] = Field(
        "none",
        description="Position de l'image par rapport au texte. Ignoré si image_url est absent.",
    )

    @model_validator(mode="after")
    def alt_required_when_image(self) -> "ContentBlockSchema":
        if self.image_url and not self.image_alt:
            raise ValueError(
                "image_alt est obligatoire quand image_url est renseigné (accessibilité + SEO)."
            )
        return self


class FAQItem(BaseModel):
    """Une paire question/réponse pour le composant FAQ."""

    question: str = Field(
        ...,
        max_length=150,
        description=(
            "Question formulée comme un internaute la poserait dans Google. "
            "Ex: 'Comment fonctionne le retargeting Facebook ?'."
        ),
    )
    answer: str = Field(
        ...,
        min_length=40,
        max_length=500,
        description=(
            "Réponse concise et directe. La première phrase doit répondre directement. "
            "Peut contenir du Markdown simple (gras, listes)."
        ),
    )


class FAQSchema(BaseModel):
    """Composant FAQ — questions/réponses structurées avec schema.org FAQPage.

    Rendu côté frontend : composant <FAQAccordion> (shadcn/ui Accordion).
    Génère automatiquement le JSON-LD FAQPage pour les rich snippets Google.
    """

    component_type: Literal["FAQ"] = "FAQ"

    section_title: str = Field(
        "Questions fréquentes",
        max_length=80,
        description="Titre H2 de la section FAQ. Peut être personnalisé par niche.",
    )
    items: list[FAQItem] = Field(
        ...,
        min_length=3,
        max_length=10,
        description=(
            "Liste de 3 à 10 paires question/réponse. "
            "Les questions doivent correspondre à des requêtes People Also Ask (PAA) "
            "identifiées par le SEO Node."
        ),
    )


class CTASchema(BaseModel):
    """Composant CTA Banner — bandeau d'appel à l'action secondaire.

    Rendu côté frontend : composant <CTABanner> (fond coloré pleine largeur).
    Typiquement placé avant le footer pour convertir les lecteurs de la page.
    """

    component_type: Literal["CTABanner"] = "CTABanner"

    headline: str = Field(
        ...,
        max_length=80,
        description=(
            "Titre principal du bandeau CTA. Crée l'urgence ou rappelle le bénéfice clé. "
            "Ex: 'Prêt à transformer votre stratégie SEO ?'."
        ),
    )
    subtext: Optional[str] = Field(
        None,
        max_length=150,
        description="Texte de réassurance sous le titre. Ex: 'Sans engagement. Annulez à tout moment.'.",
    )
    cta_label: str = Field(
        ...,
        max_length=40,
        description="Texte du bouton d'action. Ex: 'Commencer maintenant', 'Demander une démo'.",
    )
    cta_url: str = Field(
        ...,
        description="URL ou ancre href du bouton CTA.",
    )
    background_color: Literal["primary", "secondary", "dark", "light"] = Field(
        "primary",
        description=(
            "Variante de couleur de fond du bandeau. Mappe vers les tokens Tailwind "
            "du design system : 'primary' = couleur principale de marque."
        ),
    )


# ===========================================================================
# 3. DISCRIMINATED UNION — Point d'entrée pour le frontend
# ===========================================================================

UIComponent = Annotated[
    Union[
        HeroSectionSchema,
        FeatureGridSchema,
        ContentBlockSchema,
        FAQSchema,
        CTASchema,
    ],
    Field(discriminator="component_type"),
]
"""Type union discriminé sur `component_type`.

Le frontend Next.js résout le composant React correspondant via :
    const componentMap = {
      HeroSection: HeroSection,
      FeatureGrid: FeatureGrid,
      ContentBlock: ContentBlock,
      FAQ: FAQAccordion,
      CTABanner: CTABanner,
    }
    sections.map(s => componentMap[s.component_type](s))
"""


# ===========================================================================
# 4. SCHÉMA MAÎTRE — Sortie finale de l'Architect Node
# ===========================================================================

class GenerativeUISchema(BaseModel):
    """Objet JSON final produit par l'Architect Node.

    C'est le SEUL artefact transmis au frontend Next.js via l'API FastAPI.
    Pydantic valide cet objet en mode strict avant tout envoi vers Vercel.
    Si la validation échoue, le pipeline s'arrête ici — jamais côté déploiement.

    Exemple de consommation frontend (Next.js App Router) :
        const page: GenerativeUISchema = await fetch('/pipeline/run').then(r => r.json())
        return <>{page.sections.map(s => <DynamicComponent key={s.component_type} {...s} />)}</>
    """

    page_slug: str = Field(
        ...,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description=(
            "Slug URL kebab-case de la page générée. "
            "Ex: 'agence-seo-paris', 'logiciel-crm-pme'. "
            "Utilisé comme segment de route Next.js."
        ),
    )
    brand_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Nom de la marque/entreprise tel qu'il apparaîtra sur la page.",
    )
    seo_metadata: PageMetadata = Field(
        ...,
        description="Métadonnées SEO complètes. Injectées dans generateMetadata() de Next.js.",
    )
    art_direction: ArtDirectionTokens = Field(
        ...,
        description=(
            "Tokens de direction artistique générés par l'Art Director Agent. "
            "Définit la vibe visuelle, la typographie, les animations et la palette de couleurs. "
            "Le frontend Next.js utilise ces tokens pour appliquer le design system dynamiquement."
        ),
    )
    sections: list[UIComponent] = Field(
        ...,
        min_length=1,
        description=(
            "Liste ordonnée des sections de la page. Chaque élément est un composant typé "
            "discriminé sur `component_type`. Le frontend itère sur cette liste dans l'ordre."
        ),
    )
    generated_at: datetime = Field(
        ...,
        description="Timestamp UTC de génération. Permet le cache-busting et l'audit.",
    )
    pipeline_version: str = Field(
        "1.0.0",
        description="Version sémantique du pipeline ayant généré ce schéma.",
    )

    @model_validator(mode="after")
    def hero_must_be_first(self) -> "GenerativeUISchema":
        """La première section DOIT être un HeroSection (convention UX)."""
        if not isinstance(self.sections[0], HeroSectionSchema):
            raise ValueError(
                "La première section doit être de type 'HeroSection'. "
                f"Reçu : '{self.sections[0].component_type}'."
            )
        return self

    @model_validator(mode="after")
    def no_duplicate_component_types(self) -> "GenerativeUISchema":
        """Interdit les doublons de composants à fort impact UX (Hero, CTA)."""
        restricted = ["HeroSection", "CTABanner"]
        for comp_type in restricted:
            occurrences = sum(
                1 for s in self.sections if s.component_type == comp_type
            )
            if occurrences > 1:
                raise ValueError(
                    f"Le composant '{comp_type}' ne peut apparaître qu'une seule fois par page. "
                    f"Trouvé {occurrences} fois."
                )
        return self


# ===========================================================================
# 5. RÉSOLUTION DES FORWARD REFERENCES
# ===========================================================================
# Nécessaire avec `from __future__ import annotations` (PEP 563) :
# Pydantic v2 ne résout pas automatiquement les annotations stringifiées
# dans les modèles imbriqués — model_rebuild() force la résolution.

FeatureGridSchema.model_rebuild()
FAQSchema.model_rebuild()
GenerativeUISchema.model_rebuild()
