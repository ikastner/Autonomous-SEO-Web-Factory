"use client";

import { HeroSectionSchema } from "@/types/schema";
import MotionWrapper from "@/components/animations/MotionWrapper";

interface HeroSectionProps extends HeroSectionSchema {
  animationFeeling?: "snappy_springs" | "smooth_ease" | "none";
}

export default function HeroSection({
  headline,
  subheadline,
  cta_primary_label,
  cta_primary_url,
  cta_secondary_label,
  cta_secondary_url,
  background_variant,
  social_proof_label,
  layout_style,
  animationFeeling = "smooth_ease",
}: HeroSectionProps) {
  const bgClasses = {
    gradient: "bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600",
    solid: "bg-gray-900",
    image: "bg-cover bg-center",
    mesh: "bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500",
  };

  // =========================================================================
  // LAYOUT STYLES — 4 variantes (centered, split_screen, asymmetric, overlapping)
  // =========================================================================

  // CENTERED — Layout classique centré
  if (layout_style === "centered") {
    return (
      <section
        className={`relative min-h-[600px] flex items-center justify-center px-6 py-20 ${bgClasses[background_variant]}`}
      >
        <div className="absolute inset-0 bg-black/20" />
        <MotionWrapper animationFeeling={animationFeeling} className="relative z-10 max-w-4xl mx-auto text-center text-white">
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            {headline}
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-white/90 max-w-2xl mx-auto">
            {subheadline}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href={cta_primary_url}
              className="px-8 py-4 bg-white text-gray-900 font-semibold rounded-lg hover:bg-white/90 transition-colors shadow-lg"
            >
              {cta_primary_label}
            </a>
            {cta_secondary_label && cta_secondary_url && (
              <a
                href={cta_secondary_url}
                className="px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition-colors"
              >
                {cta_secondary_label}
              </a>
            )}
          </div>
          {social_proof_label && (
            <p className="mt-8 text-sm text-white/80">{social_proof_label}</p>
          )}
        </MotionWrapper>
      </section>
    );
  }

  // SPLIT_SCREEN — Layout 50/50 (texte à gauche, visuel à droite)
  if (layout_style === "split_screen") {
    return (
      <section className="relative min-h-screen grid grid-cols-1 lg:grid-cols-2">
        <div className="flex items-center justify-center px-8 lg:px-16 py-20 bg-gray-50">
          <MotionWrapper animationFeeling={animationFeeling} className="max-w-xl">
            <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight text-gray-900">
              {headline}
            </h1>
            <p className="text-xl md:text-2xl mb-8 text-gray-700">
              {subheadline}
            </p>
            <div className="flex flex-col gap-4">
              <a
                href={cta_primary_url}
                className="px-8 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-center"
              >
                {cta_primary_label}
              </a>
              {cta_secondary_label && cta_secondary_url && (
                <a
                  href={cta_secondary_url}
                  className="px-8 py-4 bg-transparent border-2 border-blue-600 text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors text-center"
                >
                  {cta_secondary_label}
                </a>
              )}
            </div>
            {social_proof_label && (
              <p className="mt-8 text-sm text-gray-600">{social_proof_label}</p>
            )}
          </MotionWrapper>
        </div>
        <div className={`${bgClasses[background_variant]} relative`}>
          <div className="absolute inset-0 bg-black/10" />
        </div>
      </section>
    );
  }

  // Fallback pour les autres layouts (asymmetric, overlapping) - utilise centered par défaut
  return (
    <section
      className={`relative min-h-[600px] flex items-center justify-center px-6 py-20 ${bgClasses[background_variant]}`}
    >
      <div className="absolute inset-0 bg-black/20" />
      <MotionWrapper animationFeeling={animationFeeling} className="relative z-10 max-w-4xl mx-auto text-center text-white">
        <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
          {headline}
        </h1>
        <p className="text-xl md:text-2xl mb-8 text-white/90 max-w-2xl mx-auto">
          {subheadline}
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <a
            href={cta_primary_url}
            className="px-8 py-4 bg-white text-gray-900 font-semibold rounded-lg hover:bg-white/90 transition-colors shadow-lg"
          >
            {cta_primary_label}
          </a>
          {cta_secondary_label && cta_secondary_url && (
            <a
              href={cta_secondary_url}
              className="px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition-colors"
            >
              {cta_secondary_label}
            </a>
          )}
        </div>
        {social_proof_label && (
          <p className="mt-8 text-sm text-white/80">{social_proof_label}</p>
        )}
      </MotionWrapper>
    </section>
  );
}
