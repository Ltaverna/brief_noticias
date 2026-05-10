import Link from "next/link";

import { api } from "@/lib/api";
import { CompareColumn } from "@/components/CompareColumn";

export const dynamic = "force-dynamic";

export default async function ComparePage({
  searchParams,
}: { searchParams: Promise<{ a?: string; b?: string }> }) {
  const sp = await searchParams;
  const aId = sp.a ? Number(sp.a) : NaN;
  const bId = sp.b ? Number(sp.b) : NaN;

  if (!Number.isInteger(aId) || !Number.isInteger(bId)) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <h1 className="text-3xl font-serif font-bold">Comparar</h1>
        <p className="mt-4 text-stone-600 dark:text-stone-400">
          URL inválida. Usá <code>?a=ID&amp;b=ID</code> con dos cluster IDs válidos.
        </p>
      </main>
    );
  }

  const [a, b] = await Promise.all([
    api.getCluster(aId).catch(() => null),
    api.getCluster(bId).catch(() => null),
  ]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link href="/" className="text-sm text-stone-500 hover:underline">
        ← Volver al briefing
      </Link>
      <h1 className="mt-2 text-3xl font-serif font-bold">Comparar</h1>
      <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
        Vista lado a lado de dos clusters.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <CompareColumn cluster={a} />
        <CompareColumn cluster={b} />
      </div>
    </main>
  );
}
