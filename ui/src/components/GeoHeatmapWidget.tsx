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

/* ─── Colors ─────────────────────────────────────────────────────────────── */

const SEV_COLORS = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#60a5fa",
} as const;

type Severity = keyof typeof SEV_COLORS;

function intensityToSeverity(intensity: number): Severity {
  if (intensity >= 0.7) return "critical";
  if (intensity >= 0.4) return "high";
  if (intensity >= 0.2) return "medium";
  return "low";
}

/* ─── Projection ─────────────────────────────────────────────────────────── */

const MAP_W = 960;
const MAP_H = 480;

function proj(lat: number, lng: number): { x: number; y: number } {
  return {
    x: ((lng + 180) / 360) * MAP_W,
    y: ((90 - lat) / 180) * MAP_H,
  };
}

/* ─── Deterministic starfield ────────────────────────────────────────────── */

const STARS: Array<{ x: number; y: number; r: number; seed: number }> = (() => {
  const out: Array<{ x: number; y: number; r: number; seed: number }> = [];
  for (let i = 0; i < 120; i++) {
    out.push({
      x: (i * 71) % MAP_W,
      y: (i * 113) % MAP_H,
      r: 0.5 + (i % 3) * 0.3,
      seed: i,
    });
  }
  return out;
})();

/* ─── Stylized continent silhouettes (from redesign) ────────────────────── */

const CONTINENT_PATHS: string[] = [
  // North America
  "M 140,100 Q 170,70 220,80 L 280,100 L 300,130 L 290,170 L 270,200 L 240,220 L 200,240 L 170,230 L 150,200 L 135,160 Z",
  // Central America
  "M 200,240 L 230,250 L 245,275 L 240,290 L 220,285 L 205,270 Z",
  // South America
  "M 260,290 Q 290,280 310,300 L 320,340 L 310,380 L 290,420 L 270,430 L 255,400 L 250,360 L 255,320 Z",
  // Europe
  "M 450,110 Q 480,100 510,115 L 530,130 L 525,160 L 500,170 L 470,165 L 450,145 Z",
  // Africa
  "M 470,185 Q 510,180 540,200 L 560,240 L 555,290 L 535,330 L 510,340 L 490,320 L 475,280 L 465,230 Z",
  // Middle East
  "M 540,170 L 580,180 L 590,210 L 570,225 L 545,215 Z",
  // Russia / N. Asia
  "M 520,80 Q 600,70 720,85 L 810,100 L 820,130 L 770,140 L 700,135 L 620,130 L 550,125 L 520,115 Z",
  // China / SE Asia
  "M 700,150 Q 750,145 790,165 L 810,195 L 795,220 L 760,225 L 725,210 L 705,185 Z",
  // India
  "M 650,180 L 680,185 L 690,210 L 680,235 L 665,230 L 655,210 Z",
  // SE Asia islands
  "M 780,240 L 820,245 L 840,260 L 820,275 L 790,270 Z",
  "M 820,280 L 850,285 L 855,300 L 835,305 Z",
  // Australia
  "M 800,340 Q 840,335 870,350 L 885,370 L 870,390 L 830,395 L 805,380 Z",
  // Japan
  "M 830,150 L 845,155 L 850,175 L 840,185 L 828,170 Z",
  // UK / Ireland
  "M 448,120 L 460,118 L 462,135 L 452,140 Z",
  // Scandinavia
  "M 470,75 L 510,75 L 515,100 L 485,105 L 470,95 Z",
];

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface Hotspot {
  code: string;
  name: string;
  count: number;
  x: number;
  y: number;
  intensity: number;
  severity: Severity;
  color: string;
  pulseSeed: number;
}

interface Flow {
  from: Hotspot;
  to: Hotspot;
  severity: Severity;
  color: string;
  seed: number;
}

/* ─── Exported helpers for the /geo page panels ──────────────────────────── */

