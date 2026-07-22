"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  action: () => void;
  category: string;
}

function fuzzyMatch(query: string, text: string): boolean {
  const lower = text.toLowerCase();
  const q = query.toLowerCase();
  let qi = 0;
  for (let i = 0; i < lower.length && qi < q.length; i++) {
    if (lower[i] === q[qi]) qi++;
  }
  return qi === q.length;
}

export default function CommandMenu() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const commands: CommandItem[] = [
    { id: "dashboard", label: "Dashboard", description: "Go to main dashboard", category: "Navigation", action: () => router.push("/dashboard") },
    { id: "tenders", label: "Tenders", description: "Browse active tenders", category: "Navigation", action: () => router.push("/tenders") },
    { id: "bid-intelligence", label: "Bid Intelligence", description: "View bid analytics & win rates", category: "Navigation", action: () => router.push("/bid-intelligence") },
    { id: "axioms", label: "Axiom Engine", description: "Manage business rules", category: "Navigation", action: () => router.push("/axioms") },
    { id: "alerts", label: "Alerts", description: "Manage tender alerts", category: "Navigation", action: () => router.push("/alerts") },
    { id: "webhooks", label: "Webhooks", description: "Manage automation webhooks", category: "Navigation", action: () => router.push("/webhooks") },
    { id: "market", label: "Market Overview", description: "View market intelligence", category: "Navigation", action: () => router.push("/market") },
    { id: "settings", label: "Settings", description: "Account & preferences", category: "Navigation", action: () => router.push("/settings") },
  ];

  const filtered = query
    ? commands.filter((c) => fuzzyMatch(query, c.label) || fuzzyMatch(query, c.description || ""))
    : commands;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setSelectedIndex(0);
      }
      if (e.key === "Escape") setOpen(false);
    },
    []
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const handleItemKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && filtered[selectedIndex]) {
      filtered[selectedIndex].action();
      setOpen(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-lg rounded-xl border border-white/10 bg-[#1E293B] shadow-2xl">
        <div className="flex items-center border-b border-white/10 px-4">
          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleItemKeyDown}
            placeholder="Type a command or search..."
            className="w-full bg-transparent px-3 py-4 text-white placeholder-gray-400 outline-none"
          />
          <kbd className="rounded bg-white/10 px-2 py-0.5 text-xs text-gray-400">ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-gray-400">No results found</div>
          ) : (
            filtered.map((item, idx) => (
              <button type="button"
                key={item.id}
                onClick={() => { item.action(); setOpen(false); }}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                  idx === selectedIndex ? "bg-[#3B82F6]/20 text-white" : "text-gray-300 hover:bg-white/5"
                }`}
              >
                <div className="flex-1">
                  <div className="text-sm font-medium">{item.label}</div>
                  {item.description && <div className="text-xs text-gray-400">{item.description}</div>}
                </div>
                <span className="text-xs text-gray-500">{item.category}</span>
              </button>
            ))
          )}
        </div>
        <div className="border-t border-white/10 px-4 py-2 text-xs text-gray-500">
          <span className="mr-3">↑↓ Navigate</span>
          <span className="mr-3">↵ Select</span>
          <span>⌘K Toggle</span>
        </div>
      </div>
    </div>
  );
}
