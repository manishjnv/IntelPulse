"use client";

import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

// ── Severity badge helper ──────────────────────────────────
export function severityBadge(sev: string) {
  switch (sev) {
    case "critical": return { color: "bg-red-500/20 text-red-300 border-red-500/30", label: "Critical" };
    case "high": return { color: "bg-orange-500/20 text-orange-300 border-orange-500/30", label: "High" };
    case "medium": return { color: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30", label: "Medium" };
    case "low": return { color: "bg-green-500/20 text-green-300 border-green-500/30", label: "Low" };
    default: return { color: "bg-zinc-500/20 text-zinc-300 border-zinc-500/30", label: sev || "Unknown" };
  }
}

// ── Parse MITRE technique codes ───────────────────────────
export function parseTechnique(t: string) {
  const m = t.match(/(T\d{4}(?:\.\d{3})?)/);
  return m ? { code: m[1], label: t } : { code: null, label: t };
}

// ── Clickable entity helper ───────────────────────────────
export function EntityBadge({ label, searchPrefix, className }: { label: string; searchPrefix?: string; className?: string }) {
  const router = useRouter();
  return (
    <button
      onClick={() => router.push(`/search?q=${encodeURIComponent(searchPrefix ? `${searchPrefix}:${label}` : label)}`)}
      className={cn("cursor-pointer hover:brightness-125 transition-all", className)}
      title={`Search for "${label}"`}
    >
      {label}
    </button>
  );
}

// ── Helpers: isNew / isStale ──────────────────────────────
export function isNewEntry(firstSeen: string): boolean {
  return Date.now() - new Date(firstSeen).getTime() < 24 * 60 * 60 * 1000;
}
export function isStaleEntry(lastSeen: string, days = 7): boolean {
  return Date.now() - new Date(lastSeen).getTime() > days * 24 * 60 * 60 * 1000;
}

// ── Time helpers ─────────────────────────────────────────
export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function formatPublishDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
