import { HeroSectionSchema } from "@/types/schema";

export default function HeroSection({
  headline,
  subheadline,
  cta_primary_label,
  cta_primary_url,
  cta_secondary_label,
  cta_secondary_url,
  background_variant,
  social_proof_label,
}: HeroSectionSchema) {
  const bgClasses = {
    gradient: "bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600",
    solid: "bg-gray-900",
    image: "bg-cover bg-center",
    mesh: "bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500",
  };

  return (
    <section
      className={`relative min-h-[600px] flex items-center justify-center px-6 py-20 ${bgClasses[background_variant]}`}
    >
      <div className="absolute inset-0 bg-black/20" />
      <div className="relative z-10 max-w-4xl mx-auto text-center text-white">
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          {headline}
        </h1>
        <p className="text-xl md:text-2xl mb-8 text-white/90 max-w-2xl mx-auto">
          {subheadline}
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <a
            href={cta_primary_url}
            className="px-8 py-4 bg-white text-gray-900 font-semibold rounded-lg hover:bg-gray-100 transition-colors shadow-lg"
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
      </div>
    </section>
  );
}
