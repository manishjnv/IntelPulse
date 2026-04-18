import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { DemoBanner } from "@/components/DemoBanner";
import { WebVitalsReporter } from "@/components/WebVitalsReporter";

// `display: "swap"` shows fallback text immediately and swaps to Inter when
// the font loads — avoids flash-of-invisible-text on cold loads. `preload`
// is Next's default; keeping explicit for clarity.
const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "IntelPulse - Enterprise Threat Intelligence Platform",
  description: "IntelPulse — Threat Intelligence Platform with live feeds, IOC search, risk scoring",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        {/* Only third-party host in the UI — warm DNS + TLS so first flag
            image fetch (geo/iocs/intel pages) saves ~100-200ms. */}
        <link rel="preconnect" href="https://flagcdn.com" />
        <link rel="dns-prefetch" href="https://flagcdn.com" />
      </head>
      <body className={inter.className}>
        <WebVitalsReporter />
        <DemoBanner />
        {children}
      </body>
    </html>
  );
}
