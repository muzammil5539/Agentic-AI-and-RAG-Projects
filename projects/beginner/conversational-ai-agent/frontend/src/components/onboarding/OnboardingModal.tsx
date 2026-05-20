"use client";

import { useState, useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import {
  Bot,
  Calculator,
  Cloud,
  Clock,
  Globe,
  Code,
  BookOpen,
  ShieldCheck,
  Trash2,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  X,
} from "lucide-react";

// ── Capability cards ────────────────────────────────────────────
const CAPS = [
  { icon: Calculator, label: "Math & Logic",  desc: "Complex equations" },
  { icon: Cloud,      label: "Weather",        desc: "Real-time forecasts" },
  { icon: Clock,      label: "Date & Time",    desc: "Timezone-aware" },
  { icon: Code,       label: "Code",           desc: "Write & explain" },
  { icon: BookOpen,   label: "Documents",      desc: "Search uploads" },
  { icon: Globe,      label: "Web Search",     desc: "Latest info" },
];

type Step = "welcome" | "apikey" | "success";

interface OnboardingModalProps {
  onComplete: () => void;
}

export function OnboardingModal({ onComplete }: OnboardingModalProps) {
  const [step, setStep] = useState<Step>("welcome");
  const [visible, setVisible] = useState(false);
  const apiKey = useChatStore((s) => s.apiKey);

  // Entrance animation after mount
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 40);
    return () => clearTimeout(t);
  }, []);

  // When API key is saved while on "apikey" step → advance to success
  useEffect(() => {
    if (apiKey && step === "apikey") {
      setStep("success");
    }
  }, [apiKey, step]);

  const handleDismiss = () => {
    setVisible(false);
    setTimeout(onComplete, 380);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{
        background: "rgba(9,9,11,0.94)",
        opacity: visible ? 1 : 0,
        transition: "opacity 0.38s ease",
      }}
    >
      {/* Animated background orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none select-none">
        <div
          className="ob-orb-pulse absolute top-1/4 left-1/3 w-96 h-96 rounded-full"
          style={{ background: "radial-gradient(circle, rgba(99,102,241,0.35) 0%, transparent 70%)", filter: "blur(40px)" }}
        />
        <div
          className="ob-orb-pulse absolute bottom-1/4 right-1/3 w-80 h-80 rounded-full"
          style={{ background: "radial-gradient(circle, rgba(139,92,246,0.3) 0%, transparent 70%)", filter: "blur(40px)", animationDelay: "2s" }}
        />
      </div>

      {/* Card */}
      <div
        className="relative w-full max-w-md bg-zinc-900 border border-zinc-700/60 rounded-2xl shadow-2xl overflow-hidden"
        style={{
          opacity: visible ? 1 : 0,
          transform: visible ? "translateY(0) scale(1)" : "translateY(16px) scale(0.96)",
          transition: "opacity 0.4s ease, transform 0.4s cubic-bezier(0.34,1.4,0.64,1)",
        }}
      >
        {/* Dismiss X — always available */}
        <button
          onClick={handleDismiss}
          className="absolute top-3 right-3 z-10 w-7 h-7 rounded-lg bg-zinc-800/60 hover:bg-zinc-700 flex items-center justify-center text-zinc-500 hover:text-zinc-300 transition-colors"
          title="Skip for now"
        >
          <X className="w-3.5 h-3.5" />
        </button>

        {step === "welcome" && (
          <WelcomeStep onNext={() => setStep("apikey")} onSkip={handleDismiss} />
        )}
        {step === "apikey" && (
          <ApiKeyStep onBack={() => setStep("welcome")} />
        )}
        {step === "success" && (
          <SuccessStep onEnter={handleDismiss} />
        )}
      </div>
    </div>
  );
}

