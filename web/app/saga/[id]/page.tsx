import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SagaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sid = Number(id);
  if (!Number.isInteger(sid)) notFound();
  const saga = await api.getSaga(sid);
  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <Link href="/sagas" className="text-sm text-stone-500 hover:underline">
        ← Sagas
      </Link>
      <h1 className="mt-2 text-3xl font-serif font-bold">{saga.title}</h1>
      <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
        {saga.cluster_count} clusters · {saga.source_count} diarios ·{" "}
        {saga.article_count} artículos
      </p>
      <ul className="mt-6 space-y-3">
        {saga.clusters.map((c) => (
          <li key={c.id}>
            <Link
              href={`/cluster/${c.id}`}
              className="block rounded-md border border-stone-200 px-4 py-3 hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
            >
              <p className="font-serif text-base">
                {c.headline ?? "(análisis pendiente)"}
              </p>
              <p className="mt-1 text-xs text-stone-500">
                {c.source_count} diarios ·{" "}
                {new Date(c.last_seen_at).toLocaleDateString("es-AR")}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
