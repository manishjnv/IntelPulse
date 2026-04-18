"use client";

import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useAppStore } from "@/store";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/StatCard";
import { ThreatLevelBar } from "@/components/ThreatLevelBar";
import { FeedStatusPanel } from "@/components/FeedStatusPanel";
import { RankedDataList } from "@/components/RankedDataList";
import { SectionCard } from "@/components/SectionCard";
import {
  Skeleton,
  SkeletonStatCard,
  SkeletonRankedList,
  SkeletonDonut,
  SkeletonTableRow,
  SkeletonCardGrid,
} from "@/components/Skeleton";
import { InsightDetailModal, ViewAllModal } from "@/components/InsightDetailModal";
import { DonutChart, TrendLineChart } from "@/components/charts";
import { HowItWorks } from "@/components/HowItWorks";
import {
  Shield,
  AlertTriangle,
  TrendingUp,
  Clock,
  Loader2,
  Zap,
  Activity,
  Bell,
  FileText,
  Package,
  Skull,
  Bug,
  Lock,
  Globe,
  ChevronRight,
  ArrowRight,
  Eye,
  Swords,
  ShieldAlert,
  Flame,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import type { DashboardInsights } from "@/types";
import { cn, formatDate } from "@/lib/utils";
import {
  SEVERITY_HEX,
  feedTypeHex,
  riskBucketClasses,
  severityHex,
} from "@/lib/severity";

type ModalState =
  | { kind: "detail"; type: string; name: string }
  | { kind: "viewAll"; type: string; title: string }
  | null;

export default function DashboardPage() {
  const router = useRouter();
  const {
    dashboard,
    dashboardLoading,
    dashboardUpdatedAt,
    fetchDashboard,
    unreadCount,
    fetchUnreadCount,
    reportStats,
    fetchReportStats,
  } = useAppStore();
  const [insights, setInsights] = useState<DashboardInsights | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [productPeriod, setProductPeriod] = useState<string>("30d");
  const [modal, setModal] = useState<ModalState>(null);

  const openDetail = useCallback(
    (type: string, name: string) => setModal({ kind: "detail", type, name }),
    [],
  );
  const openViewAll = useCallback(
    (type: string, title: string) => setModal({ kind: "viewAll", type, title }),
    [],
  );
  const closeModal = useCallback(() => setModal(null), []);

  const fetchInsights = useCallback(async () => {
    setInsightsLoading(true);
    try {
      const data = await api.getDashboardInsights();
      setInsights(data);
    } catch (e) {
      console.error("Failed to fetch insights", e);
    } finally {
      setInsightsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchUnreadCount();
    fetchReportStats();
    fetchInsights();
    // Refresh the full card grid every 60s (dashboard + insights + reports).
    // Notifications tick faster at 30s for the bell badge.
    const dashInterval = setInterval(() => {
      fetchDashboard();
      fetchInsights();
      fetchReportStats();
    }, 60000);
    const notifInterval = setInterval(fetchUnreadCount, 30000);
    return () => {
      clearInterval(dashInterval);
      clearInterval(notifInterval);
    };
  }, [fetchDashboard, fetchUnreadCount, fetchReportStats, fetchInsights]);

  const sevDonut = useMemo(() => {
    if (!dashboard) return [];
    const grouped: Record<string, number> = {};
    dashboard.severity_distribution.forEach((d) => {
      grouped[d.severity] = (grouped[d.severity] || 0) + d.count;
    });
    return Object.entries(grouped).map(([severity, count]) => ({
      name: severity.charAt(0).toUpperCase() + severity.slice(1),
      value: count,
      color: severityHex(severity),
    }));
  }, [dashboard]);

  const feedTypeDonut = useMemo(() => {
    if (!dashboard) return [];
    const grouped: Record<string, number> = {};
    dashboard.severity_distribution.forEach((d) => {
      grouped[d.feed_type] = (grouped[d.feed_type] || 0) + d.count;
    });
    return Object.entries(grouped).map(([ft, count]) => ({
      name: ft.charAt(0).toUpperCase() + ft.slice(1).replace(/_/g, " "),
      value: count,
      color: feedTypeHex(ft),
    }));
  }, [dashboard]);

  const threatLevels = useMemo(() => {
    if (!dashboard) return [];
    const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    dashboard.severity_distribution.forEach((d) => {
      if (d.severity in counts) {
        counts[d.severity as keyof typeof counts] += d.count;
      }
    });
    return [
      { label: "High", value: counts.critical + counts.high, color: SEVERITY_HEX.critical },
      { label: "Medium", value: counts.medium, color: SEVERITY_HEX.medium },
      { label: "Low", value: counts.low + counts.info, color: SEVERITY_HEX.low },
    ];
  }, [dashboard]);

  const topSources = useMemo(() => {
    if (!dashboard?.top_risks) return [];
    const palette = Object.values(SEVERITY_HEX);
    const sourceMap: Record<string, number> = {};
    dashboard.top_risks.forEach((item) => {
      sourceMap[item.source_name] = (sourceMap[item.source_name] || 0) + 1;
    });
    return Object.entries(sourceMap)
      .sort((a, b) => b[1] - a[1])
      .map(([label, value], i) => ({
        label,
        value,
        color: palette[i % palette.length],
      }));
  }, [dashboard]);

  const topCVEs = insights?.top_cves ?? [];

  const topRiskItems = useMemo(() => {
    if (!dashboard?.top_risks) return [];
    return [...dashboard.top_risks]
      .sort((a, b) => b.risk_score - a.risk_score)
      .slice(0, 8);
  }, [dashboard]);

  const criticalCount = useMemo(() => {
    if (!dashboard?.severity_distribution) return 0;
    return dashboard.severity_distribution
      .filter((d) => d.severity === "critical")
      .reduce((acc, d) => acc + d.count, 0);
  }, [dashboard]);

  const totalItems = dashboard?.total_items ?? 0;
  const currentProducts = insights?.trending_products?.[productPeriod] ?? [];
  const updatedLabel = dashboardUpdatedAt
    ? formatDate(new Date(dashboardUpdatedAt).toISOString(), { relative: true })
    : null;

  return (
    <div className="p-4 lg:p-6 space-y-5">
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight">Threat Intelligence Dashboard</h1>
            {(dashboardLoading || insightsLoading) && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time overview{updatedLabel ? ` · Updated ${updatedLabel}` : ""}
          </p>
          {/* Hero briefing — single-line at-a-glance */}
          {dashboard && (
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
              <span className="text-muted-foreground">
                <span className="font-semibold text-foreground tabular-nums">
                  {(dashboard.items_last_24h ?? 0).toLocaleString()}
                </span>{" "}
                new · 24h
              </span>
              <span className="text-muted-foreground/40">·</span>
              <span className="text-red-400">
                <span className="font-semibold tabular-nums">{criticalCount.toLocaleString()}</span>{" "}
                critical
              </span>
              <span className="text-muted-foreground/40">·</span>
              <span className="text-orange-400">
                <span className="font-semibold tabular-nums">
                  {(dashboard.kev_count ?? 0).toLocaleString()}
                </span>{" "}
                KEV
              </span>
              <span className="text-muted-foreground/40">·</span>
              <span className="text-muted-foreground">
                Avg risk{" "}
                <span className="font-semibold text-foreground tabular-nums">
                  {Math.round(dashboard.avg_risk_score ?? 0)}
                </span>
              </span>
              {insights?.threat_actors?.[0] && (
                <>
                  <span className="text-muted-foreground/40">·</span>
                  <span className="text-muted-foreground">
                    Top actor{" "}
                    <span className="font-medium text-foreground capitalize">
                      {insights.threat_actors[0].name.replace(/_/g, " ")}
                    </span>
                  </span>
                </>
              )}
              {insights?.top_cves?.[0] && (
                <>
                  <span className="text-muted-foreground/40">·</span>
                  <span className="text-muted-foreground">
                    Top CVE{" "}
                    <span className="font-mono text-primary">{insights.top_cves[0].cve_id}</span>
                  </span>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <HowItWorks page="dashboard" />

      {/* KPI Stats Row — each stat is clickable */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {!dashboard ? (
          Array.from({ length: 6 }).map((_, i) => <SkeletonStatCard key={i} />)
        ) : (
          <>
        <StatCard
          title="Total Intel"
          value={totalItems}
          subtitle="All ingested items"
          icon={<Shield className="h-5 w-5" />}
          href="/threats"
        />
        <StatCard
          title="Last 24 Hours"
          value={dashboard?.items_last_24h ?? 0}
          subtitle="New items today"
          icon={<Clock className="h-5 w-5" />}
          variant="default"
          href="/threats"
        />
        <StatCard
          title="Avg Risk Score"
          value={Math.round(dashboard?.avg_risk_score ?? 0)}
          subtitle="Across all intel"
          icon={<TrendingUp className="h-5 w-5" />}
          variant={
            (dashboard?.avg_risk_score ?? 0) >= 60
              ? "danger"
              : (dashboard?.avg_risk_score ?? 0) >= 40
                ? "warning"
                : "success"
          }
          href="/threats"
        />
        <StatCard
          title="KEV Listed"
          value={dashboard?.kev_count ?? 0}
          subtitle="Known Exploited Vulns"
          icon={<AlertTriangle className="h-5 w-5" />}
          variant="danger"
          href="/threats?severity=critical"
        />
        <StatCard
          title="Reports"
          value={reportStats?.total_reports ?? 0}
          subtitle={`${reportStats?.by_status?.published ?? 0} published`}
          icon={<FileText className="h-5 w-5" />}
          href="/reports"
        />
        <StatCard
          title="Alerts"
          value={unreadCount}
          subtitle="Unread notifications"
          icon={<Bell className="h-5 w-5" />}
          variant={unreadCount > 0 ? "warning" : "success"}
          href="/notifications"
        />
          </>
        )}
      </div>

      {/* Threat Level Bar */}
      {!dashboard ? (
        <SectionCard title="Threat Level Distribution">
          <Skeleton className="h-10 rounded-lg" />
        </SectionCard>
      ) : (
        threatLevels.length > 0 && (
          <SectionCard title="Threat Level Distribution">
            <ThreatLevelBar levels={threatLevels} />
          </SectionCard>
        )
      )}

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Severity Breakdown">
          {!dashboard ? (
            <SkeletonDonut />
          ) : sevDonut.length > 0 ? (
            <DonutChart
              data={sevDonut}
              centerValue={totalItems}
              centerLabel="Total"
              height={180}
              innerRadius={50}
              outerRadius={72}
            />
          ) : (
            <EmptyState />
          )}
        </SectionCard>

        <SectionCard title="Intel by Category">
          {!dashboard ? (
            <SkeletonDonut />
          ) : feedTypeDonut.length > 0 ? (
            <DonutChart
              data={feedTypeDonut}
              centerValue={totalItems}
              centerLabel="Total"
              height={180}
              innerRadius={50}
              outerRadius={72}
            />
          ) : (
            <EmptyState />
          )}
        </SectionCard>
      </div>

      {/* Ingestion Trend (last 30 days) */}
      {!insights ? (
        <SectionCard
          title="Intel Ingestion Trend (30 Days)"
          icon={<Activity className="h-4 w-4" />}
          iconAccent="text-emerald-400"
        >
          <Skeleton className="h-[200px] w-full" />
        </SectionCard>
      ) : insights.ingestion_trend && insights.ingestion_trend.length > 0 && (
        <SectionCard
          title="Intel Ingestion Trend (30 Days)"
          icon={<Activity className="h-4 w-4" />}
          iconAccent="text-emerald-400"
          meta={
            insights.exploit_summary && (
              <div className="flex gap-3">
                <span>
                  <Zap className="h-3 w-3 inline text-red-400 mr-0.5" />
                  {insights.exploit_summary.exploit_pct}% exploitable
                </span>
                <span>
                  <AlertTriangle className="h-3 w-3 inline text-orange-400 mr-0.5" />
                  {insights.exploit_summary.kev_pct}% KEV
                </span>
                {insights.exploit_summary.avg_epss > 0 && (
                  <span>
                    Avg EPSS:{" "}
                    <span className="font-mono text-primary">
                      {insights.exploit_summary.avg_epss.toFixed(3)}
                    </span>
                  </span>
                )}
              </div>
            )
          }
        >
          <TrendLineChart
            data={insights.ingestion_trend.map((d) => ({
              date: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
              items: d.count,
            }))}
            series={[{ key: "items", label: "Intel Items", color: SEVERITY_HEX.low }]}
            xKey="date"
            height={200}
            showLegend={false}
          />
        </SectionCard>
      )}

      {/* Executive Summaries: Threat Actors, Campaigns, Exploits, Advisories */}
      {!insights ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <SectionCard key={i} title="" icon={<span />}>
              <SkeletonRankedList rows={4} />
            </SectionCard>
          ))}
        </div>
      ) : insights.executive_summaries && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {(
            [
              {
                key: "threat_actor",
                label: "Threat Actors",
                icon: <Skull className="h-4 w-4" />,
                accent: "text-red-400",
                accentBg: "bg-red-500/10",
                borderColor: "border-l-2 border-red-500/30",
              },
              {
                key: "campaign",
                label: "Campaigns",
                icon: <Swords className="h-4 w-4" />,
                accent: "text-violet-400",
                accentBg: "bg-violet-500/10",
                borderColor: "border-l-2 border-violet-500/30",
              },
              {
                key: "exploit",
                label: "Exploits",
                icon: <Flame className="h-4 w-4" />,
                accent: "text-pink-400",
                accentBg: "bg-pink-500/10",
                borderColor: "border-l-2 border-pink-500/30",
              },
              {
                key: "advisory",
                label: "Advisories",
                icon: <ShieldAlert className="h-4 w-4" />,
                accent: "text-blue-400",
                accentBg: "bg-blue-500/10",
                borderColor: "border-l-2 border-blue-500/30",
              },
            ] as const
          ).map(({ key, label, icon, accent, accentBg, borderColor }) => {
            const s = insights.executive_summaries?.[key];
            if (!s || s.total === 0) return null;
            return (
              <SectionCard
                key={key}
                title={label}
                icon={icon}
                iconAccent={accent}
                iconBg={accentBg}
                accentBorder={borderColor}
                meta={`${s.total} total · ${s.recent_7d} new this week · Avg risk ${s.avg_risk}`}
                action={
                  <Link
                    href={`/threats?feed_type=${key}`}
                    className={cn(
                      "text-xs hover:underline flex items-center gap-1",
                      accent,
                    )}
                  >
                    View all <ArrowRight className="h-3 w-3" />
                  </Link>
                }
                contentClassName="px-5 pb-4 space-y-3"
              >
                {/* Severity mini-bar */}
                <div className="flex items-center gap-1.5">
                  {[
                    { label: "Critical", count: s.critical, color: "bg-red-500" },
                    { label: "High", count: s.high, color: "bg-orange-500" },
                    { label: "Medium", count: s.medium, color: "bg-yellow-500" },
                    { label: "Low", count: s.low, color: "bg-green-500" },
                  ].map((sev) =>
                    sev.count > 0 ? (
                      <span
                        key={sev.label}
                        className={cn(
                          "text-[10px] px-1.5 py-0.5 rounded font-medium text-white",
                          sev.color,
                        )}
                      >
                        {sev.count} {sev.label}
                      </span>
                    ) : null,
                  )}
                </div>
                {/* Top items list */}
                <div className="space-y-1.5">
                  {s.top_items.map((item) => (
                    <Link
                      key={item.id}
                      href={`/intel/${item.id}`}
                      className="flex items-center gap-2.5 p-2 rounded-lg border bg-card hover:bg-accent/50 transition-colors group"
                    >
                      <span
                        className={cn(
                          "flex items-center justify-center h-7 w-7 rounded text-[11px] font-bold shrink-0",
                          riskBucketClasses(item.risk_score),
                        )}
                      >
                        {item.risk_score}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate group-hover:text-primary transition-colors">
                          {item.title}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Badge variant={item.severity as any} className="text-[9px] px-1 py-0">
                            {item.severity.toUpperCase()}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">{item.source}</span>
                          {item.cve_ids.length > 0 && (
                            <span className="text-[10px] font-mono text-primary">{item.cve_ids[0]}</span>
                          )}
                          {item.date && (
                            <span className="text-[10px] text-muted-foreground">
                              {new Date(item.date).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                              })}
                            </span>
                          )}
                        </div>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/30 group-hover:text-primary shrink-0" />
                    </Link>
                  ))}
                </div>
              </SectionCard>
            );
          })}
        </div>
      )}

      {/* THREAT LANDSCAPE INSIGHTS */}

      {/* Most Impacted Products */}
      <SectionCard
        title="Most Impacted Products"
        icon={<Package className="h-4 w-4" />}
        iconAccent="text-blue-400"
        action={
          <div className="flex gap-1">
            {(["7d", "30d", "90d", "1y"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setProductPeriod(p)}
                className={cn(
                  "px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors",
                  productPeriod === p
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted/50 text-muted-foreground hover:bg-muted",
                )}
              >
                {p === "1y" ? "1 Year" : p === "90d" ? "3 Months" : p === "30d" ? "30 Days" : "7 Days"}
              </button>
            ))}
          </div>
        }
      >
        {!insights ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-[52px] rounded-lg" />
            ))}
          </div>
        ) : currentProducts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2">
            {currentProducts.map((prod, i) => (
              <button
                key={prod.name}
                onClick={() => openDetail("product", prod.name)}
                className="flex items-center gap-3 p-2.5 rounded-lg border bg-card hover:bg-accent/50 transition-colors group text-left"
              >
                <span className="flex items-center justify-center h-7 w-7 rounded-md bg-blue-500/10 text-blue-400 text-xs font-bold shrink-0">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate group-hover:text-primary transition-colors">
                    {prod.name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-muted-foreground">{prod.count} hits</span>
                    <span className={cn("text-[10px] font-mono px-1 rounded", riskBucketClasses(prod.avg_risk))}>
                      {prod.avg_risk}
                    </span>
                    {prod.exploit && (
                      <span className="text-[10px] text-red-400">
                        <Bug className="h-2.5 w-2.5 inline" />
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState text="No affected product data for this period" />
        )}
      </SectionCard>

      {/* Threat Actors & Ransomware (side by side) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard
          title="Most Active Threat Actors"
          icon={<Skull className="h-4 w-4" />}
          iconAccent="text-red-400"
          action={
            <button
              onClick={() => openViewAll("threat_actor", "All Threat Actors")}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              View all <Eye className="h-3 w-3" />
            </button>
          }
        >
          {!insights ? (
            <SkeletonRankedList rows={4} />
          ) : insights.threat_actors && insights.threat_actors.length > 0 ? (
            <div className="space-y-2">
              {insights.threat_actors.map((ta) => (
                <InsightRow
                  key={ta.name}
                  name={ta.name}
                  count={ta.count}
                  avgRisk={ta.avg_risk}
                  icon={<Skull className="h-3.5 w-3.5" />}
                  accentClass="text-red-400 bg-red-500/10"
                  badges={[
                    ...ta.cves.slice(0, 3).map((c) => ({ label: c, color: "text-primary bg-primary/10" })),
                    ...ta.industries.slice(0, 2).map((ind) => ({
                      label: ind,
                      color: "text-blue-400 bg-blue-500/10",
                    })),
                    ...ta.regions.slice(0, 3).map((r) => ({
                      label: r,
                      color: "text-emerald-400 bg-emerald-500/10",
                    })),
                  ]}
                  onClick={() => openDetail("threat_actor", ta.name)}
                />
              ))}
            </div>
          ) : (
            <EmptyState text="No threat actor intelligence detected" />
          )}
        </SectionCard>

        <SectionCard
          title="Most Active Ransomware"
          icon={<Lock className="h-4 w-4" />}
          iconAccent="text-orange-400"
          action={
            <button
              onClick={() => openViewAll("ransomware", "All Ransomware")}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              View all <Eye className="h-3 w-3" />
            </button>
          }
        >
          {!insights ? (
            <SkeletonRankedList rows={4} />
          ) : insights.ransomware && insights.ransomware.length > 0 ? (
            <div className="space-y-2">
              {insights.ransomware.map((rw) => (
                <InsightRow
                  key={rw.name}
                  name={rw.name}
                  count={rw.count}
                  avgRisk={rw.avg_risk}
                  icon={<Lock className="h-3.5 w-3.5" />}
                  accentClass="text-orange-400 bg-orange-500/10"
                  badges={[
                    ...(rw.exploit
                      ? [{ label: "Exploit Available", color: "text-red-400 bg-red-500/10" }]
                      : []),
                    ...rw.industries.slice(0, 3).map((ind) => ({
                      label: ind,
                      color: "text-blue-400 bg-blue-500/10",
                    })),
                    ...rw.regions.slice(0, 3).map((r) => ({
                      label: r,
                      color: "text-emerald-400 bg-emerald-500/10",
                    })),
                  ]}
                  onClick={() => openDetail("ransomware", rw.name)}
                />
              ))}
            </div>
          ) : (
            <EmptyState text="No ransomware intelligence detected" />
          )}
        </SectionCard>
      </div>

      {/* Malware / Infostealer / Rootkit */}
      <SectionCard
        title="Malware, Infostealers & Botnets"
        icon={<Bug className="h-4 w-4" />}
        iconAccent="text-purple-400"
        action={
          <button
            onClick={() => openViewAll("malware", "All Malware, Infostealers & Botnets")}
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            View all <Eye className="h-3 w-3" />
          </button>
        }
      >
        {!insights ? (
          <SkeletonCardGrid count={6} height={64} />
        ) : insights.malware_families && insights.malware_families.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {insights.malware_families.map((mw) => (
              <button
                key={mw.name}
                onClick={() => openDetail("malware", mw.name)}
                className="flex items-center gap-3 p-2.5 rounded-lg border bg-card hover:bg-accent/50 transition-colors group text-left"
              >
                <span
                  className={cn(
                    "flex items-center justify-center h-8 w-8 rounded-md text-xs font-bold shrink-0",
                    riskBucketClasses(mw.avg_risk),
                  )}
                >
                  {Math.round(mw.avg_risk)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-semibold capitalize group-hover:text-primary transition-colors">
                      {mw.name.replace(/_/g, " ")}
                    </p>
                    <span className="text-[10px] text-muted-foreground">{mw.count} intel</span>
                  </div>
                  {mw.regions.length > 0 && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <Globe className="h-2.5 w-2.5 text-muted-foreground" />
                      <span className="text-[10px] text-muted-foreground">
                        {mw.regions.slice(0, 4).join(", ")}
                      </span>
                    </div>
                  )}
                </div>
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/30 group-hover:text-primary shrink-0" />
              </button>
            ))}
          </div>
        ) : (
          <EmptyState text="No malware intelligence detected" />
        )}
      </SectionCard>

      {/* Sources & CVEs & Feed Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <SectionCard title="Top Sources">
          {!dashboard ? (
            <SkeletonRankedList rows={6} />
          ) : topSources.length > 0 ? (
            <RankedDataList items={topSources} showIndex maxItems={6} />
          ) : (
            <EmptyState text="No source data" />
          )}
        </SectionCard>

        <SectionCard title="Top CVEs Referenced">
          {!insights ? (
            <SkeletonRankedList rows={6} />
          ) : topCVEs.length > 0 ? (
            <div className="space-y-2">
              {topCVEs.slice(0, 8).map((cve, idx) => {
                const maxCount = topCVEs[0]?.count ?? 1;
                return (
                  <button
                    key={cve.cve_id}
                    onClick={() => openDetail("cve", cve.cve_id)}
                    className="w-full group text-left"
                  >
                    <div className="flex items-center justify-between text-xs mb-0.5">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="text-[10px] font-medium text-muted-foreground/50 w-4 text-right">
                          {idx + 1}
                        </span>
                        <span className="h-2 w-2 rounded-full shrink-0 bg-red-500" />
                        <span className="text-muted-foreground truncate group-hover:text-primary transition-colors font-mono">
                          {cve.cve_id}
                        </span>
                        {cve.is_kev && (
                          <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 font-semibold leading-none">
                            KEV
                          </span>
                        )}
                        {cve.has_exploit && (
                          <span className="text-[9px] px-1 py-0.5 rounded bg-orange-500/15 text-orange-400 font-semibold leading-none">
                            Exploit
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-2 shrink-0">
                        <span
                          className={cn(
                            "text-[10px] font-mono px-1 rounded",
                            riskBucketClasses(cve.max_risk),
                          )}
                        >
                          {cve.max_risk}
                        </span>
                        <span className="font-semibold tabular-nums">{cve.count}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-8 mb-0.5">
                      {cve.products.length > 0 && (
                        <span className="text-[10px] text-blue-400 truncate">
                          {cve.products.slice(0, 2).join(", ")}
                        </span>
                      )}
                      {cve.first_seen && (
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {new Date(cve.first_seen).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                      )}
                    </div>
                    <div className="h-1 rounded-full bg-muted/50 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500 bg-red-500"
                        style={{ width: `${(cve.count / maxCount) * 100}%` }}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <EmptyState text="No CVE data" />
          )}
        </SectionCard>

        <SectionCard title="Feed Connectors">
          {!dashboard ? (
            <SkeletonRankedList rows={5} />
          ) : dashboard.feed_status && dashboard.feed_status.length > 0 ? (
            <FeedStatusPanel feeds={dashboard.feed_status} />
          ) : (
            <EmptyState text="No feeds configured" />
          )}
        </SectionCard>
      </div>

      {/* Top Risks Table */}
      <SectionCard
        title="Highest Risk Items"
        action={
          <Link
            href="/threats?severity=critical"
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        }
      >
        {!dashboard ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50">
                  {["Risk", "Severity", "Title", "Source", "Type", "CVEs", "KEV"].map((h) => (
                    <th
                      key={h}
                      className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonTableRow key={i} cols={7} />
                ))}
              </tbody>
            </table>
          </div>
        ) : topRiskItems.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50">
                  <th className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider">
                    Risk
                  </th>
                  <th className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider">
                    Title
                  </th>
                  <th className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider">
                    Source
                  </th>
                  <th className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider">
                    Type
                  </th>
                  <th className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider">
                    CVEs
                  </th>
                  <th className="text-left py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wider">
                    KEV
                  </th>
                </tr>
              </thead>
              <tbody>
                {topRiskItems.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-border/30 hover:bg-accent/30 transition-colors cursor-pointer"
                    onClick={() => router.push(`/intel/${item.id}`)}
                  >
                    <td className="py-2.5 px-2">
                      <span
                        className={cn(
                          "inline-flex items-center justify-center h-7 w-10 rounded-md text-xs font-bold tabular-nums",
                          riskBucketClasses(item.risk_score),
                        )}
                      >
                        {item.risk_score}
                      </span>
                    </td>
                    <td className="py-2.5 px-2">
                      <Badge variant={item.severity as any} className="text-[10px] px-1.5 py-0">
                        {item.severity.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-2 max-w-xs">
                      <span className="font-medium text-foreground line-clamp-1">{item.title}</span>
                    </td>
                    <td className="py-2.5 px-2 text-muted-foreground">{item.source_name}</td>
                    <td className="py-2.5 px-2">
                      <span className="text-muted-foreground capitalize">
                        {item.feed_type.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="py-2.5 px-2">
                      {item.cve_ids?.length > 0 ? (
                        <span className="font-mono text-primary">{item.cve_ids[0]}</span>
                      ) : (
                        <span className="text-muted-foreground/40">—</span>
                      )}
                      {(item.cve_ids?.length ?? 0) > 1 && (
                        <span className="text-muted-foreground ml-1">+{item.cve_ids.length - 1}</span>
                      )}
                    </td>
                    <td className="py-2.5 px-2">
                      {item.is_kev ? (
                        <span className="text-red-500 font-semibold flex items-center gap-1">
                          <Zap className="h-3 w-3" /> Yes
                        </span>
                      ) : (
                        <span className="text-muted-foreground/40">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Shield className="h-10 w-10 mb-3 opacity-20" />
            <p className="text-sm">No threat intel data yet.</p>
            <p className="text-xs mt-1">Feed ingestion will populate this automatically.</p>
          </div>
        )}
      </SectionCard>

      {/* Modals */}
      <InsightDetailModal
        open={modal?.kind === "detail"}
        onClose={closeModal}
        type={modal?.kind === "detail" ? modal.type : ""}
        name={modal?.kind === "detail" ? modal.name : ""}
      />
      <ViewAllModal
        open={modal?.kind === "viewAll"}
        onClose={closeModal}
        type={modal?.kind === "viewAll" ? modal.type : ""}
        title={modal?.kind === "viewAll" ? modal.title : ""}
        onSelect={(name) => {
          if (modal?.kind === "viewAll") {
            setModal({ kind: "detail", type: modal.type, name });
          }
        }}
      />
    </div>
  );
}

function EmptyState({ text = "No data yet" }: { text?: string }) {
  return (
    <div className="h-[180px] flex items-center justify-center text-xs text-muted-foreground/60">
      {text}
    </div>
  );
}

function InsightRow({
  name,
  count,
  avgRisk,
  icon,
  accentClass,
  badges,
  onClick,
}: {
  name: string;
  count: number;
  avgRisk: number;
  icon: React.ReactNode;
  accentClass: string;
  badges: Array<{ label: string; color: string }>;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-start gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors group text-left"
    >
      <span
        className={cn(
          "flex items-center justify-center h-9 w-9 rounded-md shrink-0",
          accentClass,
        )}
      >
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold capitalize group-hover:text-primary transition-colors">
            {name.replace(/_/g, " ")}
          </span>
          <span className="text-[10px] text-muted-foreground">{count} intel items</span>
          <span className={cn("text-[10px] font-mono px-1.5 py-0.5 rounded", riskBucketClasses(avgRisk))}>
            Risk {avgRisk}
          </span>
        </div>
        {badges.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {badges.map((b, i) => (
              <span
                key={`${b.label}-${i}`}
                className={cn(
                  "inline-flex items-center text-[10px] px-1.5 py-0.5 rounded font-medium",
                  b.color,
                )}
              >
                {b.label}
              </span>
            ))}
          </div>
        )}
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground/30 group-hover:text-primary shrink-0 mt-2.5" />
    </button>
  );
}
