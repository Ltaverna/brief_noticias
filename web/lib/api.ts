import {
  BiasScorecard,
  Briefing,
  ClusterDetail,
  EntityDetail,
  EntitySummary,
  QAMessage,
  QAResponse,
  RunDetail,
  Saga,
  SagaDetail,
  SearchResults,
  SourceListItem,
  Subscription,
  ToneTrends,
} from "./types";

const baseUrl = (): string => {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_URL ?? "http://api:8000";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
};

export const apiUrl = baseUrl;

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
  getTodayBriefing: (params?: { topic?: string }): Promise<Briefing> => {
    const qs = params?.topic ? `?topic=${encodeURIComponent(params.topic)}` : "";
    return get(`/briefings/today${qs}`, { cache: "no-store" });
  },
  getBriefingByDate: (date: string, params?: { topic?: string }): Promise<Briefing> => {
    const qs = params?.topic ? `?topic=${encodeURIComponent(params.topic)}` : "";
    return get(`/briefings/${date}${qs}`, { cache: "no-store" });
  },
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
  getSubscriptions: async (): Promise<Subscription[]> => {
    const url =
      typeof window === "undefined"
        ? `${baseUrl()}/subscriptions`
        : "/api/subscriptions";
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`API /subscriptions failed: ${res.status}`);
    return res.json();
  },
  addSubscription: async (body: {
    kind: "entity" | "topic" | "all";
    value?: string;
    alert_threshold_sources?: number;
  }): Promise<Subscription> => {
    const url =
      typeof window === "undefined"
        ? `${baseUrl()}/subscriptions`
        : "/api/subscriptions";
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  },
  deleteSubscription: async (id: number): Promise<void> => {
    const url =
      typeof window === "undefined"
        ? `${baseUrl()}/subscriptions/${id}`
        : `/api/subscriptions/${id}`;
    const res = await fetch(url, { method: "DELETE" });
    if (!res.ok) throw new Error(`${res.status}`);
  },
  askQA: async (query: string, conversationId?: string | null): Promise<QAResponse> => {
    // Always go through the Next.js proxy at /api/qa so this works from the
    // browser (no CORS) and from server components alike.
    const url =
      typeof window === "undefined"
        ? `${baseUrl()}/qa`
        : "/api/qa";
    const body: Record<string, string> = { query };
    if (conversationId) body.conversation_id = conversationId;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`QA failed: ${res.status}${text ? ` — ${text}` : ""}`);
    }
    return res.json();
  },
  getQAHistory: async (conversationId: string): Promise<QAMessage[]> => {
    const url =
      typeof window === "undefined"
        ? `${baseUrl()}/qa/history?conversation_id=${encodeURIComponent(conversationId)}`
        : `/api/qa/history?conversation_id=${encodeURIComponent(conversationId)}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  },
};
