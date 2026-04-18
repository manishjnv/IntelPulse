"use client";

import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import type { GraphNode, GraphEdge, GraphResponse } from "@/types";

/* ── Cyber-theme colour palettes ──────────────────────── */
const NODE_COLORS: Record<string, { fill: string; glow: string; icon: string }> = {
  intel: { fill: "#3b82f6", glow: "#60a5fa", icon: "I" },
  ioc: { fill: "#f97316", glow: "#fb923c", icon: "!" },
  technique: { fill: "#8b5cf6", glow: "#a78bfa", icon: "T" },
  cve: { fill: "#ef4444", glow: "#f87171", icon: "C" },
};

const SEVERITY_RING: Record<string, string> = {
  critical: "#dc2626",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
  info: "#6b7280",
  unknown: "#374151",
};

/* Edge palette — slightly desaturated from the node palette so links
 * read as "connective tissue" rather than competing with node colour. */
const EDGE_COLORS: Record<string, string> = {
  "shares-ioc": "#e8944a",
  shares_ioc: "#e8944a",
  "shares-cve": "#d85555",
  shares_cve: "#d85555",
  "shares-technique": "#9b82d1",
  shares_technique: "#9b82d1",
  indicates: "#6b9ae0",
  uses: "#4ab88f",
  exploits: "#c84545",
  "co-occurs": "#6b7280",
  co_occurs: "#6b7280",
  "related-to": "#4db6c9",
};

/* ── Edge evidence extractor ──────────────────────────
 * Relationship metadata populated by the worker tasks —
 * shapes we handle:
 *   shares-ioc   → { shared_ioc_count: n }
 *   indicates    → { ioc_value, ioc_type }
 *   shares-cve   → { cve_id } / { shared_cve_count }
 *   shares-technique → { technique_id } / { shared_technique_count }
 * Returns at most 3 human-readable lines.
 */
function extractEvidence(edge: GraphEdge): Array<{ label: string; value: string }> {
  const m = (edge.metadata || {}) as Record<string, unknown>;
  const out: Array<{ label: string; value: string }> = [];
  const push = (label: string, value: unknown) => {
    if (value === undefined || value === null || value === "") return;
    out.push({ label, value: String(value) });
  };

  if (typeof m.ioc_value === "string") {
    const t = typeof m.ioc_type === "string" ? m.ioc_type : "ioc";
    push(`via ${t}:`, m.ioc_value);
  }
  if (typeof m.shared_ioc_count === "number" && m.shared_ioc_count > 0) {
    push("shared iocs:", m.shared_ioc_count);
  }
  if (typeof m.cve_id === "string") push("via cve:", m.cve_id);
  if (typeof m.shared_cve_count === "number" && m.shared_cve_count > 0) {
    push("shared cves:", m.shared_cve_count);
  }
  if (typeof m.technique_id === "string") push("via technique:", m.technique_id);
  if (typeof m.shared_technique_count === "number" && m.shared_technique_count > 0) {
    push("shared techniques:", m.shared_technique_count);
  }

  if (edge.first_seen) {
    const d = new Date(edge.first_seen);
    if (!isNaN(d.getTime())) push("first seen:", d.toLocaleDateString());
  }

  return out.slice(0, 3);
}

/* ── layout ──────────────────────────────────────────── */
interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  isCenter?: boolean;
}

/**
 * Orbital layout — the shape we render at depth=1. The queried entity sits
 * at the geometric center; satellites are placed on concentric rings, one
 * ring per type, in a fixed priority order (intel → ioc → cve → technique).
 * Within a ring, nodes are spaced evenly; start-angles are staggered per
 * ring so adjacent rings don't align into radial spokes. This beats the
 * previous force-directed initial layout for 1-hop data: predictable,
 * symmetric, no hairball even when one type has 40+ satellites.
 */
function orbitalLayout(
  nodes: GraphNode[],
  center: string,
  width: number,
  height: number,
): SimNode[] {
  const cx = width / 2;
  const cy = height / 2;
  const centerNode = nodes.find((n) => n.id === center);
  const satellites = nodes.filter((n) => n.id !== center);

  const ringOrder = ["intel", "ioc", "cve", "technique"];
  const byType: Record<string, GraphNode[]> = {};
  satellites.forEach((n) => { (byType[n.type] ??= []).push(n); });
  const types = ringOrder.filter((t) => byType[t]?.length);
  // Any extra type we didn't anticipate (e.g. future "actor") lands on
  // the outermost ring in insertion order.
  Object.keys(byType).forEach((t) => { if (!types.includes(t)) types.push(t); });

  const minDim = Math.min(width, height);
  // Generous inner radius + wide ring gap so the centre sits alone in
  // a clear "breathing room" disc and each type-ring is visually distinct.
  // firstRing 0.36 keeps the first ring well outside the hero's ambient
  // halo; ringGap 0.20 gives air between type bands.
  const firstRing = minDim * 0.36;
  const ringGap = minDim * 0.20;
  const subRingGap = 52;     // px between sub-rings of the same type
  const nodePitch = 56;      // min px between node centers on a sub-ring

  const out: SimNode[] = [];
  if (centerNode) {
    out.push({ ...centerNode, x: cx, y: cy, vx: 0, vy: 0, isCenter: true });
  }

  // Walk each type outward; when a type has more nodes than fit on one
  // circle at the current radius, split across concentric sub-rings so
  // labels don't collide. The next type then starts outside this type's
  // outermost sub-ring to prevent cross-type overlap.
  let currentR = firstRing;
  types.forEach((type, ti) => {
    const group = byType[type];
    const count = group.length;
    const circumference = 2 * Math.PI * currentR;
    const maxPerRing = Math.max(8, Math.floor(circumference / nodePitch));
    const subRings = Math.ceil(count / maxPerRing);
    const perSub = Math.ceil(count / subRings);

    for (let i = 0; i < count; i++) {
      const subIdx = Math.floor(i / perSub);
      const subR = currentR + subIdx * subRingGap;
      const idxInSub = i % perSub;
      const countInSub = Math.min(perSub, count - subIdx * perSub);
      // Stagger start-angle per type and per sub-ring so nothing aligns
      // into radial spokes.
      const startAngle = ti * 0.45 + subIdx * 0.21;
      const angle = startAngle + (idxInSub / countInSub) * 2 * Math.PI;
      out.push({
        ...group[i],
        x: cx + subR * Math.cos(angle),
        y: cy + subR * Math.sin(angle),
        vx: 0,
        vy: 0,
        isCenter: false,
      });
    }

    // Advance past this type's outermost sub-ring before laying the next.
    currentR += (subRings - 1) * subRingGap + ringGap;
  });

  return out;
}

