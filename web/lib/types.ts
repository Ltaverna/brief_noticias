export type EditorialGroup = "mainstream" | "critico" | "economico";

export interface SourceRef {
  slug: string;
  name: string;
  editorial_group: EditorialGroup;
}

export interface ClusterSummary {
  id: number;
  headline: string | null;
  source_count: number;
  article_count: number;
  sources: string[];
  rank_score: number | null;
  common_facts: string[];
  divergence_count: number;
}

export interface Briefing {
  date: string;
  generated_at: string | null;
  clusters: ClusterSummary[];
}

export interface ArticleDetail {
  id: number;
  source: SourceRef;
  title: string;
  url: string;
  summary: string | null;
  has_full_text: boolean;
  published_at: string | null;
}

export interface BySourceAnalysis {
  highlights: string[];
  framing: string;
  tone: string;
}

export interface Omission {
  source: string;
  not_mentioned: string;
}

export interface Divergence {
  topic: string;
  positions: Record<string, string>;
}

export interface AnalysisDetail {
  headline: string | null;
  common_facts: string[];
  by_source: Record<string, BySourceAnalysis>;
  omissions: Omission[];
  divergences: Divergence[];
  model: string | null;
  prompt_version: string | null;
  generated_at: string;
}

export interface ClusterDetail {
  id: number;
  first_seen_at: string;
  last_seen_at: string;
  article_count: number;
  source_count: number;
  analysis: AnalysisDetail | null;
  articles: ArticleDetail[];
  saga: { id: number; title: string } | null;
}

export interface Saga {
  id: number;
  title: string;
  cluster_count: number;
  source_count: number;
  article_count: number;
  first_seen_at: string;
  last_seen_at: string;
}

export interface SagaClusterRef {
  id: number;
  headline: string | null;
  source_count: number;
  article_count: number;
  last_seen_at: string;
  is_top: boolean;
}

export interface SagaDetail extends Saga {
  clusters: SagaClusterRef[];
}

export interface SourceListItem {
  slug: string;
  name: string;
  editorial_group: EditorialGroup;
  rss_url: string;
  base_url: string;
  enabled: boolean;
}

export interface RunDetail {
  id: number;
  trigger: "cron" | "manual";
  status: "queued" | "running" | "success" | "partial" | "failed";
  started_at: string;
  finished_at: string | null;
  stats: Record<string, unknown> | null;
  error: string | null;
}

export interface ClusterHit {
  id: number;
  headline: string | null;
  source_count: number;
  article_count: number;
  rank: number;
}

export interface ArticleHit {
  id: number;
  title: string;
  url: string;
  source_slug: string;
  cluster_id: number | null;
  published_at: string | null;
  rank: number;
}

export interface SearchResults {
  query: string;
  clusters: ClusterHit[];
  articles: ArticleHit[];
}
