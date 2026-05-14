// frontend/tabs/glyph/ComparisonCard.tsx
"use client";

import React from "react";

type Props = {
  title: string;
  traditional: string;
  glyph: string;
  labels: string;
};

export default function ComparisonCard({ title, traditional, glyph, labels }: Props) {
  return (
    <div className="p-10 bg-white rounded-[2.5rem] shadow-xl shadow-gray-200/50 border border-gray-100 flex flex-col justify-between">
      <div>
        <h3 className="text-xs font-bold text-gray-300 uppercase tracking-widest mb-6">{title}</h3>

        <div className="mb-8">
          <p className="text-[10px] text-gray-400 font-bold uppercase mb-2">Traditional</p>
          <p className="text-lg text-gray-600 font-light leading-snug tracking-tight">{traditional}</p>
        </div>
      </div>

      <div className="pt-8 border-t border-gray-50">
        <p className="text-[10px] text-[#0071e3] font-bold uppercase mb-4 tracking-wider">Glyph OS</p>
        <div className="text-5xl mb-3">{glyph}</div>
        <p className="text-xs font-medium text-gray-400 uppercase tracking-tighter">{labels}</p>
      </div>
    </div>
  );
}