"use client";

import React, { useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { TrendPoint } from "@/types";
import { SEVERITY_HEX } from "@/lib/severity";

/**
 * 30-day ingestion trend chart — SVG area-and-line over the
 * insights.ingestion_trend series with date labels at 4 evenly-spaced
 * x-positions. Keeps the chart inline-SVG so it ships ~zero additional
 * JS weight (vs pulling recharts). Adapted from docs/IntelPulse Redesign.html
 * IngestTrend.
 */
interface IngestionTrendChartProps {
  data: TrendPoint[];
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  const mon = d.toLocaleString("en-US", { month: "short" });
  return `${mon} ${d.getDate()}`;
}

export function IngestionTrendChart({ data }: IngestionTrendChartProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  if (!data || data.length < 2) return null;
  const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date));
  const maxCount = Math.max(1, ...sorted.map((d) => d.count));
  const totalCount = sorted.reduce((a, d) => a + d.count, 0);
  const w = 700;
  const h = 140;
  const pad = 8;

  const points = sorted
    .map((d, i) => {
      const x = (i / (sorted.length - 1)) * w;
      const y = h - (d.count / maxCount) * (h - pad * 2) - pad;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const area = `0,${h} ${points} ${w},${h}`;

  // X-axis: 4 labels — first / 1/3 / 2/3 / last
  const labelIndices = [
    0,
    Math.round(sorted.length / 3),
    Math.round((sorted.length * 2) / 3),
    sorted.length - 1,
  ];

  /* Hover → nearest-day index. Runs on mousemove over an invisible overlay
     inside the SVG so we can get viewBox-space coordinates regardless of
     how the SVG is scaled by its container. */
  const handleMove = (e: React.MouseEvent<SVGRectElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    // x in viewBox-space (0..w)
    const viewX = ((e.clientX - rect.left) / rect.width) * w;
    const idx = Math.round((viewX / w) * (sorted.length - 1));
    const clamped = Math.max(0, Math.min(sorted.length - 1, idx));
    setHoverIdx(clamped);
  };
  const handleLeave = () => setHoverIdx(null);

  const hover = hoverIdx !== null ? sorted[hoverIdx] : null;
  const hoverPrev =
    hoverIdx !== null && hoverIdx > 0 ? sorted[hoverIdx - 1] : null;
  const hoverDelta =
    hover && hoverPrev ? hover.count - hoverPrev.count : 0;

  return (
    <section className="rounded-lg border border-border/50 bg-card">
      <Link
        href="/threats"
        className="group flex items-center justify-between gap-2 border-b border-border/40 px-4 py-3 hover:bg-accent/30 transition-colors"
      >
        <div className="min-w-0">
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            Intel ingestion
          </p>
          <p className="text-xs font-medium text-foreground mt-0.5 inline-flex items-center gap-1">
            {sorted.length}-day volume
            <ArrowRight className="h-3 w-3 opacity-0 -translate-x-1 group-hover:opacity-60 group-hover:translate-x-0 transition-all" />
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs font-mono font-semibold tabular-nums text-foreground">
            {totalCount.toLocaleString()}
          </div>
          <div className="text-[9px] font-mono text-muted-foreground/70 uppercase tracking-widest">
            total ingested
          </div>
        </div>
      </Link>
      <div className="p-4 relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${w} ${h + 22}`}
          width="100%"
          className="block overflow-visible"
        >
          <defs>
            <linearGradient id="ingest-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={SEVERITY_HEX.info} stopOpacity="0.28" />
              <stop offset="100%" stopColor={SEVERITY_HEX.info} stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* gridlines */}
          {[0.25, 0.5, 0.75].map((p) => (
            <line
              key={p}
              x1="0"
              x2={w}
              y1={h * p}
              y2={h * p}
              stroke="currentColor"
              className="text-border/40"
              strokeDasharray="2,4"
            />
          ))}
          <polygon points={area} fill="url(#ingest-grad)" />
          <polyline
            points={points}
            stroke={SEVERITY_HEX.info}
            strokeWidth="1.6"
            fill="none"
            strokeLinecap="round"
          />
          {/* latest-marker */}
          {sorted.length > 0 && (() => {
            const last = sorted[sorted.length - 1];
            const x = w;
            const y = h - (last.count / maxCount) * (h - pad * 2) - pad;
            return (
              <circle cx={x} cy={y} r="3.5" fill={SEVERITY_HEX.info} stroke="hsl(var(--card))" strokeWidth="2" />
            );
          })()}
          {/* x-axis labels */}
          {labelIndices.map((idx) => {
            const x = (idx / (sorted.length - 1)) * w;
            const anchor = idx === 0 ? "start" : idx === sorted.length - 1 ? "end" : "middle";
            return (
              <text
                key={idx}
                x={x}
                y={h + 16}
                fill="currentColor"
                className="text-muted-foreground/70"
                fontSize="10"
                fontFamily="ui-monospace, monospace"
                textAnchor={anchor}
              >
                {formatShortDate(sorted[idx].date)}
              </text>
            );
          })}
          {/* Hover crosshair + marker */}
          {hoverIdx !== null && (() => {
            const d = sorted[hoverIdx];
            const x = (hoverIdx / (sorted.length - 1)) * w;
            const y = h - (d.count / maxCount) * (h - pad * 2) - pad;
            return (
              <g pointerEvents="none">
                <line
                  x1={x}
                  x2={x}
                  y1={0}
                  y2={h}
                  stroke={SEVERITY_HEX.info}
                  strokeWidth="0.8"
                  opacity="0.4"
                />
                <circle
                  cx={x}
                  cy={y}
                  r="4"
                  fill={SEVERITY_HEX.info}
                  stroke="hsl(var(--card))"
                  strokeWidth="2"
                />
              </g>
            );
          })()}
          {/* Invisible hover catcher — placed last so it's on top */}
          <rect
            x={0}
            y={0}
            width={w}
            height={h + 22}
            fill="transparent"
            onMouseMove={handleMove}
            onMouseLeave={handleLeave}
            style={{ cursor: "crosshair" }}
          />
        </svg>
        {/* Hover tooltip — absolute-positioned, tracks nearest day */}
        {hover && hoverIdx !== null && (() => {
          const leftPct = (hoverIdx / (sorted.length - 1)) * 100;
          const dateLabel = new Date(hover.date).toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
          });
          return (
            <div
              className="absolute pointer-events-none z-20 -translate-x-1/2"
              style={{ left: `calc(${leftPct}% + 16px)`, top: 8 }}
            >
              <div className="rounded-md border border-border/60 bg-popover px-2.5 py-1.5 text-[10px] font-mono shadow-lg whitespace-nowrap">
                <div className="text-muted-foreground">{dateLabel}</div>
                <div className="text-foreground font-semibold tabular-nums">
                  {hover.count.toLocaleString()} items
                  {hoverPrev && (
                    <span
                      className={
                        hoverDelta > 0
                          ? "ml-1.5 text-emerald-400"
                          : hoverDelta < 0
                            ? "ml-1.5 text-red-400"
                            : "ml-1.5 text-muted-foreground"
                      }
                    >
                      {hoverDelta > 0 ? "+" : ""}
                      {hoverDelta}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })()}
      </div>
    </section>
  );
}
