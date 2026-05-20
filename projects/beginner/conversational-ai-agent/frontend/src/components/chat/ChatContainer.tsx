"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import { ThinkingPanel } from "./ThinkingPanel";
import { Bot, Wifi, WifiOff, Calculator, Cloud, Clock, Globe, Code, BookOpen } from "lucide-react";

const TOOLS = [
  { icon: Calculator, label: "Calculator", example: "What is √(144) + 2³?" },
  { icon: Cloud, label: "Weather", example: "What's the weather in Tokyo?" },
  { icon: Clock, label: "DateTime", example: "What time is it in New York?" },
  { icon: Globe, label: "Web Search", example: "Latest news on AI agents?" },
  { icon: Code, label: "Code Interpreter", example: "Write a Python fibonacci function" },
  { icon: BookOpen, label: "RAG Search", example: "Search my documents for..." },
];

export function ChatContainer() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const currentSteps = useChatStore((s) => s.currentSteps);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const wsConnected = useChatStore((s) => s.wsConnected);
  const apiKey = useChatStore((s) => s.apiKey);
  const selectedModel = useChatStore((s) => s.selectedModel);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentSteps, streamingContent]);

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/50 backdrop-blur flex-shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium text-zinc-200">Conversational AI Agent</span>
          <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">{selectedModel}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {wsConnected ? (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <Wifi className="w-3 h-3" />
              <span className="hidden sm:inline">Connected</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-zinc-500">
              <WifiOff className="w-3 h-3" />
              <span className="hidden sm:inline">Disconnected</span>
            </span>
          )}
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full gap-6 max-w-2xl mx-auto w-full">
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mx-auto mb-4">
                <Bot className="w-8 h-8 text-blue-400" />
              </div>
              <h2 className="text-xl font-semibold text-zinc-200 mb-1">Conversational AI Agent</h2>
              <p className="text-sm text-zinc-500">ReAct reasoning • 6 tools • Streaming thought process</p>
            </div>

            {!apiKey ? (
              /* Setup guide when no API key */
              <div className="w-full bg-zinc-900 border border-zinc-700/50 rounded-xl p-5 space-y-3">
                <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Get started in 2 steps</p>
                <div className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 text-xs flex items-center justify-center flex-shrink-0 font-bold mt-0.5">1</span>
                  <div>
                    <p className="text-sm text-zinc-200 font-medium">Open Settings</p>
                    <p className="text-xs text-zinc-500 mt-0.5">Click <strong className="text-zinc-300">Settings</strong> at the bottom of the sidebar</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 text-xs flex items-center justify-center flex-shrink-0 font-bold mt-0.5">2</span>
                  <div>
                    <p className="text-sm text-zinc-200 font-medium">Enter your OpenAI API key</p>
                    <p className="text-xs text-zinc-500 mt-0.5">Your key is never stored — forwarded to OpenAI per-request only</p>
                  </div>
                </div>
              </div>
            ) : (
              /* Tool suggestion grid */
              <div className="w-full grid grid-cols-2 sm:grid-cols-3 gap-2">
                {TOOLS.map(({ icon: Icon, label, example }) => (
                  <button
                    key={label}
                    onClick={() => sendMessage(example)}
                    disabled={!wsConnected}
                    className="flex flex-col items-start gap-1.5 p-3 bg-zinc-900 border border-zinc-800 rounded-xl text-left hover:border-zinc-600 hover:bg-zinc-800/60 transition-all disabled:opacity-40 disabled:cursor-not-allowed group"
                  >
                    <Icon className="w-4 h-4 text-blue-400 group-hover:text-blue-300" />
                    <span className="text-xs font-medium text-zinc-300">{label}</span>
                    <span className="text-xs text-zinc-500 line-clamp-1">{example}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Live streaming state */}
        {isStreaming && (
          <div className="space-y-2">
            {currentSteps.length > 0 && (
              <ThinkingPanel steps={currentSteps} isLive />
            )}
            {streamingContent && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-zinc-800/60 rounded-2xl rounded-tl-md px-4 py-3 max-w-[80%] text-zinc-200 text-sm whitespace-pre-wrap">
                  {streamingContent}
                  <span className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-0.5" />
                </div>
              </div>
            )}
            {currentSteps.length === 0 && !streamingContent && (
              <div className="flex gap-3 items-center">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" />
                  <span className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:0.2s]" />
                  <span className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <MessageInput />
    </div>
  );
}
