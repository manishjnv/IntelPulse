"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { TopCVEInsight } from "@/types";
import { SEVERITY_HEX } from "@/lib/severity";

/**
 * Top-CVEs heat rail — one row per CVE with a max_risk-proportional bar,
 * plus KEV / EXPL tags. Adapted from docs/IntelPulse Redesign.html CveRail.
 * Data comes from insights.top_cves (DashboardInsights).
 */
interface CveHeatRailProps {
  cves: TopCVEInsight[];
  limit?: number;
}

const accentCve = "#b8e34d";

export function CveHeatRail({ cves, limit = 8 }: CveHeatRailProps) {
  if (!cves || cves.length === 0) return null;
  const top = [...cves]
    .sort((a, b) => b.count - a.count || b.max_risk - a.max_risk)
    .slice(0, limit);
  const maxCount = Math.max(1, ...top.map((c) => c.count));

  return (
    <section className="rounded-lg border border-border/50 bg-card">
      <header className="flex items-center justify-between gap-2 border-b border-border/40 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            Top CVEs
          </p>
          <p className="text-xs font-medium text-foreground mt-0.5">
            Ranked by intel mentions · max_risk color
          </p>
        </div>
        <Link
          href="/threats?feed_type=vulnerability"
          className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
        >
          All CVEs
          <ChevronRight className="h-3 w-3" />
        </Link>
      </header>
      <div>
        {top.map((c, i) => {
          const pct = (c.count / maxCount) * 100;
          const barColor = c.is_kev
            ? SEVERITY_HEX.critical
            : c.has_exploit
              ? SEVERITY_HEX.high
              : SEVERITY_HEX.info;
          const product = c.products?.[0] ?? "—";
          return (
            <Link
              key={c.cve_id}
              href={`/search?q=${encodeURIComponent(c.cve_id)}`}
              className={`block px-4 py-2.5 hover:bg-accent/20 transition-colors ${
                i < top.length - 1 ? "border-b border-border/30" : ""
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span
                  className="text-xs font-mono font-semibold flex-1 min-w-0 truncate"
                  style={{ color: accentCve }}
                >
                  {c.cve_id}
                </span>
                {c.is_kev && (
                  <span
                    className="text-[9px] font-mono font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded"
                    style={{
                      color: SEVERITY_HEX.critical,
                      backgroundColor: `${SEVERITY_HEX.critical}15`,
                    }}
                  >
                    KEV
                  </span>
                )}
                {c.has_exploit && (
                  <span
                    className="text-[9px] font-mono font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded"
                    style={{
                      color: SEVERITY_HEX.high,
                      backgroundColor: `${SEVERITY_HEX.high}15`,
                    }}
                  >
                    EXPL
                  </span>
                )}
                <span className="text-xs font-mono font-semibold tabular-nums text-foreground min-w-[24px] text-right">
                  {c.count}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-[3px] bg-muted/30 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${pct}%`, backgroundColor: barColor }}
                  />
                </div>
                <span className="text-[10px] font-mono text-muted-foreground/70 truncate max-w-[140px]">
                  {product}
                </span>
                <span className="text-[10px] font-mono tabular-nums text-muted-foreground/70">
                  risk {c.max_risk}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
