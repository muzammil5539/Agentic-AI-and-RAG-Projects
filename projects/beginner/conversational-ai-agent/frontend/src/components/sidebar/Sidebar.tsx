"use client";

import { useChatStore } from "@/stores/chatStore";
import { SessionList } from "./SessionList";
import { ApiKeyInput } from "../settings/ApiKeyInput";
import { ModelSelector } from "../settings/ModelSelector";
import {
  Bot,
  PanelLeftClose,
  PanelLeft,
  Plus,
  Settings,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState, useEffect } from "react";

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const createSession = useChatStore((s) => s.createSession);
  const apiKey = useChatStore((s) => s.apiKey);

  // Auto-open settings panel when there is no API key set
  useEffect(() => {
    if (!apiKey) setShowSettings(true);
  }, [apiKey]);

  if (collapsed) {
    return (
      <div className="w-12 bg-zinc-900 border-r border-zinc-800 flex flex-col items-center py-3 gap-2">
        <button
          onClick={() => setCollapsed(false)}
          className="w-8 h-8 rounded-lg hover:bg-zinc-800 flex items-center justify-center text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Expand sidebar"
        >
          <PanelLeft className="w-4 h-4" />
        </button>
        <button
          onClick={createSession}
          disabled={!apiKey}
          className="w-8 h-8 rounded-lg hover:bg-zinc-800 flex items-center justify-center text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
          title="New Chat"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-72 bg-zinc-900 border-r border-zinc-800 flex flex-col h-full">
      {/* Header */}
      <div className="p-3 flex items-center justify-between border-b border-zinc-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-zinc-200">AI Agent</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={createSession}
            disabled={!apiKey}
            className="w-7 h-7 rounded-lg hover:bg-zinc-800 flex items-center justify-center text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={apiKey ? "New Chat" : "Enter API key first"}
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={() => setCollapsed(true)}
            className="w-7 h-7 rounded-lg hover:bg-zinc-800 flex items-center justify-center text-zinc-400 hover:text-zinc-200 transition-colors"
            title="Collapse sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <SessionList />
      </div>

      {/* Settings — always visible at bottom */}
      <div className="border-t border-zinc-800 flex-shrink-0">
        <button
          onClick={() => setShowSettings(!showSettings)}
          className={`w-full flex items-center gap-2 px-3 py-2.5 text-xs transition-colors ${
            !apiKey
              ? "text-amber-400 hover:text-amber-300 bg-amber-500/5 hover:bg-amber-500/10"
              : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
          }`}
        >
          <Settings className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="flex-1 text-left">
            {!apiKey ? "⚠ Set API key to chat" : "Settings"}
          </span>
          {showSettings ? (
            <ChevronDown className="w-3 h-3" />
          ) : (
            <ChevronUp className="w-3 h-3" />
          )}
        </button>
        {showSettings && (
          <div className="px-3 pb-3 space-y-3 border-t border-zinc-800/50">
            <div className="pt-2">
              <ModelSelector />
            </div>
            <ApiKeyInput />
          </div>
        )}
      </div>
    </div>
  );
}
