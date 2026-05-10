"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function SourceToggle({
  slug,
  enabled: initial,
}: {
  slug: string;
  enabled: boolean;
}) {
  const [enabled, setEnabled] = useState(initial);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function toggle() {
    setLoading(true);
    const next = !enabled;
    try {
      const res = await fetch(`/api/sources/${slug}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: next }),
      });
      if (res.ok) {
        setEnabled(next);
        router.refresh();
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={loading}
      className={`rounded-md px-3 py-1 text-sm font-medium transition ${
        enabled
          ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100"
          : "bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-400"
      } disabled:opacity-50`}
    >
      {enabled ? "Activo" : "Apagado"}
    </button>
  );
}
