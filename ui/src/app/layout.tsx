import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { DemoBanner } from "@/components/DemoBanner";
import { WebVitalsReporter } from "@/components/WebVitalsReporter";

const inter = Inter({ subsets: ["latin"] });

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
      <body className={inter.className}>
        <WebVitalsReporter />
        <DemoBanner />
        {children}
      </body>
    </html>
  );
}
