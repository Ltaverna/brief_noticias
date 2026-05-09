import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Noticias",
  description: "Comparador de coberturas de diarios argentinos",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="min-h-screen bg-white text-stone-900 dark:bg-stone-950 dark:text-stone-100">
        <Providers>
          <Header />
          {children}
        </Providers>
      </body>
    </html>
  );
}