/**
 * Force-directed fallback — kept for data with no resolvable center (or
 * a future multi-hop mode). Depth=1 data from the backend always has a
 * center node so the orbital path is used in practice.
 */
function initialLayout(
  nodes: GraphNode[],
  center: string,
  width: number,
  height: number,
): SimNode[] {
  const cx = width / 2;
  const cy = height / 2;
  const byType: Record<string, GraphNode[]> = {};
  nodes.forEach((n) => {
    (byType[n.type] ??= []).push(n);
  });
  const types = Object.keys(byType);

  return nodes.map((n) => {
    const isCenter = n.id === center;
    if (isCenter) return { ...n, x: cx, y: cy, vx: 0, vy: 0, isCenter };

    const ti = types.indexOf(n.type);
    const group = byType[n.type];
    const gi = group.indexOf(n);
    const sectorAngle = (2 * Math.PI) / Math.max(types.length, 1);
    const baseAngle = ti * sectorAngle;
    const spread = sectorAngle * 0.8;
    const angle = baseAngle + (gi / Math.max(group.length, 1)) * spread;
    const r = 120 + Math.random() * 100 + gi * 3;
    return {
      ...n,
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      vx: 0,
      vy: 0,
      isCenter: false,
    };
  });
}

/**
 * Edge geometry — quadratic bezier from source to target, bowed
 * consistently to one side so parallel edges don't overprint. Returns
 * the SVG path, the control point, and the point on the curve at t=0.5
 * (used for hover-tooltip anchoring).
 */
function edgeGeometry(sx: number, sy: number, tx: number, ty: number) {
  const dx = tx - sx;
  const dy = ty - sy;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const bow = Math.min(32, len * 0.13);
  // Perpendicular unit vector (90° CCW rotation).
  const px = -dy / len;
  const py = dx / len;
  const mx = (sx + tx) / 2;
  const my = (sy + ty) / 2;
  const cx = mx + px * bow;
  const cy = my + py * bow;
  // Q at t=0.5: 0.25*P0 + 0.5*P1 + 0.25*P2.
  const curveMidX = 0.25 * sx + 0.5 * cx + 0.25 * tx;
  const curveMidY = 0.25 * sy + 0.5 * cy + 0.25 * ty;
  return { cx, cy, curveMidX, curveMidY, path: `M${sx},${sy} Q${cx},${cy} ${tx},${ty}` };
}

/** Evaluate a quadratic bezier at parameter t ∈ [0,1]. Used for animated edge particles. */
function bezierAt(
  sx: number, sy: number, cx: number, cy: number, tx: number, ty: number, t: number,
) {
  const u = 1 - t;
  return {
    x: u * u * sx + 2 * u * t * cx + t * t * tx,
    y: u * u * sy + 2 * u * t * cy + t * t * ty,
  };
}

function simulate(nodes: SimNode[], edges: GraphEdge[], iterations = 120) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const repulsion = 5000;
  const attraction = 0.004;
  const centerGravity = 0.002;
  const damping = 0.88;

  for (let iter = 0; iter < iterations; iter++) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = repulsion / (dist * dist);
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        if (!a.isCenter) { a.vx += dx; a.vy += dy; }
        if (!b.isCenter) { b.vx -= dx; b.vy -= dy; }
      }
    }

    for (const e of edges) {
      const s = nodeMap.get(e.source);
      const t = nodeMap.get(e.target);
      if (!s || !t) continue;
      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const fx = dx * attraction;
      const fy = dy * attraction;
      if (!s.isCenter) { s.vx += fx; s.vy += fy; }
      if (!t.isCenter) { t.vx -= fx; t.vy -= fy; }
    }

    const cx = nodes.reduce((s, n) => s + n.x, 0) / nodes.length;
    const cy = nodes.reduce((s, n) => s + n.y, 0) / nodes.length;
    for (const n of nodes) {
      if (n.isCenter) continue;
      n.vx -= (n.x - cx) * centerGravity;
      n.vy -= (n.y - cy) * centerGravity;
      n.vx *= damping;
      n.vy *= damping;
      n.x += n.vx;
      n.y += n.vy;
    }
  }
}

/* ── component ────────────────────────────────────────── */
interface Props {
  data: GraphResponse;
  width?: number;
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
  onNodeSelect?: (node: GraphNode | null) => void;
  selectedNodeId?: string | null;
  className?: string;
}

