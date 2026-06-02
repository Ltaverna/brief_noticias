import { Skeleton } from "@/components/Skeleton";

export default function Loading() {
  return (
    <main
      className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:py-12"
      aria-busy="true"
      aria-label="Cargando contenido"
    >
      <div className="flex flex-col gap-3">
        <Skeleton className="h-10 w-64 md:h-12" />
        <Skeleton className="h-5 w-48" />
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-20 rounded-full" />
        ))}
      </div>

      <ul className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <li key={i}>
            <div className="rounded-xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-stone-900/60">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="mt-3 h-6 w-3/4" />
              <Skeleton className="mt-4 h-4 w-1/2" />
              <div className="mt-4 flex gap-1.5">
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
