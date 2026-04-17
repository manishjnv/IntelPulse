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
  Cloud,
  Workflow,
  Target,
  CheckCircle2,
} from "lucide-react";

export type PageKey =
  | "dashboard"
  | "threats"
  | "news"
  | "intel"
  | "cases"
  | "reports"
  | "investigate"
  | "techniques"
  | "search"
  | "iocs"
  | "detections"
  | "briefings"
  | "analytics"
  | "geo"
  | "feeds"
  | "notifications"
  | "settings";

type PageGuide = {
  title: string;
  purpose: string;
  howToUse: string[];
};

const PAGE_GUIDES: Record<PageKey, PageGuide> = {
  dashboard: {
    title: "Threat Intelligence Dashboard",
    purpose:
      "Real-time overview of every intel item, risk trend, top CVE and active campaign — your daily starting point.",
    howToUse: [
      "Click any KPI card to drill into the filtered threat list.",
      "Hover charts for per-severity and per-feed breakdowns.",
      "Use the ranked lists to jump into a CVE, actor or vendor.",
    ],
  },
  threats: {
    title: "Active Threats",
    purpose:
      "Searchable, filterable feed of every ingested threat item — vulnerabilities, IOCs, malware, actors, campaigns.",
    howToUse: [
      "Toggle KEV Only / Exploitable for actively-weaponised items.",
      "Filter by severity, feed type or asset; sort by risk or date.",
      "Export the current filter to Excel with the Download button.",
    ],
  },
  news: {
    title: "Cyber News",
    purpose:
      "Structured cyber-news feed with AI-extracted CVEs, IOCs, threat actors and campaigns.",
    howToUse: [
      "Switch tabs: Cyber News Feed / Vulnerable Products / Threat Actors.",
      "Open the reading pane for the AI brief, risk assessment and IOCs.",
      "Use Hunt to pivot into IOC search, Investigate for the graph view.",
    ],
  },
  intel: {
    title: "Intel Items",
    purpose:
      "Raw list of every ingested intelligence item — ideal for reviewing what the pipeline has produced.",
    howToUse: [
      "Filter by feed type, severity or source.",
      "Click an item to see its enriched detail page.",
      "Use Relate to find items sharing CVEs or IOCs.",
    ],
  },
  cases: {
    title: "Cases",
    purpose:
      "Investigation workspaces — bundle intel items, IOCs and notes around a single incident or campaign.",
    howToUse: [
      "Create a case, then attach intel items from Threats or News.",
      "Add notes and findings; each case tracks its timeline.",
      "Export case content into a report when ready.",
    ],
  },
  reports: {
    title: "Reports",
    purpose:
      "Executive and technical threat reports generated from enriched intel and open cases.",
    howToUse: [
      "Pick a template (exec brief / technical / IOC dump) and select sources.",
      "Preview the draft, edit freely, then publish.",
      "Download as Markdown, PDF or JSON for downstream tools.",
    ],
  },
  investigate: {
    title: "Investigate",
    purpose:
      "Graph-based explorer that connects intel items, IOCs, actors and campaigns through shared relationships.",
    howToUse: [
      "Search an IOC, CVE or actor to seed the graph.",
      "Expand neighbours to pivot across data types.",
      "Pin nodes of interest and send them to a case.",
    ],
  },
  techniques: {
    title: "ATT&CK Matrix",
    purpose:
      "MITRE ATT&CK tactics and techniques mapped to the threat activity you have ingested.",
    howToUse: [
      "Heat-mapped cells show which techniques appear most in your feed.",
      "Click a technique to see linked intel items and detections.",
      "Use this to prioritise detection engineering work.",
    ],
  },
  search: {
    title: "IOC Search",
    purpose:
      "Unified lookup across the local IOC database plus live internet sources (VirusTotal, OSINT).",
    howToUse: [
      "Paste a CVE, hash, IP, domain or URL.",
      "See on-platform matches first, then internet enrichment.",
      "Pivot any result into Investigate or attach it to a case.",
    ],
  },
  iocs: {
    title: "IOC Database",
    purpose:
      "All IOCs the pipeline has extracted — with first-seen / last-seen, source count and reputation.",
    howToUse: [
      "Filter by IOC type, TLP or confidence.",
      "Sort by freshness or source count to find the hot IOCs.",
      "Export the current view for your SIEM or EDR.",
    ],
  },
  detections: {
    title: "Detection Rules",
    purpose:
      "Library of Sigma / YARA detection rules aligned to observed threats and techniques.",
    howToUse: [
      "Filter by ATT&CK technique, severity or rule format.",
      "Copy a rule directly into your SIEM or EDR.",
      "Linked intel items show why the rule exists.",
    ],
  },
  briefings: {
    title: "Threat Briefings",
    purpose:
      "Auto-generated narrative briefings stitched together from the day's top intel — human-readable summaries.",
    howToUse: [
      "Open a briefing to read the narrative, key IOCs and recommended actions.",
      "Share the briefing link with stakeholders.",
      "Use 'Export' to archive as PDF or Markdown.",
    ],
  },
  analytics: {
    title: "Analytics",
    purpose:
      "Deep-dive charts on feed velocity, severity trends, actor activity and enrichment coverage.",
    howToUse: [
      "Pick a time range at the top-right to re-scope every chart.",
      "Click a chart series for the underlying item list.",
      "Export any chart as PNG or the data as CSV.",
    ],
  },
  geo: {
    title: "Geographic View",
    purpose:
      "World map of observed threat activity by region, sector and threat actor origin.",
    howToUse: [
      "Hover a country for per-severity and per-feed breakdown.",
      "Click a region to filter the threat list to that geography.",
      "Use the layer toggle to switch between attack origin and target.",
    ],
  },
  feeds: {
    title: "Feed Status",
    purpose:
      "Health monitor for every ingest source — green = fresh, red = failing.",
    howToUse: [
      "Scan the grid for any red / yellow source tiles.",
      "Click a source for last success, last error and item count.",
      "Use this when the feed looks stale — it usually tells you why.",
    ],
  },
  notifications: {
    title: "Notifications",
    purpose:
      "Alerts raised when high-risk items land (critical severity, KEV, IOCs matching your watchlist).",
    howToUse: [
      "Mark read or dismiss to keep the queue clean.",
      "Click through to the originating intel item.",
      "Tune what triggers an alert in Settings → Notifications.",
    ],
  },
  settings: {
    title: "Settings",
    purpose:
      "Configure your profile, AI model routing, API keys, feeds and notification rules.",
    howToUse: [
      "Edit values in place, then click Save at the bottom of each section.",
      "AI Model: switch between Bedrock agents and direct models.",
      "Feeds: enable / disable sources and tune polling intervals.",
    ],
  },
};

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
      "RSS feeds, CISA KEV, NVD, vendor advisories, threat-actor reports and OSINT blogs are polled on a schedule.",
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
      "Amazon Bedrock agents specialise — one classifies & summarises, one correlates IOCs with VirusTotal, one builds attack narratives — then hand results to each other.",
  },
  {
    icon: ShieldAlert,
    label: "Score & Alert",
    color: "text-rose-300",
    bg: "bg-rose-500/15",
    border: "border-rose-500/30",
    short: "Risk-scored + KEV flagged",
    detail:
      "A weighted risk engine (severity, exploit availability, KEV listing, freshness, reliability) ranks each item and drives the alerts you see here.",
  },
];

