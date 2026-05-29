"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getAuthorArticles, type AuthorArticle } from "@/lib/authors";

export function AuthorArticlesList({ slug }: { slug: string }) {
  const [arts, setArts] = useState<AuthorArticle[]>([]);

  useEffect(() => {
    getAuthorArticles(slug, 50)
      .then(d => setArts(d.articles ?? []))
      .catch(() => setArts([]));
  }, [slug]);

  return (
    <ul className="space-y-2">
      {arts.map(a => (
        <li key={a.id} className="text-sm">
          {a.cluster_id ? (
            <Link href={`/cluster/${a.cluster_id}`} className="hover:underline">{a.title}</Link>
          ) : (
            <span>{a.title}</span>
          )}
          {a.published_at && (
            <span className="text-xs text-slate-500 ml-2">
              {new Date(a.published_at).toLocaleDateString()}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
