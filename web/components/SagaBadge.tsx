import Link from "next/link";

export function SagaBadge({ id, title }: { id: number; title: string }) {
  return (
    <Link
      href={`/saga/${id}`}
      className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-900 hover:bg-indigo-200 dark:bg-indigo-950 dark:text-indigo-200 dark:hover:bg-indigo-900"
    >
      <span>📖</span>
      <span>Saga: {title}</span>
    </Link>
  );
}