export interface DerivedFlow {
  from: { code: string; name: string; count: number };
  to: { code: string; name: string; count: number };
  severity: Severity;
}

/** Derive the same decorative flow arcs that GeoHeatmapWidget renders.
 *  Call with `iocStats.country_distribution.slice(0, 18)` to stay in sync. */
export function deriveFlows(
  countries: Array<{ code: string; name: string; count: number }>
): DerivedFlow[] {
  // Only include countries that have a known centroid (same filter as hotspots)
  const dist = countries.filter((c) => ISO2_CENTROIDS[c.code] !== undefined);
  if (dist.length < 2) return [];

  const maxCount = Math.max(1, ...dist.map((c) => c.count));
  const sorted = [...dist].sort((a, b) => b.count - a.count);
  const hub = sorted[0];
  const out: DerivedFlow[] = [];

  // Hub → top 4 other countries
  for (let i = 1; i < Math.min(5, sorted.length); i++) {
    const target = sorted[i];
    const intensity = Math.max(0.18, Math.min(1.0, target.count / maxCount));
    const rawSev = intensityToSeverity(intensity);
    const sev: Severity = rawSev === "low" ? "medium" : rawSev;
    out.push({ from: hub, to: target, severity: sev });
  }

  // Secondary links between ranks 2-3, 3-5 if present
  if (sorted.length >= 3) {
    out.push({ from: sorted[1], to: sorted[2], severity: "high" });
  }
  if (sorted.length >= 5) {
    out.push({ from: sorted[2], to: sorted[4], severity: "medium" });
  }

  return out;
}

interface TooltipState {
  hotspot: Hotspot;
  anchorX: number; // fractional position (0-1) inside container
  anchorY: number;
}

/** Minimal shape we need from DashboardInsights.threat_actors — avoids a
 *  cross-module type dependency. */
export interface ThreatActorMini {
  name: string;
  regions?: string[];
  count?: number;
}

export interface GeoHeatmapWidgetProps {
  stats?: IOCStatsResponse | null;
  height?: number;
  title?: string;
  subtitle?: string;
  onCountryClick?: (code: string, name: string) => void;
  /** Compact mode for the dashboard: thinner legend, no secondary chrome. */
  compact?: boolean;
  /** Accent color used for continent stipple + graticule (defaults to ember). */
  accent?: string;
  /** Optional threat-actor feed. When provided, the hover tooltip lists up to
   *  3 actors whose `regions` array contains the hotspot country. Actors whose
   *  names look like tag placeholders (pure lowercase, literal "threat_actor",
   *  or < 3 chars) are filtered out. */
  threatActors?: ThreatActorMini[];
}

/** Build a name → sorted actor-names map from the raw threat_actors feed.
 *  Drops obvious junk names so the tooltip stays clean. */
function buildActorsByRegion(
  actors: ThreatActorMini[] | undefined,
): Map<string, string[]> {
  const out = new Map<string, string[]>();
  if (!actors || actors.length === 0) return out;
  const isCleanName = (n: string): boolean => {
    if (!n || n.length < 3) return false;
    if (n === "threat_actor") return false;
    // drop pure-lowercase single-token names that look like tags
    if (/^[a-z][a-z0-9_]*$/.test(n)) return false;
    return true;
  };
  // Sort by count desc so the most-referenced actor lands first per region
  const sorted = [...actors].sort((a, b) => (b.count ?? 0) - (a.count ?? 0));
  for (const a of sorted) {
    if (!isCleanName(a.name)) continue;
    for (const region of a.regions ?? []) {
      if (!region) continue;
      const key = region.toLowerCase();
      const list = out.get(key) ?? [];
      if (!list.includes(a.name)) list.push(a.name);
      out.set(key, list);
    }
  }
  return out;
}

/* ─── Component ──────────────────────────────────────────────────────────── */

