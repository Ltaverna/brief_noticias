import Link from "next/link";

import { ClusterSummary, EditorialGroup, SourceListItem } from "@/lib/types";
import { SourceChip } from "./SourceChip";

interface Props {
  cluster: ClusterSummary;
  sourcesById: Map<string, SourceListItem>;
}

export function ClusterCard({ cluster, sourcesById }: Props) {
  return (
    <Link
      href={`/cluster/${cluster.id}`}
      className="block rounded-lg border border-stone-200 bg-white p-5 transition hover:border-stone-400 dark:border-stone-800 dark:bg-stone-900 dark:hover:border-stone-600"
    >
      <h2 className="text-xl font-serif leading-snug">
        {cluster.headline ?? "Análisis pendiente"}
      </h2>
      <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
        {cluster.source_count} {cluster.source_count === 1 ? "diario" : "diarios"} ·{" "}
        {cluster.divergence_count}{" "}
        {cluster.divergence_count === 1 ? "punto de divergencia" : "puntos de divergencia"}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
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
  );
}
