"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SkeletonTableRow } from "@/components/Skeleton";
import {
  Search,
  ArrowUpDown,
  Bug,
  ExternalLink,
  FileDown,
  FileCode,
  ChevronDown,
  Users,
  Swords,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";
import * as api from "@/lib/api";
import type { ThreatCampaignsListResponse } from "@/types";
import {
  severityBadge,
  parseTechnique,
  EntityBadge,
  isNewEntry,
  isStaleEntry,
  timeAgo,
  formatPublishDate,
} from "./_newsWidgetHelpers";

// ── Campaign Timeline Widget (co-located, only used here) ──
function CampaignTimelineWidget({ campaigns }: { campaigns: Array<{ id: string; actor_name: string; first_seen: string; last_seen: string; severity: string }> }) {
  if (!campaigns || campaigns.length === 0) return null;
  // Find date range
  const allDates = campaigns.flatMap((c) => [new Date(c.first_seen).getTime(), new Date(c.last_seen).getTime()]);
  const minDate = Math.min(...allDates);
  const maxDate = Math.max(...allDates);
  const range = maxDate - minDate || 1;

  return (
    <Card className="card-3d mb-3">
      <CardHeader className="pb-2 pt-3 px-4">
        <CardTitle className="text-xs font-semibold flex items-center gap-1.5"><Calendar className="h-3.5 w-3.5 text-red-400" />Campaign Timeline</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-3">
        <div className="space-y-1">
          {campaigns.slice(0, 12).map((c) => {
            const start = ((new Date(c.first_seen).getTime() - minDate) / range) * 100;
            const width = Math.max(((new Date(c.last_seen).getTime() - new Date(c.first_seen).getTime()) / range) * 100, 2);
            const sev = c.severity;
            const color = sev === "critical" ? "bg-red-500/70" : sev === "high" ? "bg-orange-500/70" : sev === "medium" ? "bg-yellow-500/70" : "bg-green-500/70";
            return (
              <div key={c.id} className="flex items-center gap-2 text-[10px]">
                <span className="w-[140px] truncate text-muted-foreground font-medium" title={c.actor_name}>{c.actor_name}</span>
                <div className="flex-1 h-2.5 bg-muted/15 rounded-full relative overflow-hidden">
                  <div className={cn("absolute h-full rounded-full", color)} style={{ left: `${start}%`, width: `${width}%` }} title={`${formatPublishDate(c.first_seen)} — ${formatPublishDate(c.last_seen)}`} />
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-[9px] mt-1.5">
          <span className="text-sky-400/80 font-medium">{formatPublishDate(new Date(minDate).toISOString())}</span>
          <span className="text-sky-400/80 font-medium">{formatPublishDate(new Date(maxDate).toISOString())}</span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ThreatCampaignsTable() {
  const [data, setData] = useState<ThreatCampaignsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("last_seen");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [sevFilter, setSevFilter] = useState("");
  const [windowMode, setWindowMode] = useState<"7d" | "all">("7d");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.getThreatCampaigns({
        search: search.trim() || undefined,
        severity: sevFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 200,
        window: windowMode,
      });
      setData(result);
    } catch (err) { console.error("[news/threat-campaigns] fetchData failed", err); } finally {
      setLoading(false);
    }
  }, [search, sevFilter, sortBy, sortOrder, windowMode]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const toggleSort = (col: string) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === "desc" ? "asc" : "desc");
    } else {
      setSortBy(col);
      setSortOrder("desc");
    }
  };

  const SortHeader = ({ col, children }: { col: string; children: React.ReactNode }) => (
    <button
      onClick={() => toggleSort(col)}
      className={cn(
        "flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider hover:text-foreground transition-colors",
        sortBy === col ? "text-primary" : "text-muted-foreground/70",
      )}
    >
      {children}
      <ArrowUpDown className="h-3 w-3" />
    </button>
  );

  return (
    <div className="space-y-3">
      {/* Campaign Timeline */}
      {data && data.items.length > 0 && (
        <CampaignTimelineWidget campaigns={data.items.map((i) => ({ id: i.id, actor_name: i.actor_name, first_seen: i.first_seen, last_seen: i.last_seen, severity: i.severity }))} />
      )}
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
          <input
            type="text"
            placeholder="Search actors, campaigns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-card/50 border border-border/50 rounded-md focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/40"
          />
        </div>
        <select
          value={sevFilter}
          onChange={(e) => setSevFilter(e.target.value)}
          className="text-[11px] bg-card/50 border border-border/50 rounded-md px-2 py-1.5"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        {/* Time window toggle */}
        <div className="flex items-center bg-card/50 border border-border/50 rounded-md overflow-hidden">
          <button
            onClick={() => setWindowMode("7d")}
            className={cn(
              "px-2.5 py-1.5 text-[11px] font-medium transition-colors",
              windowMode === "7d" ? "bg-red-500/20 text-red-300" : "text-muted-foreground/60 hover:text-muted-foreground",
            )}
          >
            Last 7 Days
          </button>
          <button
            onClick={() => setWindowMode("all")}
            className={cn(
              "px-2.5 py-1.5 text-[11px] font-medium transition-colors",
              windowMode === "all" ? "bg-red-500/20 text-red-300" : "text-muted-foreground/60 hover:text-muted-foreground",
            )}
          >
            View All
          </button>
        </div>
        <span className="text-[10px] text-muted-foreground/60 ml-auto">
          {data ? `${data.total} campaigns` : ""}
        </span>
        {/* Export buttons */}
        <div className="flex items-center gap-1">
          <a href={api.getExtractionExportUrl("threat-campaigns", "csv", windowMode)} className="flex items-center gap-1 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded-md hover:bg-accent/20 transition-colors" title="Export CSV"><FileDown className="h-3 w-3" />CSV</a>
          <a href={api.getExtractionExportUrl("threat-campaigns", "json", windowMode)} className="flex items-center gap-1 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded-md hover:bg-accent/20 transition-colors" title="Export JSON"><FileCode className="h-3 w-3" />JSON</a>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="rounded-lg border border-border/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <tbody>
                {Array.from({ length: 8 }).map((_, i) => <SkeletonTableRow key={i} cols={10} />)}
              </tbody>
            </table>
          </div>
        </div>
      ) : !data || data.items.length === 0 ? (
        <Card className="card-3d">
          <CardContent className="py-12 text-center">
            <Swords className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              No active threat campaigns found{windowMode === "7d" ? " in the last 7 days" : ""}.
            </p>
            {windowMode === "7d" && (
              <button
                onClick={() => setWindowMode("all")}
                className="mt-2 text-xs text-primary hover:underline"
              >
                View all campaigns →
              </button>
            )}
            <p className="text-xs text-muted-foreground/60 mt-1">Campaigns are extracted automatically from enriched news articles.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-lg border border-border/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-card/80 border-b border-border/30">
                  <th className="text-left px-3 py-2"><SortHeader col="actor_name">Threat Actor</SortHeader></th>
                  <th className="text-left px-3 py-2 hidden md:table-cell">Campaign</th>
                  <th className="text-center px-3 py-2"><SortHeader col="severity">Severity</SortHeader></th>
                  <th className="text-left px-3 py-2 hidden lg:table-cell">Malware</th>
                  <th className="text-left px-3 py-2 hidden lg:table-cell">Techniques</th>
                  <th className="text-left px-3 py-2 hidden xl:table-cell">CVEs</th>
                  <th className="text-left px-3 py-2 hidden xl:table-cell">Linked Products</th>
                  <th className="text-left px-3 py-2 hidden xl:table-cell">Targets</th>
                  <th className="text-left px-3 py-2 hidden md:table-cell">Sources</th>
                  <th className="text-right px-3 py-2"><SortHeader col="last_seen">Published</SortHeader></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/20">
                {data.items.map((item) => {
                  const sev = severityBadge(item.severity);
                  const isNew = isNewEntry(item.first_seen);
                  const stale = isStaleEntry(item.last_seen, 14);
                  const expanded = expandedId === item.id;
                  return (
                    <React.Fragment key={item.id}>
                    <tr
                      onClick={() => setExpandedId(expanded ? null : item.id)}
                      className={cn(
                        "hover:bg-accent/10 transition-colors cursor-pointer",
                        stale && "opacity-50",
                        item.is_false_positive && "opacity-40 line-through",
                        expanded && "bg-accent/10",
                      )}
                    >
                      <td className="px-3 py-2 font-medium max-w-[220px]" title={item.actor_name}>
                        <div className="flex items-center gap-1.5">
                          <ChevronDown className={cn("h-3 w-3 text-muted-foreground/50 shrink-0 transition-transform", expanded && "rotate-180")} />
                          <Users className="h-3 w-3 text-red-400 shrink-0" />
                          <EntityBadge label={item.actor_name} searchPrefix="actor" className="text-xs font-medium text-foreground hover:text-primary" />
                          {isNew && <span className="shrink-0 text-[7px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded px-1">NEW</span>}
                          {stale && <span className="shrink-0 text-[7px] font-bold bg-zinc-500/20 text-zinc-400 border border-zinc-500/30 rounded px-1">STALE</span>}
                          {item.is_false_positive && <span className="shrink-0 text-[7px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded px-1">FP</span>}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground hidden md:table-cell max-w-[220px] truncate" title={item.campaign_name || ""}>
                        {item.campaign_name || "—"}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Badge variant="outline" className={cn("text-[9px] h-4 px-1.5 border", sev.color)}>
                          {sev.label}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 hidden lg:table-cell">
                        <div className="flex gap-1 flex-wrap max-w-[120px]">
                          {item.malware_used.slice(0, 2).map((m) => (
                            <EntityBadge key={m} label={m} searchPrefix="malware" className="text-[8px] px-1 py-0 rounded border border-purple-500/30 text-purple-300 hover:bg-purple-500/10" />
                          ))}
                          {item.malware_used.length > 2 && (
                            <span className="text-[8px] text-muted-foreground/50">+{item.malware_used.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 hidden lg:table-cell">
                        <div className="flex gap-1 flex-wrap max-w-[120px]">
                          {item.techniques_used.slice(0, 2).map((t) => {
                            const parsed = parseTechnique(t);
                            return parsed.code ? (
                              <a key={t} href={`https://attack.mitre.org/techniques/${parsed.code.replace(".", "/")}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[8px] px-1 py-0 rounded border border-sky-500/30 text-sky-300 hover:bg-sky-500/10" title={parsed.label}>
                                {parsed.code}
                              </a>
                            ) : (
                              <EntityBadge key={t} label={t} searchPrefix="technique" className="text-[8px] px-1 py-0 rounded border border-sky-500/30 text-sky-300 hover:bg-sky-500/10" />
                            );
                          })}
                          {item.techniques_used.length > 2 && (
                            <span className="text-[8px] text-muted-foreground/50">+{item.techniques_used.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 hidden xl:table-cell">
                        <div className="flex gap-1 flex-wrap max-w-[150px]">
                          {item.cves_exploited.slice(0, 2).map((c) => (
                            <a
                              key={c}
                              href={`https://nvd.nist.gov/vuln/detail/${c}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[9px] font-mono text-orange-300 hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {c}
                            </a>
                          ))}
                          {item.cves_exploited.length > 2 && (
                            <span className="text-[8px] text-muted-foreground/50">+{item.cves_exploited.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 hidden xl:table-cell">
                        <div className="flex gap-1 flex-wrap max-w-[130px]">
                          {(item.related_products || []).slice(0, 2).map((p) => (
                            <span key={p.id} className="inline-flex items-center gap-0.5 text-[8px] px-1 py-0 rounded border border-orange-500/30 text-orange-300" title={`${p.product_name}${p.cve_id ? ` (${p.cve_id})` : ''}`}>
                              <Bug className="h-2 w-2" />
                              {p.product_name.length > 16 ? p.product_name.slice(0, 14) + "…" : p.product_name}
                            </span>
                          ))}
                          {(item.related_products || []).length > 2 && (
                            <span className="text-[8px] text-muted-foreground/50">+{item.related_products.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 hidden xl:table-cell">
                        <div className="flex gap-1 flex-wrap max-w-[100px]">
                          {item.targeted_sectors.slice(0, 2).map((s) => (
                            <span key={s} className="text-[8px] text-muted-foreground">{s}</span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2 hidden md:table-cell">
                        <div className="flex flex-col gap-0.5 max-w-[180px]">
                          {(item.source_articles || []).slice(0, 2).map((a) => (
                            <a
                              key={a.id}
                              href={a.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-[10px] text-primary hover:underline truncate"
                              title={a.headline}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                              <span className="truncate">{a.source}</span>
                            </a>
                          ))}
                          {(item.source_articles || []).length > 2 && (
                            <span className="text-[9px] text-muted-foreground/50">+{item.source_articles.length - 2} more</span>
                          )}
                          {(!item.source_articles || item.source_articles.length === 0) && (
                            <span className="text-[10px] text-muted-foreground/40">{item.source_count} source{item.source_count !== 1 ? "s" : ""}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex flex-col items-end gap-0">
                          <span className="text-sky-400 font-medium text-[10px]">{timeAgo(item.last_seen)}</span>
                          <span className="text-sky-300/60 text-[9px]">{formatPublishDate(item.last_seen)}</span>
                        </div>
                      </td>
                    </tr>
                    {/* Expanded detail panel */}
                    {expanded && (
                      <tr className="bg-card/60">
                        <td colSpan={10} className="px-4 py-3">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                            {/* Col 1: Campaign Timeline + Details */}
                            <div className="space-y-2">
                              <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Campaign Details</h4>
                              <div className="space-y-1">
                                <div className="flex justify-between"><span className="text-muted-foreground">Confidence</span><Badge variant="outline" className={cn("text-[9px] h-4 px-1.5 border", item.confidence === "high" ? "border-green-500/30 text-green-300" : item.confidence === "medium" ? "border-yellow-500/30 text-yellow-300" : "border-zinc-500/30 text-zinc-300")}>{item.confidence}</Badge></div>
                                <div className="flex justify-between"><span className="text-muted-foreground">Active Period</span><span>{formatPublishDate(item.first_seen)} — {formatPublishDate(item.last_seen)}</span></div>
                                <div className="flex justify-between"><span className="text-muted-foreground">Sources</span><span>{item.source_count}</span></div>
                              </div>
                              {/* Mini timeline bar */}
                              <div className="mt-2">
                                <div className="flex items-center gap-2 text-[9px] text-muted-foreground/60">
                                  <span>{formatPublishDate(item.first_seen)}</span>
                                  <div className="flex-1 h-1.5 rounded-full bg-muted/30 relative overflow-hidden">
                                    <div className="absolute inset-y-0 left-0 rounded-full bg-red-500/60" style={{ width: "100%" }} />
                                  </div>
                                  <span>{formatPublishDate(item.last_seen)}</span>
                                </div>
                              </div>
                            </div>
                            {/* Col 2: MITRE + Malware + Regions */}
                            <div className="space-y-2">
                              {item.techniques_used.length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider mb-1">MITRE ATT&CK Techniques</h4>
                                  <div className="flex gap-1 flex-wrap">
                                    {item.techniques_used.map((t) => {
                                      const parsed = parseTechnique(t);
                                      return parsed.code ? (
                                        <a key={t} href={`https://attack.mitre.org/techniques/${parsed.code.replace(".", "/")}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[9px] px-1.5 py-0.5 rounded border border-sky-500/30 text-sky-300 hover:bg-sky-500/10">
                                          {parsed.code} — {parsed.label.replace(parsed.code, "").replace(/[:\-–—]\s*/, "").trim() || parsed.code}
                                        </a>
                                      ) : (
                                        <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-muted/30 text-muted-foreground">{t}</span>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                              {item.malware_used.length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider mb-1">Malware</h4>
                                  <div className="flex gap-1 flex-wrap">{item.malware_used.map((m) => <span key={m} className="text-[9px] px-1.5 py-0.5 rounded border border-purple-500/30 text-purple-300">{m}</span>)}</div>
                                </div>
                              )}
                              {item.targeted_sectors.length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider mb-1">Targeted Sectors</h4>
                                  <div className="flex gap-1 flex-wrap">{item.targeted_sectors.map((s) => <span key={s} className="text-[9px] px-1.5 py-0.5 rounded bg-muted/30 text-muted-foreground">{s}</span>)}</div>
                                </div>
                              )}
                              {item.targeted_regions.length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider mb-1">Targeted Regions</h4>
                                  <div className="flex gap-1 flex-wrap">{item.targeted_regions.map((r) => <span key={r} className="text-[9px] px-1.5 py-0.5 rounded bg-muted/30 text-muted-foreground">{r}</span>)}</div>
                                </div>
                              )}
                            </div>
                            {/* Col 3: CVEs + Products + Sources */}
                            <div className="space-y-2">
                              {item.cves_exploited.length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider mb-1">CVEs Exploited</h4>
                                  <div className="flex gap-1 flex-wrap">{item.cves_exploited.map((c) => (
                                    <a key={c} href={`https://nvd.nist.gov/vuln/detail/${c}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[9px] font-mono text-orange-300 hover:underline px-1.5 py-0.5 rounded border border-orange-500/30">{c}</a>
                                  ))}</div>
                                </div>
                              )}
                              {(item.related_products || []).length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider mb-1">Linked Products</h4>
                                  <div className="flex gap-1 flex-wrap">{item.related_products.map((p) => (
                                    <span key={p.id} className="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded border border-orange-500/30 text-orange-300"><Bug className="h-2.5 w-2.5" />{p.product_name}{p.cve_id ? ` (${p.cve_id})` : ""}</span>
                                  ))}</div>
                                </div>
                              )}
                              <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Source Articles ({(item.source_articles || []).length})</h4>
                              <div className="space-y-1 max-h-[120px] overflow-y-auto">
                                {(item.source_articles || []).map((a) => (
                                  <a key={a.id} href={a.source_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="flex items-start gap-1.5 p-1.5 rounded hover:bg-accent/20 transition-colors">
                                    <ExternalLink className="h-3 w-3 text-primary shrink-0 mt-0.5" />
                                    <div className="min-w-0">
                                      <div className="text-[10px] text-foreground truncate">{a.headline}</div>
                                      <div className="text-[9px] text-muted-foreground/50">{a.source}{a.published_at ? ` · ${formatPublishDate(a.published_at)}` : ""}</div>
                                    </div>
                                  </a>
                                ))}
                              </div>
                            </div>
                          </div>
                          {/* False Positive Toggle */}
                          <div className="mt-3 pt-2 border-t border-border/20 flex items-center justify-between">
                            <span className="text-[10px] text-muted-foreground/60">
                              {item.is_false_positive ? "Marked as false positive" : "Is this a false positive?"}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const newVal = !item.is_false_positive;
                                api.toggleFalsePositive("threat-campaigns", item.id, newVal).then(() => {
                                  setData(prev => prev ? { ...prev, items: prev.items.map(i => i.id === item.id ? { ...i, is_false_positive: newVal } : i) } : prev);
                                }).catch(() => { /* toggle failed — UI unchanged */ });
                              }}
                              className={cn(
                                "text-[10px] px-2 py-1 rounded-md border transition-colors",
                                item.is_false_positive
                                  ? "bg-amber-500/20 text-amber-300 border-amber-500/30 hover:bg-amber-500/10"
                                  : "text-muted-foreground border-border/40 hover:bg-accent/20"
                              )}
                            >
                              {item.is_false_positive ? "✕ Undo" : "Flag False Positive"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
