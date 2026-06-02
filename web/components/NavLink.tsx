"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Variant = "desktop" | "mobile";

interface Props {
  href: string;
  label: string;
  variant?: Variant;
  onClick?: () => void;
}

function useIsActive(href: string): boolean {
  const pathname = usePathname();
  // Home matches exactly; every other route also matches its sub-paths
  // (e.g. /authors is active on /authors/clarin).
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function NavLink({ href, label, variant = "desktop", onClick }: Props) {
  const active = useIsActive(href);

  if (variant === "mobile") {
    return (
      <Link
        href={href}
        onClick={onClick}
        aria-current={active ? "page" : undefined}
        style={{ minHeight: 44 }}
        className={`flex items-center border-l-2 px-6 py-3 text-base transition-colors ${
          active
            ? "border-stone-900 bg-stone-100 font-semibold text-stone-900 dark:border-stone-100 dark:bg-stone-900 dark:text-stone-50"
            : "border-transparent font-medium text-stone-900 hover:bg-stone-100 dark:text-stone-100 dark:hover:bg-stone-900"
        }`}
      >
        {label}
      </Link>
    );
  }

  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`cursor-pointer whitespace-nowrap rounded-md px-2.5 py-1.5 transition-colors duration-150 ${
        active
          ? "bg-stone-100 font-medium text-stone-900 dark:bg-stone-800 dark:text-stone-50"
          : "text-stone-600 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-stone-50"
      }`}
    >
      {label}
    </Link>
  );
}
