"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { RunDetail } from "@/lib/types";

type State =
  | { kind: "idle" }
  | { kind: "running"; runId: number | null; phase: string }
  | { kind: "error"; message: string };

const TERMINAL = new Set<RunDetail["status"]>(["success", "partial", "failed"]);

export function RefreshButton() {
  const [state, setState] = useState<State>({ kind: "idle" });
  const pollRef = useRef<number | null>(null);
  const router = useRouter();

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  function startPolling(runId: number | null) {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      const url = runId ? `/api/runs/${runId}` : "/api/runs/current";
      const res = await fetch(url);
      if (!res.ok) return;
      const run = (await res.json()) as RunDetail | null;
      if (!run) return;
      const phase = describePhase(run);
      setState({ kind: "running", runId: run.id, phase });
      if (TERMINAL.has(run.status)) {
        if (pollRef.current) window.clearInterval(pollRef.current);
        if (run.status === "failed") {
          setState({ kind: "error", message: run.error ?? "Falló el pipeline" });
        } else {
          setState({ kind: "idle" });
          router.refresh();
        }
      }
    }, 2000);
  }

  async function trigger() {
    setState({ kind: "running", runId: null, phase: "Encolando..." });
    const res = await fetch("/api/refresh", { method: "POST" });
    if (res.status === 202 || res.status === 409) {
      const body = await res.json().catch(() => null);
      const runId = body?.run_id ?? body?.detail?.run_id ?? null;
      startPolling(runId);
      return;
    }
    setState({ kind: "error", message: `Error ${res.status}` });
  }

  return (
    <div className="flex items-center gap-3">
      {state.kind === "error" && (
        <span className="text-sm text-red-600 dark:text-red-400">{state.message}</span>
      )}
      {state.kind === "running" && (
        <span className="text-sm text-stone-600 dark:text-stone-400">{state.phase}</span>
      )}
      <button
        type="button"
        onClick={trigger}
        disabled={state.kind === "running"}
        className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700 disabled:opacity-50 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-300"
      >
        {state.kind === "running" ? "Procesando..." : "Actualizar"}
      </button>
    </div>
  );
}

function describePhase(run: RunDetail): string {
  if (run.status === "queued") return "En cola...";
  if (run.status === "running") {
    const stats = run.stats as Record<string, number> | null;
    if (stats?.analyzed && stats.analyzed > 0) return `Analizando (${stats.analyzed})...`;
    if (stats?.embedded && stats.embedded > 0) return `Generando embeddings...`;
    if (stats?.persisted && stats.persisted > 0) return `Recolectando notas...`;
    return "Procesando...";
  }
  return run.status;
}
