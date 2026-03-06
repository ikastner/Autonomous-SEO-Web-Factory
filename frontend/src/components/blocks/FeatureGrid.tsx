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
  const gridCols = columns === 2 ? "md:grid-cols-2" : "md:grid-cols-3";

  return (
    <section className="py-20 px-6 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <MotionWrapper animationFeeling={animationFeeling} className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            {section_title}
          </h2>
          {section_subtitle && (
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              {section_subtitle}
            </p>
          )}
        </MotionWrapper>
        <div className={`grid grid-cols-1 ${gridCols} gap-8`}>
          {features.map((feature, index) => {
            const Icon = iconMap[feature.icon_name] || Zap;
            return (
              <MotionWrapper key={index} animationFeeling={animationFeeling} delay={index * 0.1}>
                <div className="bg-white p-8 rounded-xl shadow-sm hover:shadow-md transition-shadow h-full">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-6 h-6 text-blue-600" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
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
