"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useState } from "react";

import { api } from "@/lib/api";
import { QACitation, QAResponse } from "@/lib/types";

type State =
  | { kind: "idle" }
  | { kind: "loading"; query: string }
  | { kind: "answered"; data: QAResponse }
  | { kind: "error"; message: string };

export default function QAPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 3) return;
    setState({ kind: "loading", query: q });
    try {
      const data = await api.askQA(q);
      setState({ kind: "answered", data });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error";
      setState({ kind: "error", message: msg });
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-3xl font-serif font-bold">Preguntar al corpus</h1>
      <p className="mt-1 text-stone-600 dark:text-stone-400">
        Hacé una pregunta sobre las noticias indexadas. La respuesta cita los
        artículos donde se basa.
      </p>

      <form onSubmit={onSubmit} className="mt-6 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ej: ¿Qué dijo La Nación esta semana sobre Adorni?"
          className="flex-1 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm placeholder:text-stone-400 focus:border-stone-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900 dark:placeholder:text-stone-500"
        />
        <button
          type="submit"
          disabled={state.kind === "loading"}
          className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700 disabled:opacity-50 dark:bg-stone-100 dark:text-stone-900"
        >
          {state.kind === "loading" ? "Pensando..." : "Preguntar"}
        </button>
      </form>

      {state.kind === "loading" && (
        <p className="mt-8 text-stone-600 dark:text-stone-400">
          Analizando &ldquo;{state.query}&rdquo;...
        </p>
      )}

      {state.kind === "error" && (
        <p className="mt-8 text-red-600 dark:text-red-400">{state.message}</p>
      )}

      {state.kind === "answered" && <Answer data={state.data} />}
    </main>
  );
}

function Answer({ data }: { data: QAResponse }) {
  const citationsByN = new Map(data.citations.map((c) => [c.n, c]));
  return (
    <article className="mt-8">
      <p className="text-base leading-relaxed text-stone-900 dark:text-stone-100">
        {renderAnswerWithRefs(data.answer, citationsByN)}
      </p>

      {data.used_citations.length > 0 && (
        <section className="mt-8 border-t border-stone-200 pt-6 dark:border-stone-800">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">
            Fuentes citadas
          </h2>
          <ol className="mt-3 space-y-3 text-sm">
            {data.used_citations.map((n) => {
              const c = citationsByN.get(n);
              if (!c) return null;
              return (
                <li id={`cite-${n}`} key={n}>
                  <span className="font-mono text-xs text-stone-500">[{n}]</span>{" "}
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium hover:underline"
                  >
                    {c.title}
                  </a>{" "}
                  <span className="text-xs text-stone-500">
                    ({c.source_name}
                    {c.published_at &&
                      ", " +
                        new Date(c.published_at).toLocaleDateString("es-AR")}
                    )
                  </span>
                  {c.cluster_id && (
                    <>
                      {" · "}
                      <Link
                        href={`/cluster/${c.cluster_id}`}
                        className="text-xs text-stone-500 hover:underline"
                      >
                        ver cluster
                      </Link>
                    </>
                  )}
                  <p className="mt-1 text-xs italic text-stone-500">
                    &ldquo;{c.snippet}&hellip;&rdquo;
                  </p>
                </li>
              );
            })}
          </ol>
        </section>
      )}
    </article>
  );
}

function renderAnswerWithRefs(
  answer: string,
  citationsByN: Map<number, QACitation>,
): ReactNode {
  // Split by [N] markers and render each as a clickable footnote anchor.
  const parts: ReactNode[] = [];
  const re = /\[(\d+)\]/g;
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(answer)) !== null) {
    if (m.index > last) parts.push(answer.slice(last, m.index));
    const n = Number(m[1]);
    const exists = citationsByN.has(n);
    parts.push(
      <a
        key={key++}
        href={`#cite-${n}`}
        title={citationsByN.get(n)?.title ?? ""}
        className={
          exists
            ? "rounded-md bg-stone-200 px-1.5 py-0.5 font-mono text-xs text-stone-700 hover:bg-stone-300 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
            : "rounded-md bg-red-100 px-1.5 py-0.5 font-mono text-xs text-red-700"
        }
      >
        [{n}]
      </a>,
    );
    last = re.lastIndex;
  }
  if (last < answer.length) parts.push(answer.slice(last));
  return <>{parts}</>;
}
