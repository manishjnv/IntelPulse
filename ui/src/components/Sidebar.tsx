"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store";
import { IntelPulseLogo } from "@/components/IntelPulseLogo";
import {
  LayoutDashboard,
  Search,
  List,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Radio,
  Settings,
  BarChart3,
  Globe,
  Bug,
  Crosshair,
  Telescope,
  FileText,
  Bell,
  X,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  Newspaper,
  Briefcase,
  ShieldCheck,
  ScrollText,
} from "lucide-react";

const NAV_SECTIONS = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, color: "text-sky-400" },
      { href: "/threats", label: "Threat Feed", icon: AlertTriangle, color: "text-red-400" },
      { href: "/news", label: "Cyber News", icon: Newspaper, color: "text-amber-400" },
    ],
  },
  {
    label: "Investigation",
    items: [
      { href: "/intel", label: "Intel Items", icon: List, color: "text-cyan-400" },
      { href: "/cases", label: "Cases", icon: Briefcase, color: "text-purple-400" },
      { href: "/reports", label: "Reports", icon: FileText, color: "text-blue-400" },
      { href: "/investigate", label: "Investigate", icon: Telescope, color: "text-violet-400" },
      { href: "/techniques", label: "ATT&CK Map", icon: Crosshair, color: "text-rose-400" },
      { href: "/search", label: "IOC Search", icon: Search, color: "text-emerald-400" },
      { href: "/iocs", label: "IOC Database", icon: Bug, color: "text-orange-400" },
      { href: "/detections", label: "Detection Rules", icon: ShieldCheck, color: "text-green-400" },
      { href: "/briefings", label: "Threat Briefings", icon: ScrollText, color: "text-yellow-400" },
    ],
  },
  {
    label: "Analytics",
    items: [
      { href: "/analytics", label: "Analytics", icon: BarChart3, color: "text-pink-400" },
      { href: "/geo", label: "Geo View", icon: Globe, color: "text-teal-400" },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/feeds", label: "Feed Status", icon: Radio, color: "text-emerald-400" },
      { href: "/notifications", label: "Notifications", icon: Bell, color: "text-fuchsia-400" },
      { href: "/settings", label: "Settings", icon: Settings, color: "text-slate-300" },
    ],
  },
];

/* ── Desktop Sidebar ─────────────────────────────────── */
function DesktopSidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useAppStore();

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col border-r border-border/50 bg-sidebar transition-all duration-300 ease-in-out shrink-0 relative group/sidebar",
        sidebarOpen ? "w-48" : "w-[52px]"
      )}
    >
      {/* Logo */}
      <Link href="/dashboard" className="flex h-14 items-center border-b border-border/50 px-2.5 gap-2 shrink-0 hover:bg-accent/30 transition-colors">
        <div className="flex h-8 w-8 items-center justify-center shrink-0">
          <IntelPulseLogo />
        </div>
        {sidebarOpen && (
          <div className="flex flex-col flex-1 min-w-0">
            <span className="text-sm font-bold tracking-tight leading-none">IntelPulse</span>
            <span className="text-[10px] text-muted-foreground leading-none mt-0.5">Enterprise Threat Intelligence Platform</span>
          </div>
        )}
      </Link>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-3">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            {sidebarOpen && (
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/90 px-2 mb-1">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active =
                  pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={!sidebarOpen ? item.label : undefined}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-1.5 text-[12px] font-medium transition-all duration-150",
                      !sidebarOpen && "justify-center px-0",
                      active
                        ? "bg-primary/10 text-primary shadow-sm"
                        : "text-foreground/85 hover:bg-accent/50 hover:text-foreground"
                    )}
                  >
                    <Icon className={cn("h-4 w-4 shrink-0", active ? "text-primary" : item.color)} />
                    {sidebarOpen && <span className="truncate">{item.label}</span>}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom collapse/expand bar */}
      <div className="border-t border-border/50 px-2 py-1.5">
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center justify-center gap-2 rounded-md px-2 py-1.5 text-[12px] font-medium text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
          title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
        >
          {sidebarOpen ? (
            <>
              <PanelLeftClose className="h-4 w-4" />
              <span>Collapse</span>
            </>
          ) : (
            <PanelLeftOpen className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Floating toggle pill — always visible, highlighted */}
      <button
        onClick={toggleSidebar}
        className={cn(
          "absolute -right-3 top-[60px] z-30",
          "w-6 h-6 rounded-full",
          "bg-primary/20 border border-primary/50 shadow-lg shadow-primary/20",
          "flex items-center justify-center",
          "text-primary hover:text-primary-foreground hover:bg-primary hover:border-primary",
          "transition-all duration-200",
          "hover:scale-110",
          "animate-pulse hover:animate-none"
        )}
        title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
        aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
      >
        {sidebarOpen ? (
          <ChevronLeft className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>
    </aside>
  );
}

/* ── Mobile Sidebar (Drawer) ──────────────────────────── */
function MobileSidebar() {
  const pathname = usePathname();
  const { mobileSidebarOpen, setMobileSidebarOpen } = useAppStore();

  // Close on route change
  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname, setMobileSidebarOpen]);

  // Lock body scroll when open
  useEffect(() => {
    if (mobileSidebarOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [mobileSidebarOpen]);

  return (
    <>
      {/* Backdrop */}
      {mobileSidebarOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Drawer */}
      <aside
        className={cn(
          "md:hidden fixed inset-y-0 left-0 z-50 w-72 bg-sidebar border-r border-border/50",
          "flex flex-col shadow-2xl",
          "transition-transform duration-300 ease-in-out",
          mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex h-14 items-center border-b border-border/50 px-4 justify-between">
          <Link href="/dashboard" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="flex h-8 w-8 items-center justify-center shrink-0">
              <IntelPulseLogo />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight leading-none">IntelPulse</span>
              <span className="text-[10px] text-muted-foreground leading-none mt-0.5">Enterprise Threat Intelligence Platform</span>
            </div>
          </Link>
          <button
            onClick={() => setMobileSidebarOpen(false)}
            className="p-2 rounded-lg hover:bg-accent/50 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-5">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label}>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/90 px-2 mb-1.5">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active =
                    pathname === item.href || pathname?.startsWith(item.href + "/");
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                        active
                          ? "bg-primary/10 text-primary shadow-sm"
                          : "text-foreground/85 hover:bg-accent/50 hover:text-foreground active:bg-accent"
                      )}
                    >
                      <Icon className={cn("h-4.5 w-4.5 shrink-0", active ? "text-primary" : item.color)} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

      </aside>
    </>
  );
}

/* ── Hamburger Button (exported for header use) ──────── */
export function MobileMenuButton() {
  const { setMobileSidebarOpen } = useAppStore();
  return (
    <button
      onClick={() => setMobileSidebarOpen(true)}
      className="md:hidden p-2 -ml-1 rounded-lg hover:bg-accent/50 text-muted-foreground hover:text-foreground transition-colors"
      aria-label="Open menu"
    >
      <Menu className="h-5 w-5" />
    </button>
  );
}

/* ── Combined Sidebar ─────────────────────────────────── */
export function Sidebar() {
  return (
    <>
      <DesktopSidebar />
      <MobileSidebar />
    </>
  );
}
