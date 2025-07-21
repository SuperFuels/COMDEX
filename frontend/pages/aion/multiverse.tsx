'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import Head from 'next/head'

// Lazy-load the 3D map
const ContainerMap3D = dynamic(() => import('@/components/AION/ContainerMap3D'), { ssr: false })

export default function MultiversePage() {
  const [layout, setLayout] = useState<'ring' | 'grid' | 'sphere'>('sphere')

  return (
    <>
      <Head>
        <title>Multiverse Map • AION</title>
      </Head>

      {/* 🌌 Fullscreen canvas */}
      <div className="w-screen h-screen bg-black relative overflow-hidden">
        {/* 🧭 Floating HUD Controls */}
        <div className="absolute top-4 left-4 z-10 space-y-3 bg-black/70 backdrop-blur-md p-4 rounded-xl shadow-md text-white text-sm">
          <div className="font-bold text-lg mb-1">🌌 Multiverse Map</div>

          <div className="space-y-1">
            <label className="block">
              Layout:
              <select
                value={layout}
                onChange={(e) => setLayout(e.target.value as any)}
                className="ml-2 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-white"
              >
                <option value="sphere">Sphere</option>
                <option value="ring">Ring</option>
                <option value="grid">Grid</option>
              </select>
            </label>
          </div>

          <a
            href="/aion/glyph-synthesis"
            className="inline-block mt-3 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-xs"
          >
            ← Back to Synthesis Lab
          </a>
        </div>

        <ContainerMap3D layout={layout} />
      </div>
    </>
  )
}