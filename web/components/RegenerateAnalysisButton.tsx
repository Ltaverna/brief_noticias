"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function RegenerateAnalysisButton({ clusterId }: { clusterId: number }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function regen() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`/api/clusters/${clusterId}/regenerate-analysis`, {
        method: "POST",
      });
      if (!r.ok) throw new Error(`Error ${r.status}`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={regen}
        disabled={loading}
        className="rounded-md bg-amber-100 px-3 py-2 min-h-[44px] text-sm font-medium text-amber-900 transition hover:bg-amber-200 disabled:opacity-50 dark:bg-amber-900 dark:text-amber-100 dark:hover:bg-amber-800"
        title="Reemplaza el análisis IA actual con uno nuevo (cuesta una llamada a GPT-4o)"
      >
        {loading ? "Regenerando..." : "↻ Regenerar análisis"}
      </button>
      {error && (
        <span className="text-xs text-red-600 dark:text-red-400">{error}</span>
      )}
    </span>
  );
}
