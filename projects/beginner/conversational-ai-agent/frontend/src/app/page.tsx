"use client";

import { useEffect, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";
import { AlertTriangle } from "lucide-react";

export default function Home() {
  const connectWs = useChatStore((s) => s.connectWs);
  const disconnectWs = useChatStore((s) => s.disconnectWs);
  const initHealth = useChatStore((s) => s.initHealth);
  const backendReachable = useChatStore((s) => s.backendReachable);
  const apiKey = useChatStore((s) => s.apiKey);

  const [showOnboarding, setShowOnboarding] = useState(false);

  // Show on first visit if no API key
  useEffect(() => {
    if (!apiKey) setShowOnboarding(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-show if key is cleared (logout / clear all data)
  useEffect(() => {
    if (!apiKey) setShowOnboarding(true);
  }, [apiKey]);

  useEffect(() => {
    initHealth();
    connectWs();
    return () => disconnectWs();
  }, [connectWs, disconnectWs, initHealth]);

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      {/* Backend-unreachable banner */}
      {backendReachable === false && (
        <div className="flex items-center gap-2 px-4 py-2 bg-red-950/60 border-b border-red-800/50 text-red-300 text-xs">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>
            Backend unreachable at <code className="font-mono">localhost:8002</code> — start it with{" "}
            <code className="font-mono">python main.py</code>
          </span>
        </div>
      )}
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0">
          <ChatContainer />
        </main>
      </div>

      {/* Onboarding overlay */}
      {showOnboarding && (
        <OnboardingModal onComplete={() => setShowOnboarding(false)} />
      )}
    </div>
  );
}
