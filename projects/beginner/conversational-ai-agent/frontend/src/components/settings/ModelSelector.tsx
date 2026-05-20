"use client";

import { useChatStore } from "@/stores/chatStore";

export function ModelSelector() {
  const selectedModel = useChatStore((s) => s.selectedModel);
  const availableModels = useChatStore((s) => s.availableModels);
  const setModel = useChatStore((s) => s.setModel);

  return (
    <div>
      <label className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
        Model
      </label>
      <select
        value={selectedModel}
        onChange={(e) => setModel(e.target.value)}
        className="mt-1 w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/40 cursor-pointer"
      >
        {availableModels.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    </div>
  );
}
