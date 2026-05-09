import Link from "next/link";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HistorialPage() {
  const dates = await api.listBriefingDates();

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-3xl font-serif font-bold">Historial de briefings</h1>
      {dates.length === 0 ? (
        <p className="mt-6 text-stone-600 dark:text-stone-400">
          Todavía no hay briefings generados.
        </p>
      ) : (
        <ul className="mt-6 space-y-2">
          {dates.map((date) => (
            <li key={date}>
              <Link
                href={`/briefing/${date}`}
                className="block rounded-md border border-stone-200 px-4 py-3 transition hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
              >
                {new Date(date).toLocaleDateString("es-AR", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
