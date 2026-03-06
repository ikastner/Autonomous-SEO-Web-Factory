/**
 * schema.ts — Contrat TypeScript Frontend <-> Backend
 * 
 * Traduit le schéma Pydantic GenerativeUISchema en interfaces TypeScript strictes.
 * Utilise les Discriminated Unions pour UIComponent (basé sur component_type).
 */

// ===========================================================================
// 1. MÉTADONNÉES SEO
// ===========================================================================

export interface PageMetadata {
  title: string;
  description: string;
  keywords: string[];
  canonical_url?: string;
  og_title?: string;
  og_description?: string;
  og_image_url?: string;
}

// ===========================================================================
// 2. COMPOSANTS UI — Discriminated Union
// ===========================================================================

export interface HeroSectionSchema {
  component_type: "HeroSection";
  headline: string;
  subheadline: string;
  cta_primary_label: string;
  cta_primary_url: string;
  cta_secondary_label?: string;
  cta_secondary_url?: string;
  background_variant: "gradient" | "image" | "solid" | "mesh";
  social_proof_label?: string;
}

export interface FeatureItem {
  icon_name: string;
  title: string;
  description: string;
}

export interface FeatureGridSchema {
  component_type: "FeatureGrid";
  section_title: string;
  section_subtitle?: string;
  features: FeatureItem[];
  columns: 2 | 3;
}

export interface ContentBlockSchema {
  component_type: "ContentBlock";
  heading: string;
  body_markdown: string;
  image_url?: string;
  image_alt?: string;
  image_position: "left" | "right" | "none";
}

export interface FAQItem {
  question: string;
  answer: string;
}

export interface FAQSchema {
  component_type: "FAQ";
  section_title: string;
  items: FAQItem[];
}

export interface CTASchema {
  component_type: "CTABanner";
  headline: string;
  subtext?: string;
  cta_label: string;
  cta_url: string;
  background_color: "primary" | "secondary" | "dark" | "light";
}

// ===========================================================================
// 3. DISCRIMINATED UNION — Point d'entrée pour le frontend
// ===========================================================================

export type UIComponent =
  | HeroSectionSchema
  | FeatureGridSchema
  | ContentBlockSchema
  | FAQSchema
  | CTASchema;

// ===========================================================================
// 4. SCHÉMA MAÎTRE — Sortie finale de l'Architect Node
// ===========================================================================

export interface GenerativeUISchema {
  page_slug: string;
  brand_name: string;
  seo_metadata: PageMetadata;
  sections: UIComponent[];
  generated_at: string;
  pipeline_version: string;
}
