import Link from "next/link";
import { notFound } from "next/navigation";

import { api } from "@/lib/api";
import { EntityChip } from "@/components/EntityChip";

export const dynamic = "force-dynamic";

export default async function EntityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const eid = Number(id);
  if (!Number.isInteger(eid)) notFound();

  let entity;
  try {
    entity = await api.getEntity(eid);
  } catch {
    notFound();
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <Link href="/entities" className="text-sm text-stone-500 hover:underline">
        ← Entidades
      </Link>
      <div className="mt-2">
        <EntityChip id={entity.id} name={entity.name} kind={entity.kind} />
      </div>
      <h1 className="mt-2 text-3xl font-serif font-bold">{entity.name}</h1>
      <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
        Mencionada en {entity.cluster_count}{" "}
        {entity.cluster_count === 1 ? "cluster" : "clusters"}
      </p>
      <ul className="mt-6 space-y-3">
        {entity.clusters.map((c) => (
          <li key={c.id}>
            <Link
              href={`/cluster/${c.id}`}
              className="block rounded-md border border-stone-200 px-4 py-3 hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
            >
              <p className="font-serif">
                {c.headline ?? "(análisis pendiente)"}
              </p>
              <p className="mt-1 text-xs text-stone-500">
                {c.source_count} diarios &middot;{" "}
                {new Date(c.last_seen_at).toLocaleDateString("es-AR")}
                {c.is_top && " · 🎯 Top"}
              </p>
            </Link>
          </li>
        ))}
      </ul>
      {entity.clusters.length === 0 && (
        <p className="mt-4 text-stone-500 dark:text-stone-400">
          No hay clusters vinculados a esta entidad.
        </p>
      )}
    </main>
  );
}
