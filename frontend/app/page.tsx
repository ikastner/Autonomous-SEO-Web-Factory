"use client";
import { useState } from "react";
import { GenerativeUISchema } from "@/types/schema";
import ComponentRenderer from "@/components/ComponentRenderer";
import ThemeInjector from "@/components/ThemeInjector";
import AgentTerminal from "@/components/AgentTerminal";

interface AgentLog {
  id: string;
  node: string;
  message: string;
  timestamp: string;
  reasoning?: string;
  status: "running" | "complete" | "error";
}

export default function Home() {
  const [targetUrl, setTargetUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedSchema, setGeneratedSchema] = useState<GenerativeUISchema | null>(null);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const getAgentMessage = (node: string): string => {
    const messages: Record<string, string> = {
      scout_node: "🔍 Extraction et analyse du contenu web...",
      seo_node: "📊 Création de la stratégie SEO et du silo sémantique...",
      ux_node: "🎨 Conception des wireframes et layouts asymétriques...",
      art_director_node: "🖌️ Génération des design tokens (vibe, typo, couleurs)...",
      copywriter_node: "✍️ Rédaction du contenu persuasif et optimisé SEO...",
      arbitre_node: "⚖️ Validation de la cohérence UX/SEO/Copy...",
      architect_node: "🏭 Compilation du schéma UI final...",
    };
    return messages[node] || `Exécution de ${node}...`;
  };

  const getAgentReasoning = (node: string): string => {
    const reasoning: Record<string, string> = {
      scout_node: "Analyse du contenu de la page cible avec Crawl4AI.\nExtraction des éléments clés : USP, tone of voice, niche.\nCompression intelligente du contexte pour optimiser les tokens LLM.",
      seo_node: "Définition de la stratégie sémantique SEO.\nCréation du silo de mots-clés (primaires, secondaires, long-tail).\nGénération des meta tags optimisés (title, description, OG tags).",
      ux_node: "Conception de l'architecture de l'information.\nDéfinition des wireframes avec layouts intelligents (centered, split_screen, asymmetric).\nOptimisation de l'UX pour la conversion.",
      art_director_node: "Analyse de la niche pour déterminer la vibe visuelle.\nGénération des design tokens : design_vibe, typography_style, animation_feeling.\nCréation mathématique de la palette de couleurs (3-5 couleurs HEX).",
      copywriter_node: "Rédaction persuasive alignée avec le tone of voice.\nOptimisation SEO du contenu (densité de mots-clés, LSI).\nCréation de CTAs percutants et social proof.",
      arbitre_node: "Validation croisée UX/SEO/Copy/Design.\nVérification de la cohérence globale.\nDétection des incohérences et demande de retry si nécessaire.",
      architect_node: "Compilation du GenerativeUISchema final.\nMapping des données vers le contrat Pydantic.\nValidation stricte du schéma avant envoi au frontend.",
    };
    return reasoning[node] || "";
  };

  const handleGenerate = async () => {
    if (!targetUrl.trim()) {
      setError("Veuillez entrer une URL valide");
      return;
    }

    setIsLoading(true);
    setIsStreaming(true);
    setError(null);
    setAgentLogs([]);
    setGeneratedSchema(null);

    try {
      const response = await fetch("http://localhost:8000/generate-site", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ target_url: targetUrl }),
      });

      if (!response.ok) {
        throw new Error("Erreur lors de la connexion au backend");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("Impossible de lire le stream");
      }

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          setIsStreaming(false);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const eventData = JSON.parse(line.slice(6));
              
              if (eventData.status === "running" && eventData.node) {
                // Ajouter un log pour le nœud en cours
                const newLog: AgentLog = {
                  id: `${eventData.node}-${Date.now()}`,
                  node: eventData.node,
                  message: getAgentMessage(eventData.node),
                  timestamp: new Date().toLocaleTimeString(),
                  reasoning: getAgentReasoning(eventData.node),
                  status: "running",
                };
                setAgentLogs((prev) => [...prev, newLog]);
              } else if (eventData.status === "complete") {
                // Pipeline terminé, récupérer le schéma
                setIsStreaming(false);
                setIsLoading(false);
                
                // Marquer le dernier log comme complété
                setAgentLogs((prev) => {
                  const updated = [...prev];
                  if (updated.length > 0) {
                    updated[updated.length - 1].status = "complete";
                  }
                  return updated;
                });

                // CORRECTION DU BUG : utiliser generative_ui_schema au lieu de sections
                if (eventData.generative_ui_schema) {
                  setGeneratedSchema(eventData.generative_ui_schema as GenerativeUISchema);
                }
              } else if (eventData.status === "error") {
                setIsStreaming(false);
                setIsLoading(false);
                setError(eventData.message || "Une erreur est survenue");
                
                // Marquer le dernier log comme erreur
                setAgentLogs((prev) => {
                  const updated = [...prev];
                  if (updated.length > 0) {
                    updated[updated.length - 1].status = "error";
                  }
                  return updated;
                });
              }
            } catch (parseError) {
              console.error("Erreur de parsing SSE:", parseError);
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue");
      setIsStreaming(false);
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
                <div className="mt-8">
                  <AgentTerminal logs={agentLogs} isStreaming={isStreaming} />
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
