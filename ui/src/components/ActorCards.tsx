"use client";

import React from "react";
import Link from "next/link";
import { Flame, ChevronRight, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { SEVERITY_HEX } from "@/lib/severity";
import type { ThreatActorInsight } from "@/types";

/**
 * Top threat-actor intensity cards. Uses live `insights.threat_actors`
 * (DashboardInsights) — no placeholder. Dedupes case-variant names
 * ("Cobalt Strike" + "cobalt strike") into a single merged entry and
 * drops generic placeholders ("threat_actor", pure lowercase tag-ish
 * single tokens) before ranking by intel volume × risk.
 */

interface ActorCardsProps {
  actors: ThreatActorInsight[];
}

const MAX_CARDS = 8;

function riskColor(risk: number): string {
  if (risk >= 80) return SEVERITY_HEX.critical;
  if (risk >= 65) return SEVERITY_HEX.high;
  if (risk >= 45) return SEVERITY_HEX.medium;
  return SEVERITY_HEX.low;
}

function formatName(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Normalize a name for dedupe: lowercase + collapse whitespace/underscores. */
function normalizeKey(name: string): string {
  return name.toLowerCase().replace(/[_\s-]+/g, " ").trim();
}

/** Drop placeholder / tag-ish names that leak from the enrichment pipeline
 *  ("threat_actor", "unknown", pure-lowercase single tokens, sub-3-char). */
function isJunkName(name: string): boolean {
  if (!name) return true;
  const trimmed = name.trim();
  if (trimmed.length < 3) return true;
  const lower = trimmed.toLowerCase();
  if (lower === "threat_actor" || lower === "threat actor") return true;
  if (lower === "unknown" || lower === "n/a" || lower === "none") return true;
  // pure-lowercase single-token that looks like a tag, not a proper name
  if (/^[a-z][a-z0-9_]*$/.test(trimmed)) return true;
  return false;
}

/** Pick the nicer display spelling when merging case variants — prefer the
 *  one with more uppercase letters (more likely to be the canonical form). */
function pickPrettier(a: string, b: string): string {
  const upperCount = (s: string) => (s.match(/[A-Z]/g) || []).length;
  return upperCount(a) >= upperCount(b) ? a : b;
}

function mergeActors(actors: ThreatActorInsight[]): ThreatActorInsight[] {
  const byKey = new Map<string, ThreatActorInsight>();
  for (const a of actors) {
    if (isJunkName(a.name)) continue;
    const key = normalizeKey(a.name);
    const prev = byKey.get(key);
    if (!prev) {
      byKey.set(key, {
        name: a.name,
        count: a.count,
        avg_risk: a.avg_risk,
        cves: [...(a.cves ?? [])],
        industries: [...(a.industries ?? [])],
        regions: [...(a.regions ?? [])],
      });
      continue;
    }
    // Weighted risk merge — keeps the combined avg_risk honest.
    const totalCount = prev.count + a.count;
    const merged: ThreatActorInsight = {
      name: pickPrettier(prev.name, a.name),
      count: totalCount,
      avg_risk:
        totalCount > 0
          ? (prev.avg_risk * prev.count + a.avg_risk * a.count) / totalCount
          : 0,
      cves: Array.from(new Set([...(prev.cves ?? []), ...(a.cves ?? [])])),
      industries: Array.from(
        new Set([...(prev.industries ?? []), ...(a.industries ?? [])]),
      ),
      regions: Array.from(
        new Set([...(prev.regions ?? []), ...(a.regions ?? [])]),
      ),
    };
    byKey.set(key, merged);
  }
  return Array.from(byKey.values());
}

export function ActorCards({ actors }: ActorCardsProps) {
  const cleaned = React.useMemo(() => mergeActors(actors), [actors]);
  const top = React.useMemo(
    () =>
      [...cleaned]
        .sort(
          (a, b) =>
            b.count * (b.avg_risk || 0) - a.count * (a.avg_risk || 0),
        )
        .slice(0, MAX_CARDS),
    [cleaned],
  );

  if (top.length === 0) {
    return null;
  }

  // Row-below predicate for the md 2-col grid border logic. A card gets a
  // bottom border iff another row sits below it.
  const totalRows = Math.ceil(top.length / 2);
  const lastRowStart = (totalRows - 1) * 2;

  return (
    <section className="rounded-lg border border-border/50 bg-card">
      <header className="flex items-center justify-between gap-2 border-b border-border/40 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            Most active actors
          </p>
          <p className="text-xs font-medium text-foreground mt-0.5">
            Ranked by intel volume × risk · {top.length} shown
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
          const cveCount = a.cves?.length ?? 0;
          const industryCount = a.industries?.length ?? 0;
          const topCve = a.cves?.[0];
          const needsRowBorder = i < lastRowStart;
          return (
            <Link
              key={a.name + i}
              href={`/search?q=${encodeURIComponent(a.name)}`}
              className={cn(
                "p-4 transition-colors hover:bg-accent/20 block group",
                needsRowBorder && "md:border-b md:border-border/30",
              )}
              title={`Search intel mentioning ${a.name}`}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                    {formatName(a.name)}
                  </div>
                  {regions.length > 0 && (
                    <div className="text-[10px] font-mono text-muted-foreground/70 mt-0.5 truncate">
                      {regions.join(" · ")}
                      {a.regions && a.regions.length > regions.length && (
                        <span className="opacity-60"> +{a.regions.length - regions.length}</span>
                      )}
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
              {/* industry chips + optional top-CVE chip */}
              {(industries.length > 0 || topCve) && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {industries.map((ind) => (
                    <span
                      key={ind}
                      className="text-[9px] font-mono font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded bg-muted/30 text-muted-foreground"
                    >
                      {ind}
                    </span>
                  ))}
                  {topCve && (
                    <span
                      className="text-[9px] font-mono font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded flex items-center gap-1"
                      style={{
                        background: `${color}1f`,
                        color,
                        border: `1px solid ${color}33`,
                      }}
                      title={`Top CVE linked to this actor`}
                    >
                      <ShieldAlert className="h-2.5 w-2.5" />
                      {topCve}
                    </span>
                  )}
                </div>
              )}
              {/* stat strip: intel count · CVE count · industries count */}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Flame className="h-3 w-3" style={{ color }} />
                  <span className="tabular-nums font-semibold text-foreground">
                    {a.count.toLocaleString()}
                  </span>
                  <span>intel</span>
                </span>
                {cveCount > 0 && (
                  <>
                    <span className="opacity-40">·</span>
                    <span className="flex items-center gap-1">
                      <span className="tabular-nums font-semibold text-foreground">
                        {cveCount}
                      </span>
                      <span>CVE{cveCount === 1 ? "" : "s"}</span>
                    </span>
                  </>
                )}
                {industryCount > 0 && (
                  <>
                    <span className="opacity-40">·</span>
                    <span className="flex items-center gap-1">
                      <span className="tabular-nums font-semibold text-foreground">
                        {industryCount}
                      </span>
                      <span>
                        {industryCount === 1 ? "industry" : "industries"}
                      </span>
                    </span>
                  </>
                )}
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
