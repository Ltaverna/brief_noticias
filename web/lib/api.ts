import {
  Briefing,
  ClusterDetail,
  RunDetail,
  Saga,
  SagaDetail,
  SearchResults,
  SourceListItem,
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
};
