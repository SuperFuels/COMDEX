"use client";

export default function PhotonHero() {
  return (
    <section className="space-y-16">
      <div className="text-center space-y-6">
        <h1 className="text-[5rem] md:text-[8rem] font-bold tracking-tight text-slate-900 italic leading-[0.95]">
          Photon Algebra
        </h1>
        <p className="text-2xl md:text-3xl text-slate-500 font-light tracking-tight italic">
          From wave patterns to <span className="text-[#1B74E4] font-bold uppercase">executable intent.</span>
        </p>
      </div>

      <div className="bg-white rounded-[3rem] p-16 text-center shadow-[0_8px_40px_rgb(0,0,0,0.04)] border border-slate-100">
        <div className="text-7xl mb-12 tracking-tighter flex flex-wrap justify-center items-center gap-6 font-bold text-slate-800">
          <span>γ₁</span>
          <span className="text-3xl text-slate-300">⊗</span>
          <span className="text-slate-400">(</span>
          <span>γ₂</span>
          <span className="text-3xl text-slate-300">⊕</span>
          <span>γ₃</span>
          <span className="text-slate-400">)</span>
          <span className="text-3xl text-slate-300">=</span>
          <span className="text-[#1B74E4]">Ψ_norm</span>
        </div>
        <p className="text-slate-500 text-xl max-w-2xl mx-auto leading-relaxed font-medium">
          The <span className="text-slate-900 font-bold">Canonical Sum-of-Products.</span> Aion's mechanism for resolving 
          infinite wave states into a single, verifiable normal form.
        </p>
      </div>
    </section>
  );
}