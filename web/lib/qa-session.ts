const KEY = "noticias:qa-conversation";

export function getConversationId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function setConversationId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, id);
}

export function clearConversation(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
}
