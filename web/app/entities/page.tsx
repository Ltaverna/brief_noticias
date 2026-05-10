import { api } from "@/lib/api";
import { EntityChip } from "@/components/EntityChip";

export const dynamic = "force-dynamic";

const KINDS = [
  { slug: "", label: "Todas" },
  { slug: "person", label: "Personas" },
  { slug: "org", label: "Organizaciones" },
  { slug: "place", label: "Lugares" },
  { slug: "event", label: "Eventos" },
];

export default async function EntitiesPage({
  searchParams,
}: {
  searchParams: Promise<{ kind?: string; q?: string }>;
}) {
  const sp = await searchParams;
  const entities = await api.getEntities({ kind: sp.kind, q: sp.q, limit: 100 });

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-3xl font-serif font-bold">Entidades</h1>
      <div className="mt-4 flex flex-wrap gap-2">
        {KINDS.map((k) => (
          <a
            key={k.slug || "all"}
            href={k.slug ? `/entities?kind=${k.slug}` : "/entities"}
            className={`rounded-full px-3 py-1 text-sm ${
              (sp.kind ?? "") === k.slug
                ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                : "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300"
            }`}
          >
            {k.label}
          </a>
        ))}
      </div>
      <ul className="mt-6 space-y-2">
        {entities.map((e) => (
          <li key={e.id}>
            <a
              href={`/entities/${e.id}`}
              className="flex items-center justify-between rounded-md border border-stone-200 px-4 py-3 hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
            >
              <span className="flex items-center gap-2">
                <EntityChip id={e.id} name={e.name} kind={e.kind} />
              </span>
              <span className="text-xs text-stone-500">
                {e.cluster_count}{" "}
                {e.cluster_count === 1 ? "cluster" : "clusters"}
              </span>
            </a>
          </li>
        ))}
      </ul>
      {entities.length === 0 && (
        <p className="mt-8 text-center text-stone-500 dark:text-stone-400">
          No hay entidades registradas aún.
        </p>
      )}
    </main>
  );
}
