"use client";
import { useEffect, useState } from "react";
import { getAuthorScorecard, type AuthorScorecard as Data } from "@/lib/authors";

const MIN_N = 3;

export function AuthorScorecard({ slug }: { slug: string }) {
  const [data, setData] = useState<Data | null>(null);
  useEffect(() => { getAuthorScorecard(slug).then(setData); }, [slug]);
  if (!data) return <p className="text-slate-500">Cargando…</p>;

  const small = data.n < MIN_N;
  const colorClass = small ? "text-slate-400" : "";
  const title = small ? `Muestra chica (n=${data.n})` : `n=${data.n}`;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Metric label="Tono promedio" value={data.tone.avg?.toFixed(2)} className={colorClass} title={title} />
        <Metric label="Tasa omisión" value={data.omission_rate?.toFixed(2)} className={colorClass} title={title} />
        <Metric label="Divergencia" value={data.divergence_score?.toFixed(2)} className={colorClass} title={title} />
        <Metric label="Diversidad framing" value={data.framing_diversity?.toFixed(2)} className={colorClass} title={title} />
      </div>

      {data.vs_source_baseline && (
        <section className="bg-slate-50 dark:bg-slate-900 p-4 rounded text-sm">
          <h3 className="font-semibold mb-2">Comparado con {data.vs_source_baseline.source}</h3>
          <p>Δ tono: <strong>{data.vs_source_baseline.tone_delta.toFixed(2)}</strong></p>
          <p>Δ omisión: <strong>{data.vs_source_baseline.omission_delta.toFixed(2)}</strong></p>
        </section>
      )}
    </div>
  );
}

function Metric({ label, value, className, title }: {
  label: string; value: string | undefined; className?: string; title?: string
}) {
  return (
    <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded" title={title}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-xl font-semibold ${className ?? ""}`}>{value ?? "—"}</div>
    </div>
  );
}
