"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronRight, Loader2 } from "lucide-react";

interface AgentLog {
  id: string;
  node: string;
  message: string;
  timestamp: string;
  reasoning?: string;
  status: "running" | "complete" | "error";
}

interface AgentTerminalProps {
  logs: AgentLog[];
  isStreaming: boolean;
}

/**
 * AgentTerminal — Terminal d'affichage des logs agents en temps réel.
 * 
 * Style inspiré de Gemini/Windsurf avec :
 * - Fond noir, texte vert monospace
 * - Logs animés avec framer-motion
 * - Raisonnement dépliable au clic (style accordion)
 */
export default function AgentTerminal({ logs, isStreaming }: AgentTerminalProps) {
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());

  const toggleLog = (logId: string) => {
    setExpandedLogs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  const getNodeIcon = (node: string) => {
    const icons: Record<string, string> = {
      scout_node: "🔍",
      seo_node: "📊",
      ux_node: "🎨",
      art_director_node: "🖌️",
      copywriter_node: "✍️",
      arbitre_node: "⚖️",
      architect_node: "🏗️",
    };
    return icons[node] || "⚙️";
  };

  const getNodeLabel = (node: string) => {
    const labels: Record<string, string> = {
      scout_node: "Scout Agent",
      seo_node: "SEO Strategist",
      ux_node: "UX Designer",
      art_director_node: "Art Director",
      copywriter_node: "Copywriter",
      arbitre_node: "Quality Arbitrator",
      architect_node: "System Architect",
    };
    return labels[node] || node;
  };

  return (
    <div className="bg-black rounded-lg border border-green-500/30 shadow-2xl overflow-hidden font-mono">
      {/* Header du terminal */}
      <div className="bg-gray-900 px-4 py-2 border-b border-green-500/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span className="ml-4 text-green-400 text-sm">
            Autonomous SEO Web Factory — Agent Pipeline
          </span>
        </div>
        {isStreaming && (
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Streaming...</span>
          </div>
        )}
      </div>

      {/* Corps du terminal */}
      <div className="p-4 max-h-96 overflow-y-auto bg-black">
        <AnimatePresence mode="popLayout">
          {logs.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-green-500/50 text-sm"
            >
              $ Waiting for pipeline to start...
            </motion.div>
          )}

          {logs.map((log, index) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="mb-3"
            >
              {/* Log principal */}
              <div
                className={`flex items-start gap-2 cursor-pointer hover:bg-green-500/5 p-2 rounded transition-colors ${
                  log.reasoning ? "cursor-pointer" : ""
                }`}
                onClick={() => log.reasoning && toggleLog(log.id)}
              >
                <span className="text-green-400 text-sm flex-shrink-0">
                  [{log.timestamp}]
                </span>
                <span className="text-xl flex-shrink-0">{getNodeIcon(log.node)}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-green-300 font-semibold">
                      {getNodeLabel(log.node)}
                    </span>
                    {log.status === "running" && (
                      <Loader2 className="w-3 h-3 text-green-400 animate-spin" />
                    )}
                    {log.status === "complete" && (
                      <span className="text-green-500">✓</span>
                    )}
                    {log.status === "error" && (
                      <span className="text-red-500">✗</span>
                    )}
                  </div>
                  <div className="text-green-400/80 text-sm mt-1">{log.message}</div>
                </div>
                {log.reasoning && (
                  <div className="flex-shrink-0">
                    {expandedLogs.has(log.id) ? (
                      <ChevronDown className="w-4 h-4 text-green-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-green-400" />
                    )}
                  </div>
                )}
              </div>

              {/* Raisonnement dépliable */}
              <AnimatePresence>
                {log.reasoning && expandedLogs.has(log.id) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="ml-8 mt-2 p-3 bg-green-950/20 border-l-2 border-green-500/50 rounded">
                      <div className="text-green-400/60 text-xs uppercase tracking-wider mb-2">
                        Reasoning
                      </div>
                      <div className="text-green-300/70 text-sm whitespace-pre-wrap">
                        {log.reasoning}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Curseur clignotant si streaming actif */}
        {isStreaming && (
          <motion.div
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            className="text-green-400 inline-block"
          >
            ▊
          </motion.div>
        )}
      </div>
    </div>
  );
}
