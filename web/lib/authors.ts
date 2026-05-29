import { apiUrl } from "./api";

// In the browser, go through Next.js proxy routes at /api/* (same origin, no
// CORS, no need to expose the FastAPI port publicly). On the server, hit the
// internal API directly via apiUrl().
const route = (path: string): string =>
  typeof window === "undefined" ? `${apiUrl()}${path}` : `/api${path}`;

export type AuthorListItem = {
  id: number;
  name: string;
  canonical: string;
  slug: string;
  source_slug: string | null;
  is_synthetic: boolean;
  kind: string;
  article_count: number;
};

export type AuthorStats = {
  author: {
    id: number; name: string; canonical: string; slug: string;
    source: string | null; is_synthetic: boolean; kind: string;
  };
  totals: {
    articles: number; clusters: number; coauthored: number;
    first_seen: string | null; last_seen: string | null;
  };
  by_topic: { topic: string; count: number; share: number }[];
  by_month: { month: string; articles: number }[];
  top_entities: { name: string; kind: string; clusters: number }[];
};

export type AuthorScorecard = {
  n: number;
  tone: { avg: number | null; distribution: Record<string, number> };
  omission_rate: number | null;
  divergence_score: number | null;
  framing_diversity: number | null;
  vs_source_baseline: {
    tone_delta: number; omission_delta: number;
    source: string; n_baseline: number;
  } | null;
};

export type AuthorProfile = {
  profile: {
    framings_recurrentes: string[];
    fuentes_citadas_frecuentes: string[];
    entidades_dominantes: string[];
    tono_caracteristico: string;
    temas_evitados: string[];
  };
  model: string | null;
  n_sample: number;
  generated_at: string;
};

export type SimilarAuthor = {
  slug: string; name: string; source: string | null;
  score: number;
  components: { topic: number; profile: number };
};

export type CompareResponse = {
  a: { slug: string; name: string };
  b: { slug: string; name: string };
  overlap_clusters: number;
  sintesis: string;
  coincidencias?: string[];
  diferencias?: string[];
  tono_a?: number; tono_b?: number;
  delta_tono_significativo?: boolean;
  stats_a?: unknown; stats_b?: unknown;
  cached?: boolean;
};

export type AuthorArticle = {
  id: number;
  title: string;
  url: string;
  cluster_id: number | null;
  published_at: string | null;
};

export type SharedCluster = {
  id: number;
  headline: string | null;
};

export type AuthorRadar = {
  author: { slug: string; name: string };
  source: { slug: string | null; color: string };
  n: number;
  dimensions: { key: string; label: string; value: number }[];
};

export async function listAuthors(params: {
  source?: string; q?: string; kind?: string; order?: string; limit?: number
} = {}): Promise<{ authors: AuthorListItem[] }> {
  const qs = new URLSearchParams();
  if (params.source) qs.set("source", params.source);
  if (params.q) qs.set("q", params.q);
  if (params.kind) qs.set("kind", params.kind);
  if (params.order) qs.set("order", params.order);
  if (params.limit) qs.set("limit", String(params.limit));
  const r = await fetch(`${route("/authors")}?${qs}`);
  if (!r.ok) throw new Error(`listAuthors ${r.status}`);
  return r.json();
}

export async function getAuthorStats(slug: string): Promise<AuthorStats> {
  const r = await fetch(`${route("/authors")}/${slug}/stats`);
  if (!r.ok) throw new Error(`getAuthorStats ${r.status}`);
  return r.json();
}

export async function getAuthorScorecard(slug: string): Promise<AuthorScorecard> {
  const r = await fetch(`${route("/authors")}/${slug}/scorecard`);
  if (!r.ok) throw new Error(`getAuthorScorecard ${r.status}`);
  return r.json();
}

export async function getAuthorProfile(slug: string): Promise<AuthorProfile | null> {
  const r = await fetch(`${route("/authors")}/${slug}/profile`);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`getAuthorProfile ${r.status}`);
  return r.json();
}

export async function regenerateAuthorProfile(slug: string): Promise<AuthorProfile> {
  const r = await fetch(`${route("/authors")}/${slug}/profile/regenerate`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(`regenerate ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function getSimilarAuthors(slug: string): Promise<{ similar: SimilarAuthor[] }> {
  const r = await fetch(`${route("/authors")}/${slug}/similar`);
  if (!r.ok) throw new Error(`getSimilar ${r.status}`);
  return r.json();
}

export async function compareAuthors(a: string, b: string): Promise<CompareResponse> {
  const r = await fetch(`${route("/authors")}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ a, b }),
  });
  if (!r.ok) throw new Error(`compare ${r.status}`);
  return r.json();
}

export async function getAuthorArticles(
  slug: string, limit = 50
): Promise<{ articles: AuthorArticle[] }> {
  const r = await fetch(`${route("/authors")}/${slug}/articles?limit=${limit}`);
  if (!r.ok) throw new Error(`getAuthorArticles ${r.status}`);
  return r.json();
}

export async function getSharedClusters(
  a: string, b: string
): Promise<{ clusters: SharedCluster[] }> {
  const r = await fetch(`${route("/authors")}/compare/clusters?a=${a}&b=${b}`);
  if (!r.ok) throw new Error(`getSharedClusters ${r.status}`);
  return r.json();
}

export async function getAuthorRadar(slug: string): Promise<AuthorRadar> {
  const r = await fetch(`${route("/authors")}/${slug}/radar`);
  if (!r.ok) throw new Error(`getAuthorRadar ${r.status}`);
  return r.json();
}
