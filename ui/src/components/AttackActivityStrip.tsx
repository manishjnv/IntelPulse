"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { getAttackMatrix } from "@/lib/api";
import type { AttackMatrixResponse } from "@/types";
import { SEVERITY_HEX } from "@/lib/severity";

/**
 * 14-column tactic-frequency strip. Each column is a thin vertical bar
 * sized to the sum of intel-count across that tactic's techniques, with
 * the top 2 tactics highlighted in the "critical" hue. Useful as an
 * at-a-glance reading of where adversary activity concentrates.
 *
 * Adapted from docs/IntelPulse Redesign.html AttackStrip (11 MITRE
 * tactics). Real MITRE ATT&CK Enterprise has 14 — this component uses
 * whatever the /techniques/matrix endpoint returns.
 */
export function AttackActivityStrip() {
  const [matrix, setMatrix] = useState<AttackMatrixResponse | null>(null);
  const [error, setError] = useState(false);

  const fetchMatrix = useCallback(async () => {
    try {
      setMatrix(await getAttackMatrix());
      setError(false);
    } catch (e) {
      console.error("[dashboard/attack-strip] matrix fetch failed", e);
      setError(true);
    }
  }, []);

  useEffect(() => {
    fetchMatrix();
    const id = setInterval(fetchMatrix, 120_000);
    return () => clearInterval(id);
  }, [fetchMatrix]);

  const aggregated = useMemo(() => {
    if (!matrix) return [];
    return matrix.tactics.map((t) => {
      const total = t.techniques.reduce((a, te) => a + te.count, 0);
      return { tactic: t.tactic, label: t.label, count: total };
    });
  }, [matrix]);

  if (error && !matrix) {
    return (
      <div className="rounded-lg border border-border/50 bg-card p-4 text-xs text-muted-foreground">
        Could not load ATT&amp;CK activity.
      </div>
    );
  }

  if (!matrix) {
    return (
      <div className="rounded-lg border border-border/50 bg-card p-4">
        <div className="h-3 w-40 rounded bg-muted/30 animate-pulse mb-3" />
        <div className="grid grid-cols-14 gap-1.5">
          {Array.from({ length: 14 }).map((_, i) => (
            <div key={i} className="h-16 rounded bg-muted/20 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const max = Math.max(1, ...aggregated.map((a) => a.count));
  const sorted = [...aggregated].sort((a, b) => b.count - a.count);
  const hotSet = new Set(sorted.slice(0, 2).map((t) => t.tactic));

  return (
    <section className="rounded-lg border border-border/50 bg-card">
      <header className="flex items-center justify-between gap-2 border-b border-border/40 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            ATT&amp;CK activity
          </p>
          <p className="text-xs font-medium text-foreground mt-0.5">
            Tactic frequency · all mapped intel
          </p>
        </div>
        <Link
          href="/techniques"
          className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
        >
          Open matrix
          <ChevronRight className="h-3 w-3" />
        </Link>
      </header>
      <div className="p-4">
        <div
          className="grid gap-1.5"
          style={{ gridTemplateColumns: `repeat(${aggregated.length}, minmax(0,1fr))` }}
        >
          {aggregated.map((t) => {
            const pct = (t.count / max) * 100;
            const hot = hotSet.has(t.tactic) && t.count > 0;
            return (
              <Link
                key={t.tactic}
                href={`/techniques#${t.tactic}`}
                className="flex flex-col gap-1 group"
                title={`${t.label}: ${t.count.toLocaleString()} mapped intel items`}
              >
                <div className="relative h-16 rounded-sm border border-border/40 bg-muted/10 overflow-hidden flex items-end">
                  <div
                    className="w-full transition-all"
                    style={{
                      height: t.count > 0 ? `${Math.max(pct, 4)}%` : 0,
                      backgroundColor: hot ? SEVERITY_HEX.critical : "hsl(var(--primary))",
                      opacity: hot ? 0.85 : 0.55,
                    }}
                  />
                  <span
                    className={`absolute top-1 right-1 text-[9px] font-mono font-semibold tabular-nums ${
                      hot ? "text-red-400" : "text-foreground/80"
                    }`}
                  >
                    {t.count > 0 ? t.count : "·"}
                  </span>
                </div>
                <div className="text-[9px] font-mono text-muted-foreground/80 text-center leading-tight truncate group-hover:text-foreground transition-colors">
                  {t.label}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
