"use client";

import React, { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { DollarSign, Activity, TrendingUp, TrendingDown } from "lucide-react";

type DayTotals = {
  input: number;
  output: number;
  calls: number;
  estimated_cost_usd: number;
};

type UsagePayload = {
  today: DayTotals;
  yesterday: DayTotals;
  window: DayTotals & { days: number };
  by_model: Record<string, { input: number; output: number; estimated_cost_usd: number }>;
  last_updated: string;
};

const POLL_INTERVAL_MS = 15_000;

function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function fmtCost(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  if (usd < 1) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}

function pctChange(today: number, yesterday: number): number | null {
  if (yesterday === 0) return today > 0 ? 100 : null;
  return Math.round(((today - yesterday) / yesterday) * 100);
}

export function AITokenUsageWidget() {
  const [data, setData] = useState<UsagePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const load = async () => {
    try {
      const resp = await fetch("/api/v1/ai-settings/token-usage?days=7", {
        credentials: "include",
        cache: "no-store",
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const body = await resp.json();
      if (!mountedRef.current) return;
      setData(body);
      setErr(null);
    } catch (e: any) {
      if (mountedRef.current) setErr(e?.message || "Failed to load usage");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  };

  useEffect(() => {
    mountedRef.current = true;
    load();
    const timer = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      mountedRef.current = false;
      clearInterval(timer);
    };
  }, []);

  const today = data?.today || { input: 0, output: 0, calls: 0, estimated_cost_usd: 0 };
  const yesterday = data?.yesterday || { input: 0, output: 0, calls: 0, estimated_cost_usd: 0 };
  const window = data?.window || { input: 0, output: 0, calls: 0, estimated_cost_usd: 0, days: 7 };

  const totalTokens = today.input + today.output;
  const yTotalTokens = yesterday.input + yesterday.output;
  const tokensTrend = pctChange(totalTokens, yTotalTokens);
  const callsTrend = pctChange(today.calls, yesterday.calls);

  const lastUpdated = data?.last_updated
    ? new Date(data.last_updated).toLocaleTimeString()
    : "—";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Activity className="h-4 w-4 text-emerald-400" />
          AI Token Usage
          <span className="text-[10px] font-normal text-muted-foreground">
            · live · updates every {POLL_INTERVAL_MS / 1000}s
          </span>
        </CardTitle>
        <span className="text-[10px] text-muted-foreground">
          {loading ? "refreshing…" : `last: ${lastUpdated}`}
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        {err && (
          <div className="text-xs text-red-400">{err}</div>
        )}

        {/* Top-line KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <KPI
            label="Today · tokens"
            value={fmtNum(totalTokens)}
            subValue={`${fmtNum(today.input)} in / ${fmtNum(today.output)} out`}
            trend={tokensTrend}
            color="text-emerald-400"
          />
          <KPI
            label="Today · calls"
            value={fmtNum(today.calls)}
            subValue={`${fmtCost(today.estimated_cost_usd)} est.`}
            trend={callsTrend}
            color="text-sky-400"
          />
          <KPI
            label="Yesterday"
            value={fmtNum(yTotalTokens)}
            subValue={`${fmtNum(yesterday.calls)} calls · ${fmtCost(yesterday.estimated_cost_usd)}`}
            color="text-slate-300"
          />
          <KPI
            label={`Last ${window.days}d`}
            value={fmtNum(window.input + window.output)}
            subValue={`${fmtNum(window.calls)} calls · ${fmtCost(window.estimated_cost_usd)}`}
            color="text-violet-300"
            icon={<DollarSign className="h-3 w-3" />}
          />
        </div>

        {/* Per-model breakdown */}
        <div>
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
            Today · by model
          </p>
          {Object.keys(data?.by_model || {}).length === 0 ? (
            <div className="text-xs text-muted-foreground py-1.5">
              No invocations today yet — trigger an IOC lookup or enrichment run to populate.
            </div>
          ) : (
            <div className="space-y-1">
              {Object.entries(data?.by_model || {})
                .sort((a, b) => (b[1].input + b[1].output) - (a[1].input + a[1].output))
                .map(([model, t]) => {
                  const tokens = t.input + t.output;
                  const pct = totalTokens > 0 ? Math.round((tokens / totalTokens) * 100) : 0;
                  return (
                    <div key={model} className="text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[11px] truncate flex-1">{model}</span>
                        <span className="text-muted-foreground shrink-0">
                          {fmtNum(tokens)} tok · {fmtCost(t.estimated_cost_usd)}
                        </span>
                      </div>
                      <div className="h-1 mt-1 bg-muted/40 rounded overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-violet-500 to-emerald-400"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function KPI({
  label,
  value,
  subValue,
  trend,
  color,
  icon,
}: {
  label: string;
  value: string;
  subValue: string;
  trend?: number | null;
  color?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="p-2.5 rounded-md border bg-muted/10 space-y-1">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
        {icon}
        {label}
      </div>
      <div className={cn("text-lg font-bold", color)}>{value}</div>
      <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
        <span className="truncate flex-1">{subValue}</span>
        {trend !== undefined && trend !== null && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 shrink-0",
              trend > 0 ? "text-emerald-400" : trend < 0 ? "text-red-400" : "text-slate-400"
            )}
          >
            {trend > 0 ? <TrendingUp className="h-2.5 w-2.5" /> : trend < 0 ? <TrendingDown className="h-2.5 w-2.5" /> : null}
            {trend > 0 ? "+" : ""}
            {trend}%
          </span>
        )}
      </div>
    </div>
  );
}
