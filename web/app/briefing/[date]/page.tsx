import { api } from "@/lib/api";
import { ClusterCard } from "@/components/ClusterCard";
import { Footer } from "@/components/Footer";
import { TopicChips } from "@/components/TopicChips";

export const dynamic = "force-dynamic";

export default async function BriefingByDatePage({
  params,
  searchParams,
}: {
  params: Promise<{ date: string }>;
  searchParams: Promise<{ topic?: string }>;
}) {
  const { date } = await params;
  const sp = await searchParams;
  const topic = sp.topic ?? null;

  const [briefing, sources] = await Promise.all([
    api.getBriefingByDate(date, { topic: topic ?? undefined }),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <h1 className="text-3xl font-serif font-bold">
          Briefing del{" "}
          {new Date(briefing.date).toLocaleDateString("es-AR", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </h1>

        <div className="mt-4">
          <TopicChips basePath={`/briefing/${date}`} current={topic} />
        </div>

        {briefing.clusters.length === 0 ? (
          <p className="mt-8 rounded-md border border-dashed border-stone-300 p-6 text-center text-stone-600 dark:border-stone-700 dark:text-stone-400">
            {topic
              ? `No hay noticias de "${topic}" para esta fecha.`
              : "No hay briefing para esta fecha."}
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
