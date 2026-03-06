"use client";
import { useState } from "react";
import { GenerativeUISchema } from "@/types/schema";
import ComponentRenderer from "@/components/ComponentRenderer";
import ThemeInjector from "@/components/ThemeInjector";

export default function Home() {
  const [targetUrl, setTargetUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedSchema, setGeneratedSchema] = useState<GenerativeUISchema | null>(null);

  const handleGenerate = async () => {
    if (!targetUrl.trim()) {
      setError("Veuillez entrer une URL valide");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/generate-site", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ target_url: targetUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erreur lors de la génération du site");
      }

      const data: GenerativeUISchema = await response.json();
      setGeneratedSchema(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Dashboard SaaS - UI de génération */}
      <div className="container mx-auto px-6 py-20">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-gray-900 mb-4">
              Autonomous SEO Web Factory
            </h1>
            <p className="text-xl text-gray-600">
              Générez un site web optimisé SEO en 2 minutes grâce à nos agents IA
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="space-y-6">
              <div>
                <label htmlFor="url" className="block text-sm font-semibold text-gray-700 mb-2">
                  URL du site à analyser
                </label>
                <input
                  id="url"
                  type="url"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                  disabled={isLoading}
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={isLoading}
                className="w-full px-8 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-lg hover:shadow-xl"
              >
                {isLoading ? "Génération en cours..." : "Générer le Site"}
              </button>

              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-600 font-medium">{error}</p>
                </div>
              )}

              {isLoading && (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-gray-600 text-center">
                    Nos agents IA analysent et construisent votre site...
                    <br />
                    <span className="text-sm text-gray-500">(Environ 2 min)</span>
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Affichage du site généré */}
      {generatedSchema && generatedSchema.art_direction && (
        <>
          <ThemeInjector artDirection={generatedSchema.art_direction} />
          <main className="min-h-screen">
            {generatedSchema.sections?.map((section, index) => (
              <ComponentRenderer 
                key={index} 
                section={section} 
                animationFeeling={generatedSchema.art_direction.animation_feeling}
              />
            ))}
          </main>
        </>
      )}
    </div>
  );
}
