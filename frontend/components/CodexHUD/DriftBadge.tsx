"use client";
import React from "react";

export default function DriftBadge({ status, weight }: { status: string; weight: number }) {
  const color =
    status === "CLOSED" ? "bg-green-600" :
    status === "OPEN"   ? "bg-amber-500" :
    "bg-red-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs text-white ${color}`}>
      Drift: {status} · {weight.toFixed(2)}
    </span>
  );
}