// ── Step 1: Welcome ─────────────────────────────────────────────
function WelcomeStep({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  return (
    <div className="p-8 space-y-6 ob-fade-in">
      {/* Floating bot icon */}
      <div className="flex justify-center pt-2">
        <div
          className="ob-float w-20 h-20 rounded-2xl flex items-center justify-center shadow-xl"
          style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
        >
          <Bot className="w-10 h-10 text-white" />
        </div>
      </div>

      <div className="text-center space-y-1.5 px-2">
        <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">Meet Your AI Agent</h1>
        <p className="text-sm text-zinc-400 leading-relaxed">
          A <span className="text-zinc-200 font-medium">ReAct-powered</span> assistant that thinks
          step-by-step, calls tools, and streams its reasoning in real time.
        </p>
      </div>

      {/* Capability grid */}
      <div className="grid grid-cols-3 gap-2">
        {CAPS.map(({ icon: Icon, label, desc }, i) => (
          <div
            key={label}
            className="ob-slide-up flex flex-col items-center gap-1.5 p-3 bg-zinc-800/60 rounded-xl border border-zinc-700/40 text-center"
            style={{ animationDelay: `${i * 55}ms`, opacity: 0 }}
          >
            <Icon className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-semibold text-zinc-300">{label}</span>
            <span className="text-[10px] text-zinc-500 leading-tight">{desc}</span>
          </div>
        ))}
      </div>

      {/* Data / session note */}
      <div className="flex gap-2.5 p-3 bg-zinc-800/40 border border-zinc-700/30 rounded-xl text-xs text-zinc-400">
        <Trash2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-zinc-500" />
        <span>
          Sessions keep your chat history. Delete a session to prune its data, or use{" "}
          <span className="text-zinc-300 font-medium">Settings → Clear All Data</span> to reset everything.
        </span>
      </div>

      <div className="space-y-2">
        <button
          onClick={onNext}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm transition-colors shadow-lg"
        >
          Get Started <ArrowRight className="w-4 h-4" />
        </button>
        <button
          onClick={onSkip}
          className="w-full text-xs text-zinc-600 hover:text-zinc-400 py-1 transition-colors"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}

// ── Step 2: API Key ─────────────────────────────────────────────
function ApiKeyStep({ onBack }: { onBack: () => void }) {
  const setApiKey = useChatStore((s) => s.setApiKey);
  const [input, setInput] = useState("");
  const [visible, setVisible] = useState(false);
  const [saving, setSaving] = useState(false);

  const isValid = input.trim().startsWith("sk-") && input.trim().length > 10;

  const handleSave = () => {
    if (!isValid) return;
    setSaving(true);
    setApiKey(input.trim());
    // setSaving stays true briefly; parent useEffect transitions to success
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave();
  };

  return (
    <div className="p-8 space-y-5 ob-fade-in">
      <button
        onClick={onBack}
        className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors"
      >
        ← Back
      </button>

      {/* Icon + heading */}
      <div className="text-center space-y-2">
        <div className="w-14 h-14 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto">
          <ShieldCheck className="w-7 h-7 text-amber-400" />
        </div>
        <h2 className="text-xl font-bold text-zinc-100">Connect Your OpenAI Key</h2>
        <p className="text-sm text-zinc-400 leading-relaxed">
          Your key is{" "}
          <span className="text-emerald-400 font-medium">never stored on disk</span> — forwarded
          to OpenAI per-request only.
        </p>
      </div>

      {/* Input */}
      <div className="space-y-2 ob-slide-up" style={{ opacity: 0 }}>
        <label className="text-xs text-zinc-500 uppercase tracking-wider font-medium">
          OpenAI API Key
        </label>
        <div className="relative">
          <input
            type={visible ? "text" : "password"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="sk-..."
            autoFocus
            className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 pr-10 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/50 transition-all"
          />
          <button
            type="button"
            onClick={() => setVisible(!visible)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {input.length > 0 && !isValid && (
          <p className="text-[11px] text-amber-400">Key must start with <code>sk-</code></p>
        )}
      </div>

      {/* Privacy grid */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "Private",     desc: "Never logged" },
          { label: "Per-request", desc: "No caching" },
          { label: "Deletable",   desc: "Clear anytime" },
        ].map(({ label, desc }) => (
          <div key={label} className="text-center p-2.5 bg-zinc-800/40 rounded-xl">
            <p className="text-xs font-semibold text-emerald-400">{label}</p>
            <p className="text-[10px] text-zinc-500 mt-0.5">{desc}</p>
          </div>
        ))}
      </div>

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={!isValid || saving}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors"
      >
        {saving ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Saving…
          </>
        ) : (
          <>Save Key <ArrowRight className="w-4 h-4" /></>
        )}
      </button>
    </div>
  );
}

// ── Step 3: Success ─────────────────────────────────────────────
function SuccessStep({ onEnter }: { onEnter: () => void }) {
  useEffect(() => {
    const t = setTimeout(onEnter, 2200);
    return () => clearTimeout(t);
  }, [onEnter]);

  return (
    <div className="p-8 space-y-5 text-center ob-scale-in">
      {/* Animated check circle */}
      <div className="flex justify-center pt-2">
        <div className="w-18 h-18 relative">
          <svg viewBox="0 0 56 56" className="w-20 h-20">
            {/* Background circle */}
            <circle cx="28" cy="28" r="26" fill="none" stroke="#22c55e22" strokeWidth="2" />
            {/* Animated ring */}
            <circle
              cx="28" cy="28" r="26"
              fill="none"
              stroke="#22c55e"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray="163"
              strokeDashoffset="163"
              style={{ animation: "ob-check-draw 0.6s ease 0.1s forwards" }}
              transform="rotate(-90 28 28)"
            />
            {/* Checkmark */}
            <polyline
              points="16,28 24,36 40,20"
              fill="none"
              stroke="#22c55e"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="40"
              strokeDashoffset="40"
              style={{ animation: "ob-check-draw 0.5s ease 0.5s forwards" }}
            />
          </svg>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-bold text-zinc-100 mb-1">You&apos;re All Set!</h2>
        <p className="text-sm text-zinc-400">Your API key is connected. Starting chat…</p>
      </div>

      {/* Quick tips */}
      <div className="text-left bg-zinc-800/40 border border-zinc-700/30 rounded-xl p-4 space-y-2 ob-slide-up" style={{ opacity: 0 }}>
        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Quick tips</p>
        <p className="text-xs text-zinc-500">
          <span className="text-zinc-300">+ New Chat</span> in the sidebar starts a fresh session
        </p>
        <p className="text-xs text-zinc-500">
          Delete a session to <span className="text-zinc-300">prune its history</span> from both the UI and backend
        </p>
        <p className="text-xs text-zinc-500">
          <span className="text-zinc-300">Settings → Clear All Data</span> removes your key and all sessions
        </p>
      </div>

      <button
        onClick={onEnter}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-colors"
      >
        Enter Chat <ArrowRight className="w-4 h-4" />
      </button>

      {/* Progress bar countdown */}
      <div className="h-0.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-500/50 rounded-full"
          style={{ animation: "ob-check-draw 2.2s linear forwards", width: "100%" }}
        />
      </div>
    </div>
  );
}
