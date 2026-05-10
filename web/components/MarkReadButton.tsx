"use client";

import { useReadState } from "./ReadStateProvider";

export function MarkReadButton({ clusterId }: { clusterId: number }) {
  const { isRead, toggle } = useReadState();
  const read = isRead(clusterId);

  return (
    <button
      type="button"
      onClick={() => toggle(clusterId)}
      className={`rounded-md px-3 py-2 min-h-[44px] text-sm font-medium transition ${
        read
          ? "bg-emerald-100 text-emerald-900 hover:bg-emerald-200 dark:bg-emerald-900 dark:text-emerald-100"
          : "bg-stone-200 text-stone-700 hover:bg-stone-300 dark:bg-stone-800 dark:text-stone-300"
      }`}
    >
      {read ? "✓ Leído" : "Marcar leído"}
    </button>
  );
}
