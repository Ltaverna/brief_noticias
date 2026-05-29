"use client";

import Link from "next/link";

import { ClusterSummary, EditorialGroup, SourceListItem } from "@/lib/types";
import { useReadState } from "./ReadStateProvider";
import { SourceChip } from "./SourceChip";
import { TOPIC_LABELS } from "./TopicChips";

interface Props {
  cluster: ClusterSummary;
  sourcesById: Map<string, SourceListItem>;
}

export function ClusterCard({ cluster, sourcesById }: Props) {
  const { isRead, toggle } = useReadState();
  const read = isRead(cluster.id);

  return (
    <div
      className={`group relative rounded-xl border bg-white shadow-sm transition-all duration-200 dark:bg-stone-900/60 dark:shadow-none dark:ring-1 dark:ring-stone-800 ${
        read
          ? "border-stone-200 opacity-60 dark:border-stone-800/60"
          : "border-stone-200 hover:-translate-y-0.5 hover:border-stone-300 hover:shadow-md dark:border-stone-800 dark:hover:border-stone-700 dark:hover:bg-stone-900 dark:hover:ring-stone-700"
      }`}
    >
      <Link
        href={`/cluster/${cluster.id}`}
        className="block cursor-pointer p-5 pr-14"
      >
        <h2 className="font-serif text-xl font-semibold leading-snug tracking-tight">
          {cluster.headline ?? "Análisis pendiente"}
        </h2>
        <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
          {cluster.source_count} {cluster.source_count === 1 ? "diario" : "diarios"} ·{" "}
          {cluster.divergence_count}{" "}
          {cluster.divergence_count === 1 ? "punto de divergencia" : "puntos de divergencia"}
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {cluster.topic && (
            <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-700 dark:bg-stone-800 dark:text-stone-300">
              {TOPIC_LABELS[cluster.topic] ?? cluster.topic}
            </span>
          )}
          {cluster.sources.map((slug) => {
            const src = sourcesById.get(slug);
            if (!src) return null;
            return (
              <SourceChip
                key={slug}
                slug={slug}
                group={src.editorial_group as EditorialGroup}
              />
            );
          })}
        </div>
      </Link>
      <button
        type="button"
        onClick={() => toggle(cluster.id)}
        title={read ? "Marcar como no leído" : "Marcar como leído"}
        aria-label={read ? "Marcar como no leído" : "Marcar como leído"}
        aria-pressed={read}
        className="absolute right-2 top-2 flex h-10 w-10 cursor-pointer items-center justify-center rounded-full text-stone-400 transition-colors duration-150 hover:bg-stone-100 hover:text-stone-700 focus:outline-none focus:ring-2 focus:ring-stone-300 dark:hover:bg-stone-800 dark:hover:text-stone-200 dark:focus:ring-stone-600"
      >
        {read ? (
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
          </svg>
        )}
      </button>
    </div>
  );
}
