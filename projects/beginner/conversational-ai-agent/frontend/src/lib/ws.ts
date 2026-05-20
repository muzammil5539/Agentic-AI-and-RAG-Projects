/* ── WebSocket client for agent streaming ─────────────────────── */

import type { WSChatMessage, WSOutgoingEvent } from "./types";

export type WSEventHandler = (event: WSOutgoingEvent) => void;

export class AgentWebSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private handlers: Set<WSEventHandler> = new Set();
  private url: string;

  constructor(url?: string) {
    this.url =
      url || `ws://localhost:8002/ws/chat`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data: WSOutgoingEvent = JSON.parse(event.data);
        this.handlers.forEach((h) => h(data));
      } catch (e) {
        console.error("[WS] Failed to parse message:", e);
      }
    };

    this.ws.onclose = (event) => {
      console.log("[WS] Disconnected", event.code);
      // Auto-reconnect after 2s (unless intentionally closed)
      if (event.code !== 1000) {
        this.reconnectTimer = setTimeout(() => this.connect(), 2000);
      }
    };

    this.ws.onerror = (error) => {
      console.error("[WS] Error:", error);
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close(1000);
    this.ws = null;
  }

  send(message: WSChatMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.error("[WS] Not connected");
      return;
    }
    this.ws.send(JSON.stringify(message));
  }

  onEvent(handler: WSEventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
