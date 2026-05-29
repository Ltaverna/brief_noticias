"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { listAuthors, type AuthorListItem } from "@/lib/authors";

export default function AuthorsPage() {
  const [authors, setAuthors] = useState<AuthorListItem[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listAuthors({ q: q || undefined, order: "articles_desc", limit: 100 })
      .then(r => setAuthors(r.authors))
      .finally(() => setLoading(false));
  }, [q]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Autores</h1>
      <input
        type="search"
        placeholder="Buscar autor..."
        value={q}
        onChange={e => setQ(e.target.value)}
        className="w-full mb-4 px-3 py-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900"
      />
      {loading && <p className="text-slate-500">Cargando…</p>}
      <ul className="divide-y divide-slate-200 dark:divide-slate-800">
        {authors.map(a => (
          <li key={a.id} className="py-3 flex justify-between items-baseline">
            <Link href={`/authors/${a.slug}`} className="hover:underline">
              <span className={a.is_synthetic ? "text-slate-500 italic" : "font-medium"}>
                {a.name}
              </span>
              {a.source_slug && (
                <span className="text-xs text-slate-500 ml-2">{a.source_slug}</span>
              )}
            </Link>
            <span className="text-sm text-slate-500">{a.article_count} notas</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
