import Link from "next/link";

export const TOPIC_LABELS: Record<string, string> = {
  politica: "Política",
  economia: "Economía",
  deportes: "Deportes",
  internacional: "Internacional",
  sociedad: "Sociedad",
  espectaculos: "Espectáculos",
  otros: "Otros",
};

export const TOPIC_ORDER = [
  "politica",
  "economia",
  "internacional",
  "sociedad",
  "deportes",
  "espectaculos",
  "otros",
];

export function TopicChips({
  basePath,
  current,
}: {
  basePath: string;
  current: string | null;
}) {
  const baseChip =
    "cursor-pointer rounded-full px-3.5 py-1.5 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-stone-400 dark:focus:ring-stone-600 dark:focus:ring-offset-stone-950";
  const activeChip =
    "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900";
  const inactiveChip =
    "bg-stone-200/70 text-stone-700 hover:bg-stone-300 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700";

  return (
    <div className="flex flex-wrap gap-2 text-sm">
      <Link
        href={basePath}
        className={`${baseChip} ${!current ? activeChip : inactiveChip}`}
      >
        Todas
      </Link>
      {TOPIC_ORDER.map((t) => (
        <Link
          key={t}
          href={`${basePath}?topic=${t}`}
          className={`${baseChip} ${current === t ? activeChip : inactiveChip}`}
        >
          {TOPIC_LABELS[t]}
        </Link>
      ))}
    </div>
  );
}
