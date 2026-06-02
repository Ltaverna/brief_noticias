export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-stone-200 motion-reduce:animate-none dark:bg-stone-800 ${className}`}
    />
  );
}
