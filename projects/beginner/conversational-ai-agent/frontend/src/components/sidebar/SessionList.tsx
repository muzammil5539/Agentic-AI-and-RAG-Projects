"use client";

import { useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import { MessageSquare, Trash2 } from "lucide-react";

export function SessionList() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const selectSession = useChatStore((s) => s.selectSession);
  const deleteSession = useChatStore((s) => s.deleteSession);
  const loadSessions = useChatStore((s) => s.loadSessions);
  const apiKey = useChatStore((s) => s.apiKey);

  useEffect(() => {
    if (apiKey) loadSessions();
  }, [apiKey, loadSessions]);

  if (!apiKey) {
    return (
      <div className="px-3 py-6 text-center text-xs text-zinc-500">
        Enter your API key to get started
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="px-3 py-6 text-center text-xs text-zinc-500">
        No conversations yet
      </div>
    );
  }

  return (
    <div className="py-2 space-y-0.5">
      {sessions.map((session) => {
        const isActive = session.id === activeSessionId;
        return (
          <div
            key={session.id}
            className={`group flex items-center gap-2 px-3 py-2 mx-1 rounded-lg cursor-pointer transition-colors ${
              isActive
                ? "bg-zinc-800 text-zinc-100"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
            }`}
            onClick={() => selectSession(session.id)}
          >
            <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="text-xs truncate flex-1">{session.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteSession(session.id);
              }}
              className="w-5 h-5 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400 transition-all"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
