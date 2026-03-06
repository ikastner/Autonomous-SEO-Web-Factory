"use client";

import { FeatureGridSchema } from "@/types/schema";
import { Zap, Shield, BarChart2, Target, Rocket, Star } from "lucide-react";
import MotionWrapper from "@/components/animations/MotionWrapper";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Zap,
  Shield,
  BarChart2,
  Target,
  Rocket,
  Star,
};

interface FeatureGridProps extends FeatureGridSchema {
  animationFeeling?: "snappy_springs" | "smooth_ease" | "none";
}

export default function FeatureGrid({
  section_title,
  section_subtitle,
  features,
  columns,
  layout_style,
  animationFeeling = "smooth_ease",
}: FeatureGridProps) {
  // =========================================================================
  // LAYOUT STYLES — 4 variantes (grid_classic, bento_box, masonry, staggered)
  // =========================================================================

  // GRID_CLASSIC — Grille uniforme classique
  if (layout_style === "grid_classic") {
    const gridCols = columns === 2 ? "md:grid-cols-2" : "md:grid-cols-3";
    return (
      <section className="py-20 px-6 bg-[var(--color-neutral-light)]">
        <div className="max-w-6xl mx-auto">
          <MotionWrapper animationFeeling={animationFeeling} className="text-center mb-16">
            <h2 className="text-4xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-4">
              {section_title}
            </h2>
            {section_subtitle && (
              <p className="text-xl text-[var(--color-neutral-dark)]/70 max-w-2xl mx-auto font-[var(--font-weight-base)]">
                {section_subtitle}
              </p>
            )}
          </MotionWrapper>
          <div className={`grid grid-cols-1 ${gridCols} gap-8`}>
            {features.map((feature, index) => {
              const Icon = iconMap[feature.icon_name] || Zap;
              return (
                <MotionWrapper key={index} animationFeeling={animationFeeling} delay={index * 0.1}>
                  <div className="bg-white p-8 rounded-[var(--border-radius)] border-[var(--border-width)] border-[var(--color-neutral-dark)]/10 hover:border-[var(--color-accent)] transition-[var(--transition-base)] h-full">
                    <div className="w-12 h-12 bg-[var(--color-accent)]/10 rounded-[var(--border-radius)] flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6 text-[var(--color-accent)]" />
                    </div>
                    <h3 className="text-xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-3">
                      {feature.title}
                    </h3>
                    <p className="text-[var(--color-neutral-dark)]/70 leading-relaxed font-[var(--font-weight-base)]">
                      {feature.description}
                    </p>
                  </div>
                </MotionWrapper>
              );
            })}
          </div>
        </div>
      </section>
    );
  }

  // BENTO_BOX — Layout type Bento (cartes de tailles variables, style Apple)
  if (layout_style === "bento_box") {
    return (
      <section className="py-20 px-6 bg-[var(--color-neutral-light)]">
        <div className="max-w-7xl mx-auto">
          <MotionWrapper animationFeeling={animationFeeling} className="text-center mb-16">
            <h2 className="text-4xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-4">
              {section_title}
            </h2>
            {section_subtitle && (
              <p className="text-xl text-[var(--color-neutral-dark)]/70 max-w-2xl mx-auto font-[var(--font-weight-base)]">
                {section_subtitle}
              </p>
            )}
          </MotionWrapper>
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4 auto-rows-[200px]">
            {features.map((feature, index) => {
              const Icon = iconMap[feature.icon_name] || Zap;
              // Pattern Bento : première carte large, alternance de tailles
              const spanClasses = [
                "md:col-span-4 md:row-span-2", // Grande carte
                "md:col-span-2 md:row-span-1", // Petite carte
                "md:col-span-3 md:row-span-1", // Moyenne carte
                "md:col-span-3 md:row-span-1", // Moyenne carte
                "md:col-span-2 md:row-span-2", // Haute carte
                "md:col-span-4 md:row-span-1", // Large carte
              ];
              const spanClass = spanClasses[index % spanClasses.length];
              
              return (
                <MotionWrapper key={index} animationFeeling={animationFeeling} delay={index * 0.1} className={spanClass}>
                  <div className="bg-white p-8 rounded-[var(--border-radius)] border-[var(--border-width)] border-[var(--color-neutral-dark)]/10 hover:border-[var(--color-accent)] transition-[var(--transition-base)] h-full flex flex-col justify-between">
                    <div>
                      <div className="w-12 h-12 bg-[var(--color-accent)]/10 rounded-[var(--border-radius)] flex items-center justify-center mb-4">
                        <Icon className="w-6 h-6 text-[var(--color-accent)]" />
                      </div>
                      <h3 className="text-xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-3">
                        {feature.title}
                      </h3>
                    </div>
                    <p className="text-[var(--color-neutral-dark)]/70 leading-relaxed font-[var(--font-weight-base)]">
                      {feature.description}
                    </p>
                  </div>
                </MotionWrapper>
              );
            })}
          </div>
        </div>
      </section>
    );
  }

  // MASONRY — Layout masonry (hauteurs variables, Pinterest-style)
  if (layout_style === "masonry") {
    const gridCols = columns === 2 ? "md:columns-2" : "md:columns-3";
    return (
      <section className="py-20 px-6 bg-[var(--color-neutral-light)]">
        <div className="max-w-6xl mx-auto">
          <MotionWrapper animationFeeling={animationFeeling} className="text-center mb-16">
            <h2 className="text-4xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-4">
              {section_title}
            </h2>
            {section_subtitle && (
              <p className="text-xl text-[var(--color-neutral-dark)]/70 max-w-2xl mx-auto font-[var(--font-weight-base)]">
                {section_subtitle}
              </p>
            )}
          </MotionWrapper>
          <div className={`columns-1 ${gridCols} gap-8 space-y-8`}>
            {features.map((feature, index) => {
              const Icon = iconMap[feature.icon_name] || Zap;
              return (
                <MotionWrapper key={index} animationFeeling={animationFeeling} delay={index * 0.1} className="break-inside-avoid">
                  <div className="bg-white p-8 rounded-[var(--border-radius)] border-[var(--border-width)] border-[var(--color-neutral-dark)]/10 hover:border-[var(--color-accent)] transition-[var(--transition-base)] mb-8">
                    <div className="w-12 h-12 bg-[var(--color-accent)]/10 rounded-[var(--border-radius)] flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6 text-[var(--color-accent)]" />
                    </div>
                    <h3 className="text-xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-3">
                      {feature.title}
                    </h3>
                    <p className="text-[var(--color-neutral-dark)]/70 leading-relaxed font-[var(--font-weight-base)]">
                      {feature.description}
                    </p>
                  </div>
                </MotionWrapper>
              );
            })}
          </div>
        </div>
      </section>
    );
  }

  // STAGGERED — Cartes décalées verticalement (swiss_editorial vibe)
  if (layout_style === "staggered") {
    const gridCols = columns === 2 ? "md:grid-cols-2" : "md:grid-cols-3";
    return (
      <section className="py-20 px-6 bg-[var(--color-neutral-light)]">
        <div className="max-w-6xl mx-auto">
          <MotionWrapper animationFeeling={animationFeeling} className="mb-16">
            <h2 className="text-5xl md:text-6xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-4 leading-tight">
              {section_title}
            </h2>
            {section_subtitle && (
              <p className="text-xl text-[var(--color-neutral-dark)]/70 max-w-2xl font-[var(--font-weight-base)]">
                {section_subtitle}
              </p>
            )}
          </MotionWrapper>
          <div className={`grid grid-cols-1 ${gridCols} gap-x-8 gap-y-16`}>
            {features.map((feature, index) => {
              const Icon = iconMap[feature.icon_name] || Zap;
              // Décalage vertical alterné
              const offsetClass = index % 2 === 0 ? "md:mt-0" : "md:mt-16";
              return (
                <MotionWrapper key={index} animationFeeling={animationFeeling} delay={index * 0.1} className={offsetClass}>
                  <div className="bg-white p-10 rounded-[var(--border-radius)] border-[var(--border-width)] border-[var(--color-neutral-dark)]/10 hover:border-[var(--color-accent)] transition-[var(--transition-base)]">
                    <div className="w-16 h-16 bg-[var(--color-accent)]/10 rounded-[var(--border-radius)] flex items-center justify-center mb-6">
                      <Icon className="w-8 h-8 text-[var(--color-accent)]" />
                    </div>
                    <h3 className="text-2xl font-[var(--font-weight-heading)] text-[var(--color-neutral-dark)] mb-4">
                      {feature.title}
                    </h3>
                    <p className="text-[var(--color-neutral-dark)]/70 leading-relaxed font-[var(--font-weight-base)] text-lg">
                      {feature.description}
                    </p>
                  </div>
                </MotionWrapper>
              );
            })}
          </div>
        </div>
      </section>
    );
  }

  // Fallback (ne devrait jamais arriver)
  return null;
}
