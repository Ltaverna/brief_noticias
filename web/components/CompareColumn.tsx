import Link from "next/link";

import { ClusterDetail } from "@/lib/types";

export function CompareColumn({ cluster }: { cluster: ClusterDetail | null }) {
  if (!cluster) {
    return (
      <div className="rounded-md border border-dashed border-stone-300 p-6 text-center text-sm text-stone-500 dark:border-stone-700 dark:text-stone-400">
        Cluster no encontrado.
      </div>
    );
  }
  const a = cluster.analysis;
  return (
    <div className="rounded-md border border-stone-200 p-5 dark:border-stone-800">
      <Link href={`/cluster/${cluster.id}`} className="text-xs text-stone-500 hover:underline">
        Ver cluster #{cluster.id} →
      </Link>
      <h2 className="mt-1 text-xl font-serif font-semibold leading-snug">
        {a?.headline ?? "(análisis pendiente)"}
      </h2>
      {cluster.topic && (
        <p className="mt-1 text-xs text-stone-500">tema: {cluster.topic}</p>
      )}
      <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
        {cluster.source_count} diarios · {cluster.article_count} artículos
      </p>

      {a && (
        <>
          {a.common_facts.length > 0 && (
            <section className="mt-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide">Hechos en común</h3>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm">
                {a.common_facts.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </section>
          )}

          {Object.keys(a.by_source).length > 0 && (
            <section className="mt-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide">Por diario</h3>
              <div className="mt-2 space-y-3 text-sm">
                {Object.entries(a.by_source).map(([slug, info]) => (
                  <div key={slug} className="rounded-md bg-stone-100 p-3 dark:bg-stone-800">
                    <p className="font-mono text-xs text-stone-500">{slug} · {info.tone}</p>
                    <p className="mt-1 italic">{info.framing}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
