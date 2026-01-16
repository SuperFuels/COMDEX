// frontend/components/PaperFrame.tsx
"use client";

import * as React from "react";

type PaperFrameProps = {
  title?: string;
  subtitle?: React.ReactNode;
  rightSlot?: React.ReactNode;
  /** If you want a progress bar (visual only), set 0..1 */
  progress?: number;
  children: React.ReactNode;
  className?: string;
};

export default function PaperFrame({
  title = "Technical Papers",
  subtitle,
  rightSlot,
  progress = 0.33,
  children,
  className,
}: PaperFrameProps) {
  const pct = Math.max(0, Math.min(1, progress));

  return (
    <section className={`w-full mt-32 animate-in fade-in slide-in-from-bottom-8 duration-1000 ${className ?? ""}`}>
      <div className="flex flex-col gap-8">
        <div className="flex justify-between items-end border-b border-gray-200 pb-6">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-black">{title}</h2>
            {subtitle ? <div className="text-gray-500 mt-2">{subtitle}</div> : null}
          </div>
          {rightSlot ? (
            <div>{rightSlot}</div>
          ) : (
            <button className="text-sm font-semibold text-[#0071e3] hover:underline px-4 py-2 bg-blue-50 rounded-full">
              Download PDF Original
            </button>
          )}
        </div>

        <div className="bg-white rounded-[3rem] shadow-2xl shadow-gray-200/50 border border-gray-100 overflow-hidden relative">
          {/* Progress Bar (visual only) */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gray-100">
            <div
              className="h-full bg-[#0071e3] shadow-[0_0_10px_#0071e3]"
              style={{ width: `${pct * 100}%` }}
            />
          </div>

          <div className="p-12 md:p-20">
            {/* Prose wrapper so MDX renders nicely */}
            <div className="prose prose-slate max-w-none">
              <div className="symatics-paper-view">{children}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * Optional: a consistent loading skeleton for MDX dynamic imports
 */
export function PaperLoading() {
  return (
    <div className="text-center py-20">
      <div className="animate-pulse flex flex-col items-center">
        <div className="h-4 w-48 bg-gray-200 rounded mb-4" />
        <div className="h-4 w-64 bg-gray-100 rounded" />
        <p className="mt-8 text-gray-400 font-medium">Loading document…</p>
      </div>
    </div>
  );
}