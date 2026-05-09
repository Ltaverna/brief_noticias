import { api } from "@/lib/api";
import { ClusterCard } from "@/components/ClusterCard";
import { Footer } from "@/components/Footer";

export const dynamic = "force-dynamic";

export default async function BriefingByDatePage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const [briefing, sources] = await Promise.all([
    api.getBriefingByDate(date),
    api.getSources(),
  ]);
  const sourcesById = new Map(sources.map((s) => [s.slug, s]));

  return (
    <>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <h1 className="text-3xl font-serif font-bold">
          Briefing del{" "}
          {new Date(briefing.date).toLocaleDateString("es-AR", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </h1>
        <ul className="mt-6 grid gap-4 md:grid-cols-2">
          {briefing.clusters.map((c) => (
            <li key={c.id}>
              <ClusterCard cluster={c} sourcesById={sourcesById} />
            </li>
          ))}
        </ul>
      </main>
      <Footer generatedAt={briefing.generated_at} />
    </>
  );
}
