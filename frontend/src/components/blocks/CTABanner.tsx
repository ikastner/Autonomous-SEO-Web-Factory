import { CTASchema } from "@/types/schema";

export default function CTABanner({
  headline,
  subtext,
  cta_label,
  cta_url,
  background_color,
}: CTASchema) {
  const bgClasses = {
    primary: "bg-gradient-to-r from-blue-600 to-purple-600",
    secondary: "bg-gradient-to-r from-green-600 to-teal-600",
    dark: "bg-gray-900",
    light: "bg-gray-100",
  };

  const textColor =
    background_color === "light" ? "text-gray-900" : "text-white";
  const buttonClasses =
    background_color === "light"
      ? "bg-blue-600 text-white hover:bg-blue-700"
      : "bg-white text-gray-900 hover:bg-gray-100";

  return (
    <section className={`py-20 px-6 ${bgClasses[background_color]}`}>
      <div className="max-w-4xl mx-auto text-center">
        <h2 className={`text-3xl md:text-4xl font-bold mb-4 ${textColor}`}>
          {headline}
        </h2>
        {subtext && (
          <p
            className={`text-lg mb-8 ${
              background_color === "light"
                ? "text-gray-600"
                : "text-white/90"
            }`}
          >
            {subtext}
          </p>
        )}
        <a
          href={cta_url}
          className={`inline-block px-8 py-4 font-semibold rounded-lg transition-colors shadow-lg ${buttonClasses}`}
        >
          {cta_label}
        </a>
      </div>
    </section>
  );
}
