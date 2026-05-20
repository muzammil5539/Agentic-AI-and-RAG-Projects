/* ── Zustand chat store — single source of truth for the UI ────── */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AgentStep, ChatMessage, Session, WSOutgoingEvent } from "@/lib/types";
import { AgentWebSocket } from "@/lib/ws";
import { api } from "@/lib/api";

interface ChatState {
  // ── Auth ──────────────────────────────────────────────
  apiKey: string;
  setApiKey: (key: string) => void;

  // ── Model ─────────────────────────────────────────────
  selectedModel: string;
  availableModels: string[];
  setModel: (model: string) => void;

  // ── Sessions ──────────────────────────────────────────
  sessions: Session[];
  activeSessionId: string | null;
  loadSessions: () => Promise<void>;
  createSession: () => Promise<void>;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => Promise<void>;

  // ── Messages ──────────────────────────────────────────
  messages: ChatMessage[];
  messagesMap: Record<string, ChatMessage[]>;
  isStreaming: boolean;
  currentSteps: AgentStep[];
  streamingContent: string;

  // ── Actions ───────────────────────────────────────────
  sendMessage: (query: string) => void;
  clearMessages: () => void;
  clearAllData: () => Promise<void>;

  // ── WebSocket ─────────────────────────────────────────
  ws: AgentWebSocket | null;
  wsConnected: boolean;
  backendReachable: boolean;
  connectWs: () => void;
  disconnectWs: () => void;

  // ── Init ──────────────────────────────────────────────
  initHealth: () => Promise<void>;
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // ── Auth ────────────────────────────────────────────
      apiKey: "",
      setApiKey: (key) => set({ apiKey: key }),

      // ── Model ───────────────────────────────────────────
      selectedModel: "gpt-4o-mini",
      availableModels: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"],
      setModel: (model) => set({ selectedModel: model }),

      // ── Sessions ────────────────────────────────────────
      sessions: [],
      activeSessionId: null,

      loadSessions: async () => {
        const { apiKey } = get();
        if (!apiKey) return;
        try {
          const res = await api.sessions.list(apiKey);
          set({ sessions: res.sessions });
        } catch (e) {
          console.error("Failed to load sessions:", e);
        }
      },

      createSession: async () => {
        const { apiKey } = get();
        if (!apiKey) return;
        try {
          const session = await api.sessions.create(apiKey);
          set((s) => ({
            sessions: [session, ...s.sessions],
            activeSessionId: session.id,
            messages: [],
            currentSteps: [],
            streamingContent: "",
          }));
        } catch (e) {
          console.error("Failed to create session:", e);
        }
      },

      selectSession: (id) => {
        const { messagesMap } = get();
        set({
          activeSessionId: id,
          messages: messagesMap[id] ?? [],
          currentSteps: [],
          streamingContent: "",
        });
      },

      deleteSession: async (id) => {
        const { apiKey } = get();
        if (!apiKey) return;
        // Remove from local state immediately for instant UI feedback
        set((s) => ({
          sessions: s.sessions.filter((sess) => sess.id !== id),
          messagesMap: Object.fromEntries(
            Object.entries(s.messagesMap).filter(([k]) => k !== id)
          ),
          ...(s.activeSessionId === id
            ? { activeSessionId: null, messages: [], currentSteps: [], streamingContent: "" }
            : {}),
        }));
        // Best-effort delete on backend (ignore 404 — session may already be gone)
        try {
          await api.sessions.delete(apiKey, id);
        } catch (e) {
          // Silently ignore — local state is already clean
          console.warn("Session delete backend call failed (already cleaned locally):", e);
        }
      },

      // ── Messages ────────────────────────────────────────
      messages: [],
      messagesMap: {},
      isStreaming: false,
      currentSteps: [],
      streamingContent: "",

      sendMessage: (query) => {
        const { ws, apiKey, selectedModel, activeSessionId } = get();
        if (!apiKey || !ws) return;

        const userMsg: ChatMessage = {
          id: generateId(),
          role: "user",
          content: query,
          steps: [],
          timestamp: new Date().toISOString(),
        };

        set((s) => ({
          messages: [...s.messages, userMsg],
          isStreaming: true,
          currentSteps: [],
          streamingContent: "",
          // Persist user message immediately so it survives a refresh
          ...(activeSessionId
            ? {
                messagesMap: {
                  ...s.messagesMap,
                  [activeSessionId]: [...(s.messagesMap[activeSessionId] ?? []), userMsg],
                },
              }
            : {}),
        }));

        ws.send({
          type: "chat",
          query,
          session_id: activeSessionId,
          model: selectedModel,
          api_key: apiKey,
        });
      },

