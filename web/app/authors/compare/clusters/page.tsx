"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getSharedClusters, type SharedCluster } from "@/lib/authors";

export default function SharedClustersPage() {
  const sp = useSearchParams();
  const a = sp.get("a") ?? "";
  const b = sp.get("b") ?? "";
  const [clusters, setClusters] = useState<SharedCluster[]>([]);

  useEffect(() => {
    if (!a || !b) return;
    getSharedClusters(a, b).then(d => setClusters(d.clusters ?? []));
  }, [a, b]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-xl font-semibold mb-4">Clusters compartidos</h1>
      <p className="text-sm text-slate-500 mb-6">{a} vs {b}</p>
      <ul className="space-y-2">
        {clusters.map(c => (
          <li key={c.id}>
            <Link
              href={`/cluster/${c.id}?compare_authors=${a},${b}`}
              className="text-sm hover:underline"
            >
              {c.headline ?? `Cluster ${c.id}`}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
