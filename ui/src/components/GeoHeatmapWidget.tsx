"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Globe } from "lucide-react";
import { getIOCStats, type IOCStatsResponse } from "@/lib/api";
import { SectionCard } from "@/components/SectionCard";

/* ─── ISO2 → [lng, lat] centroids ───────────────────────────────────────── */

const ISO2_CENTROIDS: Record<string, [number, number]> = {
  US: [-98.58, 39.83],
  CA: [-96.82, 56.13],
  MX: [-102.55, 23.63],
  BR: [-51.93, -14.24],
  AR: [-63.62, -38.42],
  CL: [-71.54, -35.68],
  CO: [-74.30, 4.71],
  VE: [-66.59, 6.42],
  PE: [-75.02, -9.19],
  GB: [-3.44, 55.38],
  DE: [10.45, 51.17],
  FR: [2.21, 46.23],
  IT: [12.57, 41.87],
  ES: [-3.75, 40.46],
  NL: [5.29, 52.13],
  BE: [4.47, 50.50],
  PL: [19.15, 51.92],
  RU: [105.32, 61.52],
  UA: [31.17, 48.38],
  RO: [24.97, 45.94],
  CZ: [15.47, 49.82],
  SE: [18.64, 60.13],
  NO: [8.47, 60.47],
  FI: [25.75, 61.92],
  DK: [9.50, 56.26],
  IE: [-8.24, 53.41],
  PT: [-8.22, 39.40],
  CH: [8.23, 46.82],
  AT: [14.55, 47.52],
  GR: [21.82, 39.07],
  TR: [35.24, 38.96],
  IL: [34.85, 31.05],
  SA: [45.08, 23.89],
  AE: [53.85, 23.42],
  QA: [51.18, 25.35],
  IR: [53.69, 32.43],
  IQ: [43.68, 33.22],
  EG: [30.80, 26.82],
  ZA: [25.08, -29.00],
  NG: [8.68, 9.08],
  KE: [37.91, 0.02],
  MA: [-7.09, 31.79],
  DZ: [1.66, 28.03],
  CN: [104.20, 35.86],
  JP: [138.25, 36.20],
  KR: [127.77, 35.91],
  IN: [78.96, 20.59],
  PK: [69.35, 30.38],
  BD: [90.36, 23.68],
  VN: [108.28, 14.06],
  TH: [100.99, 15.87],
  ID: [113.92, -0.79],
  MY: [109.70, 4.21],
  SG: [103.82, 1.35],
  PH: [121.77, 12.88],
  AU: [133.78, -25.27],
  NZ: [172.69, -40.90],
  TW: [120.96, 23.70],
  HK: [114.11, 22.40],
  KP: [127.51, 40.34],
};

/* ─── Helpers ────────────────────────────────────────────────────────────── */

function lngLatToViewBox(lng: number, lat: number): [number, number] {
  const x = Math.max(2, Math.min(98, ((lng + 180) / 360) * 100));
  const y = Math.max(2, Math.min(98, ((90 - lat) / 180) * 100));
  return [x, y];
}

function intensityToColor(intensity: number): string {
  if (intensity >= 0.7) return "#ef4444"; // critical red
  if (intensity >= 0.4) return "#f97316"; // high orange
  if (intensity >= 0.2) return "#eab308"; // medium yellow
  return "#60a5fa";                        // low gray-blue
}

/** Pre-computed dot positions for the decorative land mask. Seeded so SSR
 *  and CSR produce the same markup (no Math.random in render path). */
const LAND_DOTS: Array<{ x: number; y: number }> = (() => {
  const dots: Array<{ x: number; y: number }> = [];
  // Simple linear congruential generator so output is deterministic.
  let seed = 42;
  const rand = () => {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 0xffffffff;
  };
  for (let x = 4; x < 100; x += 3) {
    for (let y = 10; y < 75; y += 3) {
      const inLand =
        (x > 15 && x < 32 && y > 18 && y < 60) || // Americas
        (x > 42 && x < 58 && y > 20 && y < 58) || // Europe/Africa
        (x > 60 && x < 90 && y > 22 && y < 55) || // Asia
        (x > 22 && x < 36 && y > 55 && y < 72) || // South America
        (x > 48 && x < 62 && y > 55 && y < 72);   // Southern Africa
      if (inLand && rand() > 0.35) dots.push({ x, y });
    }
  }
  return dots;
})();

/* ─── Props ──────────────────────────────────────────────────────────────── */

interface TooltipState {
  code: string;
  name: string;
  count: number;
  x: number;
  y: number;
}

export interface GeoHeatmapWidgetProps {
  stats?: IOCStatsResponse | null;
  height?: number;
  title?: string;
  subtitle?: string;
  onCountryClick?: (code: string, name: string) => void;
}

/* ─── Component ──────────────────────────────────────────────────────────── */

