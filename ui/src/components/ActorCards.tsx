"use client";

import React from "react";
import Link from "next/link";
import { Flame, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { SEVERITY_HEX } from "@/lib/severity";

/**
 * Top-4 threat-actor intensity cards in a 2x2 grid. Uses live
 * `insights.threat_actors` data (DashboardInsights) — no placeholder.
 *
 * Adapted from docs/IntelPulse Redesign.html ActorCards. Additive,
 * renders as a SectionCard on the dashboard.
 */
import type { ThreatActorInsight } from "@/types";

interface ActorCardsProps {
  actors: ThreatActorInsight[];
}

function riskColor(risk: number): string {
  if (risk >= 80) return SEVERITY_HEX.critical;
  if (risk >= 65) return SEVERITY_HEX.high;
  if (risk >= 45) return SEVERITY_HEX.medium;
  return SEVERITY_HEX.low;
}

function formatName(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ActorCards({ actors }: ActorCardsProps) {
  const top = [...actors]
    .sort((a, b) => (b.count * (b.avg_risk || 0)) - (a.count * (a.avg_risk || 0)))
    .slice(0, 4);

  if (top.length === 0) {
    return null;
  }

  return (
    <section className="rounded-lg border border-border/50 bg-card">
      <header className="flex items-center justify-between gap-2 border-b border-border/40 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            Most active actors
          </p>
          <p className="text-xs font-medium text-foreground mt-0.5">
            Ranked by intel volume × risk
          </p>
        </div>
        <Link
          href="/threats?feed_type=threat_actor"
          className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
        >
          All actors
          <ChevronRight className="h-3 w-3" />
        </Link>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border/30">
        {top.map((a, i) => {
          const color = riskColor(a.avg_risk);
          const pct = Math.min(100, Math.max(4, a.avg_risk));
          const industries = (a.industries ?? []).slice(0, 3);
          const regions = (a.regions ?? []).slice(0, 3);
          return (
            <div
              key={a.name + i}
              className={cn(
                "p-4 transition-colors hover:bg-accent/20",
                i < 2 && "md:border-b md:border-border/30"
              )}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-foreground truncate">
                    {formatName(a.name)}
                  </div>
                  {regions.length > 0 && (
                    <div className="text-[10px] font-mono text-muted-foreground/70 mt-0.5 truncate">
                      {regions.join(" · ")}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <div
                    className="text-xl font-semibold tabular-nums leading-none"
                    style={{ color }}
                  >
                    {Math.round(a.avg_risk)}
                  </div>
                  <div className="text-[9px] font-mono text-muted-foreground/70 uppercase tracking-wider mt-0.5">
                    risk
                  </div>
                </div>
              </div>
              {/* intensity bar */}
              <div className="h-[3px] w-full bg-muted/30 rounded-full overflow-hidden mb-2.5">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>
              {/* industries */}
              <div className="flex flex-wrap gap-1 mb-2">
                {industries.map((ind) => (
                  <span
                    key={ind}
                    className="text-[9px] font-mono font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded bg-muted/30 text-muted-foreground"
                  >
                    {ind}
                  </span>
                ))}
              </div>
              {/* count line */}
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <Flame className="h-3 w-3" style={{ color }} />
                <span className="tabular-nums font-semibold text-foreground">
                  {a.count.toLocaleString()}
                </span>
                <span>intel items mentioning this actor</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
