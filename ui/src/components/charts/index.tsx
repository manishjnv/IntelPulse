"use client";

/**
 * Dynamic-import chart facade.
 *
 * recharts + its d3-shaped deps add ~60-70 KB gzipped to whatever chunk
 * they land in. Every page that imports a chart previously inlined that
 * weight into its page bundle even if the user never scrolled to a chart.
 *
 * By wrapping the three charts in ``next/dynamic`` with ``ssr: false``
 * the recharts blob moves to a separate async chunk that is only
 * downloaded when a chart actually mounts in the viewport. LCP and TTI
 * improve on every page that uses any chart (dashboard, analytics, geo,
 * iocs, search, threats).
 *
 * The ``loading`` placeholder matches the chart footprint so the layout
 * does not jump when the async chunk resolves.
 */

import dynamic from "next/dynamic";
import React from "react";

const ChartSkeleton = ({ height = 160 }: { height?: number }) => (
  <div
    aria-hidden
    role="presentation"
    className="w-full rounded-md bg-muted/20 animate-pulse"
    style={{ height }}
  />
);

export const DonutChart = dynamic(
  () => import("./DonutChart").then((m) => m.DonutChart),
  {
    ssr: false,
    loading: () => <ChartSkeleton height={180} />,
  },
);

export const TrendLineChart = dynamic(
  () => import("./TrendLineChart").then((m) => m.TrendLineChart),
  {
    ssr: false,
    loading: () => <ChartSkeleton height={200} />,
  },
);

export const HorizontalBarChart = dynamic(
  () => import("./HorizontalBarChart").then((m) => m.HorizontalBarChart),
  {
    ssr: false,
    loading: () => <ChartSkeleton height={180} />,
  },
);
