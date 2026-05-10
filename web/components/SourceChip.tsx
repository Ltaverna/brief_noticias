import { EditorialGroup } from "@/lib/types";

const groupClass: Record<EditorialGroup, string> = {
  mainstream: "bg-mainstream-bg text-mainstream-fg",
  critico: "bg-critico-bg text-critico-fg",
  economico: "bg-economico-bg text-economico-fg",
};

export function SourceChip({
  slug,
  group,
}: {
  slug: string;
  group: EditorialGroup;
}) {
  return (
    <span
      className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${groupClass[group]}`}
    >
      {slug}
    </span>
  );
}
