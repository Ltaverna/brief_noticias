import { ToneTrends } from "@/lib/types";

const TONE_COLORS: Record<string, string> = {
  favorable: "#10b981",    // emerald-500
  celebratorio: "#34d399", // emerald-400
  neutral: "#a8a29e",      // stone-400
  critico: "#f43f5e",      // rose-500
  esceptico: "#fbbf24",    // amber-400
  alarmista: "#fb923c",    // orange-400
  otro: "#94a3b8",         // slate-400
};

const TONE_LABEL: Record<string, string> = {
  favorable: "Favorable",
  celebratorio: "Celebratorio",
  neutral: "Neutral",
  critico: "Crítico",
  esceptico: "Escéptico",
  alarmista: "Alarmista",
  otro: "Otro",
};

export function ToneDistributionChart({ data }: { data: ToneTrends }) {
  if (data.sources.length === 0) {
    return (
      <p className="text-sm text-stone-500 dark:text-stone-400">
        No hay datos suficientes en este rango.
      </p>
    );
  }

  // Aggregate per-source totals across all buckets (for the stacked bar)
  const bySource = new Map<string, Record<string, number>>();
  for (const src of data.sources) {
    const totals: Record<string, number> = {};
    const buckets = data.data[src] ?? {};
    for (const bk of Object.keys(buckets)) {
      for (const tone of Object.keys(buckets[bk])) {
        totals[tone] = (totals[tone] ?? 0) + buckets[bk][tone];
      }
    }
    bySource.set(src, totals);
  }

  return (
    <div className="space-y-3">
      {data.sources.map((src) => {
        const totals = bySource.get(src) ?? {};
        const total = Object.values(totals).reduce((s, n) => s + n, 0);
        if (total === 0) return null;
        return (
          <div key={src}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-mono">{src}</span>
              <span className="text-xs text-stone-500">{total} análisis</span>
            </div>
            <div className="flex h-6 w-full overflow-hidden rounded-md">
              {data.tones.map((tone) => {
                const count = totals[tone] ?? 0;
                if (count === 0) return null;
                const pct = (count / total) * 100;
                return (
                  <div
                    key={tone}
                    title={`${TONE_LABEL[tone] ?? tone}: ${count} (${pct.toFixed(0)}%)`}
                    style={{ width: `${pct}%`, backgroundColor: TONE_COLORS[tone] ?? "#888" }}
                  />
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-3 pt-3 text-xs">
        {data.tones.map((tone) => (
          <div key={tone} className="flex items-center gap-1.5">
            <span
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: TONE_COLORS[tone] ?? "#888" }}
            />
            <span>{TONE_LABEL[tone] ?? tone}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
