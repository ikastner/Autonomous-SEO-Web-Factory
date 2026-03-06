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
    gradient: "bg-gradient-to-br from-[var(--color-primary)] via-[var(--color-accent)] to-[var(--color-secondary)]",
    solid: "bg-[var(--color-neutral-dark)]",
    image: "bg-cover bg-center",
    mesh: "bg-gradient-to-br from-[var(--color-primary)] via-[var(--color-accent)] to-[var(--color-secondary)]",
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
          <h1 className="text-5xl md:text-7xl font-[var(--font-weight-heading)] mb-6 leading-tight">
            {headline}
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-white/90 max-w-2xl mx-auto font-[var(--font-weight-base)]">
            {subheadline}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href={cta_primary_url}
              className="px-8 py-4 bg-white text-[var(--color-neutral-dark)] font-semibold rounded-[var(--border-radius)] hover:bg-white/90 transition-[var(--transition-base)] shadow-lg"
            >
              {cta_primary_label}
            </a>
            {cta_secondary_label && cta_secondary_url && (
              <a
                href={cta_secondary_url}
                className="px-8 py-4 bg-transparent border-[var(--border-width)] border-white text-white font-semibold rounded-[var(--border-radius)] hover:bg-white/10 transition-[var(--transition-base)]"
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
        <div className="flex items-center justify-center px-8 lg:px-16 py-20 bg-[var(--color-neutral-light)]">
          <MotionWrapper animationFeeling={animationFeeling} className="max-w-xl">
            <h1 className="text-5xl md:text-7xl font-[var(--font-weight-heading)] mb-6 leading-tight text-[var(--color-neutral-dark)]">
              {headline}
            </h1>
            <p className="text-xl md:text-2xl mb-8 text-[var(--color-neutral-dark)]/80 font-[var(--font-weight-base)]">
              {subheadline}
            </p>
            <div className="flex flex-col gap-4">
              <a
                href={cta_primary_url}
                className="px-8 py-4 bg-[var(--color-primary)] text-white font-semibold rounded-[var(--border-radius)] hover:opacity-90 transition-[var(--transition-base)] text-center"
              >
                {cta_primary_label}
              </a>
              {cta_secondary_label && cta_secondary_url && (
                <a
                  href={cta_secondary_url}
                  className="px-8 py-4 bg-transparent border-[var(--border-width)] border-[var(--color-primary)] text-[var(--color-primary)] font-semibold rounded-[var(--border-radius)] hover:bg-[var(--color-primary)]/10 transition-[var(--transition-base)] text-center"
                >
                  {cta_secondary_label}
                </a>
              )}
            </div>
            {social_proof_label && (
              <p className="mt-8 text-sm text-[var(--color-neutral-dark)]/60">{social_proof_label}</p>
            )}
          </MotionWrapper>
        </div>
        <div className={`${bgClasses[background_variant]} relative`}>
          <div className="absolute inset-0 bg-black/10" />
        </div>
      </section>
    );
  }

  // ASYMMETRIC — Layout asymétrique swiss_editorial (espaces blancs massifs)
  if (layout_style === "asymmetric") {
    return (
      <section className="relative min-h-screen px-8 lg:px-24 py-32 bg-[var(--color-neutral-light)]">
        <div className="grid grid-cols-12 gap-8 lg:gap-16">
          <MotionWrapper animationFeeling={animationFeeling} className="col-span-12 lg:col-span-7 lg:col-start-2">
            <h1 className="text-6xl md:text-8xl font-[var(--font-weight-heading)] mb-12 leading-[0.95] text-[var(--color-neutral-dark)]">
              {headline}
            </h1>
          </MotionWrapper>
          <MotionWrapper animationFeeling={animationFeeling} delay={0.2} className="col-span-12 lg:col-span-5 lg:col-start-7">
            <p className="text-xl md:text-2xl mb-12 text-[var(--color-neutral-dark)]/70 font-[var(--font-weight-base)] leading-relaxed">
              {subheadline}
            </p>
            <div className="flex flex-col gap-4">
              <a
                href={cta_primary_url}
                className="px-8 py-4 bg-[var(--color-primary)] text-white font-semibold rounded-[var(--border-radius)] hover:opacity-90 transition-[var(--transition-base)] inline-block"
              >
                {cta_primary_label}
              </a>
              {cta_secondary_label && cta_secondary_url && (
                <a
                  href={cta_secondary_url}
                  className="px-8 py-4 text-[var(--color-primary)] font-semibold hover:underline transition-[var(--transition-base)] inline-block"
                >
                  {cta_secondary_label}
                </a>
              )}
            </div>
            {social_proof_label && (
              <p className="mt-12 text-sm text-[var(--color-neutral-dark)]/50 uppercase tracking-wider">
                {social_proof_label}
              </p>
            )}
          </MotionWrapper>
        </div>
      </section>
    );
  }

  // OVERLAPPING — Layout superposé neo_brutalism (z-index, bordures épaisses)
  if (layout_style === "overlapping") {
    return (
      <section className="relative min-h-screen px-8 lg:px-16 py-20 bg-[var(--color-accent)] overflow-hidden">
        <div className="relative z-10 max-w-6xl mx-auto">
          <MotionWrapper animationFeeling={animationFeeling} className="relative">
            <div className="bg-[var(--color-primary)] text-white p-12 lg:p-16 border-[var(--border-width)] border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transform -rotate-1">
              <h1 className="text-5xl md:text-7xl font-[var(--font-weight-heading)] mb-6 leading-tight">
                {headline}
              </h1>
              <p className="text-xl md:text-2xl mb-8 text-white/90 font-[var(--font-weight-base)]">
                {subheadline}
              </p>
            </div>
          </MotionWrapper>
          <MotionWrapper animationFeeling={animationFeeling} delay={0.2} className="relative -mt-8 ml-8 lg:ml-16">
            <div className="bg-white p-8 lg:p-12 border-[var(--border-width)] border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transform rotate-1">
              <div className="flex flex-col sm:flex-row gap-4">
                <a
                  href={cta_primary_url}
                  className="px-8 py-4 bg-[var(--color-primary)] text-white font-bold border-[var(--border-width)] border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
                >
                  {cta_primary_label}
                </a>
                {cta_secondary_label && cta_secondary_url && (
                  <a
                    href={cta_secondary_url}
                    className="px-8 py-4 bg-white text-[var(--color-primary)] font-bold border-[var(--border-width)] border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
                  >
                    {cta_secondary_label}
                  </a>
                )}
              </div>
              {social_proof_label && (
                <p className="mt-6 text-sm text-black/70 font-bold uppercase tracking-wider">
                  {social_proof_label}
                </p>
              )}
            </div>
          </MotionWrapper>
        </div>
      </section>
    );
  }

  // Fallback (ne devrait jamais arriver)
  return null;
}
