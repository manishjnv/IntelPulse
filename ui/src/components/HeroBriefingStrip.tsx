"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, AlertTriangle, Flame } from "lucide-react";
import { getStatusBar } from "@/lib/api";
import type { StatusBarData } from "@/types";
import { SeverityStackBar } from "@/components/SeverityStackBar";
import { SEVERITY_HEX } from "@/lib/severity";

/**
 * Top-of-dashboard "situation read" strip — three columns:
 *   LEFT:  posture label + headline sentence templated from live counts
 *   MIDDLE: 24h intel sparkline + 3 stats (Ingested / Critical / Avg risk)
 *   RIGHT: 4-bucket severity stack + caption
 *
 * Lifted in spirit from docs/IntelPulse Redesign.html HeroRead. Additive —
 * renders above existing dashboard content; no removal of any widget.
 * Self-fetches /api/v1/status/bar (CF edge-cached, ~60ms) on a 60s tick.
 */
interface HeroBriefingStripProps {
  severityCounts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
}

function Sparkline({ data }: { data: number[] }) {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const w = 260;
  const h = 60;
  const points = data.map((v, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * w;
    const y = h - (v / max) * (h - 4) - 2;
    return `${x},${y}`;
  });
  const area = `0,${h} ${points.join(" ")} ${w},${h}`;
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="block">
      <defs>
        <linearGradient id="hero-spark" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={SEVERITY_HEX.info} stopOpacity="0.35" />
          <stop offset="100%" stopColor={SEVERITY_HEX.info} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#hero-spark)" />
      <polyline
        points={points.join(" ")}
        stroke={SEVERITY_HEX.info}
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
      />
      {/* latest-marker */}
      <circle
        cx={(data.length - 1) / Math.max(data.length - 1, 1) * w}
        cy={h - (data[data.length - 1] / max) * (h - 4) - 2}
        r="3"
        fill={SEVERITY_HEX.info}
      />
    </svg>
  );
}

function postureLabel(criticalCount: number, highCount: number): {
  text: string;
  color: string;
} {
  if (criticalCount >= 3) return { text: "Elevated posture", color: SEVERITY_HEX.critical };
  if (criticalCount >= 1 || highCount >= 10) return { text: "Guarded posture", color: SEVERITY_HEX.high };
  return { text: "Normal posture", color: SEVERITY_HEX.low };
}

function utcTimeLabel(): string {
  const d = new Date();
  const date = d.toISOString().slice(0, 10);
  const time = d.toISOString().slice(11, 16);
  return `${date} · ${time} UTC`;
}

export function HeroBriefingStrip({ severityCounts }: HeroBriefingStripProps) {
  const [status, setStatus] = useState<StatusBarData | null>(null);
  const refresh = useCallback(async () => {
    try {
      setStatus(await getStatusBar());
    } catch {
      // best-effort
    }
  }, []);
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, [refresh]);

  const posture = postureLabel(severityCounts.critical, severityCounts.high);
  const criticalCount = severityCounts.critical;
  const highCount = severityCounts.high;

  return (
    <section
      className="relative overflow-hidden rounded-xl border border-border/50 bg-gradient-to-br from-card via-card to-card/80 p-5 md:p-6"
      aria-label="Situation read"
    >
      {/* Accent glow — keeps it on-brand with the card treatment elsewhere */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full blur-3xl"
        style={{ background: `radial-gradient(circle, ${posture.color}22 0%, transparent 60%)` }}
      />

      <div className="relative grid grid-cols-1 lg:grid-cols-[1.3fr_1fr_1fr] gap-6 lg:gap-8">
        {/* LEFT — posture + headline + CTAs */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span
              className="h-2 w-2 rounded-full animate-pulse-slow"
              style={{ backgroundColor: posture.color, boxShadow: `0 0 10px ${posture.color}` }}
            />
            <span
              className="text-[10px] font-mono font-semibold uppercase tracking-widest"
              style={{ color: posture.color }}
            >
              {posture.text} · {utcTimeLabel()}
            </span>
          </div>
          <h2 className="text-xl md:text-2xl lg:text-[26px] font-semibold tracking-tight leading-snug text-foreground">
            {criticalCount > 0 ? (
              <>
                <span style={{ color: SEVERITY_HEX.critical }} className="font-bold">
                  {criticalCount.toLocaleString()} critical
                </span>
                {highCount > 0 ? (
                  <>
                    {" and "}
                    <span style={{ color: SEVERITY_HEX.high }} className="font-bold">
                      {highCount.toLocaleString()} high
                    </span>
                  </>
                ) : null}
                {" advisories are in scope in the last "}
                <span className="text-primary font-bold">24 hours</span>.
              </>
            ) : (
              <>
                No critical advisories in the last{" "}
                <span className="text-primary font-bold">24 hours</span> — posture remains{" "}
                <span style={{ color: posture.color }} className="font-bold">
                  {posture.text.toLowerCase()}
                </span>.
              </>
            )}
          </h2>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/threats"
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              Open threat feed
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              href="/briefings"
              className="inline-flex items-center gap-1.5 rounded-md border border-border/60 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent/40 transition-colors"
            >
              <Flame className="h-3.5 w-3.5" />
              Today&apos;s briefing
            </Link>
          </div>
        </div>

        {/* MIDDLE — 24h sparkline + stat row */}
        <div>
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70 mb-2">
            24h intel velocity
          </p>
          {status?.sparkline && status.sparkline.length > 0 ? (
            <Sparkline data={status.sparkline} />
          ) : (
            <div className="h-[60px] w-full rounded bg-muted/20 animate-pulse" />
          )}
          <div className="mt-3 grid grid-cols-3 gap-3 text-[11px]">
            <Stat label="Ingested" value={status?.intel_24h ?? 0} />
            <Stat label="Critical" value={criticalCount} danger />
            <Stat label="Avg risk" value={status?.avg_risk_score ?? 0} suffix="" />
          </div>
        </div>

        {/* RIGHT — severity stack + caption */}
        <div>
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70 mb-2">
            Severity posture
          </p>
          <SeverityStackBar counts={severityCounts} />
        </div>
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  danger,
  suffix = "",
}: {
  label: string;
  value: number;
  danger?: boolean;
  suffix?: string;
}) {
  return (
    <div>
      <div className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground/70">
        {label}
      </div>
      <div
        className={`text-lg font-semibold tabular-nums mt-0.5 ${
          danger ? "text-red-400" : "text-foreground"
        }`}
      >
        {value.toLocaleString()}
        {suffix}
      </div>
    </div>
  );
}
