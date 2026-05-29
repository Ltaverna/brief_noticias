import { api } from "@/lib/api";
import { ClusterCard } from "@/components/ClusterCard";
import { Footer } from "@/components/Footer";
import { RefreshButton } from "@/components/RefreshButton";
import { TopicChips } from "@/components/TopicChips";

export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string }>;
}) {
  const sp = await searchParams;
  const topic = sp.topic ?? null;

  const [briefing, sources] = await Promise.all([
    api.getTodayBriefing({ topic: topic ?? undefined }),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:py-12">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-tight md:text-5xl">
              Briefing del día
            </h1>
            <p className="mt-2 text-base text-stone-600 first-letter:capitalize dark:text-stone-400">
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

        <div className="mt-6">
          <TopicChips basePath="/" current={topic} />
        </div>

        {briefing.clusters.length === 0 ? (
          <p className="mt-10 rounded-md border border-dashed border-stone-300 p-6 text-center text-stone-600 dark:border-stone-700 dark:text-stone-400">
            {topic
              ? `No hay noticias de "${topic}" para hoy.`
              : "Briefing no generado todavía. Tocá "}
            {!topic && <strong>Actualizar</strong>}
            {!topic && " para correr el pipeline."}
          </p>
        ) : (
          <ul className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
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
