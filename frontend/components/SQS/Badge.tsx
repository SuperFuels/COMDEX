import * as React from "react";

export default function Badge({
  label, value, title,
}: { label: string; value?: number; title: string }) {
  const v = typeof value === "number" ? Math.max(0, Math.min(1, value)) : undefined;
  const hue = v === undefined ? 0 : Math.round(120 * v);
  const style = v === undefined ? {} : { borderColor: `hsl(${hue} 70% 50%)`, color: `hsl(${hue} 70% 55%)` };
  return (
    <span
      className="px-1 py-[1px] rounded text-[10px] border bg-neutral-900/40"
      style={style}
      title={`${title}: ${v === undefined ? "—" : v.toFixed(2)}`}
    >
      {label}:{v === undefined ? "—" : v.toFixed(2)}
    </span>
  );
}