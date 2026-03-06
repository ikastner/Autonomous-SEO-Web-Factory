"use client";

import { ArtDirectionTokens } from "@/types/schema";
import { useEffect } from "react";

interface ThemeInjectorProps {
  artDirection: ArtDirectionTokens;
}

/**
 * ThemeInjector — Injecte dynamiquement les Design Tokens dans le DOM.
 * 
 * Responsabilités :
 * 1. Injecter les couleurs de color_palette_hex comme CSS variables
 * 2. Appliquer la typographie selon typography_style
 * 3. Définir les variables d'animation selon animation_feeling
 * 
 * Les variables CSS sont ensuite utilisées par tous les composants UI.
 */
export default function ThemeInjector({ artDirection }: ThemeInjectorProps) {
  useEffect(() => {
    const root = document.documentElement;
    const { color_palette_hex, typography_style, design_vibe, animation_feeling } = artDirection;

    // =========================================================================
    // 1. INJECTION DES COULEURS (Palette dynamique)
    // =========================================================================
    // Ordre attendu : [primary, secondary, accent, neutral_dark, neutral_light]
    const [primary, secondary, accent, neutralDark, neutralLight] = color_palette_hex;

    root.style.setProperty("--color-primary", primary || "#000000");
    root.style.setProperty("--color-secondary", secondary || "#FFFFFF");
    root.style.setProperty("--color-accent", accent || "#0066FF");
    root.style.setProperty("--color-neutral-dark", neutralDark || "#1A1A1A");
    root.style.setProperty("--color-neutral-light", neutralLight || "#F5F5F5");

    // Mapping vers les variables shadcn/ui (Tailwind CSS)
    root.style.setProperty("--background", neutralLight || "#FFFFFF");
    root.style.setProperty("--foreground", neutralDark || "#000000");
    root.style.setProperty("--primary", primary || "#000000");
    root.style.setProperty("--primary-foreground", neutralLight || "#FFFFFF");
    root.style.setProperty("--accent", accent || "#0066FF");
    root.style.setProperty("--accent-foreground", neutralLight || "#FFFFFF");

    // =========================================================================
    // 2. INJECTION DE LA TYPOGRAPHIE
    // =========================================================================
    const typographyMap = {
      sans_serif_heavy: {
        fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
        fontWeightBase: "400",
        fontWeightHeading: "700",
      },
      serif_elegant: {
        fontFamily: "'Merriweather', 'Georgia', serif",
        fontWeightBase: "300",
        fontWeightHeading: "600",
      },
      monospaced_tech: {
        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
        fontWeightBase: "400",
        fontWeightHeading: "600",
      },
    };

    const typo = typographyMap[typography_style];
    root.style.setProperty("--font-family-base", typo.fontFamily);
    root.style.setProperty("--font-weight-base", typo.fontWeightBase);
    root.style.setProperty("--font-weight-heading", typo.fontWeightHeading);

    // =========================================================================
    // 3. INJECTION DES VARIABLES D'ANIMATION
    // =========================================================================
    const animationMap = {
      snappy_springs: {
        transition: "all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)", // Spring-like
        duration: "300ms",
      },
      smooth_ease: {
        transition: "all 0.6s cubic-bezier(0.4, 0, 0.2, 1)", // Smooth ease
        duration: "600ms",
      },
      none: {
        transition: "none",
        duration: "0ms",
      },
    };

    const anim = animationMap[animation_feeling];
    root.style.setProperty("--transition-base", anim.transition);
    root.style.setProperty("--transition-duration", anim.duration);

    // =========================================================================
    // 4. INJECTION DES VARIABLES DE VIBE (Espacements, Bordures)
    // =========================================================================
    const vibeMap = {
      swiss_editorial: {
        spacing: "3rem", // Espaces blancs généreux
        borderWidth: "1px",
        borderRadius: "0px", // Angles droits
      },
      neo_brutalism: {
        spacing: "1.5rem",
        borderWidth: "4px", // Bordures épaisses
        borderRadius: "0px",
      },
      minimalist_tech: {
        spacing: "2rem",
        borderWidth: "1px",
        borderRadius: "12px", // Coins arrondis subtils
      },
      organic_elegant: {
        spacing: "2.5rem",
        borderWidth: "0px",
        borderRadius: "24px", // Coins très arrondis
      },
    };

    const vibe = vibeMap[design_vibe];
    root.style.setProperty("--spacing-section", vibe.spacing);
    root.style.setProperty("--border-width", vibe.borderWidth);
    root.style.setProperty("--border-radius", vibe.borderRadius);

    // Appliquer la font-family au body
    document.body.style.fontFamily = typo.fontFamily;
  }, [artDirection]);

  return null; // Ce composant n'a pas de rendu visuel
}
