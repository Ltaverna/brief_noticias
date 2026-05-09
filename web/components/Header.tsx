import Link from "next/link";

import { SearchBox } from "./SearchBox";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/85 backdrop-blur dark:border-stone-800 dark:bg-stone-950/85">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-xl font-serif font-bold tracking-tight">
          Noticias
        </Link>
        <div className="flex items-center gap-4">
          <SearchBox />
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/qa" className="hover:underline">Preguntar</Link>
            <Link href="/analytics" className="hover:underline">Análisis</Link>
            <Link href="/entities" className="hover:underline">Entidades</Link>
            <Link href="/sagas" className="hover:underline">Sagas</Link>
            <Link href="/historial" className="hover:underline">Historial</Link>
            <Link href="/fuentes" className="hover:underline">Fuentes</Link>
            <Link href="/subscriptions" className="hover:underline">Suscripciones</Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
