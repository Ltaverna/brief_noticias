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
  return (
    <div className="flex flex-wrap gap-2 text-sm">
      <Link
        href={basePath}
        className={`rounded-full px-3 py-1 ${
          !current
            ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
            : "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300"
        }`}
      >
        Todas
      </Link>
      {TOPIC_ORDER.map((t) => (
        <Link
          key={t}
          href={`${basePath}?topic=${t}`}
          className={`rounded-full px-3 py-1 ${
            current === t
              ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
              : "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300"
          }`}
        >
          {TOPIC_LABELS[t]}
        </Link>
      ))}
    </div>
  );
}
