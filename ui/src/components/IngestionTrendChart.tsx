"use client";

import React from "react";
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

  return (
    <section className="rounded-lg border border-border/50 bg-card">
      <header className="flex items-center justify-between gap-2 border-b border-border/40 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            Intel ingestion
          </p>
          <p className="text-xs font-medium text-foreground mt-0.5">
            {sorted.length}-day volume
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
      </header>
      <div className="p-4">
        <svg viewBox={`0 0 ${w} ${h + 22}`} width="100%" className="block overflow-visible">
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
        </svg>
      </div>
    </section>
  );
}
