import Link from "next/link";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = (q ?? "").trim();

  if (query.length < 2) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="text-3xl font-serif font-bold">Búsqueda</h1>
        <p className="mt-4 text-stone-600 dark:text-stone-400">
          Escribí al menos 2 caracteres en la barra de búsqueda.
        </p>
      </main>
    );
  }

  const results = await api.search(query);

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-3xl font-serif font-bold">Resultados</h1>
      <p className="mt-1 text-stone-600 dark:text-stone-400">
        {results.clusters.length + results.articles.length} resultados para{" "}
        <em>&ldquo;{query}&rdquo;</em>
      </p>

      {results.clusters.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-serif font-semibold">Historias agrupadas</h2>
          <ul className="mt-3 space-y-2">
            {results.clusters.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/cluster/${c.id}`}
                  className="block rounded-md border border-stone-200 px-4 py-3 hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
                >
                  <p className="font-medium">{c.headline ?? "Análisis pendiente"}</p>
                  <p className="mt-1 text-sm text-stone-500">
                    {c.source_count} diarios · {c.article_count} artículos
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {results.articles.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-serif font-semibold">Artículos sueltos</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {results.articles.map((a) => (
              <li key={a.id} className="flex flex-wrap items-baseline gap-2">
                <span className="font-mono text-xs text-stone-500">{a.source_slug}</span>
                {a.cluster_id ? (
                  <Link href={`/cluster/${a.cluster_id}`} className="hover:underline">
                    {a.title}
                  </Link>
                ) : (
                  <a
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline"
                  >
                    {a.title}
                  </a>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {results.clusters.length === 0 && results.articles.length === 0 && (
        <p className="mt-8 text-stone-600 dark:text-stone-400">
          No se encontraron resultados. Probá con otros términos.
        </p>
      )}
    </main>
  );
}
