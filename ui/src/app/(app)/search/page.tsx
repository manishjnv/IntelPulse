import SearchClient from "./search-client";
import type { SearchResponse } from "@/types";
import type { SearchAggStats } from "@/lib/api";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";

type Search = Record<string, string | string[] | undefined>;

function pickString(v: string | string[] | undefined): string | null {
  if (typeof v === "string" && v.length > 0) return v;
  return null;
}

async function fetchInitial(searchParams: Search): Promise<{
  stats: SearchAggStats | null;
  searchResult: SearchResponse | null;
  query: string;
}> {
  const q = pickString(searchParams.q);

  try {
    const statsPromise = fetch(`${BACKEND_URL}/api/v1/search/stats`, {
      cache: "no-store",
    });
    const searchPromise: Promise<Response | null> = q
      ? fetch(`${BACKEND_URL}/api/v1/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: q,
            page: 1,
            page_size: 20,
            sort_by: "risk_score",
            sort_dir: "desc",
          }),
          cache: "no-store",
        })
      : Promise.resolve(null);

    const [statsRes, searchRes] = await Promise.all([statsPromise, searchPromise]);
    const stats = statsRes.ok ? ((await statsRes.json()) as SearchAggStats) : null;
    const raw: SearchResponse | null =
      searchRes && searchRes.ok ? ((await searchRes.json()) as SearchResponse) : null;
    // SSR payload trim — mirrors 7077637 (threats/page.tsx slim pattern).
    // The table renders: id, title, source_ref, asset_type, risk_score,
    // published_at, ingested_at, severity, confidence, source_name.
    // The enrichment dialog (opened by the Zap button on each row) also reads
    // is_kev, cve_ids, and tags off the row object — those MUST stay intact.
    // Everything else is unused on first paint; zero it so the embedded HTML
    // is smaller. Client-side refetches via /api/v1/search still get the full
    // shape — no backend change.
    const searchResult: SearchResponse | null = raw
      ? {
          ...raw,
          results: raw.results.map((it) => ({
            ...it,
            summary: null,
            description: null,
            updated_at: null,
            source_url: null,
            source_reliability: 0,
            tlp: "",
            geo: [],
            industries: [],
            affected_products: [],
            related_ioc_count: 0,
            exploit_available: false,
            exploitability_score: null,
            ai_summary: null,
            ai_summary_at: null,
            source_hash: "",
          })),
        }
      : null;
    return { stats, searchResult, query: q ?? "" };
  } catch {
    return { stats: null, searchResult: null, query: q ?? "" };
  }
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Search;
}) {
  const { stats, searchResult, query } = await fetchInitial(searchParams);
  return (
    <SearchClient
      initialStats={stats}
      initialSearchResult={searchResult}
      initialQuery={query}
    />
  );
}
