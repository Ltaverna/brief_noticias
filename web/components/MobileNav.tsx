"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { NAV_LINKS, type NavLink } from "@/lib/nav";

export function MobileNav({ links }: { links?: NavLink[] }) {
  const items = links && links.length > 0 ? links : NAV_LINKS;
  const [open, setOpen] = useState(false);

  // Close drawer on route change (escape key too)
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // Prevent body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="lg:hidden min-h-[44px] min-w-[44px] flex items-center justify-center rounded-md hover:bg-stone-100 dark:hover:bg-stone-800"
        aria-label="Abrir menú"
        aria-expanded={open}
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {open && (
        <>
          {/* Backdrop — own fixed element, no parent stacking issues */}
          <div
            className="fixed inset-0 z-40 bg-black/60 lg:hidden"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer — own fixed element with explicit dvh height */}
          <nav
            role="dialog"
            aria-modal="true"
            aria-label="Menú de navegación"
            style={{ height: "100dvh", maxHeight: "100vh" }}
            className="fixed right-0 top-0 z-50 flex w-72 max-w-[85vw] flex-col overflow-y-auto bg-white shadow-2xl lg:hidden dark:bg-stone-950"
          >
            <div className="flex shrink-0 items-center justify-between border-b border-stone-200 bg-white px-6 py-4 dark:border-stone-800 dark:bg-stone-950">
              <span className="text-lg font-serif font-bold text-stone-900 dark:text-stone-100">
                Menú
              </span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="flex h-11 w-11 items-center justify-center rounded-md text-stone-700 hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800"
                aria-label="Cerrar menú"
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
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <ul className="grow py-2">
              {items.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    onClick={() => setOpen(false)}
                    style={{ minHeight: 44, color: "inherit" }}
                    className="flex items-center px-6 py-3 text-base font-medium text-stone-900 hover:bg-stone-100 dark:text-stone-100 dark:hover:bg-stone-900"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </>
      )}
    </>
  );
}
