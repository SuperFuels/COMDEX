"use client";

import dynamic from "next/dynamic";

const SymaticsPaper = dynamic(
  () => import("../../content/symatics/symatics_full_technical_document.mdx"),
  {
    ssr: false,
    loading: () => (
      <div className="text-center py-20">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-4 w-48 bg-gray-200 rounded mb-4" />
          <div className="h-4 w-64 bg-gray-100 rounded" />
          <p className="mt-8 text-gray-400 font-medium">Loading document…</p>
        </div>
      </div>
    ),
  },
);

export default function SymaticsPaperViewer() {
  return (
    <section className="w-full mt-32 animate-in fade-in slide-in-from-bottom-8 duration-1000">
      <div className="flex flex-col gap-8">
        <div className="flex justify-between items-end border-b border-gray-200 pb-6">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-black">Technical Papers</h2>
            <p className="text-gray-500 mt-2">
              Active Document:{" "}
              <span className="text-[#0071e3] font-mono">symatics_full_technical_document.mdx</span>
            </p>
          </div>
          <button className="text-sm font-semibold text-[#0071e3] hover:underline px-4 py-2 bg-blue-50 rounded-full">
            Download PDF Original
          </button>
        </div>

        <div className="bg-white rounded-[3rem] shadow-2xl shadow-gray-200/50 border border-gray-100 overflow-hidden relative">
          <div className="absolute top-0 left-0 w-full h-1 bg-gray-100">
            <div className="h-full bg-[#0071e3] w-1/3 shadow-[0_0_10px_#0071e3]" />
          </div>

          <div className="p-12 md:p-20 prose prose-slate max-w-none">
            <div className="symatics-paper-view">
              <SymaticsPaper />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}