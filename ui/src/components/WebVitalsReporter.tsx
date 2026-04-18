"use client";

import { useReportWebVitals } from "next/web-vitals";
import { usePathname } from "next/navigation";

/**
 * Beams Core Web Vitals (LCP / CLS / INP / FCP / TTFB) plus Next.js router
 * timings to `/api/v1/rum`. Uses sendBeacon so the POST survives page
 * unload (which is when LCP/INP typically report).
 *
 * Zero cost when the browser doesn't support web-vitals — the hook simply
 * no-ops. RUM traffic is capped separately in the rate-limit middleware.
 */
export function WebVitalsReporter() {
  const pathname = usePathname();

  useReportWebVitals((metric) => {
    const body = JSON.stringify({
      name: metric.name,
      value: metric.value,
      id: metric.id,
      path: pathname ?? "/",
      rating: (metric as { rating?: "good" | "needs-improvement" | "poor" }).rating,
    });
    try {
      if (typeof navigator !== "undefined" && navigator.sendBeacon) {
        navigator.sendBeacon(
          "/api/v1/rum",
          new Blob([body], { type: "application/json" }),
        );
      } else {
        void fetch("/api/v1/rum", {
          method: "POST",
          body,
          headers: { "Content-Type": "application/json" },
          keepalive: true,
        });
      }
    } catch {
      // best-effort: RUM beacons must never throw into user code
    }
  });

  return null;
}
