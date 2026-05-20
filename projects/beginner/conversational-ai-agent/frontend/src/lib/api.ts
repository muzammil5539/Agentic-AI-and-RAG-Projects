/* ── REST API client ────────────────────────────────────────────── */

import type {
  ChatResponse,
  HealthResponse,
  SessionListResponse,
  Session,
  ToolListResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

async function request<T>(
  path: string,
  options: RequestInit = {},
  apiKey?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ── Endpoints ───────────────────────────────────────────────────

export const api = {
  health: () => request<HealthResponse>("/api/v1/health"),

  tools: () => request<ToolListResponse>("/api/v1/tools"),

  chat: (query: string, model: string, apiKey: string, sessionId?: string) =>
    request<ChatResponse>(
      "/api/v1/chat",
      {
        method: "POST",
        body: JSON.stringify({
          query,
          model,
          session_id: sessionId || null,
        }),
      },
      apiKey
    ),

  sessions: {
    list: (apiKey: string) =>
      request<SessionListResponse>("/api/v1/sessions", {}, apiKey),

    create: (apiKey: string, title?: string) =>
      request<Session>(
        "/api/v1/sessions",
        {
          method: "POST",
          body: JSON.stringify({ title: title || null }),
        },
        apiKey
      ),

    get: (apiKey: string, sessionId: string) =>
      request<Session>(`/api/v1/sessions/${sessionId}`, {}, apiKey),

    delete: (apiKey: string, sessionId: string) =>
      request<void>(
        `/api/v1/sessions/${sessionId}`,
        { method: "DELETE" },
        apiKey
      ),

    updateTitle: (apiKey: string, sessionId: string, title: string) =>
      request<Session>(
        `/api/v1/sessions/${sessionId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ title }),
        },
        apiKey
      ),
  },
};
