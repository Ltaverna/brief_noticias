import { Divergence } from "@/lib/types";

export function DivergenceTable({ divergences }: { divergences: Divergence[] }) {
  if (divergences.length === 0) {
    return (
      <p className="text-sm text-stone-500 dark:text-stone-400">
        No se detectaron divergencias significativas entre las coberturas.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-stone-300 dark:border-stone-700">
            <th className="py-2 pr-4 text-left font-medium">Tema en disputa</th>
            <th className="py-2 text-left font-medium">Posiciones</th>
          </tr>
        </thead>
        <tbody>
          {divergences.map((d, i) => (
            <tr key={i} className="border-b border-stone-200 align-top dark:border-stone-800">
              <td className="py-3 pr-4 font-medium">{d.topic}</td>
              <td className="py-3">
                <ul className="space-y-1">
                  {Object.entries(d.positions).map(([slug, stance]) => (
                    <li key={slug}>
                      <span className="font-mono text-xs text-stone-500">{slug}:</span>{" "}
                      <span>{stance}</span>
                    </li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
