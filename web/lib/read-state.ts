const KEY = "noticias:read";
const EVENT = "noticias:read-changed";

export function getReadIds(): Set<number> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((v): v is number => typeof v === "number"));
  } catch {
    return new Set();
  }
}

function persist(ids: Set<number>): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify([...ids]));
  window.dispatchEvent(new CustomEvent(EVENT));
}

export function markRead(id: number): void {
  const ids = getReadIds();
  ids.add(id);
  persist(ids);
}

export function markUnread(id: number): void {
  const ids = getReadIds();
  ids.delete(id);
  persist(ids);
}

export function clearAllRead(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
  window.dispatchEvent(new CustomEvent(EVENT));
}

export const READ_STATE_EVENT = EVENT;
