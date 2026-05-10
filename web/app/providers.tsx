"use client";

import { ThemeProvider } from "next-themes";
import { ReadStateProvider } from "@/components/ReadStateProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <ReadStateProvider>{children}</ReadStateProvider>
    </ThemeProvider>
  );
}
