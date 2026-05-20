/* ── Shared TypeScript types matching backend Pydantic models ────── */

// Agent step in the ReAct trace
export interface AgentStep {
  type: "thought" | "tool_call" | "tool_result" | "answer";
  content: string;
  tool_name?: string | null;
  tool_args?: Record<string, unknown> | null;
  timestamp: string;
}

// Chat message (user or assistant)
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  steps: AgentStep[];
  timestamp: string;
  model?: string;
}

// Session metadata
export interface Session {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

// Tool info
export interface ToolInfo {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  category: "openai_builtin" | "custom";
}

// ── API responses ────────────────────────────────────────────────

export interface ChatResponse {
  answer: string;
  session_id: string;
  model: string;
  steps: AgentStep[];
}

export interface SessionListResponse {
  sessions: Session[];
}

export interface ToolListResponse {
  tools: ToolInfo[];
}

export interface HealthResponse {
  status: string;
  version: string;
  models: string[];
  tools_count: number;
}

// ── WebSocket messages ──────────────────────────────────────────

export interface WSChatMessage {
  type: "chat";
  query: string;
  session_id?: string | null;
  model: string;
  api_key: string;
}

export type WSOutgoingEvent =
  | { type: "thought"; content: string; timestamp: string }
  | {
      type: "tool_call";
      tool_name: string;
      tool_args: Record<string, unknown>;
      timestamp: string;
    }
  | {
      type: "tool_result";
      tool_name: string;
      content: string;
      timestamp: string;
    }
  | { type: "token"; content: string }
  | { type: "done"; session_id: string; model: string }
  | { type: "error"; message: string };
