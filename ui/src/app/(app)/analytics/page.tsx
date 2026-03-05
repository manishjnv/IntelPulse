"use client";

import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useAppStore } from "@/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loading } from "@/components/Loading";
import { StatCard } from "@/components/StatCard";
import { DonutChart, HorizontalBarChart, TrendLineChart } from "@/components/charts";
import { RankedDataList } from "@/components/RankedDataList";
import {
  BarChart3,
  TrendingUp,
  Shield,
  AlertTriangle,
  Globe,
  Activity,
  Zap,
  Clock,
  Brain,
  Bug,
  Swords,
  Building2,
  ShieldAlert,
  Flame,
  Tag,
  Server,
  Skull,
  ChevronRight,
  Target,
} from "lucide-react";
import Link from "next/link";
import * as api from "@/lib/api";
import type { DashboardInsights, IntelStatsResponse } from "@/types";
import { cn } from "@/lib/utils";

const SEV_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
  info: "#3b82f6",
  unknown: "#6b7280",
};

const FEED_TYPE_COLORS: Record<string, string> = {
  vulnerability: "#ef4444",
  ioc: "#f97316",
  malware: "#a855f7",
  exploit: "#ec4899",
  advisory: "#3b82f6",
  threat_actor: "#14b8a6",
  campaign: "#8b5cf6",
};

const RISK_BG = (score: number) =>
  score >= 80 ? "bg-red-500/15 text-red-400" :
  score >= 60 ? "bg-orange-500/15 text-orange-400" :
  score >= 40 ? "bg-yellow-500/15 text-yellow-400" :
  "bg-green-500/15 text-green-400";

