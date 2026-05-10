import Link from "next/link";

import { BiasScorecard } from "@/components/BiasScorecard";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function BiasPage({
  searchParams,
}: {
  searchParams: Promise<{ kind?: string }>;
}) {
  const sp = await searchParams;
  const data = await api.getBiasScorecard({
    top_entities: 8,
    kind: sp.kind ?? "person",
  });

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="text-3xl font-serif font-bold">Bias scorecard</h1>
      <p className="mt-1 text-stone-600 dark:text-stone-400">
        % de análisis favorables vs críticos por diario × entidad (últimos 30 días).
      </p>

      <nav className="mt-4 flex gap-3 text-sm">
        <Link href="/analytics" className="hover:underline">
          Trends
        </Link>
        <Link href="/analytics/bias" className="font-medium underline">
          Bias scorecard
        </Link>
      </nav>

      <div className="mt-4 flex gap-2 text-sm">
        {(["person", "org", "place", "event"] as const).map((k) => (
          <Link
            key={k}
            href={`/analytics/bias?kind=${k}`}
            className={`rounded-full px-3 py-1 ${
              (sp.kind ?? "person") === k
                ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                : "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300"
            }`}
          >
            {k === "person"
              ? "Personas"
              : k === "org"
                ? "Orgs"
                : k === "place"
                  ? "Lugares"
                  : "Eventos"}
          </Link>
        ))}
      </div>

      <div className="mt-6">
        <BiasScorecard data={data} />
      </div>
    </main>
  );
}
