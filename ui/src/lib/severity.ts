// Single source of truth for severity, feed-type, and risk-score visual tokens.
// Prefer these exports over re-defining `Record<string, string>` tables locally.
// Companion to `lib/utils.ts` which exports coarser semver-style badge helpers.

export type Severity =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "info"
  | "unknown";

export type FeedType =
  | "vulnerability"
  | "ioc"
  | "malware"
  | "exploit"
  | "advisory"
  | "threat_actor"
  | "campaign";

// Hex values for recharts / inline-style consumers (donut segments, progress
// bars, ThreatLevelBar). Resolved via `severityHex()` for unknown keys.
export const SEVERITY_HEX: Record<Severity, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
  info: "#3b82f6",
  unknown: "#6b7280",
};

export const FEED_TYPE_HEX: Record<FeedType, string> = {
  vulnerability: "#ef4444",
  ioc: "#f97316",
  malware: "#a855f7",
  exploit: "#ec4899",
  advisory: "#3b82f6",
  threat_actor: "#14b8a6",
  campaign: "#8b5cf6",
};

// Tailwind class bundles for badge-style pills (bg-tint + foreground + border).
// Matches the legacy `InsightDetailModal.SEV_COLORS` shape so that component can
// migrate later without breaking pixel parity.
export const SEVERITY_CLASSES: Record<Severity, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/20",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/20",
  low: "bg-green-500/15 text-green-400 border-green-500/20",
  info: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  unknown: "bg-muted text-muted-foreground border-border",
};

export function severityHex(s: string): string {
  return SEVERITY_HEX[s as Severity] ?? SEVERITY_HEX.unknown;
}

export function feedTypeHex(ft: string): string {
  return FEED_TYPE_HEX[ft as FeedType] ?? SEVERITY_HEX.unknown;
}

export function severityClasses(s: string): string {
  return SEVERITY_CLASSES[s as Severity] ?? SEVERITY_CLASSES.unknown;
}

// Risk-score bucket → Tailwind bundle combining tint background + readable
// foreground, sized for ~28px badges. Four buckets (80+/60+/40+/else) to match
// the dashboard's historical palette. `lib/utils.riskBg()` uses five buckets +
// /10 opacity; prefer this one for new code, keep the old one for existing call
// sites that rely on the finer bucketing.
export function riskBucketClasses(score: number): string {
  if (score >= 80) return "bg-red-500/15 text-red-400";
  if (score >= 60) return "bg-orange-500/15 text-orange-400";
  if (score >= 40) return "bg-yellow-500/15 text-yellow-400";
  return "bg-green-500/15 text-green-400";
}
