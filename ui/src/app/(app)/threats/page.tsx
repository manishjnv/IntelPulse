import { ThreatsClient } from "./threats-client";
import type { IntelListResponse, IntelStatsResponse } from "@/types";

// Force dynamic rendering — searchParams drive the initial fetch and we want
// fresh intel data on every request (not ISR-cached).
export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";

type Search = Record<string, string | string[] | undefined>;

function pickString(v: string | string[] | undefined): string | null {
  if (typeof v === "string" && v.length > 0) return v;
  return null;
}

async function fetchInitial(searchParams: Search): Promise<{
  data: IntelListResponse | null;
  stats: IntelStatsResponse | null;
}> {
  const qs = new URLSearchParams();
  qs.set("page", "1");
  qs.set("page_size", "20");
  qs.set("sort_by", "ingested_at");
  qs.set("sort_order", "desc");
  const sev = pickString(searchParams.severity);
  const ft = pickString(searchParams.feed_type);
  if (sev) qs.set("severity", sev);
  if (ft) qs.set("feed_type", ft);

  try {
    const [dataRes, statsRes] = await Promise.all([
      fetch(`${BACKEND_URL}/api/v1/intel?${qs}`, { cache: "no-store" }),
      fetch(`${BACKEND_URL}/api/v1/intel/stats`, { cache: "no-store" }),
    ]);
    const data = dataRes.ok ? ((await dataRes.json()) as IntelListResponse) : null;
    const stats = statsRes.ok ? ((await statsRes.json()) as IntelStatsResponse) : null;
    return { data, stats };
  } catch {
    return { data: null, stats: null };
  }
}

export default async function ThreatsPage({ searchParams }: { searchParams: Search }) {
  const { data, stats } = await fetchInitial(searchParams);
  return <ThreatsClient initialData={data} initialStats={stats} />;
}
