"use client";

import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  READ_STATE_EVENT,
  getReadIds,
  markRead,
  markUnread,
} from "@/lib/read-state";

interface ReadStateContextValue {
  isRead: (id: number) => boolean;
  toggle: (id: number) => void;
}

const ReadStateContext = createContext<ReadStateContextValue | null>(null);

export function ReadStateProvider({ children }: { children: ReactNode }) {
  const [readIds, setReadIds] = useState<Set<number>>(() => new Set());

  // Hydrate from localStorage on mount and stay in sync via custom events
  useEffect(() => {
    setReadIds(getReadIds());
    const handler = () => setReadIds(getReadIds());
    window.addEventListener(READ_STATE_EVENT, handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener(READ_STATE_EVENT, handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  const isRead = useCallback((id: number) => readIds.has(id), [readIds]);
  const toggle = useCallback(
    (id: number) => {
      if (readIds.has(id)) markUnread(id);
      else markRead(id);
    },
    [readIds],
  );

  return (
    <ReadStateContext.Provider value={{ isRead, toggle }}>
      {children}
    </ReadStateContext.Provider>
  );
}

export function useReadState(): ReadStateContextValue {
  const ctx = useContext(ReadStateContext);
  if (!ctx) {
    return { isRead: () => false, toggle: () => {} };
  }
  return ctx;
}
