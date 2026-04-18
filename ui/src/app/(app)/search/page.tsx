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
    const searchResult =
      searchRes && searchRes.ok ? ((await searchRes.json()) as SearchResponse) : null;
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
