"use client";

import { ArtDirectionTokens } from "@/types/schema";

interface ThemeInjectorProps {
  artDirection: ArtDirectionTokens;
}

/**
 * ThemeInjector — Injecte dynamiquement les couleurs depuis color_palette_hex.
 * 
 * Utilise une balise <style> pour définir les variables CSS Tailwind.
 */
export default function ThemeInjector({ artDirection }: ThemeInjectorProps) {
  const { color_palette_hex } = artDirection;
  
  // Vérification de sécurité
  if (!color_palette_hex || !Array.isArray(color_palette_hex)) {
    return null;
  }
  
  // Ordre attendu : [primary, secondary, accent, neutral_dark, neutral_light]
  const [primary, secondary, accent, neutralDark, neutralLight] = color_palette_hex;

  return (
    <style jsx global>{`
      :root {
        --background: ${neutralLight || "#FFFFFF"};
        --foreground: ${neutralDark || "#000000"};
        --primary: ${primary || "#000000"};
        --primary-foreground: ${neutralLight || "#FFFFFF"};
        --accent: ${accent || "#0066FF"};
        --accent-foreground: ${neutralLight || "#FFFFFF"};
      }
    `}</style>
  );
}
