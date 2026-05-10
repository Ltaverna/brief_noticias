import Link from "next/link";

const KIND_CLASSES: Record<string, string> = {
  person: "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-200",
  org: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
  place: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  event: "bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200",
};

const KIND_LABEL: Record<string, string> = {
  person: "👤",
  org: "🏛",
  place: "📍",
  event: "📰",
};

export function EntityChip({
  id,
  name,
  kind,
}: {
  id: number;
  name: string;
  kind: string;
}) {
  const cls = KIND_CLASSES[kind] ?? "bg-stone-200 text-stone-800";
  return (
    <Link
      href={`/entities/${id}`}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium hover:opacity-80 ${cls}`}
    >
      <span>{KIND_LABEL[kind] ?? "•"}</span>
      <span>{name}</span>
    </Link>
  );
}
