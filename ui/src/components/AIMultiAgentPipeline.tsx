"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Workflow, Bot, Zap, ArrowRight, AlertCircle, RefreshCw } from "lucide-react";

type RoutingRow = {
  feature: string;
  path: string;
  model: string;
  flag: string | null;
  flag_value: boolean | null;
};

type AgentRow = {
  name: string;
  role?: string;
  agent_id: string;
  alias_id?: string;
  alias_name?: string;
  status: string;
  collaborators?: number;
  action_groups?: number;
  error?: string;
};

type ActionGroup = { name: string; state: string; agent: string };

type PipelinePayload = {
  routing: RoutingRow[];
  agents: AgentRow[];
  action_groups: ActionGroup[];
  region: string;
  primary_model: string;
};

const statusTone = (s: string): string => {
  const up = (s || "").toUpperCase();
  if (up === "PREPARED" || up === "ENABLED") return "text-emerald-400 border-emerald-400/40 bg-emerald-500/10";
  if (up === "UNREACHABLE" || up === "FAILED") return "text-red-400 border-red-400/40 bg-red-500/10";
  if (up === "PREPARING" || up === "CREATING") return "text-amber-400 border-amber-400/40 bg-amber-500/10";
  return "text-slate-300 border-slate-400/30 bg-slate-500/10";
};

const pathTone = (path: string): string => {
  if (path.startsWith("agent")) return "text-violet-300 border-violet-400/40 bg-violet-500/10";
  return "text-sky-300 border-sky-400/40 bg-sky-500/10";
};

export function AIMultiAgentPipeline() {
  const [data, setData] = useState<PipelinePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setErr(null);
    try {
      const resp = await fetch("/api/v1/ai-settings/pipeline", { credentials: "include" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setData(await resp.json());
    } catch (e: any) {
      setErr(e?.message || "Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Workflow className="h-4 w-4 text-violet-400" />
          Multi-Agent Pipeline
        </CardTitle>
        <button
          onClick={load}
          disabled={loading}
          className="p-1 rounded hover:bg-muted/40 transition-colors text-muted-foreground"
          title="Refresh"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
        </button>
      </CardHeader>
      <CardContent className="space-y-4">
        {err && (
          <div className="flex items-center gap-2 text-xs text-red-400">
            <AlertCircle className="h-3.5 w-3.5" /> {err}
          </div>
        )}

        {/* Routing */}
        <div>
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
            Feature → Path
          </p>
          <div className="space-y-1">
            {(data?.routing || []).map((r) => (
              <div
                key={r.feature}
                className="flex items-center gap-2 text-xs py-1.5 px-2 rounded-md hover:bg-muted/20"
              >
                <span className="w-40 shrink-0 font-medium truncate">{r.feature}</span>
                <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                <Badge variant="outline" className={cn("text-[10px]", pathTone(r.path))}>
                  {r.path}
                </Badge>
                <span className="text-[10px] text-muted-foreground truncate flex-1">
                  {r.model}
                </span>
                {r.flag && (
                  <code className="text-[9px] text-muted-foreground/70 px-1 py-0.5 rounded bg-muted/40">
                    {r.flag}={String(r.flag_value)}
                  </code>
                )}
              </div>
            ))}
            {!data && loading && (
              <div className="text-xs text-muted-foreground py-2">Loading routing…</div>
            )}
          </div>
        </div>

        {/* Agents */}
        <div>
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
            Agent Catalog ({data?.region || "—"})
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {(data?.agents || []).map((a, i) => (
              <div
                key={`${a.agent_id}-${i}`}
                className="p-2.5 rounded-md border bg-muted/10 space-y-1"
              >
                <div className="flex items-center gap-1.5">
                  <Bot className="h-3 w-3 text-violet-400 shrink-0" />
                  <span className="text-xs font-semibold truncate">{a.name}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Badge variant="outline" className={cn("text-[9px]", statusTone(a.status))}>
                    {a.status}
                  </Badge>
                  {a.collaborators !== undefined && a.collaborators > 0 && (
                    <span className="text-[9px] text-muted-foreground">
                      {a.collaborators} collabs
                    </span>
                  )}
                  {a.action_groups !== undefined && a.action_groups > 0 && (
                    <span className="text-[9px] text-muted-foreground">
                      {a.action_groups} action groups
                    </span>
                  )}
                </div>
                <div className="text-[9px] text-muted-foreground/70 font-mono truncate">
                  {a.agent_id}
                  {a.alias_name ? ` · ${a.alias_name}` : ""}
                </div>
                {a.error && (
                  <div className="text-[9px] text-red-400 truncate" title={a.error}>
                    {a.error}
                  </div>
                )}
              </div>
            ))}
            {!data && loading && (
              <div className="text-xs text-muted-foreground col-span-3 py-2">
                Loading agents…
              </div>
            )}
          </div>
        </div>

        {/* Action groups */}
        {data?.action_groups && data.action_groups.length > 0 && (
          <div>
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
              Action Groups
            </p>
            <div className="flex flex-wrap gap-1.5">
              {data.action_groups.map((ag, i) => (
                <Badge
                  key={`${ag.name}-${i}`}
                  variant="outline"
                  className={cn("text-[10px] gap-1", statusTone(ag.state))}
                >
                  <Zap className="h-2.5 w-2.5" />
                  {ag.name}
                  <span className="text-muted-foreground">· {ag.agent}</span>
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
