export default function PhotonTheoremGrid() {
  const theorems = [
    { id: "T8", label: "⊕ Distributivity", status: "VERIFIED", desc: "⊗ expands over ⊕" },
    { id: "T9", label: "Double Negation", status: "VERIFIED", desc: "¬(¬a) ≡ a" },
    { id: "T10", label: "Entanglement", status: "VERIFIED", desc: "↔ factoring over ⊕" },
    { id: "T13", label: "Absorption", status: "VERIFIED", desc: "a ⊕ (a ⊗ b) ≡ a" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {theorems.map((t) => (
        <div key={t.id} className="p-6 bg-white rounded-3xl border border-slate-100 shadow-sm hover:shadow-md transition-all group">
          <div className="flex justify-between items-center mb-3">
            <span className="font-mono text-[10px] font-black text-[#1B74E4]">{t.id}</span>
            <span className="text-[10px] bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full font-bold">LEAN_PROVED</span>
          </div>
          <div className="font-bold text-slate-900 uppercase italic tracking-tight">{t.label}</div>
          <div className="mt-2 text-xs text-slate-500 font-medium">{t.desc}</div>
        </div>
      ))}
    </div>
  );
}