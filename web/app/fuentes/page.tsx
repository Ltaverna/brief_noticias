import { api } from "@/lib/api";
import { SourceToggle } from "@/components/SourceToggle";

export const dynamic = "force-dynamic";

const groupLabel: Record<string, string> = {
  mainstream: "Mainstream",
  critico: "Crítico",
  economico: "Económico",
};

export default async function FuentesPage() {
  const sources = await api.getSources();
  const groups = sources.reduce<Record<string, typeof sources>>((acc, s) => {
    (acc[s.editorial_group] ??= []).push(s);
    return acc;
  }, {});

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-3xl font-serif font-bold">Fuentes</h1>
      {Object.entries(groups).map(([group, items]) => (
        <section key={group} className="mt-6">
          <h2 className="text-lg font-serif font-semibold">{groupLabel[group] ?? group}</h2>
          <ul className="mt-3 space-y-2">
            {items.map((s) => (
              <li
                key={s.slug}
                className="flex items-center justify-between rounded-md border border-stone-200 px-4 py-3 dark:border-stone-800"
              >
                <div>
                  <p className="font-medium">{s.name}</p>
                  <p className="font-mono text-xs text-stone-500">{s.slug}</p>
                </div>
                <SourceToggle slug={s.slug} enabled={s.enabled} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </main>
  );
}