export function HowItWorks({
  page,
  className,
  defaultOpen = false,
}: {
  page: PageKey;
  className?: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const guide = PAGE_GUIDES[page];

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
        aria-label={`About ${guide.title}`}
      >
        <div className="flex items-center gap-1.5 shrink-0">
          <Info className="h-3.5 w-3.5 text-primary/80" />
          <span className="text-[11px] font-semibold text-foreground/90 hidden sm:inline">
            About {guide.title}
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
          <span className="hidden md:inline">AWS Bedrock</span>
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
        <div className="border-t border-border/40 bg-background/40 px-3 py-3 space-y-3">
          {/* Purpose + How to use — side by side on wider screens */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <div className="rounded-md border border-primary/30 bg-primary/5 p-2.5">
              <div className="flex items-center gap-1.5 mb-1">
                <Target className="h-3.5 w-3.5 text-primary" />
                <span className="text-[11px] font-semibold text-primary">
                  Purpose
                </span>
              </div>
              <p className="text-[11px] text-foreground/90 leading-relaxed">
                {guide.purpose}
              </p>
            </div>

            <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-2.5">
              <div className="flex items-center gap-1.5 mb-1">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-[11px] font-semibold text-emerald-300">
                  How to use this page
                </span>
              </div>
              <ul className="space-y-0.5">
                {guide.howToUse.map((tip, i) => (
                  <li
                    key={i}
                    className="text-[11px] text-foreground/85 leading-relaxed flex items-start gap-1.5"
                  >
                    <span className="text-emerald-400/70 shrink-0 mt-0.5">
                      •
                    </span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Pipeline stages */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Workflow className="h-3.5 w-3.5 text-violet-300" />
              <span className="text-[11px] font-semibold text-violet-200">
                How IntelPulse processes data
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
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
                      <span
                        className={cn("text-[11px] font-semibold", s.color)}
                      >
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
            </div>
          </div>

          {/* AWS / Multi-agent detail */}
          <div className="rounded-md border border-orange-500/25 bg-orange-500/5 p-2.5">
            <div className="flex items-center gap-1.5 mb-1">
              <Cloud className="h-3.5 w-3.5 text-orange-400" />
              <span className="text-[11px] font-semibold text-orange-300">
                AWS-powered multi-agent AI
              </span>
            </div>
            <p className="text-[11px] text-foreground/85 leading-relaxed">
              Enrichment runs on{" "}
              <span className="font-semibold text-orange-300">
                Amazon Bedrock
              </span>{" "}
              with three specialist agents coordinated by a supervisor:
            </p>
            <ul className="mt-1 space-y-0.5">
              <li className="text-[10px] text-foreground/85 leading-relaxed flex items-start gap-1.5">
                <span className="text-orange-400/80 shrink-0 mt-0.5">•</span>
                <span>
                  <span className="font-semibold">Classifier / Summariser</span>{" "}
                  — tags category, extracts CVEs, produces the executive brief.
                </span>
              </li>
              <li className="text-[10px] text-foreground/85 leading-relaxed flex items-start gap-1.5">
                <span className="text-orange-400/80 shrink-0 mt-0.5">•</span>
                <span>
                  <span className="font-semibold">IOC Correlator</span> —
                  validates indicators against VirusTotal and clusters related
                  IOCs.
                </span>
              </li>
              <li className="text-[10px] text-foreground/85 leading-relaxed flex items-start gap-1.5">
                <span className="text-orange-400/80 shrink-0 mt-0.5">•</span>
                <span>
                  <span className="font-semibold">Narrative Builder</span> —
                  writes the attack narrative, risk assessment and detection
                  opportunities.
                </span>
              </li>
            </ul>
            <p className="text-[10px] text-muted-foreground/90 leading-relaxed mt-1.5">
              <span className="font-semibold text-foreground/90">Privacy:</span>{" "}
              IntelPulse only processes public threat-intel sources. No account
              data or private files are sent to AI models. Results are cached
              for fast page loads.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
