import Link from "next/link";

import { NAV_LINKS } from "@/lib/nav";
import { MobileNav } from "./MobileNav";
import { SearchBox } from "./SearchBox";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/85 backdrop-blur-md dark:border-stone-800 dark:bg-stone-950/85">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 sm:px-6">
        {/* Logo */}
        <Link href="/" className="text-xl font-serif font-bold tracking-tight shrink-0">
          Noticias
        </Link>

        {/* Desktop search — centered */}
        <div className="hidden lg:flex flex-1 justify-center">
          <SearchBox />
        </div>

        {/* Spacer when search is hidden (below lg) */}
        <div className="flex-1 lg:hidden" />

        {/* Desktop nav (>= lg, 1024px) */}
        <nav className="hidden lg:flex items-center gap-1 text-sm shrink-0">
          {NAV_LINKS.slice(1).map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="cursor-pointer whitespace-nowrap rounded-md px-2.5 py-1.5 text-stone-600 transition-colors duration-150 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-stone-50"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        {/* Theme toggle (always visible) */}
        <ThemeToggle className="shrink-0" />

        {/* Mobile/tablet controls: search icon + hamburger (< lg) */}
        <div className="lg:hidden flex items-center gap-1 shrink-0">
          <Link
            href="/search"
            aria-label="Buscar"
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-md text-stone-600 transition-colors duration-150 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-stone-50"
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
          <MobileNav />
        </div>
      </div>
    </header>
  );
}
