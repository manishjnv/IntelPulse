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
    const news = newsRes.ok ? ((await newsRes.json()) as NewsListResponse) : null;
    const categories = catRes.ok
      ? ((await catRes.json()) as NewsCategoriesResponse)
      : null;
    const stats = statsRes.ok ? ((await statsRes.json()) as NewsStatsResponse) : null;
    const pipelineStatus = pipeRes.ok
      ? ((await pipeRes.json()) as NewsPipelineStatus)
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
