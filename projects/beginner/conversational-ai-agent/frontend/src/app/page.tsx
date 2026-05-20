"use client";

import { useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatContainer } from "@/components/chat/ChatContainer";

export default function Home() {
  const connectWs = useChatStore((s) => s.connectWs);
  const disconnectWs = useChatStore((s) => s.disconnectWs);
  const initHealth = useChatStore((s) => s.initHealth);

  useEffect(() => {
    initHealth();
    connectWs();
    return () => disconnectWs();
  }, [connectWs, disconnectWs, initHealth]);

  return (
    <div className="flex h-screen bg-zinc-950">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <ChatContainer />
      </main>
    </div>
  );
}
