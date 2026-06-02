export interface NavLink {
  href: string;
  label: string;
}

// Primary destinations — shown directly in the desktop top bar (≤5 items,
// per the bottom-nav-limit / overflow-menu guideline). "Inicio" is reached
// via the logo, so the bar effectively shows 4 + a "Más" overflow.
export const PRIMARY_NAV: NavLink[] = [
  { href: "/", label: "Inicio" },
  { href: "/qa", label: "Preguntar" },
  { href: "/analytics", label: "Análisis" },
  { href: "/authors", label: "Autores" },
];

// Secondary destinations — grouped under the "Más" overflow menu on desktop.
export const SECONDARY_NAV: NavLink[] = [
  { href: "/entities", label: "Entidades" },
  { href: "/sagas", label: "Sagas" },
  { href: "/historial", label: "Historial" },
  { href: "/fuentes", label: "Fuentes" },
  { href: "/subscriptions", label: "Suscripciones" },
];

// Full flat list — used by the mobile drawer, which can hold everything.
export const NAV_LINKS: NavLink[] = [...PRIMARY_NAV, ...SECONDARY_NAV];
