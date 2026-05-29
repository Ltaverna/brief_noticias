"use client";

type Series = {
  label: string;
  color: string;
  values: number[];
  n: number;
};

type Props = {
  series: Series[];
  labels: string[]; // 6 axis labels
  size?: number;
};

const MIN_N = 3;

export function AuthorRadarChart({ series, labels, size = 320 }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const r = (size / 2) * 0.65;
  const axes = labels.length;
  const angle = (i: number) => (i * 2 * Math.PI) / axes - Math.PI / 2;
  const pointAt = (i: number, value: number) => {
    const a = angle(i);
    return {
      x: cx + r * value * Math.cos(a),
      y: cy + r * value * Math.sin(a),
    };
  };
  const labelAt = (i: number) => {
    const a = angle(i);
    return {
      x: cx + r * 1.18 * Math.cos(a),
      y: cy + r * 1.18 * Math.sin(a),
    };
  };
  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-md mx-auto">
        {/* concentric rings */}
        {rings.map(rv => (
          <polygon
            key={rv}
            points={Array.from({ length: axes }, (_, i) => {
              const p = pointAt(i, rv);
              return `${p.x},${p.y}`;
            }).join(" ")}
            fill="none"
            stroke="#e2e8f0"
            strokeDasharray={rv === 1 ? undefined : "3 3"}
            strokeWidth={1}
          />
        ))}
        {/* axes */}
        {Array.from({ length: axes }, (_, i) => {
          const p = pointAt(i, 1);
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={p.x}
              y2={p.y}
              stroke="#e2e8f0"
              strokeWidth={1}
            />
          );
        })}
        {/* series polygons */}
        {series.map((s, idx) => {
          const opacity = s.n < MIN_N ? 0.2 : 0.35;
          const strokeOpacity = s.n < MIN_N ? 0.4 : 0.85;
          const points = s.values
            .map((v, i) => {
              const p = pointAt(i, Math.max(0, Math.min(1, v)));
              return `${p.x},${p.y}`;
            })
            .join(" ");
          return (
            <g key={`${s.label}-${idx}`}>
              <polygon
                points={points}
                fill={s.color}
                fillOpacity={opacity}
                stroke={s.color}
                strokeOpacity={strokeOpacity}
                strokeWidth={2}
              />
            </g>
          );
        })}
        {/* labels */}
        {labels.map((label, i) => {
          const p = labelAt(i);
          const anchor: "start" | "middle" | "end" =
            p.x < cx - 5 ? "end" : p.x > cx + 5 ? "start" : "middle";
          return (
            <text
              key={label}
              x={p.x}
              y={p.y}
              textAnchor={anchor}
              dominantBaseline="middle"
              className="fill-slate-600 dark:fill-slate-300"
              fontSize={11}
            >
              {label}
            </text>
          );
        })}
      </svg>
      <ul className="flex flex-wrap justify-center gap-3 text-xs">
        {series.map(s => (
          <li key={s.label} className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: s.color, opacity: s.n < MIN_N ? 0.4 : 1 }}
            />
            <span className={s.n < MIN_N ? "text-slate-400 italic" : ""}>
              {s.label}
              {s.n < MIN_N && ` (muestra chica n=${s.n})`}
              {s.n >= MIN_N && ` (n=${s.n})`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
