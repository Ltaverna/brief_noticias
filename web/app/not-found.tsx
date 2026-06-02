import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex max-w-2xl flex-col items-center px-4 py-24 text-center sm:px-6">
      <p className="font-mono text-sm font-medium text-stone-400 dark:text-stone-600">
        404
      </p>
      <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight">
        Página no encontrada
      </h1>
      <p className="mt-3 text-stone-600 dark:text-stone-400">
        La página que buscás no existe o fue movida.
      </p>
      <Link
        href="/"
        className="mt-8 cursor-pointer rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-300"
      >
        Volver al inicio
      </Link>
    </main>
  );
}
