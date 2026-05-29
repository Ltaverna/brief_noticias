"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getAuthorStats, type AuthorStats } from "@/lib/authors";
import { AuthorStatsSummary } from "@/components/AuthorStatsSummary";
import { AuthorScorecard } from "@/components/AuthorScorecard";
import { AuthorProfilePanel } from "@/components/AuthorProfilePanel";
import { AuthorArticlesList } from "@/components/AuthorArticlesList";

type Tab = "resumen" | "sesgo" | "perfil" | "notas";

export default function AuthorPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [stats, setStats] = useState<AuthorStats | null>(null);
  const [tab, setTab] = useState<Tab>("resumen");

  useEffect(() => {
    if (!slug) return;
    getAuthorStats(slug).then(setStats);
  }, [slug]);

  if (!stats) return <div className="p-8 text-slate-500">Cargando…</div>;
  const a = stats.author;
  const n = stats.totals.articles;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="flex items-center justify-between mb-6 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-semibold">{a.name}</h1>
          <p className="text-sm text-slate-500">
            {a.source ?? "sin diario"} · {n} notas
          </p>
        </div>
        <Link
          href={`/authors/compare?a=${slug}`}
          className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          Comparar con otro autor
        </Link>
      </header>

      <nav className="flex gap-2 mb-6 border-b border-slate-200 dark:border-slate-800 overflow-x-auto">
        {(["resumen", "sesgo", "perfil", "notas"] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm whitespace-nowrap border-b-2 ${
              tab === t
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "resumen" ? "Resumen" :
              t === "sesgo" ? "Sesgo" :
              t === "perfil" ? "Perfil IA" : `Notas (${n})`}
          </button>
        ))}
      </nav>

      {tab === "resumen" && <AuthorStatsSummary slug={slug} stats={stats} />}
      {tab === "sesgo" && <AuthorScorecard slug={slug} />}
      {tab === "perfil" && <AuthorProfilePanel slug={slug} nSample={n} />}
      {tab === "notas" && <AuthorArticlesList slug={slug} />}
    </div>
  );
}