export default function AnalyticsPage() {
  const { dashboard, dashboardLoading, fetchDashboard } = useAppStore();
  const [insights, setInsights] = useState<DashboardInsights | null>(null);
  const [stats, setStats] = useState<IntelStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchDashboard(),
        api.getDashboardInsights().then(setInsights).catch(() => {}),
        api.getIntelStats().then(setStats).catch(() => {}),
      ]);
    } finally {
      setLoading(false);
    }
  }, [fetchDashboard]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Severity distribution from stats (accurate DB counts)
  const sevHBar = useMemo(() => {
    if (!stats) {
      if (!dashboard) return [];
      const grouped: Record<string, number> = {};
      dashboard.severity_distribution.forEach((d) => {
        grouped[d.severity] = (grouped[d.severity] || 0) + d.count;
      });
      return Object.entries(grouped)
        .sort((a, b) => b[1] - a[1])
        .map(([sev, count]) => ({ name: sev.charAt(0).toUpperCase() + sev.slice(1), value: count, color: SEV_COLORS[sev] || SEV_COLORS.unknown }));
    }
    return [
      { name: "Critical", value: stats.critical, color: SEV_COLORS.critical },
      { name: "High", value: stats.high, color: SEV_COLORS.high },
      { name: "Medium", value: stats.medium, color: SEV_COLORS.medium },
      { name: "Low", value: stats.low, color: SEV_COLORS.low },
      { name: "Info", value: stats.info, color: SEV_COLORS.info },
    ].filter((s) => s.value > 0).sort((a, b) => b.value - a.value);
  }, [stats, dashboard]);

  // Feed type counts from stats (accurate)
  const feedTypeDonut = useMemo(() => {
    if (!stats?.feed_type_counts) {
      if (!dashboard) return [];
      const grouped: Record<string, number> = {};
      dashboard.severity_distribution.forEach((d) => {
        grouped[d.feed_type] = (grouped[d.feed_type] || 0) + d.count;
      });
      const colors = ["#ef4444", "#f97316", "#a855f7", "#3b82f6", "#22c55e", "#ec4899", "#14b8a6"];
      return Object.entries(grouped).sort((a, b) => b[1] - a[1]).map(([ft, count], i) => ({
        name: ft.charAt(0).toUpperCase() + ft.slice(1).replace(/_/g, " "), value: count, color: colors[i % colors.length],
      }));
    }
    return Object.entries(stats.feed_type_counts)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([ft, count]) => ({
        name: ft.charAt(0).toUpperCase() + ft.slice(1).replace(/_/g, " "),
        value: count,
        color: FEED_TYPE_COLORS[ft] || "#6b7280",
      }));
  }, [stats, dashboard]);

  // Ingestion trend for line chart
  const trendData = useMemo(() => {
    if (!insights?.ingestion_trend) return [];
    return insights.ingestion_trend.map((p) => ({
      date: new Date(p.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      items: p.count,
    }));
  }, [insights]);

  // Asset type breakdown
  const assetTypeData = useMemo(() => {
    if (!stats?.asset_type_counts) return [];
    const colors = ["#3b82f6", "#ef4444", "#22c55e", "#f97316", "#a855f7", "#ec4899", "#14b8a6", "#eab308"];
    return Object.entries(stats.asset_type_counts)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([name, value], i) => ({
        name: name.replace(/_/g, " "),
        value,
        color: colors[i % colors.length],
      }));
  }, [stats]);

  // Top sources from stats
  const topSourcesData = useMemo(() => {
    if (!stats?.top_sources) return [];
    return stats.top_sources.slice(0, 10).map((s) => ({
      name: s.name,
      value: s.count,
      color: "#22c55e",
    }));
  }, [stats]);

  // Top tags as ranked list
  const topTagsList = useMemo(() => {
    if (!stats?.top_tags) return [];
    const colors = ["#3b82f6", "#ef4444", "#22c55e", "#f97316", "#a855f7", "#ec4899", "#14b8a6", "#eab308"];
    return stats.top_tags.slice(0, 12).map((tag, i) => ({
      label: tag,
      value: 0,
      color: colors[i % colors.length],
    }));
  }, [stats]);

  const totalItems = stats?.total ?? dashboard?.total_items ?? 0;

  if (loading && !dashboard && !stats) return <Loading text="Loading analytics..." />;

  return (
    <div className="p-4 lg:p-6 space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          Threat Analytics
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Deep analysis across all ingested intelligence
        </p>
      </div>

      {/* ═══════ STATS ROW 1  ═══════ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="Total Intel"
          value={totalItems.toLocaleString()}
          icon={<Shield className="h-5 w-5" />}
        />
        <StatCard
          title="Today"
          value={stats?.today ?? dashboard?.items_last_24h ?? 0}
          icon={<Clock className="h-5 w-5" />}
          variant="success"
        />
        <StatCard
          title="Critical"
          value={stats?.critical ?? 0}
          subtitle={totalItems > 0 ? `${((stats?.critical ?? 0) / totalItems * 100).toFixed(1)}% of total` : undefined}
          icon={<AlertTriangle className="h-5 w-5" />}
          variant="danger"
        />
        <StatCard
          title="High Severity"
          value={stats?.high ?? 0}
          subtitle={totalItems > 0 ? `${((stats?.high ?? 0) / totalItems * 100).toFixed(1)}% of total` : undefined}
          icon={<TrendingUp className="h-5 w-5" />}
          variant="warning"
        />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="KEV Listed"
          value={stats?.kev_count ?? dashboard?.kev_count ?? 0}
          icon={<ShieldAlert className="h-5 w-5" />}
          variant="danger"
        />
        <StatCard
          title="Exploits"
          value={stats?.exploit_count ?? 0}
          icon={<Flame className="h-5 w-5" />}
          variant="warning"
        />
        <StatCard
          title="AI Enriched"
          value={stats?.ai_enriched ?? 0}
          subtitle={totalItems > 0 ? `${((stats?.ai_enriched ?? 0) / totalItems * 100).toFixed(0)}% coverage` : undefined}
          icon={<Brain className="h-5 w-5" />}
          variant="success"
        />
        <StatCard
          title="Sources"
          value={stats?.sources ?? 0}
          icon={<Server className="h-5 w-5" />}
        />
      </div>

      {/* ═══════ INGESTION TREND ═══════ */}
      {trendData.length > 0 && (
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Ingestion Trend</CardTitle>
              <span className="text-[10px] text-muted-foreground ml-auto">Last 30 days</span>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <TrendLineChart
              data={trendData}
              series={[{ key: "items", label: "Intel Items", color: "#3b82f6" }]}
              xKey="date"
              height={220}
              showLegend={false}
            />
          </CardContent>
        </Card>
      )}

      {/* ═══════ EXPLOIT POSTURE ═══════ */}
      {insights?.exploit_summary && (
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Bug className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Exploit & Vulnerability Posture</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {[
                { label: "With Exploits", value: insights.exploit_summary.with_exploit, pct: insights.exploit_summary.exploit_pct, color: "text-red-400", bg: "bg-red-500/10" },
                { label: "KEV Listed", value: insights.exploit_summary.kev_count, pct: insights.exploit_summary.kev_pct, color: "text-orange-400", bg: "bg-orange-500/10" },
                { label: "Avg EPSS", value: (insights.exploit_summary.avg_epss * 100).toFixed(1) + "%", pct: null, color: "text-yellow-400", bg: "bg-yellow-500/10" },
                { label: "High EPSS (>0.7)", value: insights.exploit_summary.high_epss_count, pct: null, color: "text-pink-400", bg: "bg-pink-500/10" },
                { label: "Total Analyzed", value: insights.exploit_summary.total, pct: null, color: "text-blue-400", bg: "bg-blue-500/10" },
              ].map((m) => (
                <div key={m.label} className={cn("rounded-lg p-3 text-center", m.bg)}>
                  <p className={cn("text-xl font-bold tabular-nums", m.color)}>
                    {typeof m.value === "number" ? m.value.toLocaleString() : m.value}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{m.label}</p>
                  {m.pct !== null && (
                    <p className="text-[10px] font-medium text-muted-foreground/70 mt-0.5">{m.pct.toFixed(1)}%</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ═══════ SEVERITY + INTEL CATEGORIES ═══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle className="text-sm font-semibold">Severity Distribution</CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {sevHBar.length > 0 ? <HorizontalBarChart data={sevHBar} /> : <EmptyState />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle className="text-sm font-semibold">Intel Categories</CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {feedTypeDonut.length > 0 ? (
              <DonutChart
                data={feedTypeDonut}
                centerValue={totalItems.toLocaleString()}
                centerLabel="Total"
                height={200}
                innerRadius={55}
                outerRadius={78}
              />
            ) : (
              <EmptyState />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ═══════ TOP CVEs ═══════ */}
      {insights?.top_cves && insights.top_cves.length > 0 && (
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Bug className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Top CVEs</CardTitle>
              <span className="text-[10px] text-muted-foreground ml-auto">{insights.top_cves.length} tracked</span>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <div className="space-y-1.5">
              {insights.top_cves.slice(0, 10).map((cve, idx) => (
                <div key={cve.cve_id} className="flex items-center gap-3 p-2 rounded-lg border bg-card hover:bg-accent/30 transition-colors text-xs">
                  <span className="text-[10px] font-medium text-muted-foreground/50 w-4 text-right">{idx + 1}</span>
                  <span className={cn("flex items-center justify-center h-6 w-6 rounded text-[10px] font-bold shrink-0", RISK_BG(cve.max_risk))}>
                    {cve.max_risk}
                  </span>
                  <span className="font-mono font-semibold text-primary">{cve.cve_id}</span>
                  <div className="flex items-center gap-1.5 ml-auto">
                    {cve.is_kev && <Badge variant="destructive" className="text-[9px] px-1 py-0">KEV</Badge>}
                    {cve.has_exploit && <Badge className="text-[9px] px-1 py-0 bg-pink-600">Exploit</Badge>}
                    <span className="text-muted-foreground tabular-nums">{cve.count} refs</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ═══════ GEO + INDUSTRIES + ATTACK TECHNIQUES ═══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Threat Geography</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <RankedBarList items={insights?.threat_geography} colorClass="bg-cyan-500" emptyText="No geographic data" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Target Industries</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <RankedBarList items={insights?.target_industries} colorClass="bg-amber-500" capitalize emptyText="No industry data" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Attack Techniques</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <RankedBarList
              items={insights?.attack_techniques}
              colorClass="bg-rose-500"
              showRisk={false}
              capitalize
              formatName={(n) => n.replace(/_/g, " ")}
              emptyText="No technique data"
            />
          </CardContent>
        </Card>
      </div>

      {/* ═══════ THREAT ACTORS + RANSOMWARE + MALWARE ═══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Skull className="h-4 w-4 text-red-400" />
              <CardTitle className="text-sm font-semibold">Threat Actors</CardTitle>
              {insights?.threat_actors && (
                <span className="text-[10px] text-muted-foreground ml-auto">{insights.threat_actors.length} tracked</span>
              )}
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <RankedBarList items={insights?.threat_actors} colorClass="bg-red-500" emptyText="No threat actor data" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-violet-400" />
              <CardTitle className="text-sm font-semibold">Ransomware</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <RankedBarList items={insights?.ransomware} colorClass="bg-violet-500" emptyText="No ransomware data" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-purple-400" />
              <CardTitle className="text-sm font-semibold">Malware Families</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            <RankedBarList items={insights?.malware_families} colorClass="bg-purple-500" emptyText="No malware data" />
          </CardContent>
        </Card>
      </div>

      {/* ═══════ TOP SOURCES + TAGS + ASSET TYPES ═══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Top Sources</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {topSourcesData.length > 0 ? (
              <HorizontalBarChart data={topSourcesData} barColor="#22c55e" />
            ) : (
              <EmptyState text="No source data" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-semibold">Top Tags</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {topTagsList.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {topTagsList.map((t) => (
                  <Badge key={t.label} variant="outline" className="text-[10px] capitalize">
                    {t.label}
                  </Badge>
                ))}
              </div>
            ) : (
              <EmptyState text="No tag data" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle className="text-sm font-semibold">Asset Types</CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {assetTypeData.length > 0 ? (
              <HorizontalBarChart data={assetTypeData} />
            ) : (
              <EmptyState text="No asset type data" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ═══════ EXECUTIVE SUMMARIES ═══════ */}
      {insights?.executive_summaries && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {([
            { key: "threat_actor", label: "Threat Actors", icon: <Skull className="h-4 w-4" />, accent: "text-red-400", accentBg: "bg-red-500/10", borderColor: "border-red-500/30" },
            { key: "campaign", label: "Campaigns", icon: <Swords className="h-4 w-4" />, accent: "text-violet-400", accentBg: "bg-violet-500/10", borderColor: "border-violet-500/30" },
            { key: "exploit", label: "Exploits", icon: <Flame className="h-4 w-4" />, accent: "text-pink-400", accentBg: "bg-pink-500/10", borderColor: "border-pink-500/30" },
            { key: "advisory", label: "Advisories", icon: <ShieldAlert className="h-4 w-4" />, accent: "text-blue-400", accentBg: "bg-blue-500/10", borderColor: "border-blue-500/30" },
          ] as const).map(({ key, label, icon, accent, accentBg, borderColor }) => {
            const s = insights.executive_summaries?.[key];
            if (!s || s.total === 0) return null;
            return (
              <Card key={key} className={cn("border-l-2", borderColor)}>
                <CardHeader className="pb-2 pt-4 px-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={cn("flex items-center justify-center h-7 w-7 rounded-md", accent, accentBg)}>
                        {icon}
                      </span>
                      <div>
                        <CardTitle className="text-sm font-semibold">{label}</CardTitle>
                        <p className="text-[10px] text-muted-foreground mt-0.5">
                          {s.total} total · {s.recent_7d} new this week · Avg risk {s.avg_risk}
                        </p>
                      </div>
                    </div>
                    <Link
                      href={`/threats?feed_type=${key}`}
                      className={cn("text-xs hover:underline flex items-center gap-1", accent)}
                    >
                      View all <ChevronRight className="h-3 w-3" />
                    </Link>
                  </div>
                </CardHeader>
                <CardContent className="px-5 pb-4 space-y-3">
                  <div className="flex items-center gap-1.5">
                    {[
                      { label: "Critical", count: s.critical, color: "bg-red-500" },
                      { label: "High", count: s.high, color: "bg-orange-500" },
                      { label: "Medium", count: s.medium, color: "bg-yellow-500" },
                      { label: "Low", count: s.low, color: "bg-green-500" },
                    ].map((sev) =>
                      sev.count > 0 ? (
                        <span key={sev.label} className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium text-white", sev.color)}>
                          {sev.count} {sev.label}
                        </span>
                      ) : null
                    )}
                  </div>
                  <div className="space-y-1.5">
                    {s.top_items.slice(0, 3).map((item) => (
                      <Link
                        key={item.id}
                        href={`/intel/${item.id}`}
                        className="flex items-center gap-2.5 p-2 rounded-lg border bg-card hover:bg-accent/50 transition-colors group"
                      >
                        <span className={cn("flex items-center justify-center h-6 w-6 rounded text-[10px] font-bold shrink-0", RISK_BG(item.risk_score))}>
                          {item.risk_score}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium truncate group-hover:text-primary transition-colors">{item.title}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <Badge variant={item.severity as any} className="text-[9px] px-1 py-0">{item.severity.toUpperCase()}</Badge>
                            <span className="text-[10px] text-muted-foreground">{item.source}</span>
                            {item.cve_ids.length > 0 && <span className="text-[10px] font-mono text-primary">{item.cve_ids[0]}</span>}
                          </div>
                        </div>
                        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/30 group-hover:text-primary shrink-0" />
                      </Link>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ─── Inline helper components ──────────────────────────────── */

function EmptyState({ text = "No data available" }: { text?: string }) {
  return (
    <div className="h-[180px] flex items-center justify-center text-xs text-muted-foreground/60">
      {text}
    </div>
  );
}

function RankedBarList({
  items,
  colorClass,
  showRisk = true,
  capitalize: cap = false,
  emptyText = "No data",
  formatName,
}: {
  items: Array<{ name: string; count: number; avg_risk?: number }> | undefined;
  colorClass: string;
  showRisk?: boolean;
  capitalize?: boolean;
  emptyText?: string;
  formatName?: (name: string) => string;
}) {
  if (!items || items.length === 0) return <EmptyState text={emptyText} />;
  const maxCount = items[0]?.count ?? 1;
  return (
    <div className="space-y-1.5">
      {items.slice(0, 10).map((item, idx) => (
        <div key={item.name} className="group">
          <div className="flex items-center justify-between text-xs mb-0.5">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <span className="text-[10px] font-medium text-muted-foreground/50 w-4 text-right">{idx + 1}</span>
              <span className={cn("h-2 w-2 rounded-full shrink-0", colorClass)} />
              <span className={cn("text-muted-foreground truncate font-medium", cap && "capitalize")}>
                {formatName ? formatName(item.name) : item.name}
              </span>
            </div>
            <div className="flex items-center gap-2 ml-2">
              {showRisk && item.avg_risk !== undefined && (
                <span className={cn("text-[10px] font-mono px-1 rounded", RISK_BG(item.avg_risk))}>{item.avg_risk}</span>
              )}
              <span className="font-semibold tabular-nums">{item.count}</span>
            </div>
          </div>
          <div className="h-1 rounded-full bg-muted/50 overflow-hidden">
            <div className={cn("h-full rounded-full transition-all duration-500", colorClass)} style={{ width: `${(item.count / maxCount) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