export function GeoHeatmapWidget({
  stats: statsProp,
  height,
  title = "Geo threat map",
  subtitle = "IOC activity by country",
  onCountryClick,
  compact = false,
  accent = "#f97316",
  threatActors,
}: GeoHeatmapWidgetProps) {
  const [internalStats, setInternalStats] = useState<IOCStatsResponse | null>(null);
  const [loading, setLoading] = useState(statsProp === undefined);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [tick, setTick] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  /* Fetch only if caller did not supply stats */
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

  /* Animation tick — throttled to ~30 fps + paused when tab hidden to keep the
     dashboard cheap. Full 60 fps on this many SVG elements is wasteful. */
  useEffect(() => {
    let raf: number | null = null;
    let frame = 0;
    const loop = () => {
      frame++;
      if (frame % 2 === 0 && !document.hidden) {
        setTick((t) => (t + 1) % 10_000);
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => { if (raf !== null) cancelAnimationFrame(raf); };
  }, []);

  const stats = statsProp !== undefined ? statsProp : internalStats;

  /* Build hotspots from real country_distribution */
  const hotspots: Hotspot[] = useMemo(() => {
    const dist = (stats?.country_distribution ?? []).slice(0, 18);
    if (dist.length === 0) return [];
    const maxCount = Math.max(1, ...dist.map((c) => c.count));
    return dist
      .filter((c) => ISO2_CENTROIDS[c.code] !== undefined)
      .map((c, i) => {
        const [lng, lat] = ISO2_CENTROIDS[c.code];
        const p = proj(lat, lng);
        const raw = c.count / maxCount;
        const intensity = Math.max(0.18, Math.min(1.0, raw));
        const severity = intensityToSeverity(intensity);
        return {
          code: c.code,
          name: c.name,
          count: c.count,
          x: p.x,
          y: p.y,
          intensity,
          severity,
          color: SEV_COLORS[severity],
          pulseSeed: i,
        };
      });
  }, [stats]);

  /* Region (country-name) → actor names. Lowercase-keyed for case-insensitive
     lookup against hotspot names. */
  const actorsByRegion = useMemo(
    () => buildActorsByRegion(threatActors),
    [threatActors],
  );

  /* Derive decorative flow arcs — delegates to the exported deriveFlows helper
     so the widget and the /geo Attack Corridors panel share a single source of
     truth. These are visual only; they do not represent live attack paths. */
  const flows: Flow[] = useMemo(() => {
    if (hotspots.length < 2) return [];
    // Build a minimal country array from the current hotspots (already filtered
    // to ISO2_CENTROIDS keys) and re-map back to internal Flow shape.
    const hotspotInput = hotspots.map((h) => ({
      code: h.code,
      name: h.name,
      count: h.count,
    }));
    return deriveFlows(hotspotInput).map((df, i) => {
      // Re-resolve Hotspot objects so the SVG positions are correct.
      const fromH = hotspots.find((h) => h.code === df.from.code)!;
      const toH = hotspots.find((h) => h.code === df.to.code)!;
      return {
        from: fromH,
        to: toH,
        severity: df.severity,
        color: SEV_COLORS[df.severity],
        seed: i < 5 ? i + 1 : i === 5 ? 7 : 11,
      };
    });
  }, [hotspots]);

  /* Hover handlers — position tooltip relative to the container (not viewport),
     so it tracks the hotspot even during scroll. */
  const handleHotspotEnter = useCallback((h: Hotspot) => {
    setTooltip({
      hotspot: h,
      anchorX: h.x / MAP_W,
      anchorY: h.y / MAP_H,
    });
  }, []);

  const handleHotspotLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  const t = tick * 0.03; // tick is ~30/s, t-units are radians-ish

  const isEmpty = !loading && hotspots.length === 0;
  const totalShownIOCs = useMemo(
    () => hotspots.reduce((sum, h) => sum + h.count, 0),
    [hotspots],
  );
  const totalRegions = stats?.country_distribution?.length ?? 0;
  const effectiveHeight = height ?? (compact ? 300 : undefined);
  const useAspect = effectiveHeight === undefined;

  const mapContent = (
    <div
      ref={containerRef}
      className="relative overflow-hidden rounded-md"
      style={{
        ...(useAspect
          ? { aspectRatio: `${MAP_W} / ${MAP_H}` }
          : { height: effectiveHeight }),
        background:
          "radial-gradient(ellipse at center, #0c1420 0%, #050810 70%, #030509 100%)",
      }}
    >
      {/* Starfield — painted beneath everything */}
      <svg
        className="absolute inset-0"
        width="100%"
        height="100%"
        viewBox={`0 0 ${MAP_W} ${MAP_H}`}
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        {STARS.map((s) => {
          const twinkle = 0.15 + 0.25 * Math.abs(Math.sin(t * 1.5 + s.seed));
          return (
            <circle
              key={s.seed}
              cx={s.x}
              cy={s.y}
              r={s.r}
              fill="#ffffff"
              opacity={twinkle}
            />
          );
        })}
      </svg>

      {/* Main map — graticule, continents, flows, halos, markers */}
      <svg
        className="absolute inset-0"
        width="100%"
        height="100%"
        viewBox={`0 0 ${MAP_W} ${MAP_H}`}
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <pattern id="geo-dotgrid" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.8" fill={accent} opacity="0.38" />
          </pattern>
          <filter id="geo-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="geo-glow-big" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="10" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Graticule */}
        {[0, 60, 120, 180, 240, 300, 360, 420, 480].map((y) => (
          <line
            key={`lat-${y}`}
            x1="0"
            y1={y}
            x2={MAP_W}
            y2={y}
            stroke={accent}
            strokeWidth="0.3"
            opacity="0.1"
          />
        ))}
        {[0, 120, 240, 360, 480, 600, 720, 840, 960].map((x) => (
          <line
            key={`lng-${x}`}
            x1={x}
            y1="0"
            x2={x}
            y2={MAP_H}
            stroke={accent}
            strokeWidth="0.3"
            opacity="0.1"
          />
        ))}
        {/* Equator */}
        <line
          x1="0"
          y1="240"
          x2={MAP_W}
          y2="240"
          stroke={accent}
          strokeWidth="0.5"
          opacity="0.25"
          strokeDasharray="4 4"
        />

        {/* Stippled continent silhouettes */}
        <g fill="url(#geo-dotgrid)" opacity="0.85">
          {CONTINENT_PATHS.map((d, i) => (
            <path key={i} d={d} />
          ))}
        </g>

        {/* Decorative great-circle arcs between hub hotspots */}
        {flows.map((f, i) => {
          const ax = f.from.x, ay = f.from.y;
          const bx = f.to.x, by = f.to.y;
          const mx = (ax + bx) / 2;
          const my = (ay + by) / 2;
          const dx = bx - ax;
          const dy = by - ay;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const lift = Math.min(120, dist * 0.35);
          const cy = my - lift;
          const dashOffset = (t * 40 + f.seed * 20) % 40;
          return (
            <g key={`flow-${i}`}>
              <path
                d={`M ${ax} ${ay} Q ${mx} ${cy} ${bx} ${by}`}
                fill="none"
                stroke={f.color}
                strokeWidth="1.2"
                opacity="0.4"
                style={{ filter: "url(#geo-glow)" }}
              />
              <path
                d={`M ${ax} ${ay} Q ${mx} ${cy} ${bx} ${by}`}
                fill="none"
                stroke={f.color}
                strokeWidth="0.7"
                opacity="0.9"
                strokeDasharray="4 36"
                strokeDashoffset={-dashOffset}
              />
            </g>
          );
        })}

        {/* Heat halos beneath markers */}
        {hotspots.map((h, i) => {
          const pulse = 1 + Math.sin(t * 1.5 + h.pulseSeed * 0.4) * 0.25;
          const baseR = 8 + Math.sqrt(h.count) * 4;
          const phase = (t * 0.5 + i * 0.3) % 1;
          const rippleR = baseR + phase * baseR * 2.5;
          return (
            <g key={`halo-${h.code}`}>
              <circle
                cx={h.x}
                cy={h.y}
                r={baseR * 2.5 * pulse}
                fill={h.color}
                opacity="0.08"
              />
              <circle
                cx={h.x}
                cy={h.y}
                r={baseR * 1.6 * pulse}
                fill={h.color}
                opacity="0.14"
              />
              {/* Expanding ripple */}
              <circle
                cx={h.x}
                cy={h.y}
                r={rippleR}
                fill="none"
                stroke={h.color}
                strokeWidth="0.8"
                opacity={(1 - phase) * 0.6}
              />
            </g>
          );
        })}

        {/* Hotspot markers */}
        {hotspots.map((h) => {
          const isHovered = tooltip?.hotspot.code === h.code;
          const baseR = 3 + Math.sqrt(h.count) * 0.9;
          return (
            <g
              key={`dot-${h.code}`}
              onMouseEnter={() => handleHotspotEnter(h)}
              onMouseLeave={handleHotspotLeave}
              onClick={() => onCountryClick?.(h.code, h.name)}
              style={{ cursor: onCountryClick ? "pointer" : "default" }}
            >
              <circle
                cx={h.x}
                cy={h.y}
                r={baseR + 4}
                fill={h.color}
                opacity={isHovered ? 0.4 : 0.18}
                style={{ filter: "url(#geo-glow-big)" }}
              />
              <circle
                cx={h.x}
                cy={h.y}
                r={baseR}
                fill={h.color}
                stroke="#ffffff"
                strokeWidth={isHovered ? 1.5 : 0.8}
                opacity="1"
                style={{ filter: "url(#geo-glow)" }}
              />
              <circle
                cx={h.x}
                cy={h.y}
                r={baseR * 0.4}
                fill="#ffffff"
                opacity="0.9"
              />
              {/* Enlarged invisible hit target */}
              <circle
                cx={h.x}
                cy={h.y}
                r={Math.max(baseR + 10, 18)}
                fill="transparent"
                pointerEvents="all"
              />
            </g>
          );
        })}
      </svg>

      {/* Loading state */}
      {loading && (
        <div className="absolute top-2 right-2 flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <svg className="h-3 w-3 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          Loading
        </div>
      )}

      {/* Empty state */}
      {isEmpty && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-xs text-muted-foreground">
            No geo data yet — waiting for IOC enrichment.
          </span>
        </div>
      )}

      {/* Hover tooltip — anchored to the container so it tracks the hotspot */}
      {tooltip && (() => {
        const rightSide = tooltip.anchorX > 0.5;
        const leftPct = tooltip.anchorX * 100;
        const topPct = tooltip.anchorY * 100;
        const col = tooltip.hotspot.color;
        return (
          <div
            className="absolute pointer-events-none z-20"
            style={{
              left: `${leftPct}%`,
              top: `${topPct}%`,
              transform: rightSide
                ? "translate(calc(-100% - 14px), -50%)"
                : "translate(14px, -50%)",
              background: "rgba(10,13,18,0.95)",
              backdropFilter: "blur(12px)",
              WebkitBackdropFilter: "blur(12px)",
              border: `1px solid ${col}66`,
              borderRadius: 8,
              padding: "10px 12px",
              minWidth: 180,
              maxWidth: 240,
              boxShadow: `0 12px 40px ${col}33`,
            }}
          >
            <div
              className="font-mono text-[9px] font-semibold uppercase"
              style={{ color: col, letterSpacing: 1 }}
            >
              {tooltip.hotspot.severity}
            </div>
            <div className="text-sm font-semibold mt-0.5 text-foreground">
              {tooltip.hotspot.name}
            </div>
            <div
              className="flex items-baseline gap-3 mt-2 pt-2"
              style={{ borderTop: "1px solid rgba(148,163,184,0.2)" }}
            >
              <div>
                <div className="font-mono text-[9px] uppercase text-muted-foreground" style={{ letterSpacing: 0.5 }}>
                  IOCs
                </div>
                <div
                  className="font-mono text-lg font-semibold"
                  style={{ color: col }}
                >
                  {tooltip.hotspot.count.toLocaleString()}
                </div>
              </div>
              <div className="flex-1">
                <div className="font-mono text-[9px] uppercase text-muted-foreground" style={{ letterSpacing: 0.5 }}>
                  Code
                </div>
                <div className="text-xs text-foreground/90 mt-1">
                  {tooltip.hotspot.code}
                </div>
              </div>
            </div>
            {(() => {
              const actors = actorsByRegion.get(tooltip.hotspot.name.toLowerCase());
              if (!actors || actors.length === 0) return null;
              return (
                <div
                  className="mt-2 pt-2"
                  style={{ borderTop: "1px solid rgba(148,163,184,0.2)" }}
                >
                  <div className="font-mono text-[9px] uppercase text-muted-foreground" style={{ letterSpacing: 0.5 }}>
                    Top actors
                  </div>
                  <div className="text-xs text-foreground/90 mt-1 leading-snug">
                    {actors.slice(0, 3).join(", ")}
                  </div>
                </div>
              );
            })()}
          </div>
        );
      })()}

      {/* LIVE · 24H chip (top-right) */}
      <div
        className="absolute top-3 right-3 flex items-center gap-2 font-mono text-[10px] text-muted-foreground rounded-md px-2.5 py-1.5 border"
        style={{
          background: "rgba(10,13,18,0.7)",
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
          borderColor: "rgba(148,163,184,0.18)",
        }}
      >
        <span
          className="h-1.5 w-1.5 rounded-full geo-live-pulse"
          style={{
            background: SEV_COLORS.critical,
            boxShadow: `0 0 6px ${SEV_COLORS.critical}`,
          }}
        />
        LIVE · 24H
      </div>

      {/* Scale context (bottom-right) — tells the user what they're looking at:
          how many IOCs across how many regions drive the hotspots. Rendered in
          both compact and full mode; suppressed while loading or empty so it
          doesn't show zeros. */}
      {!loading && !isEmpty && hotspots.length > 0 && (
        <div
          className="absolute bottom-3 right-3 flex items-center gap-2 font-mono text-[10px] text-muted-foreground rounded-md px-2.5 py-1.5 border"
          style={{
            background: "rgba(10,13,18,0.7)",
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            borderColor: "rgba(148,163,184,0.18)",
          }}
        >
          <span className="text-foreground/90">
            {totalShownIOCs.toLocaleString()}
          </span>
          <span>IOCs</span>
          <span className="opacity-40">·</span>
          <span className="text-foreground/90">
            {hotspots.length}
            {totalRegions > hotspots.length ? ` / ${totalRegions}` : ""}
          </span>
          <span>regions</span>
        </div>
      )}

      {/* Severity legend (bottom-left). Hidden in compact mode to save space. */}
      {!compact && (
        <div
          className="absolute bottom-3 left-3 flex gap-3 font-mono text-[10px] text-muted-foreground rounded-md px-3 py-2 border"
          style={{
            background: "rgba(10,13,18,0.7)",
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            borderColor: "rgba(148,163,184,0.18)",
          }}
        >
          {(["critical", "high", "medium"] as Severity[]).map((sev) => (
            <span key={sev} className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{
                  background: SEV_COLORS[sev],
                  boxShadow: `0 0 8px ${SEV_COLORS[sev]}`,
                }}
              />
              {sev}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <SectionCard
      title={title}
      icon={<Globe className="h-4 w-4" />}
      meta={<span className="text-[11px] text-muted-foreground">{subtitle}</span>}
    >
      {mapContent}
    </SectionCard>
  );
}

export default GeoHeatmapWidget;
