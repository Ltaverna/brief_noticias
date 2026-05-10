import Link from "next/link";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SagasPage() {
  const sagas = await api.getSagas();
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-3xl font-serif font-bold">Sagas activas</h1>
      <p className="mt-1 text-stone-600 dark:text-stone-400">
        Historias en desarrollo a través de varios días
      </p>
      {sagas.length === 0 ? (
        <p className="mt-8 text-stone-500">No hay sagas activas en este momento.</p>
      ) : (
        <ul className="mt-6 space-y-3">
          {sagas.map((s) => (
            <li key={s.id}>
              <Link
                href={`/saga/${s.id}`}
                className="block rounded-md border border-stone-200 px-4 py-3 hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
              >
                <p className="font-serif text-lg leading-snug">{s.title}</p>
                <p className="mt-1 text-sm text-stone-500">
                  {s.cluster_count} clusters · {s.source_count} diarios ·{" "}
                  {s.article_count} artículos
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
