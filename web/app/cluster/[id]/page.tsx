import Link from "next/link";
import { notFound } from "next/navigation";

import { api } from "@/lib/api";
import { DivergenceTable } from "@/components/DivergenceTable";
import { Footer } from "@/components/Footer";
import { SourceChip } from "@/components/SourceChip";
import { SourceTabs } from "@/components/SourceTabs";

export const revalidate = 300;

export default async function ClusterPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const clusterId = Number(id);
  if (!Number.isInteger(clusterId)) notFound();

  const [cluster, sources] = await Promise.all([
    api.getCluster(clusterId),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-4xl space-y-8 px-6 py-8">
        <header>
          <Link href="/" className="text-sm text-stone-500 hover:underline">
            ← Volver al briefing
          </Link>
          <h1 className="mt-2 text-3xl font-serif font-bold">
            {cluster.analysis?.headline ?? "Análisis pendiente"}
          </h1>
          <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
            {cluster.source_count} diarios · {cluster.article_count} artículos
          </p>
        </header>

        {cluster.analysis === null ? (
          <p className="rounded-md border border-amber-300 bg-amber-50 p-4 text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
            El análisis para este cluster aún no se generó o falló. Tocá Actualizar para reintentar.
          </p>
        ) : (
          <>
            <section>
              <h2 className="text-xl font-serif font-semibold">Hechos en común</h2>
              <ul className="mt-3 list-inside list-disc space-y-1 text-sm">
                {cluster.analysis.common_facts.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-serif font-semibold">Por diario</h2>
              <div className="mt-3">
                <SourceTabs
                  bySource={cluster.analysis.by_source}
                  sourcesById={sourcesById}
                />
              </div>
            </section>

            <section>
              <h2 className="text-xl font-serif font-semibold">Omisiones</h2>
              {cluster.analysis.omissions.length === 0 ? (
                <p className="mt-3 text-sm text-stone-500 dark:text-stone-400">
                  No se detectaron omisiones relevantes.
                </p>
              ) : (
                <ul className="mt-3 list-inside list-disc space-y-1 text-sm">
                  {cluster.analysis.omissions.map((o, i) => (
                    <li key={i}>
                      <strong className="font-mono text-xs">{o.source}</strong>{" "}
                      omite: {o.not_mentioned}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h2 className="text-xl font-serif font-semibold">Divergencias</h2>
              <div className="mt-3">
                <DivergenceTable divergences={cluster.analysis.divergences} />
              </div>
            </section>
          </>
        )}

        <section>
          <h2 className="text-xl font-serif font-semibold">Artículos fuente</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {cluster.articles.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-2">
                <SourceChip
                  slug={a.source.slug}
                  group={a.source.editorial_group}
                />
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                >
                  {a.title}
                </a>
                {!a.has_full_text && (
                  <span className="text-xs text-stone-500">(solo título/resumen)</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      </main>
      <Footer generatedAt={cluster.analysis?.generated_at ?? null} />
    </>
  );
}
