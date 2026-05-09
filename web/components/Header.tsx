import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/85 backdrop-blur dark:border-stone-800 dark:bg-stone-950/85">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-xl font-serif font-bold tracking-tight">
          Noticias
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/historial" className="hover:underline">Historial</Link>
          <Link href="/fuentes" className="hover:underline">Fuentes</Link>
        </nav>
      </div>
    </header>
  );
}
