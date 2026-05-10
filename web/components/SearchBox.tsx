"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

interface SearchBoxProps {
  /** When true, always visible and full-width (e.g. on the /search page) */
  fullWidth?: boolean;
  initialQuery?: string;
}

export function SearchBox({ fullWidth = false, initialQuery = "" }: SearchBoxProps) {
  const [q, setQ] = useState(initialQuery);
  const router = useRouter();

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = q.trim();
    if (trimmed.length < 2) return;
    router.push(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  return (
    <form onSubmit={onSubmit} className={fullWidth ? "w-full" : "hidden md:block"}>
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Buscar..."
        className={`rounded-md border border-stone-300 bg-white/70 px-3 py-2 text-sm placeholder:text-stone-400 focus:border-stone-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900/70 dark:placeholder:text-stone-500 ${
          fullWidth ? "w-full" : "w-48 lg:w-64"
        }`}
      />
    </form>
  );
}
