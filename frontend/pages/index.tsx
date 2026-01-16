// frontend/pages/index.tsx
'use client';

import { useState } from 'react';
import type { NextPage } from 'next';

/** * ⚠️ NOTE: QFC is currently disabled to prevent the useQFCFocus error 
 * breaking the demo until the Provider is implemented.
 */

const Home: NextPage = () => {
  const [activeTab, setActiveTab] = useState<'glyph' | 'symatics'>('glyph');

  return (
    /* h-full + min-h-screen ensures the background covers everything and allows scrolling */
    <div className="h-full min-h-screen bg-[#f5f5f7] text-[#1d1d1f] selection:bg-blue-100 font-sans antialiased overflow-y-auto">
      
      {/* Main container: Removed justify-center to allow natural top-to-bottom scrolling */}
      <main className="relative z-10 flex flex-col items-center pt-24 pb-32 px-6 max-w-5xl mx-auto">
        
        {/*  Minimalist Tab Switcher (Apple Style) */}
        <nav className="mb-20 p-1 bg-white/70 backdrop-blur-md border border-gray-200 rounded-full flex gap-1 shadow-sm sticky top-8 z-50">
          <button
            onClick={() => setActiveTab('glyph')}
            className={`px-10 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${
              activeTab === 'glyph' 
              ? 'bg-[#0071e3] text-white shadow-md' 
              : 'text-gray-500 hover:text-black'
            }`}
          >
            Glyph OS
          </button>
          <button
            onClick={() => setActiveTab('symatics')}
            className={`px-10 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${
              activeTab === 'symatics' 
              ? 'bg-[#0071e3] text-white shadow-md' 
              : 'text-gray-500 hover:text-black'
            }`}
          >
            Symatics
          </button>
        </nav>

        {/* 📦 Content Area */}
        <div className="w-full">
          
          {activeTab === 'glyph' && (
            <section className="animate-in fade-in zoom-in-95 duration-700 space-y-20">
              <div className="text-center space-y-8">
                <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
                  Glyph OS
                </h1>
                <p className="text-2xl md:text-3xl text-gray-500 font-light tracking-tight">
                  The Language of Symbols. <span className="text-black font-medium">The Speed of Light.</span>
                </p>
                <p className="max-w-2xl mx-auto text-lg md:text-xl text-gray-500 leading-relaxed">
                   An operating system built in symbols, executing at the speed of thought, 
                   compressed for the next era of cognition.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-10">
                <ComparisonCard 
                  title="Culinary Logic" 
                  traditional="Get eggs, crack, whisk, heat pan, add butter, cook, and plate."
                  glyph="🥚 → 🍳 → 🍽️"
                  labels="Ingredients → Cook → Serve"
                />
                <ComparisonCard 
                  title="Document Intelligence" 
                  traditional="Open document, scan for key points, extract data, summarize, and file."
                  glyph="📄 → ✨ → 🗂️"
                  labels="Input → Intelligence → Archive"
                />
              </div>

              <div className="text-center font-medium text-gray-400 text-xl pt-10">
                “Same result. Less noise.”
              </div>
            </section>
          )}

          {activeTab === 'symatics' && (
            <section className="animate-in fade-in zoom-in-95 duration-700 space-y-20">
              <div className="text-center space-y-8">
                <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
                  Symatics
                </h1>
                <p className="text-2xl md:text-3xl text-gray-500 font-light tracking-tight">
                  Start with <span className="text-[#0071e3] font-medium uppercase">patterns</span>, not numbers.
                </p>
              </div>

              <div className="bg-white rounded-[3rem] py-24 px-10 text-center shadow-xl shadow-gray-200/50 border border-gray-100">
                <div className="text-7xl md:text-9xl mb-8 tracking-widest flex justify-center items-center gap-6">
                  🌊 <span className="text-4xl text-gray-300">+</span> 🌊 <span className="text-4xl text-gray-300">=</span> <span className="text-[#0071e3] drop-shadow-2xl font-bold">🌊✨</span>
                </div>
                <p className="text-gray-400 text-xl italic pt-4">
                  Two waves combine into one stronger pattern.
                </p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                {['🌊 Wave', '💡 Photon', '⊕ Superpose', '↔ Entangle', '⟲ Resonance', '∇ Collapse', '⇒ Trigger'].map((op) => (
                  <div key={op} className="p-6 bg-white rounded-2xl text-center shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-default">
                    <span className="text-base font-semibold text-gray-700">{op}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* 🔘 Call to Action */}
        <footer className="mt-32 flex flex-col md:flex-row gap-6 pb-20">
          <button className="px-16 py-5 bg-black text-white rounded-full font-semibold text-xl hover:bg-gray-800 transition-all shadow-xl">
            Launch GlyphNet
          </button>
          <button className="px-16 py-5 border-2 border-black text-black rounded-full font-semibold text-xl hover:bg-black hover:text-white transition-all">
            View Multiverse
          </button>
        </footer>
      </main>

      {/* 📟 Control HUD */}
      <div className="fixed bottom-8 right-8 p-5 bg-white/80 border border-gray-200 rounded-2xl backdrop-blur-xl text-[12px] font-bold text-gray-400 tracking-wider shadow-2xl z-50">
        <div className="flex gap-8 uppercase">
          <span>Space: Pause</span>
          <span>1-4: Glyph</span>
          <span>5-8: Symatics</span>
          <span className="text-[#0071e3]">R: Restart</span>
        </div>
      </div>
    </div>
  );
};

/* Reusable Comparison Component */
const ComparisonCard = ({ title, traditional, glyph, labels }: any) => (
  <div className="p-12 bg-white rounded-[3rem] shadow-2xl shadow-gray-200/60 border border-gray-100 flex flex-col justify-between min-h-[400px]">
    <div>
      <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest mb-10">{title}</h3>
      <div className="mb-10">
        <p className="text-[11px] text-gray-400 font-black uppercase mb-3 tracking-widest">Traditional</p>
        <p className="text-xl text-gray-600 font-light leading-snug tracking-tight">{traditional}</p>
      </div>
    </div>
    <div className="pt-10 border-t border-gray-100">
      <p className="text-[11px] text-[#0071e3] font-black uppercase mb-5 tracking-widest">Glyph OS</p>
      <div className="text-6xl mb-4 leading-none">{glyph}</div>
      <p className="text-sm font-semibold text-gray-400 uppercase tracking-tight">{labels}</p>
    </div>
  </div>
);

export default Home;