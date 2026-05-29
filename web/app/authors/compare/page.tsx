"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  compareAuthors,
  listAuthors,
  getAuthorRadar,
  type CompareResponse,
  type AuthorListItem,
  type AuthorRadar,
} from "@/lib/authors";
import { AuthorRadarChart } from "@/components/AuthorRadarChart";

export default function ComparePage() {
  const sp = useSearchParams();
  const a = sp.get("a") ?? "";
  const b = sp.get("b") ?? "";
  const [data, setData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [bOptions, setBOptions] = useState<AuthorListItem[]>([]);
  const [bSelect, setBSelect] = useState(b);
  const [radarA, setRadarA] = useState<AuthorRadar | null>(null);
  const [radarB, setRadarB] = useState<AuthorRadar | null>(null);

  useEffect(() => {
    listAuthors({ order: "articles_desc", limit: 100 }).then(r => setBOptions(r.authors));
  }, []);

  async function run() {
    if (!a || !bSelect) return;
    setLoading(true);
    try {
      const r = await compareAuthors(a, bSelect);
      setData(r);
      Promise.all([getAuthorRadar(a), getAuthorRadar(bSelect)])
        .then(([rA, rB]) => { setRadarA(rA); setRadarB(rB); })
        .catch(() => { /* radar is non-critical */ });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <h1 className="text-2xl font-semibold">Comparar autores</h1>
      <div className="flex gap-2 items-center">
        <span className="text-sm text-slate-600">A: <strong>{a || "(?)"}</strong></span>
        <span className="text-slate-400">vs</span>
        <select
          value={bSelect}
          onChange={e => setBSelect(e.target.value)}
          className="px-2 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900"
        >
          <option value="">Elegir B…</option>
          {bOptions.filter(o => o.slug !== a).map(o => (
            <option key={o.slug} value={o.slug}>{o.name}</option>
          ))}
        </select>
        <button
          onClick={run}
          disabled={!a || !bSelect || loading}
          className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-300"
        >
          {loading ? "Comparando…" : "Comparar"}
        </button>
      </div>

      {data && (
        <>
          <header className="flex justify-between text-sm pb-4 border-b border-slate-200 dark:border-slate-800">
            <span><strong>{data.a.name}</strong></span>
            <span className="text-slate-400">vs</span>
            <span><strong>{data.b.name}</strong></span>
          </header>

          <section className="bg-amber-50 dark:bg-amber-950/30 p-4 rounded">
            <div className="text-xs text-slate-500 uppercase mb-2">Síntesis</div>
            <p className="text-sm">{data.sintesis}</p>
          </section>

          {radarA && radarB && (
            <section>
              <h2 className="text-xs text-slate-500 uppercase mb-2">Radar comparativo</h2>
              <AuthorRadarChart
                series={[
                  { label: radarA.author.name, color: radarA.source.color,
                    values: radarA.dimensions.map(d => d.value), n: radarA.n },
                  { label: radarB.author.name, color: radarB.source.color,
                    values: radarB.dimensions.map(d => d.value), n: radarB.n },
                ]}
                labels={radarA.dimensions.map(d => d.label)}
              />
            </section>
          )}

          {data.coincidencias && data.coincidencias.length > 0 && (
            <section className="border-l-2 border-green-500 pl-4">
              <h2 className="text-xs text-slate-500 uppercase mb-2">Coincidencias</h2>
              <ul className="text-sm space-y-1 list-disc list-inside">
                {data.coincidencias.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </section>
          )}

          {data.diferencias && data.diferencias.length > 0 && (
            <section className="border-l-2 border-red-500 pl-4">
              <h2 className="text-xs text-slate-500 uppercase mb-2">Diferencias</h2>
              <ul className="text-sm space-y-1 list-disc list-inside">
                {data.diferencias.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </section>
          )}

          {data.overlap_clusters > 0 && (
            <Link
              href={`/authors/compare/clusters?a=${data.a.slug}&b=${data.b.slug}`}
              className="block text-center bg-blue-50 dark:bg-blue-950/30 p-3 rounded text-sm text-blue-600 hover:bg-blue-100"
            >
              Ver los {data.overlap_clusters} clusters compartidos →
            </Link>
          )}
        </>
      )}
    </div>
  );
}
