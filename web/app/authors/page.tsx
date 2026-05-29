"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { listAuthors, type AuthorListItem } from "@/lib/authors";

const KIND_BADGE: Record<string, { label: string; cls: string }> = {
  person: { label: "Periodista", cls: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300" },
  newsroom: { label: "Redacción", cls: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400" },
  editorial: { label: "Editorial", cls: "bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300" },
  agency: { label: "Agencia", cls: "bg-orange-50 text-orange-700 dark:bg-orange-950 dark:text-orange-300" },
};

const KIND_FILTERS = [
  { key: "", label: "Todos" },
  { key: "person", label: "Periodistas" },
  { key: "newsroom", label: "Redacción" },
  { key: "editorial", label: "Editoriales" },
  { key: "agency", label: "Agencias" },
];

export default function AuthorsPage() {
  const [authors, setAuthors] = useState<AuthorListItem[]>([]);
  const [q, setQ] = useState("");
  const [kindFilter, setKindFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listAuthors({
      q: q || undefined,
      kind: kindFilter || undefined,
      order: "articles_desc",
      limit: 100,
    })
      .then(r => setAuthors(r.authors))
      .finally(() => setLoading(false));
  }, [q, kindFilter]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Autores</h1>

      <input
        type="search"
        placeholder="Buscar autor..."
        value={q}
        onChange={e => setQ(e.target.value)}
        className="w-full mb-3 px-3 py-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900"
      />

      <div className="flex flex-wrap gap-1.5 mb-4">
        {KIND_FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setKindFilter(f.key)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
              kindFilter === f.key
                ? "border-blue-600 bg-blue-600 text-white"
                : "border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-slate-500">Cargando…</p>}
      <ul className="divide-y divide-slate-200 dark:divide-slate-800">
        {authors.map(a => {
          const badge = KIND_BADGE[a.kind] ?? KIND_BADGE.person;
          return (
            <li key={a.id} className="py-3 flex justify-between items-baseline gap-3">
              <div className="flex items-baseline gap-2 min-w-0">
                <Link href={`/authors/${a.slug}`} className="hover:underline truncate">
                  <span className={a.is_synthetic ? "text-slate-500" : "font-medium"}>
                    {a.name}
                  </span>
                </Link>
                <span
                  className={`shrink-0 text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${badge.cls}`}
                >
                  {badge.label}
                </span>
                {a.source_slug && (
                  <span className="text-xs text-slate-500 truncate">{a.source_slug}</span>
                )}
              </div>
              <span className="text-sm text-slate-500 shrink-0">{a.article_count} notas</span>
            </li>
          );
        })}
        {!loading && authors.length === 0 && (
          <li className="py-3 text-sm text-slate-500">Sin resultados.</li>
        )}
      </ul>
    </div>
  );
}