export function GraphExplorer({
  data,
  width: propWidth,
  height = 640,
  onNodeClick,
  onNodeSelect,
  selectedNodeId,
  className,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(propWidth || 800);
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);
  const [dragNode, setDragNode] = useState<string | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const [animTick, setAnimTick] = useState(0);
  const [filterQuery, setFilterQuery] = useState("");

  // Measure container width responsively
  useEffect(() => {
    if (propWidth) { setContainerWidth(propWidth); return; }
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(Math.floor(entry.contentRect.width));
      }
    });
    observer.observe(el);
    setContainerWidth(el.clientWidth || 800);
    return () => observer.disconnect();
  }, [propWidth]);

  const width = containerWidth;

  // Animated particle tick
  useEffect(() => {
    const interval = setInterval(() => setAnimTick((t) => (t + 1) % 1000), 50);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!data.nodes.length) { setNodes([]); return; }
    const w = isFullscreen ? (typeof window !== "undefined" ? window.innerWidth : 1200) : width;
    const h = isFullscreen ? (typeof window !== "undefined" ? window.innerHeight - 60 : 800) : height;
    const hasCenter = data.nodes.some((n) => n.id === data.center);
    if (hasCenter) {
      // 1-hop data — orbital layout is final, no force simulation needed.
      setNodes(orbitalLayout(data.nodes, data.center, w, h));
    } else {
      // Fallback for data without an identifiable center.
      const sim = initialLayout(data.nodes, data.center, w, h);
      simulate(sim, data.edges);
      setNodes(sim);
    }
    setTransform({ x: 0, y: 0, k: 1 });
  }, [data, width, height, isFullscreen]);

  // ESC to exit fullscreen
  useEffect(() => {
    if (!isFullscreen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setIsFullscreen(false); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isFullscreen]);

  const handleMouseDown = useCallback(
    (id: string) => (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragNode(id);
    },
    [],
  );

  const handleBgMouseDown = useCallback((e: React.MouseEvent) => {
    if (dragNode) return;
    setPanStart({ x: e.clientX, y: e.clientY, tx: transform.x, ty: transform.y });
  }, [dragNode, transform]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (panStart && !dragNode) {
        setTransform((t) => ({
          ...t,
          x: panStart.tx + (e.clientX - panStart.x),
          y: panStart.ty + (e.clientY - panStart.y),
        }));
        return;
      }
      if (!dragNode || !svgRef.current) return;
      const svg = svgRef.current;
      const pt = svg.createSVGPoint();
      pt.x = e.clientX;
      pt.y = e.clientY;
      const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
      setNodes((prev) =>
        prev.map((n) =>
          n.id === dragNode
            ? { ...n, x: (svgP.x - transform.x) / transform.k, y: (svgP.y - transform.y) / transform.k }
            : n,
        ),
      );
    },
    [dragNode, transform, panStart],
  );

  const handleMouseUp = useCallback(() => {
    setDragNode(null);
    setPanStart(null);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    setTransform((t) => ({
      ...t,
      k: Math.min(4, Math.max(0.15, t.k * factor)),
    }));
  }, []);

  const zoomIn = () => setTransform((t) => ({ ...t, k: Math.min(4, t.k * 1.3) }));
  const zoomOut = () => setTransform((t) => ({ ...t, k: Math.max(0.15, t.k / 1.3) }));
  const resetView = () => setTransform({ x: 0, y: 0, k: 1 });
  const toggleFullscreen = useCallback(() => setIsFullscreen((f) => !f), []);

  // Serialise the live SVG with its gradient defs + a painted background.
  // Used by both exporters so the output looks like what the user sees —
  // the canvas background is normally a CSS gradient, which SVG export
  // alone wouldn't capture, so we inject a rect with an inline gradient.
  const buildSerialisedSVG = useCallback((): string | null => {
    const svg = svgRef.current;
    if (!svg) return null;

    const w = svg.clientWidth || svg.viewBox.baseVal.width || 800;
    const h = svg.clientHeight || svg.viewBox.baseVal.height || 560;

    // Clone so we don't mutate the live DOM.
    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
    clone.setAttribute("width", String(w));
    clone.setAttribute("height", String(h));
    clone.setAttribute("viewBox", `0 0 ${w} ${h}`);

    // Prepend a real background rect (CSS gradient on the original SVG
    // doesn't survive serialisation).
    const bgDef = clone.ownerDocument?.createElementNS("http://www.w3.org/2000/svg", "defs");
    const bgGrad = clone.ownerDocument?.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
    if (bgDef && bgGrad) {
      bgGrad.setAttribute("id", "export-bg");
      bgGrad.setAttribute("x1", "0"); bgGrad.setAttribute("y1", "0");
      bgGrad.setAttribute("x2", "1"); bgGrad.setAttribute("y2", "1");
      ["#0a0e1a", "#0f172a", "#0a101f"].forEach((c, i) => {
        const s = clone.ownerDocument!.createElementNS("http://www.w3.org/2000/svg", "stop");
        s.setAttribute("offset", `${i * 50}%`);
        s.setAttribute("stop-color", c);
        bgGrad.appendChild(s);
      });
      bgDef.appendChild(bgGrad);
      clone.insertBefore(bgDef, clone.firstChild);

      const bgRect = clone.ownerDocument!.createElementNS("http://www.w3.org/2000/svg", "rect");
      bgRect.setAttribute("width", "100%");
      bgRect.setAttribute("height", "100%");
      bgRect.setAttribute("fill", "url(#export-bg)");
      clone.insertBefore(bgRect, bgDef.nextSibling);
    }

    return new XMLSerializer().serializeToString(clone);
  }, []);

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const timestamp = () =>
    new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);

  const exportSVG = useCallback(() => {
    const s = buildSerialisedSVG();
    if (!s) return;
    const blob = new Blob([s], { type: "image/svg+xml;charset=utf-8" });
    downloadBlob(blob, `intelpulse-graph-${timestamp()}.svg`);
  }, [buildSerialisedSVG]);

  const exportPNG = useCallback(() => {
    const s = buildSerialisedSVG();
    if (!s || !svgRef.current) return;
    const w = svgRef.current.clientWidth || 800;
    const h = svgRef.current.clientHeight || 560;
    const img = new Image();
    const url = URL.createObjectURL(
      new Blob([s], { type: "image/svg+xml;charset=utf-8" }),
    );
    img.onload = () => {
      // 2× DPR for crisp PNG on retina displays.
      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = w * scale;
      canvas.height = h * scale;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.scale(scale, scale);
        ctx.drawImage(img, 0, 0, w, h);
      }
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => {
        if (blob) downloadBlob(blob, `intelpulse-graph-${timestamp()}.png`);
      }, "image/png");
    };
    img.onerror = () => URL.revokeObjectURL(url);
    img.src = url;
  }, [buildSerialisedSVG]);

  const [showExportMenu, setShowExportMenu] = useState(false);
  const [pathMode, setPathMode] = useState(false);
  const [pathSource, setPathSource] = useState<string | null>(null);
  const [pathTarget, setPathTarget] = useState<string | null>(null);

  // BFS shortest path within the currently-loaded graph. Returns ordered
  // list of node IDs from source → target inclusive, or null if no path.
  const pathIds = useMemo((): string[] | null => {
    if (!pathSource || !pathTarget || pathSource === pathTarget) return null;
    const adj = new Map<string, string[]>();
    data.edges.forEach((e) => {
      if (!adj.has(e.source)) adj.set(e.source, []);
      if (!adj.has(e.target)) adj.set(e.target, []);
      adj.get(e.source)!.push(e.target);
      adj.get(e.target)!.push(e.source);
    });
    const prev = new Map<string, string | null>();
    prev.set(pathSource, null);
    const queue: string[] = [pathSource];
    while (queue.length) {
      const cur = queue.shift()!;
      if (cur === pathTarget) break;
      for (const n of adj.get(cur) || []) {
        if (!prev.has(n)) {
          prev.set(n, cur);
          queue.push(n);
        }
      }
    }
    if (!prev.has(pathTarget)) return null;
    const out: string[] = [];
    let step: string | null = pathTarget;
    while (step !== null) {
      out.unshift(step);
      step = prev.get(step) ?? null;
    }
    return out;
  }, [pathSource, pathTarget, data.edges]);

  const pathNodeSet = useMemo(() => new Set(pathIds ?? []), [pathIds]);
  const pathEdgeSet = useMemo(() => {
    if (!pathIds || pathIds.length < 2) return new Set<string>();
    const s = new Set<string>();
    for (let i = 0; i < pathIds.length - 1; i++) {
      const a = pathIds[i], b = pathIds[i + 1];
      data.edges.forEach((e) => {
        if ((e.source === a && e.target === b) || (e.source === b && e.target === a)) {
          s.add(e.id);
        }
      });
    }
    return s;
  }, [pathIds, data.edges]);

  const pathSourceLabel = data.nodes.find((n) => n.id === pathSource)?.label;
  const pathTargetLabel = data.nodes.find((n) => n.id === pathTarget)?.label;

  const clearPath = () => {
    setPathSource(null);
    setPathTarget(null);
  };

  // Handle a click made while in path mode — intercept before parent's
  // onNodeSelect so selecting source/target doesn't open the detail panel.
  const handlePathPick = useCallback(
    (nodeId: string) => {
      if (!pathSource) {
        setPathSource(nodeId);
        setPathTarget(null);
      } else if (!pathTarget) {
        setPathTarget(nodeId);
      } else {
        // Start over from this node
        setPathSource(nodeId);
        setPathTarget(null);
      }
    },
    [pathSource, pathTarget],
  );

  // Mini-map — compute bounds of the current node layout so we can scale
  // every node into a 180×120 overview rect. Re-computes when nodes move
  // (drag, new data).
  const miniW = 180;
  const miniH = 120;
  const miniPad = 6;

  const bounds = useMemo(() => {
    if (!nodes.length) return { minX: 0, minY: 0, maxX: 1, maxY: 1 };
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      if (n.x < minX) minX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.x > maxX) maxX = n.x;
      if (n.y > maxY) maxY = n.y;
    }
    return { minX, minY, maxX, maxY };
  }, [nodes]);

  const projectMini = useCallback(
    (x: number, y: number) => {
      const bw = Math.max(1, bounds.maxX - bounds.minX);
      const bh = Math.max(1, bounds.maxY - bounds.minY);
      const scale = Math.min(
        (miniW - miniPad * 2) / bw,
        (miniH - miniPad * 2) / bh,
      );
      return {
        x: miniPad + (x - bounds.minX) * scale,
        y: miniPad + (y - bounds.minY) * scale,
        scale,
      };
    },
    [bounds],
  );

  const handleMiniClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const bw = Math.max(1, bounds.maxX - bounds.minX);
      const bh = Math.max(1, bounds.maxY - bounds.minY);
      const scale = Math.min(
        (miniW - miniPad * 2) / bw,
        (miniH - miniPad * 2) / bh,
      );
      // Reverse: mini-space → world coordinates
      const worldX = bounds.minX + (mx - miniPad) / scale;
      const worldY = bounds.minY + (my - miniPad) / scale;
      // Center the main viewport on that world point given current zoom.
      const w = svgRef.current?.clientWidth || 800;
      const h = svgRef.current?.clientHeight || 560;
      setTransform((t) => ({
        ...t,
        x: w / 2 - worldX * t.k,
        y: h / 2 - worldY * t.k,
      }));
    },
    [bounds],
  );

  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const connectedTo = useMemo(() => {
    const active = hoveredNode || selectedNodeId;
    if (!active) return new Set<string>();
    const s = new Set<string>();
    data.edges.forEach((e) => {
      if (e.source === active) s.add(e.target);
      if (e.target === active) s.add(e.source);
    });
    return s;
  }, [hoveredNode, selectedNodeId, data.edges]);

  // Degree = how many edges touch each node. Drives node radius so the most
  // connected entities visually dominate — a core "at-a-glance centrality"
  // cue every graph viewer should have.
  const degreeMap = useMemo(() => {
    const m = new Map<string, number>();
    data.edges.forEach((e) => {
      m.set(e.source, (m.get(e.source) ?? 0) + 1);
      m.set(e.target, (m.get(e.target) ?? 0) + 1);
    });
    return m;
  }, [data.edges]);

  const maxDegree = useMemo(() => {
    let mx = 1;
    degreeMap.forEach((v) => { if (v > mx) mx = v; });
    return mx;
  }, [degreeMap]);

  // Search filter — dims everything not matching OR connected to a match.
  // Empty query = no filter. Matches are substring, case-insensitive against
  // the node label + id (so a CVE number or partial IP still finds things).
  const filterMatch = useMemo(() => {
    const q = filterQuery.trim().toLowerCase();
    if (!q) return null;
    const direct = new Set<string>();
    data.nodes.forEach((n) => {
      const hay = `${n.label} ${n.id}`.toLowerCase();
      if (hay.includes(q)) direct.add(n.id);
    });
    // Expand to one-hop neighbours so context is preserved — a matched
    // IOC alone with no edges would be lonely.
    const neighbours = new Set<string>(direct);
    data.edges.forEach((e) => {
      if (direct.has(e.source)) neighbours.add(e.target);
      if (direct.has(e.target)) neighbours.add(e.source);
    });
    return { direct, neighbours };
  }, [filterQuery, data.nodes, data.edges]);

  const activeNode = hoveredNode || selectedNodeId;

  const svgW = isFullscreen ? "100vw" : width;
  const svgH = isFullscreen ? "calc(100vh - 60px)" : height;

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative select-none overflow-hidden",
        isFullscreen && "fixed inset-0 z-50 bg-[#0a0e1a]",
        className,
      )}
    >
      {/* SVG defs for glow effects & gradients */}
      <svg width={0} height={0} className="absolute">
        <defs>
          <filter id="glow-blue" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="node-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000" floodOpacity="0.5" />
          </filter>
          {Object.entries(NODE_COLORS).map(([type, c]) => (
            <React.Fragment key={type}>
              {/* Solid fill at the edge (was 0.8 → ghosted on dark bg). */}
              <radialGradient id={`grad-${type}`} cx="35%" cy="35%">
                <stop offset="0%" stopColor={c.glow} stopOpacity="1" />
                <stop offset="70%" stopColor={c.fill} stopOpacity="1" />
                <stop offset="100%" stopColor={c.fill} stopOpacity="1" />
              </radialGradient>
              <radialGradient id={`grad-${type}-active`} cx="35%" cy="35%">
                <stop offset="0%" stopColor="#ffffff" stopOpacity="0.55" />
                <stop offset="40%" stopColor={c.glow} stopOpacity="1" />
                <stop offset="100%" stopColor={c.fill} stopOpacity="1" />
              </radialGradient>
              {/* Hero gradient — reserved for the center node. White hot core,
                  big bright mid, saturated edge; drives the visual anchor. */}
              <radialGradient id={`grad-${type}-hero`} cx="38%" cy="38%">
                <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
                <stop offset="25%" stopColor="#ffffff" stopOpacity="0.4" />
                <stop offset="55%" stopColor={c.glow} stopOpacity="1" />
                <stop offset="100%" stopColor={c.fill} stopOpacity="1" />
              </radialGradient>
            </React.Fragment>
          ))}
          <radialGradient id="center-ambient">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          {/* Vignette — transparent well past the node zone so nothing
           * in the graph gets tinted; only the outer corners darken. */}
          <radialGradient id="vignette" cx="50%" cy="50%" r="85%">
            <stop offset="65%" stopColor="#000" stopOpacity="0" />
            <stop offset="100%" stopColor="#000" stopOpacity="0.35" />
          </radialGradient>
        </defs>
      </svg>

      {/* Top-left: single glass bar — legend + filter + counts. One row of
          chrome reads more cleanly than two stacked pills, and drops the
          right-side counts badge for a tighter right-edge. */}
      <div className="absolute top-3 left-3 z-20 bg-[#0f172a]/85 backdrop-blur-md border border-white/[0.06] rounded-xl px-3 py-1.5 text-[11px] flex items-center gap-3 shadow-lg shadow-black/20">
        {Object.entries(NODE_COLORS).map(([type, c]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{ background: c.fill, boxShadow: `0 0 8px ${c.glow}` }}
            />
            <span className="capitalize text-slate-400">{type}</span>
          </div>
        ))}
        <span className="h-3.5 w-px bg-white/10" />
        <div className="flex items-center gap-1.5">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" className="shrink-0">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
          </svg>
          <input
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Filter…"
            className="bg-transparent outline-none border-none text-[11px] text-slate-200 placeholder:text-slate-500 w-32"
          />
          {filterQuery && (
            <button
              onClick={() => setFilterQuery("")}
              className="p-0.5 rounded hover:bg-slate-700/50 text-slate-500 hover:text-slate-300"
              title="Clear filter"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
          {filterMatch && (
            <span className="text-[9px] text-amber-300 tabular-nums">
              {filterMatch.direct.size}
            </span>
          )}
        </div>
        <span className="h-3.5 w-px bg-white/10" />
        <span className="text-slate-500 tabular-nums">
          {data.total_nodes}n · {data.total_edges}e
        </span>
      </div>

      {/* Top-right: Controls */}
      <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5">
        {[
          { label: "+", action: zoomIn, title: "Zoom in" },
          { label: "−", action: zoomOut, title: "Zoom out" },
        ].map((btn) => (
          <button
            key={btn.title}
            onClick={btn.action}
            className="w-8 h-8 rounded-lg bg-[#0f172a]/90 border border-[#1e293b] text-slate-300 hover:text-white hover:border-blue-500/50 flex items-center justify-center transition-all text-sm"
            title={btn.title}
          >
            {btn.label}
          </button>
        ))}
        <button
          onClick={resetView}
          className="w-8 h-8 rounded-lg bg-[#0f172a]/90 border border-[#1e293b] text-slate-300 hover:text-white hover:border-blue-500/50 flex items-center justify-center transition-all"
          title="Reset view"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
          </svg>
        </button>
        {/* Path-explorer toggle */}
        <button
          onClick={() => {
            setPathMode((m) => {
              if (m) clearPath();
              return !m;
            });
          }}
          className={cn(
            "w-8 h-8 rounded-lg border flex items-center justify-center transition-all",
            pathMode
              ? "bg-amber-500/20 border-amber-400/60 text-amber-300"
              : "bg-[#0f172a]/90 border-[#1e293b] text-slate-300 hover:text-white hover:border-amber-400/50",
          )}
          title={pathMode ? "Exit path mode" : "Find shortest path — click two nodes"}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="6" cy="19" r="3" /><circle cx="18" cy="5" r="3" />
            <path d="M9 19h2a4 4 0 0 0 4-4V8a3 3 0 0 1 3-3" />
          </svg>
        </button>

        {/* Export menu */}
        <div className="relative">
          <button
            onClick={() => setShowExportMenu((v) => !v)}
            className="w-8 h-8 rounded-lg bg-[#0f172a]/90 border border-[#1e293b] text-slate-300 hover:text-white hover:border-blue-500/50 flex items-center justify-center transition-all"
            title="Export graph"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </button>
          {showExportMenu && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setShowExportMenu(false)} />
              <div className="absolute right-0 top-full mt-1 w-36 z-40 rounded-lg bg-[#0f172a]/95 backdrop-blur-sm border border-[#1e293b] shadow-xl overflow-hidden">
                <button
                  onClick={() => { setShowExportMenu(false); exportPNG(); }}
                  className="w-full text-left px-3 py-2 text-[11px] text-slate-300 hover:bg-slate-800/60 hover:text-white flex items-center gap-2"
                >
                  <span className="text-emerald-400 font-mono text-[10px]">PNG</span>
                  <span>Rasterised · 2×</span>
                </button>
                <button
                  onClick={() => { setShowExportMenu(false); exportSVG(); }}
                  className="w-full text-left px-3 py-2 text-[11px] text-slate-300 hover:bg-slate-800/60 hover:text-white flex items-center gap-2 border-t border-[#1e293b]"
                >
                  <span className="text-sky-400 font-mono text-[10px]">SVG</span>
                  <span>Vector · editable</span>
                </button>
              </div>
            </>
          )}
        </div>
        <button
          onClick={toggleFullscreen}
          className="w-8 h-8 rounded-lg bg-[#0f172a]/90 border border-[#1e293b] text-slate-300 hover:text-white hover:border-blue-500/50 flex items-center justify-center transition-all"
          title={isFullscreen ? "Exit fullscreen (Esc)" : "Fullscreen"}
        >
          {isFullscreen ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
            </svg>
          )}
        </button>
      </div>

      {/* Zoom indicator */}
      {transform.k !== 1 && (
        <div className="absolute bottom-3 right-3 z-20 bg-[#0f172a]/80 backdrop-blur-sm border border-[#1e293b] rounded-lg px-2 py-1 text-[10px] text-slate-500">
          {Math.round(transform.k * 100)}%
        </div>
      )}

      {/* Path-explorer banner — shows state in path mode */}
      {pathMode && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 bg-amber-950/90 backdrop-blur-sm border border-amber-500/40 rounded-xl px-4 py-2 text-[11px] flex items-center gap-3 shadow-lg max-w-[520px]">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2" className="shrink-0">
            <circle cx="6" cy="19" r="3" /><circle cx="18" cy="5" r="3" />
            <path d="M9 19h2a4 4 0 0 0 4-4V8a3 3 0 0 1 3-3" />
          </svg>
          {!pathSource ? (
            <span className="text-amber-200">Click a node to set the path <strong>source</strong>…</span>
          ) : !pathTarget ? (
            <span className="text-amber-200 truncate">
              Source: <span className="text-amber-100 font-semibold">{pathSourceLabel || pathSource}</span> · click a second node for the <strong>target</strong>
            </span>
          ) : pathIds ? (
            <span className="text-amber-100 truncate">
              <span className="text-amber-400 font-semibold">{pathIds.length - 1} hops</span>{" "}
              · <span className="font-semibold">{pathSourceLabel}</span> → <span className="font-semibold">{pathTargetLabel}</span>
            </span>
          ) : (
            <span className="text-red-300">
              No path found between <span className="font-semibold">{pathSourceLabel}</span> and <span className="font-semibold">{pathTargetLabel}</span> in the loaded graph — try a deeper explore.
            </span>
          )}
          {(pathSource || pathTarget) && (
            <button
              onClick={clearPath}
              className="text-amber-300 hover:text-amber-100 text-[10px] underline underline-offset-2 shrink-0"
            >
              reset
            </button>
          )}
          <button
            onClick={() => { setPathMode(false); clearPath(); }}
            className="text-amber-300 hover:text-amber-100 shrink-0"
            title="Exit path mode"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Mini-map — bottom-left. Only shown for graphs big enough to
          warrant one; below the threshold the overview adds clutter more
          than it aids navigation. Click to pan the main view. */}
      {nodes.length > 20 && (
        <div className="absolute bottom-3 left-3 z-20 bg-[#0f172a]/90 backdrop-blur-sm border border-[#1e293b] rounded-lg overflow-hidden shadow-lg">
          <svg
            width={miniW}
            height={miniH}
            className="cursor-crosshair"
            onClick={handleMiniClick}
          >
            <rect width="100%" height="100%" fill="#0a0e1a" />
            {/* Edges — tiny grey lines, no detail */}
            {data.edges.map((edge) => {
              const s = nodeMap.get(edge.source);
              const t = nodeMap.get(edge.target);
              if (!s || !t) return null;
              const p1 = projectMini(s.x, s.y);
              const p2 = projectMini(t.x, t.y);
              return (
                <line
                  key={edge.id}
                  x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                  stroke="#334155" strokeWidth={0.4} opacity={0.6}
                />
              );
            })}
            {/* Nodes — colored dots */}
            {nodes.map((n) => {
              const p = projectMini(n.x, n.y);
              const c = NODE_COLORS[n.type]?.fill || "#475569";
              return (
                <circle
                  key={n.id}
                  cx={p.x} cy={p.y}
                  r={n.isCenter ? 2.2 : 1.4}
                  fill={c}
                  fillOpacity={0.9}
                />
              );
            })}
            {/* Viewport rect — shows where the main view is looking */}
            {(() => {
              const w = svgRef.current?.clientWidth || 800;
              const h = svgRef.current?.clientHeight || 560;
              const worldTopLeft = projectMini(
                -transform.x / transform.k,
                -transform.y / transform.k,
              );
              const worldBotRight = projectMini(
                (-transform.x + w) / transform.k,
                (-transform.y + h) / transform.k,
              );
              const vx = Math.max(miniPad, Math.min(miniW - miniPad, worldTopLeft.x));
              const vy = Math.max(miniPad, Math.min(miniH - miniPad, worldTopLeft.y));
              const vw = Math.max(4, Math.min(miniW - vx - miniPad, worldBotRight.x - worldTopLeft.x));
              const vh = Math.max(4, Math.min(miniH - vy - miniPad, worldBotRight.y - worldTopLeft.y));
              return (
                <rect
                  x={vx} y={vy} width={vw} height={vh}
                  fill="none" stroke="#38bdf8" strokeWidth={1}
                  strokeDasharray="3 2"
                  pointerEvents="none"
                />
              );
            })()}
          </svg>
          <div className="px-2 py-0.5 text-[9px] text-slate-500 text-center border-t border-[#1e293b]">
            overview · click to pan
          </div>
        </div>
      )}

      {/* Main SVG */}
      <svg
        ref={svgRef}
        width={svgW}
        height={svgH}
        className="rounded-xl"
        style={{ background: "linear-gradient(135deg, #0a0e1a 0%, #0f172a 50%, #0a101f 100%)" }}
        onMouseDown={handleBgMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        {/* Tight ambient focus at the very center — just enough to
            seat the hero node in a soft light without bleeding into
            the satellite ring. */}
        <circle cx="50%" cy="50%" r="180" fill="url(#center-ambient)" opacity={0.22} />
        <rect width="100%" height="100%" fill="url(#vignette)" pointerEvents="none" />

        <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
          {/* Edges */}
          {data.edges.map((edge) => {
            const s = nodeMap.get(edge.source);
            const t = nodeMap.get(edge.target);
            if (!s || !t) return null;
            const isActive =
              hoveredEdge === edge.id ||
              activeNode === edge.source ||
              activeNode === edge.target;
            const isSelected =
              selectedNodeId === edge.source || selectedNodeId === edge.target;
            const color = EDGE_COLORS[edge.type] || "#475569";
            // An edge is part of the filter scope if either endpoint is a
            // direct match or a one-hop neighbour of a match.
            const filterKept =
              !filterMatch ||
              (filterMatch.neighbours.has(edge.source) &&
                filterMatch.neighbours.has(edge.target));
            const dimmed = (activeNode && !isActive) || !filterKept;

            // Curved-edge geometry. Bow direction is consistent so parallel
            // edges (e.g. two intel items sharing a hub) don't overprint.
            const geom = edgeGeometry(s.x, s.y, t.x, t.y);

            // Animated particle — walks the bezier, not a straight line.
            const particleT = ((animTick * 3 + parseInt(edge.id.slice(-4), 16)) % 200) / 200;
            const pp = bezierAt(s.x, s.y, geom.cx, geom.cy, t.x, t.y, particleT);

            const isPath = pathEdgeSet.has(edge.id);

            return (
              <g key={edge.id}>
                {/* Path highlight — golden glow under the normal edge */}
                {isPath && (
                  <path
                    d={geom.path}
                    fill="none"
                    stroke="#fbbf24"
                    strokeWidth={6}
                    strokeOpacity={0.35}
                    filter="url(#glow-strong)"
                    className="pointer-events-none"
                  />
                )}
                {(isActive || isSelected) && (
                  <path
                    d={geom.path}
                    fill="none"
                    stroke={color}
                    strokeWidth={4}
                    strokeOpacity={0.25}
                    filter="url(#glow-blue)"
                    className="pointer-events-none"
                  />
                )}
                <path
                  d={geom.path}
                  fill="none"
                  stroke={color}
                  strokeWidth={isActive ? 2.2 : 1.3}
                  strokeOpacity={dimmed ? 0.05 : isActive ? 0.9 : 0.45}
                  strokeDasharray={edge.type.includes("co") ? "4 4" : "none"}
                  strokeLinecap="round"
                  onMouseEnter={() => setHoveredEdge(edge.id)}
                  onMouseLeave={() => setHoveredEdge(null)}
                  className="cursor-pointer"
                />
                {isActive && (
                  <circle
                    cx={pp.x} cy={pp.y} r={2.5}
                    fill={color}
                    opacity={0.9}
                    filter="url(#glow-blue)"
                    className="pointer-events-none"
                  />
                )}
                {isActive && hoveredEdge === edge.id && (() => {
                  const mx = geom.curveMidX;
                  const my = geom.curveMidY;
                  const evidence = extractEvidence(edge);
                  const lineCount = evidence.length;
                  const cardW = 220;
                  const cardH = 30 + Math.max(0, lineCount) * 14;
                  return (
                    <foreignObject
                      x={mx - cardW / 2}
                      y={my - cardH - 8}
                      width={cardW}
                      height={cardH}
                      className="pointer-events-none"
                    >
                      <div
                        style={{
                          background: "rgba(15,23,42,0.95)",
                          border: `1px solid ${color}99`,
                          boxShadow: `0 4px 12px ${color}40`,
                          borderRadius: 6,
                          padding: "5px 8px",
                          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                          fontSize: 10,
                          color: "#e2e8f0",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: evidence.length ? 3 : 0 }}>
                          <span style={{ color, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            {edge.type.replace(/[_-]/g, " ")}
                          </span>
                          <span style={{ color: "#94a3b8", fontSize: 9 }}>
                            {edge.confidence}%
                          </span>
                        </div>
                        {evidence.map((e, i) => (
                          <div key={i} style={{ color: "#cbd5e1", lineHeight: 1.35, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            <span style={{ color: "#64748b" }}>{e.label}</span>{" "}
                            <span style={{ color: "#e2e8f0" }}>{e.value}</span>
                          </div>
                        ))}
                      </div>
                    </foreignObject>
                  );
                })()}
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const colorSet = NODE_COLORS[node.type] || { fill: "#475569", glow: "#64748b", icon: "?" };
            const ring = node.severity ? SEVERITY_RING[node.severity] : undefined;
            // Base radius by role/type, then boost by (degree / maxDegree).
            // Clamp so a single super-connected node can't fill the canvas
            // and low-degree satellites still stay readable.
            const deg = degreeMap.get(node.id) ?? 0;
            const degBoost = maxDegree > 1 ? (deg / maxDegree) * 12 : 0;
            // Centre is visibly the anchor — ~1.7× a satellite — but not
            // so large that its halo swallows the inner ring. Calibrated
            // against firstRing=0.36 × minDim so there's clear separation.
            const baseR = node.isCenter ? 38 : node.type === "intel" ? 20 : 17;
            const r = Math.min(node.isCenter ? 54 : 32, baseR + degBoost);
            const isHovered = hoveredNode === node.id;
            const isSelected = selectedNodeId === node.id;
            const isHighlighted = isHovered || isSelected;
            const isConnected = connectedTo.has(node.id);
            const filterKept = !filterMatch || filterMatch.neighbours.has(node.id);
            const isFilterMatch = filterMatch?.direct.has(node.id) ?? false;
            const dimmed =
              (activeNode !== null && !isHighlighted && !isConnected && node.id !== activeNode) ||
              !filterKept;

            return (
              <g
                key={node.id}
                transform={`translate(${node.x},${node.y})`}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onMouseDown={handleMouseDown(node.id)}
                onClick={(e) => {
                  e.stopPropagation();
                  if (pathMode) {
                    handlePathPick(node.id);
                    return;
                  }
                  onNodeSelect?.(node);
                }}
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  onNodeClick?.(node);
                }}
                className="cursor-pointer"
                opacity={dimmed ? 0.12 : 1}
                style={{ transition: "opacity 0.3s ease" }}
              >
                {/* Centre gets concentric "target" rings so it reads
                    unambiguously as the investigation subject. Sized
                    tight to the node so they frame it instead of
                    bleeding into the satellite ring. */}
                {node.isCenter && (
                  <>
                    <circle
                      r={r + 22}
                      fill="none"
                      stroke={colorSet.glow}
                      strokeWidth={0.8}
                      strokeOpacity={0.28}
                      strokeDasharray="3 6"
                      className="animate-pulse pointer-events-none"
                    />
                    <circle
                      r={r + 13}
                      fill="none"
                      stroke={colorSet.glow}
                      strokeWidth={1.2}
                      strokeOpacity={0.5}
                      className="pointer-events-none"
                    />
                  </>
                )}
                {/* Non-center selection pulse */}
                {!node.isCenter && isSelected && (
                  <circle
                    r={r + 12}
                    fill="none"
                    stroke={colorSet.glow}
                    strokeWidth={1}
                    strokeOpacity={0.5}
                    className="animate-pulse"
                  />
                )}
                {/* Ambient glow — generous defaults so nodes feel alive at
                    rest. Centre halo is tight so it doesn't bleed. */}
                <circle
                  r={r + (node.isCenter ? 9 : 8)}
                  fill={colorSet.glow}
                  fillOpacity={isHighlighted ? 0.35 : node.isCenter ? 0.24 : 0.18}
                  className="pointer-events-none"
                />
                {/* Search-match halo — only when a filter query is active */}
                {isFilterMatch && (
                  <circle
                    r={r + 10}
                    fill="none"
                    stroke="#fde047"
                    strokeWidth={1.5}
                    strokeOpacity={0.9}
                    strokeDasharray="4 2"
                    className="animate-pulse pointer-events-none"
                  />
                )}
                {/* Path highlight — endpoints get a bright amber ring, intermediates a muted one */}
                {pathNodeSet.has(node.id) && (
                  <circle
                    r={r + 8}
                    fill="none"
                    stroke={node.id === pathSource || node.id === pathTarget ? "#f59e0b" : "#fbbf24"}
                    strokeWidth={node.id === pathSource || node.id === pathTarget ? 2.5 : 1.5}
                    strokeOpacity={0.95}
                    filter="url(#glow-strong)"
                    className="pointer-events-none"
                  />
                )}
                {/* Severity ring */}
                {ring && (
                  <circle
                    r={r + 3}
                    fill="none"
                    stroke={ring}
                    strokeWidth={2}
                    strokeOpacity={0.7}
                    strokeDasharray={node.severity === "critical" ? "none" : "3 2"}
                  />
                )}
                {/* 3D gradient node — center uses the dedicated "hero"
                    gradient (white-hot core) so it reads instantly as the
                    focal point; hovered/selected satellites get "active". */}
                <circle
                  r={r}
                  fill={`url(#grad-${node.type}${node.isCenter ? "-hero" : isHighlighted ? "-active" : ""})`}
                  stroke={node.isCenter ? "#ffffff" : isHighlighted ? "#ffffff" : colorSet.glow}
                  strokeWidth={node.isCenter ? 2.2 : isHighlighted ? 2 : 0.8}
                  strokeOpacity={node.isCenter ? 0.85 : isHighlighted ? 0.9 : 0.55}
                  filter="url(#node-shadow)"
                />
                {/* Specular highlight */}
                <ellipse
                  cx={-r * 0.2}
                  cy={-r * 0.25}
                  rx={r * 0.45}
                  ry={r * 0.3}
                  fill="white"
                  fillOpacity={0.12}
                  className="pointer-events-none"
                />
                {/* Type icon */}
                <text
                  y={1}
                  fontSize={r * 0.65}
                  fill="#fff"
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="pointer-events-none"
                  fontWeight="700"
                  style={{ textShadow: `0 0 8px ${colorSet.glow}` }}
                >
                  {colorSet.icon}
                </text>
                {/* Label — paint-order:stroke draws the dark stroke first,
                    creating a crisp backdrop so the label reads over edges
                    or node-glow without needing a separate rect behind it. */}
                <text
                  y={r + (node.isCenter ? 20 : 17)}
                  fontSize={node.isCenter ? 13.5 : 11}
                  fill={node.isCenter ? "#ffffff" : isHighlighted ? "#f8fafc" : "#e2e8f0"}
                  fontWeight={node.isCenter ? 700 : 500}
                  stroke="#050810"
                  strokeWidth={node.isCenter ? 5 : 4}
                  strokeLinejoin="round"
                  textAnchor="middle"
                  className="pointer-events-none"
                  fontFamily="system-ui, sans-serif"
                  style={{ paintOrder: "stroke" }}
                >
                  {node.label.length > 32 ? node.label.slice(0, 30) + "…" : node.label}
                </text>
                {/* Risk score badge – only on hover / selected */}
                {isHighlighted && node.risk_score != null && node.risk_score > 0 && (
                  <g transform={`translate(${r - 1},${-r - 2})`}>
                    <rect
                      width={24}
                      height={14}
                      rx={7}
                      fill={
                        node.risk_score >= 80 ? "#dc2626" : node.risk_score >= 50 ? "#f97316" : "#475569"
                      }
                      stroke="#0f172a"
                      strokeWidth={1}
                    />
                    <text
                      x={12} y={8}
                      fontSize={8}
                      fill="#fff"
                      textAnchor="middle"
                      dominantBaseline="central"
                      className="pointer-events-none font-medium"
                    >
                      {node.risk_score}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>

    </div>
  );
}