export function GeoHeatmapWidget({
  stats: statsProp,
  height = 260,
  title = "Geo threat map",
  subtitle = "IOC activity by country",
  onCountryClick,
}: GeoHeatmapWidgetProps) {
  const [internalStats, setInternalStats] = useState<IOCStatsResponse | null>(null);
  const [loading, setLoading] = useState(statsProp === undefined);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const rafRef = useRef<number | null>(null);

  // Only fetch if caller did not supply stats prop
  useEffect(() => {
    if (statsProp !== undefined) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await getIOCStats();
        if (!cancelled) setInternalStats(data);
      } catch (e) {
        console.error("[GeoHeatmapWidget] failed to fetch IOC stats", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [statsProp]);

  const stats = statsProp !== undefined ? statsProp : internalStats;

  const countries = useMemo(() => {
    return (stats?.country_distribution ?? []).slice(0, 15);
  }, [stats]);

  const continents = useMemo(() => {
    return (stats?.continent_distribution ?? []).filter((c) => c.count > 0);
  }, [stats]);

  const maxCount = useMemo(() => {
    return Math.max(1, ...countries.map((c) => c.count));
  }, [countries]);

  const maxContinentCount = useMemo(() => {
    return Math.max(1, ...continents.map((c) => c.count));
  }, [continents]);

  const hotspots = useMemo(() => {
    return countries
      .filter((c) => ISO2_CENTROIDS[c.code] !== undefined)
      .map((c) => {
        const [lng, lat] = ISO2_CENTROIDS[c.code];
        const [svgX, svgY] = lngLatToViewBox(lng, lat);
        const raw = c.count / maxCount;
        const intensity = Math.max(0.18, Math.min(1.0, raw));
        const color = intensityToColor(intensity);
        return { code: c.code, name: c.name, count: c.count, svgX, svgY, intensity, color };
      });
  }, [countries, maxCount]);

  const handleMouseEnter = useCallback(
    (
      e: React.MouseEvent<SVGCircleElement>,
      code: string,
      name: string,
      count: number,
    ) => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        setTooltip({ code, name, count, x: e.clientX, y: e.clientY });
      });
    },
    [],
  );

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGCircleElement>) => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      setTooltip((prev) => prev ? { ...prev, x: e.clientX, y: e.clientY } : prev);
    });
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => setTooltip(null));
  }, []);

  const isEmpty = !loading && countries.length === 0;
  const BASE_RADIUS = 1.6;

  return (
    <SectionCard
      title={title}
      icon={<Globe className="h-4 w-4" />}
      meta={
        <span className="text-[11px] text-muted-foreground">{subtitle}</span>
      }
    >
      <div className="relative overflow-hidden rounded-md" style={{ height }}>
        {/* SVG map */}
        <svg
          viewBox="0 0 100 80"
          width="100%"
          height="100%"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {/* Decorative dot land mask */}
          {LAND_DOTS.map((d, i) => (
            <circle
              key={i}
              cx={d.x}
              cy={d.y}
              r="0.4"
              fill="rgba(148,163,184,0.18)"
            />
          ))}

          {/* Hotspots */}
          {!loading &&
            hotspots.map((h) => (
              <g key={h.code}>
                {/* Outer halo */}
                <circle
                  cx={h.svgX}
                  cy={h.svgY}
                  r={BASE_RADIUS * h.intensity * 3.2}
                  fill={h.color}
                  opacity={0.15}
                  style={{ pointerEvents: "none" }}
                />
                {/* Mid ring */}
                <circle
                  cx={h.svgX}
                  cy={h.svgY}
                  r={BASE_RADIUS * h.intensity * 1.6}
                  fill={h.color}
                  opacity={0.4}
                  style={{ pointerEvents: "none" }}
                />
                {/* Core dot */}
                <circle
                  cx={h.svgX}
                  cy={h.svgY}
                  r={BASE_RADIUS * 0.8}
                  fill={h.color}
                  opacity={1}
                  style={{ pointerEvents: "none" }}
                />
                {/* Invisible hit target */}
                <circle
                  cx={h.svgX}
                  cy={h.svgY}
                  r={BASE_RADIUS * h.intensity * 3.5}
                  fill="transparent"
                  style={{
                    pointerEvents: "all",
                    cursor: onCountryClick ? "pointer" : "default",
                  }}
                  onMouseEnter={(e) => handleMouseEnter(e, h.code, h.name, h.count)}
                  onMouseMove={handleMouseMove}
                  onMouseLeave={handleMouseLeave}
                  onClick={() => onCountryClick?.(h.code, h.name)}
                />
              </g>
            ))}
        </svg>

        {/* Loading spinner overlay (top-right) */}
        {loading && (
          <div className="absolute top-2 right-2 flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <svg
              className="h-3 w-3 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            Loading
          </div>
        )}

        {/* Empty state */}
        {isEmpty && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs text-muted-foreground">
              No geo data yet — waiting for IOC enrichment.
            </span>
          </div>
        )}

        {/* Continent pill overlays at bottom */}
        {!loading && continents.length > 0 && (
          <div className="absolute bottom-2 left-2 right-2 flex flex-wrap gap-2">
            {continents.map((c) => {
              const intensity = c.count / maxContinentCount;
              const color = intensityToColor(intensity);
              return (
                <div
                  key={c.code}
                  className="flex items-center gap-1.5 rounded-md border border-border/40 px-2.5 py-1"
                  style={{
                    background: "rgba(10,13,18,0.82)",
                    backdropFilter: "blur(4px)",
                    WebkitBackdropFilter: "blur(4px)",
                  }}
                >
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-[10px] font-medium text-foreground/90">
                    {c.name || c.code}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {c.count.toLocaleString()}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Hover tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none rounded-md border bg-background/90 px-2.5 py-1.5 text-xs shadow-lg backdrop-blur"
          style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}
        >
          <div className="font-semibold">{tooltip.name}</div>
          <div className="text-muted-foreground">{tooltip.count.toLocaleString()} IOCs</div>
        </div>
      )}
    </SectionCard>
  );
}

export default GeoHeatmapWidget;
