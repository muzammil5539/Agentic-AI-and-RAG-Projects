"use client";

import { useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { Eye, EyeOff, Key } from "lucide-react";

export function ApiKeyInput() {
  const apiKey = useChatStore((s) => s.apiKey);
  const setApiKey = useChatStore((s) => s.setApiKey);
  const [visible, setVisible] = useState(false);
  const [input, setInput] = useState(apiKey);

  const handleSave = () => {
    setApiKey(input.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave();
    }
  };

  return (
    <div>
      <label className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium flex items-center gap-1">
        <Key className="w-3 h-3" />
        OpenAI API Key
      </label>
      <div className="mt-1 flex gap-1">
        <div className="relative flex-1">
          <input
            type={visible ? "text" : "password"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSave}
            placeholder="sk-..."
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2.5 py-1.5 pr-7 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
          />
          <button
            onClick={() => setVisible(!visible)}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
          >
            {visible ? (
              <EyeOff className="w-3 h-3" />
            ) : (
              <Eye className="w-3 h-3" />
            )}
          </button>
        </div>
      </div>
      {apiKey && (
        <p className="text-[10px] text-green-500 mt-1">✓ Key saved locally</p>
      )}
    </div>
  );
}
