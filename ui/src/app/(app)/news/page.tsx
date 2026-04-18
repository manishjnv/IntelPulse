import NewsClient from "./news-client";
import type {
  NewsListResponse,
  NewsCategoriesResponse,
  NewsStatsResponse,
  NewsPipelineStatus,
} from "@/types";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";

type Search = Record<string, string | string[] | undefined>;

function pickString(v: string | string[] | undefined): string | null {
  if (typeof v === "string" && v.length > 0) return v;
  return null;
}

async function fetchInitial(searchParams: Search): Promise<{
  news: NewsListResponse | null;
  categories: NewsCategoriesResponse | null;
  stats: NewsStatsResponse | null;
  pipelineStatus: NewsPipelineStatus | null;
}> {
  const qs = new URLSearchParams();
  qs.set("page", "1");
  qs.set("page_size", "20");
  qs.set("sort_by", "published_at");
  qs.set("sort_order", "desc");
  qs.set("ai_enriched", "true");
  const category = pickString(searchParams.category);
  const q = pickString(searchParams.q);
  const tag = pickString(searchParams.tag);
  if (category) qs.set("category", category);
  if (q) qs.set("search", q);
  if (tag) qs.set("tag", tag);

  try {
    const [newsRes, catRes, statsRes, pipeRes] = await Promise.all([
      fetch(`${BACKEND_URL}/api/v1/news?${qs}`, { cache: "no-store" }),
      fetch(`${BACKEND_URL}/api/v1/news/categories`, { cache: "no-store" }),
      fetch(`${BACKEND_URL}/api/v1/news/stats`, { cache: "no-store" }),
      fetch(`${BACKEND_URL}/api/v1/news/pipeline-status`, { cache: "no-store" }),
    ]);
    const newsRaw = newsRes.ok ? ((await newsRes.json()) as NewsListResponse) : null;
    const categories = catRes.ok
      ? ((await catRes.json()) as NewsCategoriesResponse)
      : null;
    const stats = statsRes.ok ? ((await statsRes.json()) as NewsStatsResponse) : null;
    const pipelineStatus = pipeRes.ok
      ? ((await pipeRes.json()) as NewsPipelineStatus)
      : null;
    // SSR payload trim — mirrors the 7077637 pattern from /threats/page.tsx.
    // Fields below are never accessed by news-client.tsx in any render path;
    // nulling them here shrinks the HTML shell. Client-side refetches via
    // api.getNewsItems() still receive the full shape from the backend.
    const news = newsRaw
      ? {
          ...newsRaw,
          items: newsRaw.items.map((it) => ({
            ...it,
            campaign_name: null,
            initial_access_vector: null,
            yara_rule: null,
            kql_rule: null,
            post_exploitation: [],
            impacted_assets: [],
            reference_links: [],
            created_at: "",
            updated_at: "",
          })),
        }
      : null;
    return { news, categories, stats, pipelineStatus };
  } catch {
    return { news: null, categories: null, stats: null, pipelineStatus: null };
  }
}

export default async function NewsPage({
  searchParams,
}: {
  searchParams: Search;
}) {
  const { news, categories, stats, pipelineStatus } = await fetchInitial(searchParams);
  return (
    <NewsClient
      initialNews={news}
      initialCategories={categories}
      initialStats={stats}
      initialPipelineStatus={pipelineStatus}
    />
  );
}
