"use client";

import { useState } from "react";

import { BySourceAnalysis, EditorialGroup, SourceListItem } from "@/lib/types";

interface Props {
  bySource: Record<string, BySourceAnalysis>;
  sourcesById: Map<string, SourceListItem>;
}

const groupBg: Record<EditorialGroup, string> = {
  mainstream: "bg-mainstream-bg",
  critico: "bg-critico-bg",
  economico: "bg-economico-bg",
};

export function SourceTabs({ bySource, sourcesById }: Props) {
  const slugs = Object.keys(bySource);
  const [active, setActive] = useState(slugs[0] ?? "");
  if (slugs.length === 0) return null;

  const data = bySource[active];
  const src = sourcesById.get(active);
  const group = (src?.editorial_group ?? "mainstream") as EditorialGroup;

  return (
    <div>
      <div className="flex flex-wrap gap-1 border-b border-stone-200 dark:border-stone-800">
        {slugs.map((slug) => (
          <button
            key={slug}
            type="button"
            onClick={() => setActive(slug)}
            className={`px-3 py-2 text-sm font-medium ${
              active === slug
                ? "border-b-2 border-stone-900 text-stone-900 dark:border-stone-100 dark:text-stone-100"
                : "text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
            }`}
          >
            {sourcesById.get(slug)?.name ?? slug}
          </button>
        ))}
      </div>
      <div className={`mt-4 rounded-md p-4 ${groupBg[group]}`}>
        <p className="text-xs uppercase tracking-wide opacity-70">Tono: {data.tone}</p>
        <p className="mt-2 text-sm italic">{data.framing}</p>
        <ul className="mt-3 list-inside list-disc text-sm">
          {data.highlights.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
