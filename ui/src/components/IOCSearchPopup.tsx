"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { X, Search, ExternalLink, Loader2, AlertTriangle, Shield, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import * as api from "@/lib/api";
import type { LiveLookupResponse, LiveLookupResult
} from "@/lib/api";

/* ── IOC Search Popup ─────────────────────────────────────
   Opens as a modal overlay when users click a highlighted
   keyword (CVE, IP, hash, TA, etc.) in the news detail page.
   Uses the live-lookup API for cross-source IOC intelligence.
   ─────────────────────────────────────────────────────── */

interface IOCSearchPopupProps {
  keyword: string;
  onClose: () => void;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-400 border-red-500/30 bg-red-500/10",
  high: "text-orange-400 border-orange-500/30 bg-orange-500/10",
  medium: "text-yellow-400 border-yellow-500/30 bg-yellow-500/10",
  low: "text-green-400 border-green-500/30 bg-green-500/10",
  info: "text-blue-400 border-blue-500/30 bg-blue-500/10",
};

function severityClass(sev: string): string {
  return SEVERITY_COLORS[sev?.toLowerCase()] || SEVERITY_COLORS.info;
}

export default function IOCSearchPopup({ keyword, onClose }: IOCSearchPopupProps) {
  const [query, setQuery] = useState(keyword);
  const [data, setData] = useState<LiveLookupResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.liveLookup(q.trim());
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-search the keyword on mount
  useEffect(() => {
    doSearch(keyword);
    // Focus input after mount
    setTimeout(() => inputRef.current?.select(), 100);
  }, [keyword, doSearch]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Close on backdrop click
  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doSearch(query);
  };

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdrop}
      className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
    >
      <div className="w-full max-w-2xl mx-4 bg-[#0c0c14] border border-border/50 rounded-xl shadow-2xl overflow-hidden animate-in slide-in-from-top-4 duration-200">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border/30 bg-accent/5">
          <Shield className="h-4 w-4 text-primary shrink-0" />
          <span className="text-sm font-semibold flex-1">IOC Intelligence Lookup</span>
          <button
            onClick={onClose}
            className="h-6 w-6 rounded-md flex items-center justify-center hover:bg-accent/20 transition-colors text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search bar */}
        <form onSubmit={handleSubmit} className="px-4 py-3 border-b border-border/20">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search IOC, CVE, IP, hash, threat actor…"
              className="w-full pl-9 pr-4 py-2 text-sm bg-background/50 border border-border/30 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary/40 placeholder:text-muted-foreground/40"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-medium px-2.5 py-1 rounded-md bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 disabled:opacity-40 transition-colors"
            >
              {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : "Search"}
            </button>
          </div>
        </form>

        {/* Body */}
        <div className="max-h-[60vh] overflow-y-auto px-4 py-3 space-y-3">
          {loading && !data && (
            <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              Querying intelligence sources…
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 py-6 justify-center text-red-400 text-sm">
              <AlertTriangle className="h-4 w-4" /> {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Meta */}
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground/60">
                <span>Query: <span className="text-foreground/80 font-medium">{data.query}</span></span>
                {data.detected_type && (
                  <>
                    <span className="text-muted-foreground/20">•</span>
                    <span>Type: <span className="text-primary font-medium">{data.detected_type}</span></span>
                  </>
                )}
                <span className="text-muted-foreground/20">•</span>
                <span>{data.results.length} results from {data.sources_queried.length} sources</span>
              </div>

              {/* AI Summary */}
              {data.ai_summary && (
                <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-indigo-400 font-semibold mb-1">AI Summary</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{data.ai_summary}</p>
                </div>
              )}

              {/* AI Analysis */}
              {data.ai_analysis && (
                <div className="space-y-2">
                  {data.ai_analysis.key_findings?.length > 0 && (
                    <div className="rounded-lg border border-border/30 bg-accent/5 p-3">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-semibold mb-1.5">Key Findings</p>
                      <ul className="space-y-1">
                        {data.ai_analysis.key_findings.map((f, i) => (
                          <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                            <ChevronRight className="h-3 w-3 shrink-0 mt-0.5 text-primary/60" />
                            {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {data.ai_analysis.fix_remediation && (
                    <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-2.5">
                      <p className="text-[10px] uppercase tracking-wider text-green-400 font-semibold mb-1">Remediation</p>
                      <p className="text-xs text-muted-foreground">{data.ai_analysis.fix_remediation}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Results list */}
              {data.results.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-semibold">Results</p>
                  {data.results.map((r: LiveLookupResult, i: number) => (
                    <div key={i} className="rounded-lg border border-border/30 bg-accent/5 p-3 hover:border-border/60 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground/90 truncate">{r.title}</p>
                          <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                            {r.source} &nbsp;|&nbsp; {r.type}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {r.severity && (
                            <span className={cn("text-[9px] font-semibold px-1.5 py-0.5 rounded border", severityClass(r.severity))}>
                              {r.severity.toUpperCase()}
                            </span>
                          )}
                          {r.risk_score > 0 && (
                            <span className="text-[9px] font-mono text-muted-foreground">{r.risk_score}</span>
                          )}
                        </div>
                      </div>
                      {r.description && (
                        <p className="text-[11px] text-muted-foreground mt-1.5 line-clamp-2 leading-relaxed">{r.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground/60 text-sm">
                  No IOC results found for &ldquo;{data.query}&rdquo;
                </div>
              )}

              {/* Errors */}
              {data.errors?.length > 0 && (
                <div className="text-[10px] text-muted-foreground/40 space-y-0.5 pt-2 border-t border-border/20">
                  {data.errors.map((e, i) => <p key={i}>⚠ {e}</p>)}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer (permalink) */}
        <div className="px-4 py-2.5 border-t border-border/20 flex items-center justify-between text-[10px] text-muted-foreground/50">
          <span>Press <kbd className="px-1 py-0.5 rounded border border-border/30 text-[9px]">Esc</kbd> to close</span>
          <a
            href={`/search?q=${encodeURIComponent(query)}`}
            className="flex items-center gap-1 text-primary/60 hover:text-primary transition-colors"
          >
            Open in full search <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
