"use client";

import { FormEvent, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Subscription } from "@/lib/types";

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // form state
  const [kind, setKind] = useState<"entity" | "topic" | "all">("entity");
  const [value, setValue] = useState("");
  const [threshold, setThreshold] = useState<string>("");

  async function refresh() {
    setLoading(true);
    try {
      setSubs(await api.getSubscriptions());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.addSubscription({
        kind,
        value: kind === "all" ? undefined : value.trim(),
        alert_threshold_sources: threshold ? Number(threshold) : undefined,
      });
      setValue("");
      setThreshold("");
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    }
  }

  async function onDelete(id: number) {
    try {
      await api.deleteSubscription(id);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <h1 className="text-3xl font-serif font-bold">Suscripciones</h1>
      <p className="mt-1 text-stone-600 dark:text-stone-400">
        Filtrá el digest de Telegram a temas/entidades específicas, y opcionalmente activá alertas
        cuando un cluster cruza un umbral de fuentes.
      </p>

      <form
        onSubmit={onSubmit}
        className="mt-6 space-y-3 rounded-md border border-stone-200 p-4 dark:border-stone-800"
      >
        <h2 className="font-semibold">Agregar</h2>
        <div className="flex flex-col gap-2 text-sm sm:flex-row sm:flex-wrap">
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as typeof kind)}
            className="w-full rounded-md border border-stone-300 bg-white px-2 py-2.5 min-h-[44px] dark:border-stone-700 dark:bg-stone-900 sm:w-auto"
          >
            <option value="entity">Entidad</option>
            <option value="topic">Tema</option>
            <option value="all">Todo (sin filtro)</option>
          </select>

          {kind !== "all" && (
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={kind === "entity" ? "ej: manuel adorni" : "ej: política"}
              className="w-full rounded-md border border-stone-300 bg-white px-2 py-2.5 min-h-[44px] dark:border-stone-700 dark:bg-stone-900 sm:flex-1 sm:min-w-[180px]"
            />
          )}

          <input
            type="number"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            placeholder="alerta ≥ N fuentes"
            min={2}
            max={20}
            className="w-full rounded-md border border-stone-300 bg-white px-2 py-2.5 min-h-[44px] dark:border-stone-700 dark:bg-stone-900 sm:w-36"
          />

          <button
            type="submit"
            className="w-full rounded-md bg-stone-900 px-3 py-2.5 min-h-[44px] text-sm font-medium text-white dark:bg-stone-100 dark:text-stone-900 sm:w-auto"
          >
            Agregar
          </button>
        </div>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </form>

      <h2 className="mt-8 font-semibold">Activas</h2>
      {loading && <p className="mt-2 text-stone-500">Cargando...</p>}
      {!loading && subs.length === 0 && (
        <p className="mt-2 text-stone-500 dark:text-stone-400">
          No tenés suscripciones. El digest sale completo.
        </p>
      )}
      <ul className="mt-3 space-y-2">
        {subs.map((s) => (
          <li
            key={s.id}
            className="flex items-center justify-between rounded-md border border-stone-200 px-4 py-3 text-sm dark:border-stone-800"
          >
            <div className="min-w-0 flex-1 pr-3">
              <span className="font-mono text-xs text-stone-500">{s.kind}</span>{" "}
              <span className="font-medium">{s.value ?? "(sin filtro)"}</span>
              {s.alert_threshold_sources != null && (
                <span className="ml-2 text-xs text-amber-700 dark:text-amber-300">
                  alerta &ge; {s.alert_threshold_sources} fuentes
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => onDelete(s.id)}
              className="shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center text-xs text-red-600 hover:underline dark:text-red-400"
            >
              quitar
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
