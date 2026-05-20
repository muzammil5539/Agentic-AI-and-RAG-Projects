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
  isStreaming: boolean;
  currentSteps: AgentStep[];
  streamingContent: string;

  // ── Actions ───────────────────────────────────────────
  sendMessage: (query: string) => void;
  clearMessages: () => void;

  // ── WebSocket ─────────────────────────────────────────
  ws: AgentWebSocket | null;
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
        set({
          activeSessionId: id,
          messages: [],
          currentSteps: [],
          streamingContent: "",
        });
      },

      deleteSession: async (id) => {
        const { apiKey, activeSessionId } = get();
        if (!apiKey) return;
        try {
          await api.sessions.delete(apiKey, id);
          set((s) => ({
            sessions: s.sessions.filter((sess) => sess.id !== id),
            ...(activeSessionId === id
              ? { activeSessionId: null, messages: [] }
              : {}),
          }));
        } catch (e) {
          console.error("Failed to delete session:", e);
        }
      },

      // ── Messages ────────────────────────────────────────
      messages: [],
      isStreaming: false,
      currentSteps: [],
      streamingContent: "",

      sendMessage: (query) => {
        const { ws, apiKey, selectedModel, activeSessionId } = get();
        if (!apiKey || !ws) return;

        // Add user message
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
        }));

        // Send via WebSocket
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

      // ── WebSocket ───────────────────────────────────────
      ws: null,

      connectWs: () => {
        const existing = get().ws;
        if (existing?.isConnected) return;

        const ws = new AgentWebSocket();
        ws.connect();

        ws.onEvent((event: WSOutgoingEvent) => {
          const state = get();

          switch (event.type) {
            case "thought":
              set({
                currentSteps: [
                  ...state.currentSteps,
                  {
                    type: "thought",
                    content: event.content,
                    timestamp: event.timestamp,
                  },
                ],
              });
              break;

            case "tool_call":
              set({
                currentSteps: [
                  ...state.currentSteps,
                  {
                    type: "tool_call",
                    content: `Calling ${event.tool_name}`,
                    tool_name: event.tool_name,
                    tool_args: event.tool_args,
                    timestamp: event.timestamp,
                  },
                ],
              });
              break;

            case "tool_result":
              set({
                currentSteps: [
                  ...state.currentSteps,
                  {
                    type: "tool_result",
                    content: event.content,
                    tool_name: event.tool_name,
                    timestamp: event.timestamp,
                  },
                ],
              });
              break;

            case "token":
              set({
                streamingContent: state.streamingContent + event.content,
              });
              break;

            case "done": {
              // Finalize the assistant message
              const assistantMsg: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: state.streamingContent,
                steps: state.currentSteps,
                timestamp: new Date().toISOString(),
                model: event.model,
              };

              set((s) => ({
                messages: [...s.messages, assistantMsg],
                isStreaming: false,
                currentSteps: [],
                streamingContent: "",
                activeSessionId: event.session_id || s.activeSessionId,
              }));

              // Refresh sessions list
              get().loadSessions();
              break;
            }

            case "error":
              set({
                isStreaming: false,
                currentSteps: [
                  ...state.currentSteps,
                  {
                    type: "thought",
                    content: `Error: ${event.message}`,
                    timestamp: new Date().toISOString(),
                  },
                ],
              });
              break;
          }
        });

        set({ ws });
      },

      disconnectWs: () => {
        get().ws?.disconnect();
        set({ ws: null });
      },

      // ── Init ────────────────────────────────────────────
      initHealth: async () => {
        try {
          const health = await api.health();
          set({ availableModels: health.models });
        } catch (e) {
          console.error("Backend unreachable:", e);
        }
      },
    }),
    {
      name: "agent-chat-store",
      partialize: (state) => ({
        apiKey: state.apiKey,
        selectedModel: state.selectedModel,
      }),
    }
  )
);
