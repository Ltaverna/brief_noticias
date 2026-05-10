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

interface ToneStyle {
  label: string;
  badge: string;
  accent: string;
  dot: string;
}

const TONE_STYLES: Record<string, ToneStyle> = {
  favorable: {
    label: "A favor",
    badge: "bg-emerald-200 text-emerald-900",
    accent: "border-l-4 border-emerald-500",
    dot: "bg-emerald-500",
  },
  celebratorio: {
    label: "Celebratorio",
    badge: "bg-emerald-200 text-emerald-900",
    accent: "border-l-4 border-emerald-500",
    dot: "bg-emerald-500",
  },
  crítico: {
    label: "Crítico",
    badge: "bg-rose-200 text-rose-900",
    accent: "border-l-4 border-rose-500",
    dot: "bg-rose-500",
  },
  critico: {
    label: "Crítico",
    badge: "bg-rose-200 text-rose-900",
    accent: "border-l-4 border-rose-500",
    dot: "bg-rose-500",
  },
  escéptico: {
    label: "Escéptico",
    badge: "bg-amber-200 text-amber-900",
    accent: "border-l-4 border-amber-500",
    dot: "bg-amber-500",
  },
  esceptico: {
    label: "Escéptico",
    badge: "bg-amber-200 text-amber-900",
    accent: "border-l-4 border-amber-500",
    dot: "bg-amber-500",
  },
  alarmista: {
    label: "Alarmista",
    badge: "bg-orange-200 text-orange-900",
    accent: "border-l-4 border-orange-500",
    dot: "bg-orange-500",
  },
  neutral: {
    label: "Neutral",
    badge: "bg-stone-300 text-stone-800",
    accent: "border-l-4 border-stone-400",
    dot: "bg-stone-400",
  },
};

const FALLBACK_TONE: ToneStyle = {
  label: "Otro",
  badge: "bg-stone-300 text-stone-800",
  accent: "border-l-4 border-stone-400",
  dot: "bg-stone-400",
};

function toneStyle(tone: string): ToneStyle {
  const key = tone.trim().toLowerCase();
  return TONE_STYLES[key] ?? FALLBACK_TONE;
}

export function SourceTabs({ bySource, sourcesById }: Props) {
  const slugs = Object.keys(bySource);
  const [active, setActive] = useState(slugs[0] ?? "");
  if (slugs.length === 0) return null;

  const data = bySource[active];
  const src = sourcesById.get(active);
  const group = (src?.editorial_group ?? "mainstream") as EditorialGroup;
  const tone = toneStyle(data.tone);

  return (
    <div>
      <div className="flex flex-wrap gap-1 border-b border-stone-200 dark:border-stone-800">
        {slugs.map((slug) => {
          const t = toneStyle(bySource[slug].tone);
          return (
            <button
              key={slug}
              type="button"
              onClick={() => setActive(slug)}
              className={`flex items-center gap-2 px-3 py-2 text-sm font-medium ${
                active === slug
                  ? "border-b-2 border-stone-900 text-stone-900 dark:border-stone-100 dark:text-stone-100"
                  : "text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
              }`}
              title={`Tono: ${t.label}`}
            >
              <span className={`inline-block h-2 w-2 rounded-full ${t.dot}`} />
              {sourcesById.get(slug)?.name ?? slug}
            </button>
          );
        })}
      </div>
      <div className={`mt-4 rounded-md p-5 ${groupClasses[group]} ${tone.accent}`}>
        <span
          className={`inline-block rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${tone.badge}`}
        >
          {tone.label}
        </span>
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
