"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import { ThinkingPanel } from "./ThinkingPanel";
import { Bot } from "lucide-react";

export function ChatContainer() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const currentSteps = useChatStore((s) => s.currentSteps);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages or streaming content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentSteps, streamingContent]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
              <Bot className="w-8 h-8 text-blue-400" />
            </div>
            <div className="text-center max-w-md">
              <h2 className="text-xl font-semibold text-zinc-200 mb-2">
                Conversational AI Agent
              </h2>
              <p className="text-sm text-zinc-400">
                Ask me anything. I can search the web, calculate math, check the
                weather, look up dates, run code, and search your documents.
              </p>
            </div>
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
