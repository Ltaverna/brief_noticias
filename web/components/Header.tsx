import Link from "next/link";

import { MobileNav } from "./MobileNav";
import { SearchBox } from "./SearchBox";
import { NAV_LINKS } from "@/lib/nav";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/85 backdrop-blur dark:border-stone-800 dark:bg-stone-950/85">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 sm:px-6">
        {/* Logo */}
        <Link href="/" className="text-xl font-serif font-bold tracking-tight shrink-0">
          Noticias
        </Link>

        {/* Desktop search — centered */}
        <div className="hidden md:flex flex-1 justify-center">
          <SearchBox />
        </div>

        {/* Spacer on desktop if no search shown */}
        <div className="flex-1 md:hidden" />

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-4 text-sm shrink-0">
          {NAV_LINKS.slice(1).map((l) => (
            <Link key={l.href} href={l.href} className="hover:underline whitespace-nowrap">
              {l.label}
            </Link>
          ))}
        </nav>

        {/* Mobile controls: search icon + hamburger */}
        <div className="md:hidden flex items-center gap-1 shrink-0">
          <Link
            href="/search"
            aria-label="Buscar"
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-md hover:bg-stone-100 dark:hover:bg-stone-800"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </Link>
          <MobileNav links={NAV_LINKS} />
        </div>
      </div>
    </header>
  );
}
