// frontend/pages/index.tsx
'use client';

import { useState } from 'react';
import type { NextPage } from 'next';
import dynamic from 'next/dynamic';

// 🔌 Quantum Field Canvas remains for the "background" or immersive view
const QFC = dynamic(
  () => import('@/components/Hologram/quantum_field_canvas'),
  { ssr: false }
);

const Home: NextPage = () => {
  const [activeTab, setActiveTab] = useState<'glyph' | 'symatics'>('glyph');

  return (
    <div className="min-h-screen bg-black text-white selection:bg-blue-500/30 overflow-hidden font-sans">
      
      {/* 🌌 Background Layer: The QFC Canvas */}
      <div className="fixed inset-0 opacity-40 pointer-events-none">
        <QFC nodes={[]} links={[]} />
      </div>

      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6">
        
        {/* 🎚️ Minimalist Tab Switcher */}
        <nav className="mb-12 p-1 bg-white/5 backdrop-blur-xl border border-white/10 rounded-full flex gap-1">
          <button
            onClick={() => setActiveTab('glyph')}
            className={`px-8 py-2 rounded-full text-sm font-medium transition-all ${
              activeTab === 'glyph' ? 'bg-white text-black shadow-lg' : 'text-white/60 hover:text-white'
            }`}
          >
            Glyph OS
          </button>
          <button
            onClick={() => setActiveTab('symatics')}
            className={`px-8 py-2 rounded-full text-sm font-medium transition-all ${
              activeTab === 'symatics' ? 'bg-white text-black shadow-lg' : 'text-white/60 hover:text-white'
            }`}
          >
            Symatics
          </button>
          <div className="px-4 py-2 text-white/20 text-sm cursor-not-allowed italic">Coming Soon...</div>
        </nav>

        {/* 📦 Content Area */}
        <div className="max-w-4xl w-full transition-all duration-700">
          
          {activeTab === 'glyph' && (
            <section className="animate-in fade-in slide-in-from-bottom-8 duration-1000 space-y-12">
              <div className="text-center space-y-4">
                <h1 className="text-6xl md:text-8xl font-bold tracking-tighter bg-gradient-to-b from-white to-white/40 bg-clip-text text-transparent italic uppercase">
                  Glyph OS
                </h1>
                <p className="text-xl text-blue-400 font-mono tracking-widest uppercase">
                  The Language of Symbols. The Speed of Light.
                </p>
                <p className="max-w-xl mx-auto text-white/60 leading-relaxed">
                   An operating system built in symbols, executing at the speed of thought, 
                   compressed for the next era of cognition.
                </p>
              </div>

              {/* Comparison Grid */}
              <div className="grid md:grid-cols-2 gap-8">
                <ComparisonCard 
                  title="Cooking" 
                  traditional="Get eggs → Crack → Whisk → Heat → Butter → Cook → Plate"
                  glyph="🥚 → 🍳 → 🍽️"
                  labels="Ingredients → Cook → Serve"
                />
                <ComparisonCard 
                  title="Summarization" 
                  traditional="Open doc → Find points → Pull dates → Write summary → Save"
                  glyph="📄 → ✨ → 🗂️"
                  labels="Document → Highlights → Filed"
                />
              </div>

              <div className="text-center italic text-white/40 text-sm">
                "Same result. Less noise."
              </div>
            </section>
          )}

          {activeTab === 'symatics' && (
            <section className="animate-in fade-in slide-in-from-bottom-8 duration-1000 space-y-12">
              <div className="text-center space-y-4">
                <h1 className="text-6xl md:text-8xl font-bold tracking-tighter bg-gradient-to-b from-blue-400 to-blue-900 bg-clip-text text-transparent uppercase">
                  Symatics
                </h1>
                <p className="text-xl text-white/80 font-mono">
                  Start with patterns, not numbers.
                </p>
              </div>

              {/* Visual Equation */}
              <div className="bg-white/5 border border-white/10 rounded-3xl p-12 text-center">
                <div className="text-7xl mb-6 tracking-widest">
                  🌊 + 🌊 = <span className="text-blue-400 drop-shadow-[0_0_15px_rgba(96,165,250,0.5)]">🌊✨</span>
                </div>
                <p className="text-white/40 font-mono italic">
                  Two waves combine into one stronger pattern.
                </p>
              </div>

              {/* Primitives Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['🌊 Wave', '💡 Photon', '⊕ Superpose', '↔ Entangle', '⟲ Resonance', '∇ Collapse', '⇒ Trigger'].map((op) => (
                  <div key={op} className="p-4 bg-white/5 border border-white/5 rounded-xl text-center hover:border-blue-500/50 transition-colors cursor-default">
                    <span className="text-sm font-mono text-white/80">{op}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* 🔘 CTA Footer */}
        <footer className="mt-20 flex gap-6">
          <button className="px-10 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-full font-bold transition-all transform hover:scale-105">
            Launch GlyphNet
          </button>
          <button className="px-10 py-4 border border-white/20 hover:bg-white/10 text-white rounded-full font-bold transition-all">
            View Multiverse
          </button>
        </footer>
      </main>

      {/* 📟 Demo HUD */}
      <div className="fixed bottom-6 right-6 p-4 bg-black/80 border border-white/10 rounded-2xl backdrop-blur-md text-[10px] font-mono text-white/40 tracking-tighter uppercase">
        <div className="flex gap-4">
          <span>Space: Pause</span>
          <span>1-4: Glyph</span>
          <span>5-8: Symatics</span>
          <span className="text-blue-500">R: Restart</span>
        </div>
      </div>
    </div>
  );
};

// Helper Component for the Comparison Visuals
const ComparisonCard = ({ title, traditional, glyph, labels }: any) => (
  <div className="p-8 bg-white/5 border border-white/10 rounded-3xl space-y-6">
    <h3 className="text-xs font-mono text-white/40 uppercase tracking-[0.2em]">{title}</h3>
    <div className="space-y-2">
      <p className="text-[10px] text-white/30 uppercase">Traditional</p>
      <p className="text-sm text-white/60 leading-relaxed italic">{traditional}</p>
    </div>
    <div className="h-px bg-white/10 w-full" />
    <div className="space-y-2">
      <p className="text-[10px] text-blue-400 uppercase">Glyph OS</p>
      <div className="text-3xl tracking-widest py-2">{glyph}</div>
      <p className="text-[10px] font-mono text-white/40">{labels}</p>
    </div>
  </div>
);

export default Home;