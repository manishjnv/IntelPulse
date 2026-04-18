import { InvestigateClient } from "./investigate-client";
import type { GraphResponse, GraphStatsResponse } from "@/types";
import type { GraphFeaturedEntity } from "@/lib/api";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";

type Search = Record<string, string | string[] | undefined>;

function pickString(v: string | string[] | undefined): string | null {
  if (typeof v === "string" && v.length > 0) return v;
  return null;
}

async function fetchInitial(searchParams: Search): Promise<{
  stats: GraphStatsResponse | null;
  featured: GraphFeaturedEntity[] | null;
  graphData: GraphResponse | null;
}> {
  const id = pickString(searchParams.id);
  const type = pickString(searchParams.type) || "intel";
  const depthStr = pickString(searchParams.depth);
  const depth = depthStr && /^\d+$/.test(depthStr) ? depthStr : "2";

  try {
    const fetches: Promise<Response>[] = [
      fetch(`${BACKEND_URL}/api/v1/graph/stats`, { cache: "no-store" }),
      fetch(`${BACKEND_URL}/api/v1/graph/featured?limit=12`, { cache: "no-store" }),
    ];
    if (id) {
      fetches.push(
        fetch(
          `${BACKEND_URL}/api/v1/graph/explore?entity_id=${encodeURIComponent(id)}&entity_type=${encodeURIComponent(type)}&depth=${depth}&limit=100`,
          { cache: "no-store" },
        ),
      );
    }
    const results = await Promise.all(fetches);
    const statsRes = results[0];
    const featRes = results[1];
    const graphRes = id ? results[2] : null;

    const stats = statsRes.ok ? ((await statsRes.json()) as GraphStatsResponse) : null;
    const featResp = featRes.ok
      ? ((await featRes.json()) as { featured: GraphFeaturedEntity[] })
      : null;
    const featured = featResp?.featured ?? null;
    const graphData =
      graphRes && graphRes.ok ? ((await graphRes.json()) as GraphResponse) : null;
    return { stats, featured, graphData };
  } catch {
    return { stats: null, featured: null, graphData: null };
  }
}

export default async function InvestigatePage({
  searchParams,
}: {
  searchParams: Search;
}) {
  const { stats, featured, graphData } = await fetchInitial(searchParams);
  return (
    <InvestigateClient
      initialStats={stats}
      initialFeatured={featured}
      initialGraphData={graphData}
    />
  );
}
