"use client";

import { useState } from "react";

import { ClusterDetail } from "@/lib/types";
import { clusterToMarkdown, downloadMarkdown } from "@/lib/export";

export function ExportMenu({ cluster }: { cluster: ClusterDetail }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    const md = clusterToMarkdown(cluster);
    try {
      await navigator.clipboard.writeText(md);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: download instead
      download();
    }
  }

  function download() {
    const md = clusterToMarkdown(cluster);
    const slug =
      (cluster.analysis?.headline ?? `cluster-${cluster.id}`)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 60) || `cluster-${cluster.id}`;
    downloadMarkdown(`${slug}.md`, md);
  }

  return (
    <div className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={copy}
        className="rounded-md bg-stone-200 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-300 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
      >
        {copied ? "✓ Copiado" : "📋 Copiar Markdown"}
      </button>
      <button
        type="button"
        onClick={download}
        className="rounded-md bg-stone-200 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-300 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
        title="Descargar como .md"
      >
        ⬇ .md
      </button>
    </div>
  );
}
