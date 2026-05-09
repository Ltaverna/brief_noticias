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
      className={`relative rounded-lg border bg-white transition dark:bg-stone-900 ${
        read
          ? "border-stone-200 opacity-60 dark:border-stone-800"
          : "border-stone-200 hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
      }`}
    >
      <Link href={`/cluster/${cluster.id}`} className="block p-5 pr-12">
        <h2 className="text-xl font-serif leading-snug">
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
        className="absolute right-3 top-3 rounded-full p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700 dark:hover:bg-stone-800 dark:hover:text-stone-300"
      >
        {read ? "✓" : "○"}
      </button>
    </div>
  );
}
