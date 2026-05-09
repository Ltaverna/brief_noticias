"use client";

import { useState } from "react";

import { BySourceAnalysis, EditorialGroup, SourceListItem } from "@/lib/types";

interface Props {
  bySource: Record<string, BySourceAnalysis>;
  sourcesById: Map<string, SourceListItem>;
}

const groupClasses: Record<EditorialGroup, string> = {
  mainstream: "bg-mainstream-bg text-mainstream-fg",
  critico: "bg-critico-bg text-critico-fg",
  economico: "bg-economico-bg text-economico-fg",
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
      <div className={`mt-4 rounded-md p-5 ${groupClasses[group]}`}>
        <p className="text-xs font-semibold uppercase tracking-wide opacity-70">
          Tono: {data.tone}
        </p>
        <p className="mt-3 text-base leading-relaxed italic">{data.framing}</p>
        <ul className="mt-4 space-y-2 text-sm leading-relaxed">
          {data.highlights.map((h, i) => (
            <li key={i} className="flex gap-2">
              <span className="select-none opacity-60">▸</span>
              <span>{h}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
