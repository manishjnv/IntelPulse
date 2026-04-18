"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { SEVERITY_HEX } from "@/lib/severity";

/**
 * Dense 4-bucket severity posture strip. A single thin stacked bar with a
 * 2x2 legend grid underneath — designed for an at-a-glance read that
 * complements the full ThreatLevelBar without duplicating it.
 *
 * Derived from the "Obsidian" redesign proposal: `docs/IntelPulse Redesign.html`
 * SeverityStack component. Kept additive (does not remove ThreatLevelBar).
 */
interface SeverityStackBarProps {
  counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  className?: string;
}

const TIERS: Array<{
  key: keyof SeverityStackBarProps["counts"];
  label: string;
  color: string;
}> = [
  { key: "critical", label: "Critical", color: SEVERITY_HEX.critical },
  { key: "high", label: "High", color: SEVERITY_HEX.high },
  { key: "medium", label: "Medium", color: SEVERITY_HEX.medium },
  { key: "low", label: "Low", color: SEVERITY_HEX.low },
];

export function SeverityStackBar({ counts, className }: SeverityStackBarProps) {
  const total =
    counts.critical + counts.high + counts.medium + counts.low;
  if (total === 0) {
    return (
      <div className={cn("text-xs text-muted-foreground", className)}>
        No severity data.
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Thin 8px stacked bar */}
      <div className="flex h-2 overflow-hidden rounded-full bg-muted/30">
        {TIERS.map((t) => {
          const n = counts[t.key];
          if (n === 0) return null;
          const pct = (n / total) * 100;
          return (
            <div
              key={t.key}
              style={{ width: `${pct}%`, backgroundColor: t.color }}
              title={`${t.label}: ${n.toLocaleString()} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>

      {/* 2x2 legend grid — tabular-nums for jitter-free refresh */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono">
        {TIERS.map((t) => {
          const n = counts[t.key];
          return (
            <div key={t.key} className="flex items-center gap-2">
              <span
                className="h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ backgroundColor: t.color }}
              />
              <span className="text-muted-foreground">{t.label}</span>
              <span className="ml-auto font-semibold tabular-nums text-foreground">
                {n.toLocaleString()}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
