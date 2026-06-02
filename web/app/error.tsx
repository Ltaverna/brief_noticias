"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex max-w-2xl flex-col items-center px-4 py-24 text-center sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight">
        Algo salió mal
      </h1>
      <p className="mt-3 text-stone-600 dark:text-stone-400">
        No pudimos cargar esta sección. Puede ser un problema temporal de
        conexión con el servidor.
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={reset}
          className="cursor-pointer rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-300"
        >
          Reintentar
        </button>
        <a
          href="/"
          className="cursor-pointer rounded-md border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-800"
        >
          Volver al inicio
        </a>
      </div>
      {error.digest && (
        <p className="mt-6 font-mono text-xs text-stone-400 dark:text-stone-600">
          ref: {error.digest}
        </p>
      )}
    </main>
  );
}
