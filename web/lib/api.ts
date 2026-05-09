import {
  BiasScorecard,
  Briefing,
  ClusterDetail,
  EntityDetail,
  EntitySummary,
  QAResponse,
  RunDetail,
  Saga,
  SagaDetail,
  SearchResults,
  SourceListItem,
  ToneTrends,
} from "./types";

const baseUrl = (): string => {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_URL ?? "http://api:8000";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
};

async function get<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...opts?.headers },
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getTodayBriefing: (): Promise<Briefing> =>
    get("/briefings/today", { next: { revalidate: 60 } }),
  getBriefingByDate: (date: string): Promise<Briefing> =>
    get(`/briefings/${date}`, { next: { revalidate: 60 } }),
  listBriefingDates: (): Promise<string[]> =>
    get("/briefings", { next: { revalidate: 300 } }),
  getCluster: (id: number): Promise<ClusterDetail> =>
    get(`/clusters/${id}`, { next: { revalidate: 300 } }),
  getSources: (): Promise<SourceListItem[]> =>
    get("/sources", { next: { revalidate: 300 } }),
  getRun: (id: number): Promise<RunDetail> => get(`/runs/${id}`, { cache: "no-store" }),
  search: (q: string, limit = 30): Promise<SearchResults> =>
    get(`/search?q=${encodeURIComponent(q)}&limit=${limit}`, { cache: "no-store" }),
  getSagas: (): Promise<Saga[]> =>
    get("/sagas", { next: { revalidate: 120 } }),
  getSaga: (id: number): Promise<SagaDetail> =>
    get(`/sagas/${id}`, { next: { revalidate: 120 } }),
  getEntities: (params?: { kind?: string; q?: string; limit?: number }): Promise<EntitySummary[]> => {
    const qs = new URLSearchParams();
    if (params?.kind) qs.set("kind", params.kind);
    if (params?.q) qs.set("q", params.q);
    if (params?.limit) qs.set("limit", String(params.limit));
    const qstr = qs.toString();
    return get(`/entities${qstr ? `?${qstr}` : ""}`, { next: { revalidate: 120 } });
  },
  getEntity: (id: number): Promise<EntityDetail> =>
    get(`/entities/${id}`, { next: { revalidate: 120 } }),
  getToneTrends: (params?: {
    entity?: string;
    since?: string;
    until?: string;
    bucket?: "week" | "day";
  }): Promise<ToneTrends> => {
    const qs = new URLSearchParams();
    if (params?.entity) qs.set("entity", params.entity);
    if (params?.since) qs.set("since", params.since);
    if (params?.until) qs.set("until", params.until);
    if (params?.bucket) qs.set("bucket", params.bucket);
    return get(
      `/analytics/tone-trends${qs.toString() ? `?${qs}` : ""}`,
      { cache: "no-store" },
    );
  },
  getBiasScorecard: (params?: {
    since?: string;
    top_entities?: number;
    kind?: string;
  }): Promise<BiasScorecard> => {
    const qs = new URLSearchParams();
    if (params?.since) qs.set("since", params.since);
    if (params?.top_entities) qs.set("top_entities", String(params.top_entities));
    if (params?.kind) qs.set("kind", params.kind);
    return get(
      `/analytics/bias-scorecard${qs.toString() ? `?${qs}` : ""}`,
      { cache: "no-store" },
    );
  },
  askQA: async (query: string): Promise<QAResponse> => {
    // Always go through the Next.js proxy at /api/qa so this works from the
    // browser (no CORS) and from server components alike.
    const url =
      typeof window === "undefined"
        ? `${baseUrl()}/qa`
        : "/api/qa";
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
      cache: "no-store",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`QA failed: ${res.status}${text ? ` — ${text}` : ""}`);
    }
    return res.json();
  },
};
