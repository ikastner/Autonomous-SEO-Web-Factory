import { Metadata } from "next";
import { GenerativeUISchema } from "@/types/schema";
import ComponentRenderer from "@/components/ComponentRenderer";

const mockData: GenerativeUISchema = {
  page_slug: "restaurant-mediterraneen",
  brand_name: "L'Arc-en-Ciel",
  seo_metadata: {
    title: "Restaurant Méditerranéen L'Arc-en-Ciel — Cuisine Authentique",
    description:
      "Découvrez L'Arc-en-Ciel, restaurant méditerranéen authentique. Saveurs fraîches, ambiance chaleureuse et service impeccable. Réservez votre table dès maintenant.",
    keywords: [
      "restaurant méditerranéen",
      "cuisine méditerranéenne",
      "restaurant authentique",
      "gastronomie méditerranéenne",
    ],
  },
  sections: [
    {
      component_type: "HeroSection",
      headline: "Restaurant Méditerranéen — Saveurs Authentiques du Soleil",
      subheadline:
        "L'Arc-en-Ciel vous transporte au cœur de la Méditerranée avec des plats frais, une ambiance chaleureuse et un service exceptionnel.",
      cta_primary_label: "Réserver une table",
      cta_primary_url: "#contact",
      cta_secondary_label: "Voir la carte",
      cta_secondary_url: "#menu",
      background_variant: "gradient",
      social_proof_label: "Plus de 500 clients satisfaits chaque mois",
    },
    {
      component_type: "FeatureGrid",
      section_title: "Pourquoi choisir L'Arc-en-Ciel ?",
      section_subtitle:
        "Une expérience culinaire méditerranéenne authentique et inoubliable",
      features: [
        {
          icon_name: "Star",
          title: "Ingrédients frais et locaux",
          description:
            "Nous sélectionnons rigoureusement nos produits auprès de producteurs locaux pour garantir fraîcheur et qualité exceptionnelle.",
        },
        {
          icon_name: "Shield",
          title: "Recettes traditionnelles authentiques",
          description:
            "Nos chefs perpétuent les traditions culinaires méditerranéennes transmises de génération en génération.",
        },
        {
          icon_name: "Zap",
          title: "Service rapide et attentionné",
          description:
            "Notre équipe dévouée assure un service impeccable pour que chaque visite soit mémorable.",
        },
      ],
      columns: 3,
    },
    {
      component_type: "ContentBlock",
      heading: "Une cuisine méditerranéenne qui célèbre le terroir",
      body_markdown:
        "Chez L'Arc-en-Ciel, nous croyons que la **vraie cuisine méditerranéenne** commence par le respect des produits. Chaque plat est préparé avec passion, en utilisant des techniques ancestrales et des ingrédients soigneusement sélectionnés.\n\nNotre chef, formé dans les meilleures tables de la Méditerranée, compose des assiettes qui racontent une histoire : celle du soleil, de la mer et de la générosité.",
      image_position: "none",
    },
    {
      component_type: "FAQ",
      section_title: "Questions fréquentes",
      items: [
        {
          question: "Proposez-vous des options végétariennes ?",
          answer:
            "Oui, notre carte comprend plusieurs plats végétariens authentiques inspirés de la tradition méditerranéenne, préparés avec des légumes frais de saison.",
        },
        {
          question: "Faut-il réserver à l'avance ?",
          answer:
            "Nous recommandons vivement de réserver, surtout le week-end. Vous pouvez réserver en ligne ou par téléphone jusqu'à 2 mois à l'avance.",
        },
        {
          question: "Acceptez-vous les groupes ?",
          answer:
            "Absolument ! Nous pouvons accueillir des groupes jusqu'à 30 personnes. Contactez-nous pour organiser votre événement privé avec un menu personnalisé.",
        },
      ],
    },
    {
      component_type: "CTABanner",
      headline: "Prêt à découvrir nos saveurs méditerranéennes ?",
      subtext: "Réservez votre table dès maintenant et laissez-vous transporter",
      cta_label: "Réserver maintenant",
      cta_url: "#contact",
      background_color: "primary",
    },
  ],
  generated_at: "2026-03-06T10:30:00Z",
  pipeline_version: "1.0.0",
};

export const metadata: Metadata = {
  title: mockData.seo_metadata.title,
  description: mockData.seo_metadata.description,
  keywords: mockData.seo_metadata.keywords,
};

export default function Home() {
  return (
    <main className="min-h-screen">
      {mockData.sections.map((section, index) => (
        <ComponentRenderer key={index} section={section} />
      ))}
    </main>
  );
}
