import { UIComponent } from "@/types/schema";
import HeroSection from "./blocks/HeroSection";
import FeatureGrid from "./blocks/FeatureGrid";
import ContentBlock from "./blocks/ContentBlock";
import FAQSection from "./blocks/FAQSection";
import CTABanner from "./blocks/CTABanner";

interface ComponentRendererProps {
  section: UIComponent;
}

export default function ComponentRenderer({ section }: ComponentRendererProps) {
  switch (section.component_type) {
    case "HeroSection":
      return <HeroSection {...section} />;
    case "FeatureGrid":
      return <FeatureGrid {...section} />;
    case "ContentBlock":
      return <ContentBlock {...section} />;
    case "FAQ":
      return <FAQSection {...section} />;
    case "CTABanner":
      return <CTABanner {...section} />;
    default:
      // TypeScript exhaustiveness check
      const _exhaustive: never = section;
      console.error("Unknown component type:", _exhaustive);
      return null;
  }
}
