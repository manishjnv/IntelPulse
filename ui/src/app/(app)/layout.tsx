"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store";
import { AuthGuard } from "@/components/AuthGuard";
import { Sidebar, MobileMenuButton } from "@/components/Sidebar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { NotificationBell } from "@/components/NotificationBell";
import { HeaderStatusBar } from "@/components/HeaderStatusBar";
import { ToastProvider } from "@/components/Toast";
import { Search, Moon, Sun } from "lucide-react";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { fetchUser } = useAppStore();
  const router = useRouter();
  const searchRef = useRef<HTMLInputElement>(null);
  const [darkMode, setDarkMode] = useState(true);
  const [headerQuery, setHeaderQuery] = useState("");

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // ⌘K / Ctrl+K → focus header search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Header search → navigate to /search?q=...
  const handleHeaderSearch = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && headerQuery.trim()) {
        router.push(`/search?q=${encodeURIComponent(headerQuery.trim())}`);
        setHeaderQuery("");
        searchRef.current?.blur();
      }
    },
    [headerQuery, router]
  );

  // Theme toggle
  const toggleTheme = useCallback(() => {
    const next = !darkMode;
    setDarkMode(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }, [darkMode]);

  // Restore saved theme
  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const preferDark = saved ? saved === "dark" : true;
    setDarkMode(preferDark);
    document.documentElement.classList.toggle("dark", preferDark);
  }, []);


  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top header bar */}
          <header className="h-12 shrink-0 border-b border-gray-200/60 dark:border-border/40 bg-white/80 dark:bg-card/80 backdrop-blur-sm flex items-center gap-3 px-3 md:gap-4 md:px-4 lg:px-6">
          {/* Mobile hamburger */}
          <MobileMenuButton />

          {/* Left: search */}
          <div className="flex items-center gap-3 shrink-0 flex-1 md:flex-none">
            <div className="relative w-full md:w-64 lg:w-72">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 dark:text-muted-foreground" />
              <input
                ref={searchRef}
                type="text"
                value={headerQuery}
                onChange={(e) => setHeaderQuery(e.target.value)}
                onKeyDown={handleHeaderSearch}
                placeholder="Search threats, IOCs, CVEs..."
                className="w-full h-8 pl-8 pr-3 rounded-lg bg-gray-100/80 dark:bg-muted/30 border border-gray-200/60 dark:border-border/40 text-xs text-gray-900 dark:text-foreground placeholder:text-gray-400 dark:placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50 focus:bg-white dark:focus:bg-muted/50 transition-colors"
              />
              <kbd className="hidden sm:block absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] text-gray-400 dark:text-muted-foreground/40 border border-gray-200/40 dark:border-border/30 rounded px-1 py-0.5">
                ⌘K
              </kbd>
            </div>
          </div>

          {/* Center: status bar */}
          <div className="hidden md:flex items-center flex-1 justify-center overflow-hidden">
            <HeaderStatusBar />
          </div>
          <div className="flex-1 md:hidden" />

          {/* Right: actions */}
          <div className="flex items-center gap-2">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-muted/40 transition-colors text-gray-500 dark:text-muted-foreground"
              title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
            >
              {darkMode ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </button>

            {/* Notifications */}
            <NotificationBell />
          </div>
        </header>

        {/* Mobile status bar — compact scrollable strip below header */}
        <div className="md:hidden shrink-0 border-b border-gray-200/40 dark:border-border/30 bg-white/60 dark:bg-card/60 backdrop-blur-sm px-3 py-1.5 overflow-x-auto scrollbar-none">
          <HeaderStatusBar />
        </div>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <ToastProvider>
            <ErrorBoundary>{children}</ErrorBoundary>
          </ToastProvider>
        </main>
      </div>
    </div>
    </AuthGuard>
  );
}
