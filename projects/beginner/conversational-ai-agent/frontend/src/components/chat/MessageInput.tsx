"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import { Send, Loader2, WifiOff } from "lucide-react";

export function MessageInput() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const apiKey = useChatStore((s) => s.apiKey);
  const wsConnected = useChatStore((s) => s.wsConnected);

  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || !apiKey || !wsConnected) return;
    sendMessage(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getPlaceholder = () => {
    if (!apiKey) return "Open Settings and enter your OpenAI API key →";
    if (!wsConnected) return "Connecting to backend…";
    if (isStreaming) return "Agent is thinking…";
    return "Ask me anything… (Enter to send, Shift+Enter for newline)";
  };

  const canSend = !!apiKey && !!input.trim() && !isStreaming && wsConnected;

  return (
    <div className="border-t border-zinc-800 bg-zinc-900/80 backdrop-blur px-4 py-3 flex-shrink-0">
      {/* Status bar */}
      {(!apiKey || !wsConnected) && (
        <div className="max-w-3xl mx-auto mb-2 flex items-center gap-1.5 text-xs">
          {!wsConnected && (
            <span className="flex items-center gap-1 text-zinc-500">
              <WifiOff className="w-3 h-3" />
              Not connected to backend
            </span>
          )}
          {!apiKey && wsConnected && (
            <span className="text-amber-500/80">
              Enter your OpenAI API key in Settings to start chatting
            </span>
          )}
        </div>
      )}
      <div className="max-w-3xl mx-auto flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={getPlaceholder()}
          disabled={!apiKey || isStreaming || !wsConnected}
          rows={1}
          className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40 resize-none disabled:opacity-50 transition-all"
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors flex-shrink-0"
          title={canSend ? "Send message" : ""}
        >
          {isStreaming ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  );
}
