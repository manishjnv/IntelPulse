"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton, SkeletonTableRow } from "@/components/Skeleton";
import {
  Search,
  ArrowUpDown,
  Bug,
  ShieldAlert,
  ShieldCheck,
  Zap,
  ExternalLink,
  FileDown,
  FileCode,
  Loader2,
  ChevronDown,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import * as api from "@/lib/api";
import type { VulnerableProductsListResponse } from "@/types";
import {
  severityBadge,
  isNewEntry,
  isStaleEntry,
  timeAgo,
  formatPublishDate,
} from "./_newsWidgetHelpers";

export default function VulnerableProductsTable() {
  const [data, setData] = useState<VulnerableProductsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("last_seen");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [sevFilter, setSevFilter] = useState("");
  const [windowMode, setWindowMode] = useState<"24h" | "all">("24h");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [cveLookupOpen, setCveLookupOpen] = useState(false);
  const [cveInput, setCveInput] = useState("");
  const [cveLookupResult, setCveLookupResult] = useState<{ requested: number; found: number; missing: string[]; results: Record<string, any> } | null>(null);
  const [cveLookupLoading, setCveLookupLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.getVulnerableProducts({
        search: search.trim() || undefined,
        severity: sevFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 200,
        window: windowMode,
      });
      setData(result);
    } catch (err) { console.error("[news/vulnerable-products] fetchData failed", err); } finally {
      setLoading(false);
    }
  }, [search, sevFilter, sortBy, sortOrder, windowMode]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCveLookup = async () => {
    const cves = cveInput.split(/[\n,]+/).map(s => s.trim().toUpperCase()).filter(s => /^CVE-/.test(s));
    if (!cves.length) return;
    setCveLookupLoading(true);
    try {
      const result = await api.bulkCveLookup(cves);
      setCveLookupResult(result);
    } catch (err) { console.error("[news/vulnerable-products] bulk CVE lookup failed", err); } finally {
      setCveLookupLoading(false);
    }
  };

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
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
          <input
            type="text"
            placeholder="Search products, CVEs, vendors..."
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
            onClick={() => setWindowMode("24h")}
            className={cn(
              "px-2.5 py-1.5 text-[11px] font-medium transition-colors",
              windowMode === "24h" ? "bg-orange-500/20 text-orange-300" : "text-muted-foreground/60 hover:text-muted-foreground",
            )}
          >
            Last 24H
          </button>
          <button
            onClick={() => setWindowMode("all")}
            className={cn(
              "px-2.5 py-1.5 text-[11px] font-medium transition-colors",
              windowMode === "all" ? "bg-orange-500/20 text-orange-300" : "text-muted-foreground/60 hover:text-muted-foreground",
            )}
          >
            View All
          </button>
        </div>
        <span className="text-[10px] text-muted-foreground/60 ml-auto">
          {data ? `${data.total} products` : ""}
        </span>
        {/* Export buttons */}
        <div className="flex items-center gap-1">
          <button onClick={() => { setCveLookupOpen(!cveLookupOpen); setCveLookupResult(null); }} className={cn("flex items-center gap-1 px-2 py-1 text-[10px] border border-border/50 rounded-md hover:bg-accent/20 transition-colors", cveLookupOpen ? "text-blue-400 border-blue-500/40" : "text-muted-foreground hover:text-foreground")} title="Bulk CVE Lookup"><Search className="h-3 w-3" />CVE Lookup</button>
          <a href={api.getExtractionExportUrl("vulnerable-products", "csv", windowMode)} className="flex items-center gap-1 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded-md hover:bg-accent/20 transition-colors" title="Export CSV"><FileDown className="h-3 w-3" />CSV</a>
          <a href={api.getExtractionExportUrl("vulnerable-products", "json", windowMode)} className="flex items-center gap-1 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded-md hover:bg-accent/20 transition-colors" title="Export JSON"><FileCode className="h-3 w-3" />JSON</a>
        </div>
      </div>

      {/* Bulk CVE Lookup Panel */}
      {cveLookupOpen && (
        <div className="mb-3 p-3 bg-card/60 border border-border/40 rounded-lg space-y-2">
          <div className="flex gap-2 items-start">
            <textarea
              value={cveInput}
              onChange={e => setCveInput(e.target.value)}
              placeholder="Paste CVEs (one per line or comma-separated)&#10;CVE-2024-1234, CVE-2023-5678&#10;CVE-2024-9999"
              rows={3}
              className="flex-1 text-[11px] bg-background/60 border border-border/40 rounded-md px-2 py-1.5 resize-none focus:outline-none focus:border-blue-500/50 placeholder:text-muted-foreground/40"
            />
            <button
              onClick={handleCveLookup}
              disabled={cveLookupLoading || !cveInput.trim()}
              className="px-3 py-1.5 text-[10px] font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-40 transition-colors"
            >
              {cveLookupLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : "Lookup"}
            </button>
          </div>
          {cveLookupResult && (
            <div className="space-y-2">
              <div className="flex gap-3 text-[10px] items-center">
                <span className="text-muted-foreground">Requested: <span className="text-foreground font-medium">{cveLookupResult.requested}</span></span>
                <span className="text-green-400">Found: {cveLookupResult.found}</span>
                {cveLookupResult.missing.length > 0 && <span className="text-amber-400">Missing: {cveLookupResult.missing.length}</span>}
                {Object.keys(cveLookupResult.results).length > 0 && (
                  <div className="flex gap-1 ml-auto">
                    <button onClick={() => { const results = cveLookupResult.results; const header = "CVE,Product,Vendor,Severity,CVSS,EPSS,KEV,Exploit,Patch,Linked Actors,Sources,Published"; const rows = Object.entries(results).map(([cve, p]: [string, any]) => [cve, `"${(p.product_name||'').replace(/"/g,"'")}"`, `"${(p.vendor||'').replace(/"/g,"'")}"`, p.severity||'', p.cvss_score!=null?Number(p.cvss_score).toFixed(1):'', p.epss_score!=null?Number(p.epss_score).toFixed(1)+'%':'', String(!!p.is_kev), String(!!p.exploit_available), String(!!p.patch_available), `"${(p.related_campaigns||[]).map((c:any)=>c.actor_name).join('; ')}"`, `"${(p.source_articles||[]).map((a:any)=>a.source).join('; ')}"`, p.last_seen||''].join(',')); const blob = new Blob([header+'\n'+rows.join('\n')], {type:'text/csv'}); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'cve_lookup.csv'; a.click(); URL.revokeObjectURL(a.href); }} className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded-md hover:bg-accent/20 transition-colors" title="Export CVE Lookup CSV"><FileDown className="h-3 w-3" />CSV</button>
                    <button onClick={() => { const blob = new Blob([JSON.stringify(Object.entries(cveLookupResult.results).map(([cve, p]: [string, any]) => ({cve, product: p.product_name, vendor: p.vendor, severity: p.severity, cvss: p.cvss_score, epss: p.epss_score, is_kev: p.is_kev, exploit_available: p.exploit_available, patch_available: p.patch_available, linked_actors: (p.related_campaigns||[]).map((c:any)=>c.actor_name), sources: (p.source_articles||[]).map((a:any)=>({name: a.source, url: a.source_url})), published: p.last_seen})), null, 2)], {type:'application/json'}); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'cve_lookup.json'; a.click(); URL.revokeObjectURL(a.href); }} className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground border border-border/50 rounded-md hover:bg-accent/20 transition-colors" title="Export CVE Lookup JSON"><FileCode className="h-3 w-3" />JSON</button>
                  </div>
                )}
              </div>
              {cveLookupResult.missing.length > 0 && (
                <div className="text-[10px] text-muted-foreground/60">Not tracked: {cveLookupResult.missing.join(", ")}</div>
              )}
              {Object.keys(cveLookupResult.results).length > 0 && (
                <div className="border border-border/30 rounded overflow-hidden">
                  <table className="w-full text-[10px]">
                    <thead><tr className="bg-muted/30 text-left text-muted-foreground/60">
                      <th className="px-2 py-1">CVE</th><th className="px-2 py-1">Product</th><th className="px-2 py-1">Vendor</th><th className="px-2 py-1">Severity</th><th className="px-2 py-1">CVSS</th><th className="px-2 py-1">EPSS</th><th className="px-2 py-1">Flags</th><th className="px-2 py-1">Linked Actors</th><th className="px-2 py-1">Source</th><th className="px-2 py-1">Published</th>
                    </tr></thead>
                    <tbody>
                      {Object.entries(cveLookupResult.results).map(([cve, p]: [string, any]) => (
                        <tr key={cve} className="border-t border-border/20 hover:bg-muted/10">
                          <td className="px-2 py-1 font-mono text-blue-400">{cve}</td>
                          <td className="px-2 py-1">{p.product_name}</td>
                          <td className="px-2 py-1 text-muted-foreground">{p.vendor || "—"}</td>
                          <td className="px-2 py-1"><Badge variant="outline" className={cn("text-[9px] px-1", p.severity === "critical" ? "border-red-500/40 text-red-400" : p.severity === "high" ? "border-orange-500/40 text-orange-400" : "border-border")}>{p.severity}</Badge></td>
                          <td className="px-2 py-1">{p.cvss_score != null ? Number(p.cvss_score).toFixed(1) : "—"}</td>
                          <td className="px-2 py-1">{p.epss_score != null ? `${Number(p.epss_score).toFixed(1)}%` : "—"}</td>
                          <td className="px-2 py-1">
                            <div className="flex items-center gap-1">
                              {p.is_kev && <span title="CISA KEV"><ShieldAlert className="h-3 w-3 text-red-400" /></span>}
                              {p.exploit_available && <span title="Exploit available"><Zap className="h-3 w-3 text-amber-400" /></span>}
                              {p.patch_available && <span title="Patch available"><ShieldCheck className="h-3 w-3 text-green-400" /></span>}
                              {!p.is_kev && !p.exploit_available && !p.patch_available && "—"}
                            </div>
                          </td>
                          <td className="px-2 py-1">
                            <div className="flex gap-1 flex-wrap max-w-[120px]">
                              {(p.related_campaigns || []).slice(0, 2).map((c: any) => (
                                <span key={c.id} className="inline-flex items-center gap-0.5 text-[8px] px-1 py-0 rounded border border-red-500/30 text-red-300" title={c.campaign_name || c.actor_name}>
                                  <Users className="h-2 w-2" />{c.actor_name}
                                </span>
                              ))}
                              {(p.related_campaigns || []).length > 2 && <span className="text-[8px] text-muted-foreground/50">+{p.related_campaigns.length - 2}</span>}
                              {(!p.related_campaigns || p.related_campaigns.length === 0) && "—"}
                            </div>
                          </td>
                          <td className="px-2 py-1">
                            <div className="flex flex-col gap-0.5 max-w-[140px]">
                              {(p.source_articles || []).slice(0, 1).map((a: any) => (
                                <a key={a.id} href={a.source_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[10px] text-primary hover:underline truncate" title={a.headline}>
                                  <ExternalLink className="h-2.5 w-2.5 shrink-0" /><span className="truncate">{a.source}</span>
                                </a>
                              ))}
                              {(p.source_articles || []).length > 1 && <span className="text-[8px] text-muted-foreground/50">+{p.source_articles.length - 1} more</span>}
                              {(!p.source_articles || p.source_articles.length === 0) && <span className="text-muted-foreground/40">{p.source_count || 1} src</span>}
                            </div>
                          </td>
                          <td className="px-2 py-1 text-muted-foreground">{p.last_seen ? timeAgo(p.last_seen) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

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
            <Bug className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              No vulnerable products found{windowMode === "24h" ? " in the last 24 hours" : ""}.
            </p>
            {windowMode === "24h" && (
              <button
                onClick={() => setWindowMode("all")}
                className="mt-2 text-xs text-primary hover:underline"
              >
                View all products →
              </button>
            )}
            <p className="text-xs text-muted-foreground/60 mt-1">Products are extracted automatically from enriched news articles.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-lg border border-border/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-card/80 border-b border-border/30">
                  <th className="text-left px-3 py-2"><SortHeader col="product_name">Product</SortHeader></th>
                  <th className="text-left px-3 py-2 hidden md:table-cell">Vendor</th>
                  <th className="text-left px-3 py-2">CVE</th>
                  <th className="text-center px-3 py-2 hidden lg:table-cell"><SortHeader col="cvss_score">CVSS</SortHeader></th>
                  <th className="text-center px-3 py-2 hidden lg:table-cell"><SortHeader col="epss_score">EPSS</SortHeader></th>
                  <th className="text-center px-3 py-2"><SortHeader col="severity">Severity</SortHeader></th>
                  <th className="text-center px-3 py-2 hidden lg:table-cell">Flags</th>
                  <th className="text-left px-3 py-2 hidden xl:table-cell">Linked Actors</th>
                  <th className="text-left px-3 py-2 hidden xl:table-cell">Sources</th>
                  <th className="text-right px-3 py-2"><SortHeader col="last_seen">Published</SortHeader></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/20">
                {data.items.map((item) => {
                  const sev = severityBadge(item.severity);
                  const isNew = isNewEntry(item.first_seen);
                  const stale = isStaleEntry(item.last_seen);
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
                      <td className="px-3 py-2 font-medium max-w-[280px]" title={item.product_name}>
                        <div className="flex items-center gap-1.5">
                          <ChevronDown className={cn("h-3 w-3 text-muted-foreground/50 shrink-0 transition-transform", expanded && "rotate-180")} />
                          <span className="truncate">{item.product_name}</span>
                          {isNew && <span className="shrink-0 text-[7px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded px-1">NEW</span>}
                          {stale && <span className="shrink-0 text-[7px] font-bold bg-zinc-500/20 text-zinc-400 border border-zinc-500/30 rounded px-1">STALE</span>}
                          {item.is_false_positive && <span className="shrink-0 text-[7px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded px-1">FP</span>}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground hidden md:table-cell">{item.vendor || "—"}</td>
                      <td className="px-3 py-2">
                        {item.cve_id ? (
                          <a
                            href={`https://nvd.nist.gov/vuln/detail/${item.cve_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline font-mono text-[11px]"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {item.cve_id}
                          </a>
                        ) : (
                          <span className="text-muted-foreground/40">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center hidden lg:table-cell">
                        {item.cvss_score != null ? (
                          <span className={cn(
                            "font-mono text-[10px] font-bold",
                            item.cvss_score >= 9 ? "text-red-400" :
                            item.cvss_score >= 7 ? "text-orange-400" :
                            item.cvss_score >= 4 ? "text-yellow-400" : "text-green-400"
                          )}>
                            {item.cvss_score.toFixed(1)}
                          </span>
                        ) : <span className="text-muted-foreground/40">—</span>}
                      </td>
                      <td className="px-3 py-2 text-center hidden lg:table-cell">
                        {item.epss_score != null ? (
                          <span className={cn(
                            "font-mono text-[10px] font-bold",
                            item.epss_score >= 50 ? "text-red-400" :
                            item.epss_score >= 20 ? "text-orange-400" :
                            item.epss_score >= 5 ? "text-yellow-400" : "text-green-400"
                          )}>
                            {item.epss_score.toFixed(1)}%
                          </span>
                        ) : <span className="text-muted-foreground/40">—</span>}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Badge variant="outline" className={cn("text-[9px] h-4 px-1.5 border", sev.color)}>
                          {sev.label}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-center hidden lg:table-cell">
                        <div className="flex items-center justify-center gap-1">
                          {item.is_kev && <span title="CISA KEV" className="inline-flex items-center gap-0.5 text-[8px] font-bold px-1 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30"><ShieldAlert className="h-3 w-3" />KEV</span>}
                          {item.exploit_available && <span title="Exploit available"><Zap className="h-3.5 w-3.5 text-amber-400" /></span>}
                          {item.patch_available && <span title="Patch available"><ShieldCheck className="h-3.5 w-3.5 text-green-400" /></span>}
                        </div>
                      </td>
                      <td className="px-3 py-2 hidden xl:table-cell">
                        <div className="flex gap-1 flex-wrap max-w-[140px]">
                          {(item.related_campaigns || []).slice(0, 2).map((c) => (
                            <span key={c.id} className="inline-flex items-center gap-0.5 text-[8px] px-1 py-0 rounded border border-red-500/30 text-red-300" title={c.campaign_name || c.actor_name}>
                              <Users className="h-2 w-2" />
                              {c.actor_name}
                            </span>
                          ))}
                          {(item.related_campaigns || []).length > 2 && (
                            <span className="text-[8px] text-muted-foreground/50">+{item.related_campaigns.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 hidden xl:table-cell">
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
                            {/* Col 1: Core Details */}
                            <div className="space-y-2">
                              <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Details</h4>
                              <div className="space-y-1">
                                <div className="flex justify-between"><span className="text-muted-foreground">Confidence</span><Badge variant="outline" className={cn("text-[9px] h-4 px-1.5 border", item.confidence === "high" ? "border-green-500/30 text-green-300" : item.confidence === "medium" ? "border-yellow-500/30 text-yellow-300" : "border-zinc-500/30 text-zinc-300")}>{item.confidence}</Badge></div>
                                {item.affected_versions && <div className="flex justify-between"><span className="text-muted-foreground">Affected Versions</span><span className="text-foreground text-right max-w-[180px] truncate" title={item.affected_versions}>{item.affected_versions}</span></div>}
                                <div className="flex justify-between"><span className="text-muted-foreground">First Seen</span><span>{formatPublishDate(item.first_seen)}</span></div>
                                <div className="flex justify-between"><span className="text-muted-foreground">Last Seen</span><span>{formatPublishDate(item.last_seen)}</span></div>
                                {item.epss_score != null && (
                                  <div>
                                    <span className="text-muted-foreground">EPSS Probability</span>
                                    <div className="mt-1 h-2 rounded-full bg-muted/30 overflow-hidden">
                                      <div className={cn("h-full rounded-full", item.epss_score >= 50 ? "bg-red-500" : item.epss_score >= 20 ? "bg-orange-500" : item.epss_score >= 5 ? "bg-yellow-500" : "bg-green-500")} style={{ width: `${Math.min(item.epss_score, 100)}%` }} />
                                    </div>
                                    <span className="text-[9px] text-muted-foreground/60">{item.epss_score.toFixed(2)}% chance of exploitation in next 30 days</span>
                                  </div>
                                )}
                              </div>
                            </div>
                            {/* Col 2: Sectors & Regions */}
                            <div className="space-y-2">
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
                              {(item.related_campaigns || []).length > 0 && (
                                <div>
                                  <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider mb-1">Linked Threat Actors</h4>
                                  <div className="flex gap-1 flex-wrap">{item.related_campaigns.map((c) => (
                                    <span key={c.id} className="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded border border-red-500/30 text-red-300"><Users className="h-2.5 w-2.5" />{c.actor_name}{c.campaign_name ? ` — ${c.campaign_name}` : ""}</span>
                                  ))}</div>
                                </div>
                              )}
                            </div>
                            {/* Col 3: Source Articles */}
                            <div className="space-y-2">
                              <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Source Articles ({(item.source_articles || []).length})</h4>
                              <div className="space-y-1 max-h-[160px] overflow-y-auto">
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
                                api.toggleFalsePositive("vulnerable-products", item.id, newVal).then(() => {
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
