"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import {
  Rss,
  Puzzle,
  Cpu,
  ShieldAlert,
  ChevronDown,
  Info,
  Sparkles,
} from "lucide-react";

type Context = "dashboard" | "threats" | "news";

type Step = {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  bg: string;
  border: string;
  short: string;
  detail: string;
};

const STEPS_BASE: Step[] = [
  {
    icon: Rss,
    label: "Ingest",
    color: "text-sky-300",
    bg: "bg-sky-500/15",
    border: "border-sky-500/30",
    short: "Pull from 100+ sources",
    detail:
      "RSS feeds, CISA KEV, NVD, vendor advisories, threat-actor reports and OSINT blogs are polled every few minutes.",
  },
  {
    icon: Puzzle,
    label: "Extract",
    color: "text-amber-300",
    bg: "bg-amber-500/15",
    border: "border-amber-500/30",
    short: "Parse CVEs, IOCs, TTPs",
    detail:
      "Regex + structured parsers lift CVE IDs, domains, IPs, hashes, affected products and MITRE ATT&CK techniques out of every article.",
  },
  {
    icon: Cpu,
    label: "AI Agents",
    color: "text-violet-300",
    bg: "bg-violet-500/15",
    border: "border-violet-500/30",
    short: "Multi-agent enrichment",
    detail:
      "Bedrock agents specialise — one classifies & summarises, one correlates IOCs with VirusTotal, one builds attack narratives — then hand results to each other.",
  },
  {
    icon: ShieldAlert,
    label: "Score & Alert",
    color: "text-rose-300",
    bg: "bg-rose-500/15",
    border: "border-rose-500/30",
    short: "Risk-scored + KEV flagged",
    detail:
      "A weighted risk engine (severity, exploit availability, KEV listing, freshness, reliability) ranks each item and feeds alerts you see here.",
  },
];

const CONTEXT_TITLE: Record<Context, string> = {
  dashboard: "How IntelPulse builds this dashboard",
  threats: "How threats reach this feed",
  news: "How news articles are enriched",
};

export function HowItWorks({
  context,
  className,
  defaultOpen = false,
}: {
  context: Context;
  className?: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        "rounded-lg border border-border/50 bg-card/40 overflow-hidden",
        className,
      )}
    >
      {/* Collapsed strip */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-accent/20 transition-colors"
        aria-expanded={open}
        aria-label={CONTEXT_TITLE[context]}
      >
        <div className="flex items-center gap-1.5 shrink-0">
          <Info className="h-3.5 w-3.5 text-primary/80" />
          <span className="text-[11px] font-semibold text-foreground/90 hidden sm:inline">
            {CONTEXT_TITLE[context]}
          </span>
          <span className="text-[11px] font-semibold text-foreground/90 sm:hidden">
            How it works
          </span>
        </div>

        <div className="flex items-center gap-0 sm:gap-1 flex-1 min-w-0 overflow-x-auto scrollbar-none">
          {STEPS_BASE.map((s, i) => {
            const Icon = s.icon;
            return (
              <React.Fragment key={s.label}>
                {i > 0 && (
                  <span
                    aria-hidden
                    className="text-muted-foreground/50 text-[10px] px-0.5 shrink-0"
                  >
                    →
                  </span>
                )}
                <span
                  className={cn(
                    "flex items-center gap-1 px-1.5 py-0.5 rounded border shrink-0",
                    s.bg,
                    s.border,
                  )}
                >
                  <Icon className={cn("h-3 w-3", s.color)} />
                  <span className={cn("text-[10px] font-medium", s.color)}>
                    {s.label}
                  </span>
                </span>
              </React.Fragment>
            );
          })}
        </div>

        <span className="flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
          <Sparkles className="h-3 w-3 text-yellow-400/80" />
          <span className="hidden md:inline">AI-assisted</span>
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 transition-transform",
              open && "rotate-180",
            )}
          />
        </span>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-border/40 bg-background/40 px-3 py-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {STEPS_BASE.map((s, i) => {
            const Icon = s.icon;
            return (
              <div
                key={s.label}
                className={cn(
                  "rounded-md border p-2.5 bg-card/40",
                  s.border,
                )}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span
                    className={cn(
                      "h-5 w-5 rounded flex items-center justify-center",
                      s.bg,
                    )}
                  >
                    <Icon className={cn("h-3 w-3", s.color)} />
                  </span>
                  <span className={cn("text-[11px] font-semibold", s.color)}>
                    {i + 1}. {s.label}
                  </span>
                </div>
                <p className="text-[10px] font-medium text-foreground/90 leading-snug">
                  {s.short}
                </p>
                <p className="text-[10px] text-muted-foreground leading-relaxed mt-1">
                  {s.detail}
                </p>
              </div>
            );
          })}
          <p className="sm:col-span-2 lg:col-span-4 text-[10px] text-muted-foreground/90 leading-relaxed pt-1">
            <span className="font-semibold text-foreground/90">Privacy:</span>{" "}
            IntelPulse only processes public threat-intel sources. No account
            data or private files are sent to AI models. Agents run on Amazon
            Bedrock with results cached for fast page loads.
          </p>
        </div>
      )}
    </div>
  );
}
