"use client";

export default function SymaticsHero() {
  return (
    <section className="space-y-16">
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Symatics</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Start with <span className="text-[#0071e3] font-medium uppercase">patterns</span>, not numbers.
        </p>
      </div>

      {/* Core Equation Hero */}
      <div className="bg-white rounded-[3rem] p-16 text-center shadow-xl shadow-gray-200/50 border border-gray-100">
        <div className="text-8xl mb-12 tracking-widest flex justify-center items-center gap-8">
          <span className="font-mono text-gray-800">〰️</span>
          <span className="text-4xl text-gray-300 font-light">+</span>
          <span className="font-mono text-gray-800">〰️</span>
          <span className="text-4xl text-gray-300 font-light">=</span>
          <div className="relative inline-flex items-center justify-center">
            <span className="font-mono text-[#0071e3] drop-shadow-sm">〰️</span>
            <span className="absolute -right-8 flex items-center justify-center w-14 h-14 rounded-full border-[3px] border-[#0071e3] text-[#0071e3] text-3xl font-bold bg-white shadow-sm">
              R
            </span>
          </div>
        </div>

        <p className="text-gray-500 text-xl max-w-2xl mx-auto leading-relaxed">
          〰️ + 〰️ = 〰️® is a breakthrough in{" "}
          <span className="text-black font-semibold">qualitative state change</span>.
        </p>
      </div>

      {/* Explainer */}
      <div className="bg-white rounded-[3rem] shadow-xl shadow-gray-200/50 border border-gray-100 overflow-hidden">
        <div className="p-10 md:p-12">
          <div className="max-w-3xl mx-auto text-left bg-[#fafafa] rounded-3xl p-8 border border-gray-100">
            <div className="text-xs font-bold text-gray-300 uppercase tracking-widest mb-4">
              The New Logic of Resonance
            </div>

            <p className="text-gray-600 leading-relaxed text-lg">
              <span className="font-semibold text-gray-800">Beyond Counting: Moving from Quantity to Quality</span>
              <br />
              In the world we know, math is for accounting. If you have one dollar and add another, you have two. This
              is the logic of accumulation—simply having "more of the same."
            </p>

            <div className="mt-8 space-y-4 border-l-2 border-gray-200 pl-6">
              <div>
                <span className="font-semibold text-gray-800">Traditional Math:</span>{" "}
                <span className="font-mono bg-gray-100 px-3 py-1 rounded text-sm text-gray-600">1 + 1 = 2</span>
              </div>

              <div className="pt-2">
                <span className="font-semibold text-[#0071e3]">Symatic Logic:</span>{" "}
                <span className="font-mono bg-blue-50 text-[#0071e3] px-3 py-1 rounded text-sm">〰️ + 〰️ = 〰️®</span>
                <div className="text-gray-500 text-sm mt-1 ml-1">
                  This is the logic of harmony—where patterns combine to create a new, superior reality.
                </div>
              </div>
            </div>

            <div className="mt-12 pt-8 border-t border-gray-200">
              <div className="font-bold text-gray-800 text-lg mb-3">Why It Matters</div>
              <p className="text-gray-600 leading-relaxed">
                When your intent (〰️) perfectly aligns with the system (〰️), the noise of the world disappears. You are
                achieving Resonance (⟲).
              </p>
              <div className="mt-8 text-gray-800 font-medium text-center py-8 bg-white rounded-2xl border border-gray-100 shadow-inner italic text-lg px-6">
                “Symatics doesn't just count the world. It oscillates it into harmony.”
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Operators */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {["〰️ Wave", "💡 Photon", "⊕ Superpose", "↔ Entangle", "⟲ Resonance", "∇ Collapse", "⇒ Trigger"].map((op) => (
          <div
            key={op}
            className="p-5 bg-white rounded-2xl text-center shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-default"
          >
            <span className="text-sm font-semibold text-gray-700">{op}</span>
          </div>
        ))}
      </div>
    </section>
  );
}