      clearMessages: () =>
        set({ messages: [], currentSteps: [], streamingContent: "" }),

      clearAllData: async () => {
        const { sessions, apiKey, ws } = get();
        // Best-effort delete every session on the backend
        await Promise.allSettled(
          sessions.map((s) => api.sessions.delete(apiKey, s.id))
        );
        ws?.disconnect();
        set({
          apiKey: "",
          sessions: [],
          activeSessionId: null,
          messages: [],
          messagesMap: {},
          currentSteps: [],
          streamingContent: "",
          ws: null,
          wsConnected: false,
        });
      },

      // ── WebSocket ───────────────────────────────────────
      ws: null,
      wsConnected: false,
      backendReachable: false,

      connectWs: () => {
        const existing = get().ws;
        if (existing?.isConnected) return;

        const ws = new AgentWebSocket();

        ws.onStatusChange((connected) => {
          set({ wsConnected: connected });
        });

        ws.connect();

        ws.onEvent((event: WSOutgoingEvent) => {
          const state = get();

          switch (event.type) {
            case "thought":
              set((s) => ({
                currentSteps: [
                  ...s.currentSteps,
                  { type: "thought", content: event.content, timestamp: event.timestamp },
                ],
              }));
              break;

            case "tool_call":
              set((s) => ({
                currentSteps: [
                  ...s.currentSteps,
                  {
                    type: "tool_call",
                    content: `Calling ${event.tool_name}`,
                    tool_name: event.tool_name,
                    tool_args: event.tool_args,
                    timestamp: event.timestamp,
                  },
                ],
              }));
              break;

            case "tool_result":
              set((s) => ({
                currentSteps: [
                  ...s.currentSteps,
                  {
                    type: "tool_result",
                    content: event.content,
                    tool_name: event.tool_name,
                    timestamp: event.timestamp,
                  },
                ],
              }));
              break;

            case "token":
              set((s) => ({ streamingContent: s.streamingContent + event.content }));
              break;

            case "done": {
              // Use get() to capture the fully-accumulated streamingContent
              const latest = get();
              const assistantMsg: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: latest.streamingContent,
                steps: latest.currentSteps,
                timestamp: new Date().toISOString(),
                model: event.model,
              };
              const finalSessionId = event.session_id || latest.activeSessionId;
              const newMessages = [...latest.messages, assistantMsg];

              set((s) => ({
                messages: newMessages,
                isStreaming: false,
                currentSteps: [],
                streamingContent: "",
                activeSessionId: finalSessionId,
                // Persist complete exchange atomically
                messagesMap: finalSessionId
                  ? { ...s.messagesMap, [finalSessionId]: newMessages }
                  : s.messagesMap,
              }));

              get().loadSessions();
              break;
            }

            case "error":
              set((s) => ({
                isStreaming: false,
                currentSteps: [
                  ...s.currentSteps,
                  {
                    type: "thought",
                    content: `Error: ${event.message}`,
                    timestamp: new Date().toISOString(),
                  },
                ],
              }));
              // Add an error message bubble
              set((s) => ({
                messages: [
                  ...s.messages,
                  {
                    id: generateId(),
                    role: "assistant",
                    content: `⚠️ ${event.message}`,
                    steps: s.currentSteps,
                    timestamp: new Date().toISOString(),
                  },
                ],
              }));
              break;
          }
        });

        set({ ws });
      },

      disconnectWs: () => {
        get().ws?.disconnect();
        set({ ws: null, wsConnected: false });
      },

      // ── Init ────────────────────────────────────────────
      initHealth: async () => {
        try {
          const health = await api.health();
          set({ availableModels: health.models, backendReachable: true });
        } catch (e) {
          console.error("Backend unreachable:", e);
          set({ backendReachable: false });
        }
      },
    }),
    {
      name: "agent-chat-store",
      partialize: (state) => ({
        apiKey: state.apiKey,
        selectedModel: state.selectedModel,
        messagesMap: state.messagesMap,
      }),
    }
  )
);
