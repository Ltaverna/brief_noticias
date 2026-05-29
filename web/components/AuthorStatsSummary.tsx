"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getSimilarAuthors, type AuthorStats, type SimilarAuthor } from "@/lib/authors";

type Props = { slug: string; stats: AuthorStats };

export function AuthorStatsSummary({ slug, stats }: Props) {
  const [similar, setSimilar] = useState<SimilarAuthor[] | null>(null);

  useEffect(() => {
    getSimilarAuthors(slug).then(r => setSimilar(r.similar)).catch(() => setSimilar([]));
  }, [slug]);

  const insufficient = stats.totals.articles < 3;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <KPI label="Notas" value={stats.totals.articles} />
        <KPI label="Clusters" value={stats.totals.clusters} />
        <KPI label="Coautorías" value={stats.totals.coauthored} />
      </div>

      {insufficient && (
        <p className="text-sm text-amber-600 dark:text-amber-400">
          Datos insuficientes para tendencias (n &lt; 3).
        </p>
      )}

      {!insufficient && (
        <>
          <section>
            <h2 className="text-sm font-semibold text-slate-500 uppercase mb-2">Temas</h2>
            <ul className="space-y-1">
              {stats.by_topic.slice(0, 6).map(t => (
                <li key={t.topic} className="flex items-center gap-2 text-sm">
                  <span className="w-24 text-slate-600">{t.topic}</span>
                  <div className="flex-1 bg-slate-100 dark:bg-slate-800 h-2 rounded">
                    <div className="h-2 bg-blue-500 rounded" style={{ width: `${t.share * 100}%` }} />
                  </div>
                  <span className="w-12 text-right text-slate-500">{t.count}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-slate-500 uppercase mb-2">Top entidades</h2>
            <div className="flex flex-wrap gap-2">
              {stats.top_entities.map(e => (
                <span key={`${e.kind}:${e.name}`} className="px-2 py-0.5 text-xs rounded bg-slate-100 dark:bg-slate-800">
                  {e.name} <span className="text-slate-400">({e.clusters})</span>
                </span>
              ))}
            </div>
          </section>
        </>
      )}

      {similar && similar.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase mb-2">Autores parecidos</h2>
          <ul className="space-y-1">
            {similar.slice(0, 5).map(s => (
              <li key={s.slug} className="flex justify-between text-sm">
                <Link href={`/authors/${s.slug}`} className="hover:underline">
                  {s.name} <span className="text-slate-400">{s.source}</span>
                </Link>
                <span className="text-slate-500">{(s.score * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function KPI({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-50 dark:bg-slate-900 p-4 rounded">
      <div className="text-xs text-slate-500 uppercase">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}
