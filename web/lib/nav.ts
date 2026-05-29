export interface NavLink {
  href: string;
  label: string;
}

export const NAV_LINKS: NavLink[] = [
  { href: "/", label: "Inicio" },
  { href: "/qa", label: "Preguntar" },
  { href: "/analytics", label: "Análisis" },
  { href: "/entities", label: "Entidades" },
  { href: "/sagas", label: "Sagas" },
  { href: "/historial", label: "Historial" },
  { href: "/fuentes", label: "Fuentes" },
  { href: "/subscriptions", label: "Suscripciones" },
];
