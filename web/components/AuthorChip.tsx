"use client";
import Link from "next/link";

export type AuthorKind = "person" | "newsroom" | "editorial" | "agency";

type Props = {
  name: string;
  slug: string;
  isSynthetic?: boolean;
  kind?: AuthorKind | string;
};

// Tailwind utility classes per kind. Each tuple is [container, dot/prefix].
const KIND_STYLES: Record<string, string> = {
  person:
    "bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-950 dark:text-blue-300",
  newsroom:
    "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 italic",
  editorial:
    "bg-violet-50 text-violet-700 hover:bg-violet-100 dark:bg-violet-950 dark:text-violet-300 font-medium",
  agency:
    "bg-orange-50 text-orange-700 hover:bg-orange-100 dark:bg-orange-950 dark:text-orange-300",
};

const KIND_TITLES: Record<string, string> = {
  person: "Periodista — click para ver perfil",
  newsroom: "Atribuido a la redacción del diario (sin firma)",
  editorial: "Editorial — opinión institucional del diario",
  agency: "Agencia de noticias",
};

const KIND_PREFIX: Record<string, string> = {
  newsroom: "·",
  editorial: "✎",
  agency: "⚡",
};

export function AuthorChip({ name, slug, isSynthetic, kind }: Props) {
  // Backwards-compat: si no llega `kind`, derivamos del flag is_synthetic
  const k: string = kind ?? (isSynthetic ? "newsroom" : "person");
  const cls = KIND_STYLES[k] ?? KIND_STYLES.person;
  const title = KIND_TITLES[k] ?? `Notas de ${name}`;
  const prefix = KIND_PREFIX[k];

  return (
    <Link
      href={`/authors/${slug}`}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${cls}`}
      title={title}
    >
      {prefix && <span aria-hidden>{prefix}</span>}
      {name}
    </Link>
  );
}
