"use client";

import { useState } from "react";
import type { AgentStep } from "@/lib/types";
import {
  ChevronDown,
  ChevronRight,
  Brain,
  Wrench,
  Eye,
  MessageSquare,
  Loader2,
} from "lucide-react";

interface Props {
  steps: AgentStep[];
  isLive?: boolean;
}

const STEP_CONFIG = {
  thought: { icon: Brain, color: "text-yellow-400", bg: "bg-yellow-400/10", label: "Thinking" },
  tool_call: { icon: Wrench, color: "text-blue-400", bg: "bg-blue-400/10", label: "Tool Call" },
  tool_result: { icon: Eye, color: "text-green-400", bg: "bg-green-400/10", label: "Result" },
  answer: { icon: MessageSquare, color: "text-purple-400", bg: "bg-purple-400/10", label: "Answer" },
} as const;

export function ThinkingPanel({ steps, isLive = false }: Props) {
  const [isOpen, setIsOpen] = useState(isLive);

  if (steps.length === 0) return null;

  return (
    <div className="w-full max-w-[80%]">
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-200 transition-colors py-1 px-2 rounded-lg hover:bg-zinc-800/50"
      >
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5" />
        )}
        {isLive ? (
          <>
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Thinking...</span>
          </>
        ) : (
          <span>
            {steps.length} step{steps.length !== 1 ? "s" : ""} · View reasoning
          </span>
        )}
      </button>

      {/* Steps list */}
      {isOpen && (
        <div className="mt-1 ml-2 border-l-2 border-zinc-700/50 pl-3 space-y-2">
          {steps.map((step, i) => {
            const config = STEP_CONFIG[step.type];
            const Icon = config.icon;

            return (
              <div key={i} className="flex gap-2 items-start text-xs">
                <div
                  className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 mt-0.5 ${config.bg}`}
                >
                  <Icon className={`w-3 h-3 ${config.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <span className={`font-medium ${config.color}`}>
                    {config.label}
                    {step.tool_name && (
                      <span className="text-zinc-400 font-normal">
                        {" "}
                        · {step.tool_name}
                      </span>
                    )}
                  </span>

                  {/* Tool args */}
                  {step.tool_args && Object.keys(step.tool_args).length > 0 && (
                    <pre className="mt-1 text-[10px] bg-zinc-900/80 border border-zinc-800 rounded-md p-2 overflow-x-auto text-zinc-400">
                      {JSON.stringify(step.tool_args, null, 2)}
                    </pre>
                  )}

                  {/* Content */}
                  {step.content && step.type !== "tool_call" && (
                    <p className="mt-0.5 text-zinc-400 whitespace-pre-wrap break-words leading-relaxed">
                      {step.content.length > 500
                        ? step.content.slice(0, 500) + "..."
                        : step.content}
                    </p>
                  )}
                </div>
              </div>
            );
          })}

          {isLive && (
            <div className="flex gap-2 items-center text-xs text-zinc-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Processing...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
