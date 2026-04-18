"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronRight, AlertTriangle, Flame } from "lucide-react";
import { useAppStore } from "@/store";
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
  /** Percent of intel items with a public exploit. When provided, replaces the
   *  "Avg risk" stat (global population mean has low actionability). */
  exploitPct?: number;
}

/* The sparkline receives the 24 hourly buckets from status.sparkline, so
 * bucket `i` corresponds to the hour that starts (23 - i) hours before now
 * when reading left-to-right — but the server generates oldest-first, so
 * bucket 0 is 23h ago and bucket 23 is the current hour. */
function Sparkline({ data }: { data: number[] }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hover, setHover] = useState<number | null>(null);
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

  const handleMove = (e: React.MouseEvent<SVGRectElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const viewX = ((e.clientX - rect.left) / rect.width) * w;
    const idx = Math.round((viewX / w) * (data.length - 1));
    setHover(Math.max(0, Math.min(data.length - 1, idx)));
  };

  // Bucket i → hour label. data[data.length-1] is the current-hour bucket,
  // data[0] is 23h ago. We convert to the starting UTC hour of each bucket.
  const hourLabel = (i: number): string => {
    const now = new Date();
    now.setUTCMinutes(0, 0, 0);
    const offsetHours = data.length - 1 - i;
    const d = new Date(now.getTime() - offsetHours * 3600_000);
    return `${String(d.getUTCHours()).padStart(2, "0")}:00 UTC`;
  };

  const hoverX =
    hover !== null
      ? (hover / Math.max(data.length - 1, 1)) * w
      : null;
  const hoverY =
    hover !== null
      ? h - (data[hover] / max) * (h - 4) - 2
      : null;

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width="100%"
        viewBox={`0 0 ${w} ${h}`}
        className="block"
      >
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
        {/* Hover crosshair */}
        {hover !== null && hoverX !== null && hoverY !== null && (
          <g pointerEvents="none">
            <line
              x1={hoverX}
              x2={hoverX}
              y1={0}
              y2={h}
              stroke={SEVERITY_HEX.info}
              strokeWidth="0.8"
              opacity="0.5"
            />
            <circle
              cx={hoverX}
              cy={hoverY}
              r="3.5"
              fill={SEVERITY_HEX.info}
              stroke="hsl(var(--card))"
              strokeWidth="1.5"
            />
          </g>
        )}
        {/* Hit target */}
        <rect
          x={0}
          y={0}
          width={w}
          height={h}
          fill="transparent"
          onMouseMove={handleMove}
          onMouseLeave={() => setHover(null)}
          style={{ cursor: "crosshair" }}
        />
      </svg>
      {/* Tooltip */}
      {hover !== null && (
        <div
          className="absolute pointer-events-none z-20 -translate-x-1/2"
          style={{
            left: `${(hover / Math.max(data.length - 1, 1)) * 100}%`,
            top: -4,
            transform: "translate(-50%, -100%)",
          }}
        >
          <div className="rounded-md border border-border/60 bg-popover px-2 py-1 text-[10px] font-mono shadow-lg whitespace-nowrap">
            <span className="text-muted-foreground">{hourLabel(hover)}</span>{" "}
            <span className="text-foreground font-semibold tabular-nums">
              {data[hover].toLocaleString()}
            </span>
          </div>
        </div>
      )}
    </div>
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

export function HeroBriefingStrip({ severityCounts, exploitPct }: HeroBriefingStripProps) {
  const status = useAppStore((s) => s.statusBar);
  const fetchStatus = useAppStore((s) => s.fetchStatusBar);
  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 60_000);
    return () => clearInterval(id);
  }, [fetchStatus]);

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
          <div className="flex items-baseline justify-between gap-2 mb-2">
            <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
              24h intel velocity
            </p>
            {status?.sparkline && status.sparkline.length > 0 && (() => {
              // Peak hour caption — the bucket with the highest count.
              const buckets = status.sparkline;
              let peakIdx = 0;
              let peakVal = buckets[0] ?? 0;
              for (let i = 1; i < buckets.length; i++) {
                if (buckets[i] > peakVal) {
                  peakVal = buckets[i];
                  peakIdx = i;
                }
              }
              if (peakVal === 0) return null;
              const now = new Date();
              now.setUTCMinutes(0, 0, 0);
              const offsetHours = buckets.length - 1 - peakIdx;
              const d = new Date(now.getTime() - offsetHours * 3600_000);
              const hh = String(d.getUTCHours()).padStart(2, "0");
              return (
                <span className="text-[9px] font-mono text-muted-foreground/60">
                  Peak {hh}:00 ·{" "}
                  <span className="text-foreground font-semibold tabular-nums">
                    {peakVal.toLocaleString()}
                  </span>
                </span>
              );
            })()}
          </div>
          {status?.sparkline && status.sparkline.length > 0 ? (
            <Sparkline data={status.sparkline} />
          ) : (
            <div className="h-[60px] w-full rounded bg-muted/20 animate-pulse" />
          )}
          <div className="mt-3 grid grid-cols-3 gap-3 text-[11px]">
            <Stat label="Ingested" value={status?.intel_24h ?? 0} />
            <Stat label="Critical" value={criticalCount} danger />
            {exploitPct !== undefined ? (
              <Stat label="Exploitable" value={exploitPct} suffix="%" />
            ) : (
              <Stat label="Avg risk" value={status?.avg_risk_score ?? 0} suffix="" />
            )}
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
