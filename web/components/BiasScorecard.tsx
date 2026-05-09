import { BiasScorecard as Data } from "@/lib/types";

function pct(n: number, total: number): string {
  if (total === 0) return "—";
  return `${Math.round((n / total) * 100)}%`;
}

function classify(cell: Data["rows"][0]["cells"][string]): string {
  if (cell.total === 0) return "bg-stone-100 dark:bg-stone-900";
  const fav = cell.favorable / cell.total;
  const crit = cell.critico / cell.total;
  if (fav >= 0.5 && fav > crit + 0.2) return "bg-emerald-200 dark:bg-emerald-900";
  if (crit >= 0.5 && crit > fav + 0.2) return "bg-rose-200 dark:bg-rose-900";
  if (fav > crit) return "bg-emerald-100 dark:bg-emerald-950";
  if (crit > fav) return "bg-rose-100 dark:bg-rose-950";
  return "bg-stone-100 dark:bg-stone-900";
}

export function BiasScorecard({ data }: { data: Data }) {
  if (data.entities.length === 0 || data.rows.length === 0) {
    return (
      <p className="text-sm text-stone-500 dark:text-stone-400">
        No hay datos suficientes en este rango.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="sticky left-0 bg-white px-3 py-2 text-left font-medium dark:bg-stone-950">
              Diario
            </th>
            {data.entities.map((e) => (
              <th key={e.canonical} className="px-3 py-2 text-left font-medium">
                {e.name}
                <span className="ml-1 text-xs text-stone-500">({e.cluster_count})</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.source} className="border-t border-stone-200 dark:border-stone-800">
              <td className="sticky left-0 bg-white px-3 py-2 font-mono text-xs dark:bg-stone-950">
                {row.source}
              </td>
              {data.entities.map((e) => {
                const cell = row.cells[e.canonical];
                if (!cell) {
                  return (
                    <td key={e.canonical} className="px-3 py-2 text-stone-400">
                      —
                    </td>
                  );
                }
                return (
                  <td
                    key={e.canonical}
                    className={`px-3 py-2 align-top ${classify(cell)}`}
                    title={`${cell.total} análisis · favorable=${cell.favorable} crítico=${cell.critico} neutral=${cell.neutral} otro=${cell.other}`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-700 dark:text-emerald-300">
                        🟢{pct(cell.favorable, cell.total)}
                      </span>
                      <span className="text-rose-700 dark:text-rose-300">
                        🔴{pct(cell.critico, cell.total)}
                      </span>
                    </div>
                    <div className="text-xs text-stone-500">{cell.total}</div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
