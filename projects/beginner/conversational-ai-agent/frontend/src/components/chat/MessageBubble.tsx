"use client";

import type { ChatMessage } from "@/lib/types";
import { ThinkingPanel } from "./ThinkingPanel";
import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-1 ${
          isUser
            ? "bg-zinc-700"
            : "bg-gradient-to-br from-blue-500 to-purple-600"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-zinc-300" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={`flex flex-col gap-1.5 max-w-[80%] ${isUser ? "items-end" : ""}`}>
        {/* Thinking panel (assistant only, if steps exist) */}
        {!isUser && message.steps.length > 0 && (
          <ThinkingPanel steps={message.steps} />
        )}

        {/* Message bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-blue-600 text-white rounded-tr-md"
              : "bg-zinc-800/60 text-zinc-200 rounded-tl-md"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-700 prose-code:text-blue-300">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Metadata */}
        {!isUser && message.model && (
          <span className="text-[10px] text-zinc-600 px-1">
            {message.model}
          </span>
        )}
      </div>
    </div>
  );
}
