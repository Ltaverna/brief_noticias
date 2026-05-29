"use client";
import Link from "next/link";

type Props = {
  name: string;
  slug: string;
  isSynthetic?: boolean;
};

export function AuthorChip({ name, slug, isSynthetic }: Props) {
  return (
    <Link
      href={`/authors/${slug}`}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
        isSynthetic
          ? "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
          : "bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-950 dark:text-blue-300"
      }`}
      title={isSynthetic ? "Sin firma — atribuido a la redacción" : `Notas de ${name}`}
    >
      {isSynthetic && <span aria-hidden>·</span>}
      {name}
    </Link>
  );
}
