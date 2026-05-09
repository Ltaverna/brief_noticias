import Link from "next/link";

import { ToneDistributionChart } from "@/components/ToneDistributionChart";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AnalyticsPage({
  searchParams,
}: {
  searchParams: Promise<{ entity?: string; bucket?: "week" | "day" }>;
}) {
  const sp = await searchParams;
  const data = await api.getToneTrends({
    entity: sp.entity,
    bucket: sp.bucket ?? "week",
  });

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-3xl font-serif font-bold">Análisis de tono</h1>
      <p className="mt-1 text-stone-600 dark:text-stone-400">
        Distribución de tonos por diario en los últimos 30 días
        {sp.entity ? ` para "${sp.entity}"` : " (todos los temas)"}.
      </p>

      <nav className="mt-4 flex gap-3 text-sm">
        <Link href="/analytics" className="font-medium underline">
          Trends
        </Link>
        <Link href="/analytics/bias" className="hover:underline">
          Bias scorecard
        </Link>
      </nav>

      <div className="mt-4 flex gap-2 text-sm">
        {(["week", "day"] as const).map((b) => (
          <Link
            key={b}
            href={`/analytics?bucket=${b}${sp.entity ? `&entity=${encodeURIComponent(sp.entity)}` : ""}`}
            className={`rounded-full px-3 py-1 ${
              (sp.bucket ?? "week") === b
                ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                : "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300"
            }`}
          >
            {b === "week" ? "Semana" : "Día"}
          </Link>
        ))}
      </div>

      <div className="mt-8">
        <ToneDistributionChart data={data} />
      </div>
    </main>
  );
}
