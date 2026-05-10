"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { QACitation, QAResponse } from "@/lib/types";
import {
  clearConversation,
  getConversationId,
  setConversationId,
} from "@/lib/qa-session";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Turn {
  role: "user" | "assistant";
  content: string;
  data?: QAResponse; // only on assistant turns
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function QAPage() {
  const [query, setQuery] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConvId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // On mount: restore conversation from localStorage and load history
  useEffect(() => {
    const stored = getConversationId();
    if (!stored) return;
    setConvId(stored);
    api.getQAHistory(stored).then((msgs) => {
      const restored: Turn[] = [];
      for (const m of msgs) {
        if (m.role === "user") {
          restored.push({ role: "user", content: m.content });
        } else {
          // Re-construct a minimal QAResponse-like object for rendering
          const fakeResponse: QAResponse = {
            query: "",
            answer: m.content,
            used_citations: m.used_citations ?? [],
            citations: (m.citations as QACitation[] | null) ?? [],
            conversation_id: stored,
          };
          restored.push({ role: "assistant", content: m.content, data: fakeResponse });
        }
      }
      setTurns(restored);
    });
  }, []);

  // Scroll to bottom when turns change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 3 || loading) return;

    setError(null);
    setLoading(true);
    setTurns((prev) => [...prev, { role: "user", content: q }]);
    setQuery("");

    try {
      const data = await api.askQA(q, conversationId);
      setConvId(data.conversation_id);
      setConversationId(data.conversation_id);
      setTurns((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, data },
      ]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error desconocido";
      setError(msg);
      // Remove the optimistic user turn on error
      setTurns((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }

  function handleNewConversation() {
    clearConversation();
    setConvId(null);
    setTurns([]);
    setError(null);
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-3xl font-serif font-bold">Preguntar al corpus</h1>
          <p className="mt-1 text-stone-600 dark:text-stone-400">
            Hacé una pregunta sobre las noticias indexadas. La respuesta cita los
            artículos donde se basa.
          </p>
        </div>
        {turns.length > 0 && (
          <button
            onClick={handleNewConversation}
            className="ml-4 shrink-0 rounded-md border border-stone-300 px-3 py-1.5 text-xs text-stone-600 transition hover:border-stone-500 hover:text-stone-900 dark:border-stone-700 dark:text-stone-400 dark:hover:border-stone-500 dark:hover:text-stone-100"
          >
            Nueva conversación
          </button>
        )}
      </div>

      {/* Conversation thread */}
      {turns.length > 0 && (
        <div className="mt-8 space-y-6">
          {turns.map((turn, i) =>
            turn.role === "user" ? (
              <UserBubble key={i} content={turn.content} />
            ) : (
              <AssistantBubble key={i} data={turn.data!} />
            ),
          )}
          {loading && <ThinkingIndicator />}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Empty state */}
      {turns.length === 0 && !loading && (
        <div className="mt-12 text-center text-stone-400 dark:text-stone-500">
          <p className="text-sm">Hacé tu primera pregunta abajo.</p>
        </div>
      )}

      {error && (
        <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {/* Input form — pinned at the bottom visually but in normal flow */}
      <form onSubmit={onSubmit} className="mt-8 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
          placeholder={
            turns.length > 0
              ? "Pregunta de seguimiento..."
              : "Ej: ¿Qué dijo La Nación esta semana sobre Adorni?"
          }
          className="flex-1 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm placeholder:text-stone-400 focus:border-stone-500 focus:outline-none disabled:opacity-50 dark:border-stone-700 dark:bg-stone-900 dark:placeholder:text-stone-500"
        />
        <button
          type="submit"
          disabled={loading || query.trim().length < 3}
          className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700 disabled:opacity-50 dark:bg-stone-100 dark:text-stone-900"
        >
          {loading ? "Pensando..." : "Preguntar"}
        </button>
      </form>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Bubble components
// ---------------------------------------------------------------------------

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-stone-900 px-4 py-3 text-sm text-white dark:bg-stone-100 dark:text-stone-900">
        {content}
      </div>
    </div>
  );
}

function AssistantBubble({ data }: { data: QAResponse }) {
  const citationsByN = new Map(data.citations.map((c) => [c.n, c]));

  return (
    <div className="flex justify-start">
      <div className="max-w-[95%] space-y-4">
        <div className="rounded-2xl rounded-bl-sm bg-stone-100 px-4 py-3 text-sm leading-relaxed text-stone-900 dark:bg-stone-800 dark:text-stone-100">
          {renderAnswerWithRefs(data.answer, citationsByN)}
        </div>

        {data.used_citations.length > 0 && (
          <CitationList citations={data.citations} usedCitations={data.used_citations} />
        )}
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl rounded-bl-sm bg-stone-100 px-4 py-3 dark:bg-stone-800">
        <span className="inline-flex gap-1 text-stone-400 dark:text-stone-500">
          <span className="animate-bounce [animation-delay:0ms]">●</span>
          <span className="animate-bounce [animation-delay:150ms]">●</span>
          <span className="animate-bounce [animation-delay:300ms]">●</span>
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Citations
// ---------------------------------------------------------------------------

function CitationList({
  citations,
  usedCitations,
}: {
  citations: QACitation[];
  usedCitations: number[];
}) {
  const citationsByN = new Map(citations.map((c) => [c.n, c]));

  return (
    <section className="pl-1">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-stone-500">
        Fuentes citadas
      </h2>
      <ol className="mt-2 space-y-2 text-xs">
        {usedCitations.map((n) => {
          const c = citationsByN.get(n);
          if (!c) return null;
          return (
            <li id={`cite-${n}`} key={n}>
              <span className="font-mono text-stone-400">[{n}]</span>{" "}
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium hover:underline"
              >
                {c.title}
              </a>{" "}
              <span className="text-stone-400">
                ({c.source_name}
                {c.published_at &&
                  ", " + new Date(c.published_at).toLocaleDateString("es-AR")}
                )
              </span>
              {c.cluster_id && (
                <>
                  {" · "}
                  <Link
                    href={`/cluster/${c.cluster_id}`}
                    className="text-stone-400 hover:underline"
                  >
                    ver cluster
                  </Link>
                </>
              )}
              <p className="mt-0.5 italic text-stone-400">
                &ldquo;{c.snippet}&hellip;&rdquo;
              </p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Inline citation rendering
// ---------------------------------------------------------------------------

function renderAnswerWithRefs(
  answer: string,
  citationsByN: Map<number, QACitation>,
): ReactNode {
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
            ? "rounded bg-stone-300 px-1 py-0.5 font-mono text-xs text-stone-700 hover:bg-stone-400 dark:bg-stone-600 dark:text-stone-200 dark:hover:bg-stone-500"
            : "rounded bg-red-100 px-1 py-0.5 font-mono text-xs text-red-700"
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
