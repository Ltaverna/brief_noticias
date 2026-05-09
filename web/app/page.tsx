import { api } from "@/lib/api";
import { ClusterCard } from "@/components/ClusterCard";
import { Footer } from "@/components/Footer";
import { RefreshButton } from "@/components/RefreshButton";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [briefing, sources] = await Promise.all([
    api.getTodayBriefing(),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-serif font-bold">Briefing del día</h1>
            <p className="mt-1 text-stone-600 dark:text-stone-400">
              {new Date(briefing.date).toLocaleDateString("es-AR", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          </div>
          <RefreshButton />
        </div>

        {briefing.clusters.length === 0 ? (
          <p className="mt-8 rounded-md border border-dashed border-stone-300 p-6 text-center text-stone-600 dark:border-stone-700 dark:text-stone-400">
            Briefing no generado todavía. Tocá <strong>Actualizar</strong> para correr el pipeline.
          </p>
        ) : (
          <ul className="mt-6 grid gap-4 md:grid-cols-2">
            {briefing.clusters.map((c) => (
              <li key={c.id}>
                <ClusterCard cluster={c} sourcesById={sourcesById} />
              </li>
            ))}
          </ul>
        )}
      </main>
      <Footer generatedAt={briefing.generated_at} />
    </>
  );
}
