"use client";

import { FormEvent, useEffect, useState } from "react";

import { ClusterNote } from "@/lib/types";

export function ClusterNotes({ clusterId }: { clusterId: number }) {
  const [notes, setNotes] = useState<ClusterNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const r = await fetch(`/api/clusters/${clusterId}/notes`);
      if (r.ok) setNotes(await r.json());
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, [clusterId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setError(null);
    const r = await fetch(`/api/clusters/${clusterId}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note: text }),
    });
    if (!r.ok) {
      setError(`Error ${r.status}`);
      return;
    }
    setText("");
    await load();
  }

  async function onDelete(id: number) {
    const r = await fetch(`/api/notes/${id}`, { method: "DELETE" });
    if (r.ok || r.status === 204) await load();
  }

  return (
    <section>
      <h2 className="text-xl font-serif font-semibold">Mis notas</h2>
      <form onSubmit={onSubmit} className="mt-3 flex gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Agregar una nota..."
          maxLength={2000}
          className="flex-1 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"
        />
        <button
          type="submit"
          className="rounded-md bg-stone-900 px-3 py-2 text-sm text-white dark:bg-stone-100 dark:text-stone-900"
        >
          Guardar
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {loading ? (
        <p className="mt-4 text-sm text-stone-500">Cargando notas...</p>
      ) : notes.length === 0 ? (
        <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">
          Sin notas todavía.
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {notes.map((n) => (
            <li
              key={n.id}
              className="flex items-start justify-between gap-3 rounded-md border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
            >
              <div className="flex-1">
                <p>{n.note}</p>
                <p className="mt-1 text-xs text-stone-500">
                  {new Date(n.created_at).toLocaleString("es-AR")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onDelete(n.id)}
                className="text-xs text-red-600 hover:underline dark:text-red-400"
              >
                quitar
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
