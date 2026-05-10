import { ClusterDetail } from "./types";

export function clusterToMarkdown(cluster: ClusterDetail): string {
  const a = cluster.analysis;
  const headline = a?.headline ?? `Cluster ${cluster.id}`;
  const lines: string[] = [];
  lines.push(`# ${headline}`, "");

  if (cluster.topic) {
    lines.push(`**Tema:** ${cluster.topic}`);
  }
  lines.push(
    `**Fuentes:** ${cluster.source_count} · **Artículos:** ${cluster.article_count}`,
    "",
  );

  if (a) {
    if (a.common_facts.length) {
      lines.push("## Hechos en común", "");
      for (const f of a.common_facts) lines.push(`- ${f}`);
      lines.push("");
    }

    const sourceKeys = Object.keys(a.by_source);
    if (sourceKeys.length) {
      lines.push("## Por diario", "");
      for (const slug of sourceKeys) {
        const s = a.by_source[slug];
        lines.push(`### ${slug} (tono: ${s.tone})`, "");
        lines.push(`*${s.framing}*`, "");
        for (const h of s.highlights) lines.push(`- ${h}`);
        lines.push("");
      }
    }

    if (a.omissions.length) {
      lines.push("## Omisiones", "");
      for (const o of a.omissions) {
        lines.push(`- **${o.source}** omite: ${o.not_mentioned}`);
      }
      lines.push("");
    }

    if (a.divergences.length) {
      lines.push("## Divergencias", "");
      for (const d of a.divergences) {
        lines.push(`### ${d.topic}`);
        for (const [slug, stance] of Object.entries(d.positions)) {
          lines.push(`- **${slug}**: ${stance}`);
        }
        lines.push("");
      }
    }
  }

  if (cluster.articles.length) {
    lines.push("## Artículos fuente", "");
    for (const art of cluster.articles) {
      lines.push(`- [${art.source.name}] [${art.title}](${art.url})`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

export function downloadMarkdown(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
