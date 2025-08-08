'use client'

import { useState } from 'react'
import Head from 'next/head'
import api from '@/lib/api'
import DriftPanel from "@/components/SQI/DriftPanel";
// ...
<DriftPanel />
import KGList from "@/components/SQI/KGList";
//...
<KGList />
export default function GlyphSynthesisPage() {
  const [inputText, setInputText] = useState('')
  const [glyphs, setGlyphs] = useState<any[] | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [injectToContainer, setInjectToContainer] = useState(true)
  const [sourceLabel, setSourceLabel] = useState('manual')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleSynthesize = async () => {
    setStatus('loading')
    setErrorMessage(null)
    try {
      const res = await api.post('aion/synthesize-glyphs', {
        input: inputText,
        source: sourceLabel,
        inject_to_grid: injectToContainer,
        container: 'glyph_synthesis_lab.dc.json',
      })

      if (res.data.success) {
        setGlyphs(res.data.glyphs || [])
        setStatus('done')
      } else {
        setGlyphs(res.data.glyphs || [])
        setErrorMessage(res.data.error || 'Unknown synthesis error')
        setStatus('error')
      }
    } catch (err) {
      setErrorMessage('Network or server error')
      setStatus('error')
    }
  }

  return (
    <>
      <Head>
        <title>Glyph Compression • AION</title>
      </Head>
      <div className="p-8 max-w-5xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold flex items-center space-x-2">
          <span>🧬 Glyph Synthesis Lab</span>
        </h1>

        {/* 🔤 Input Panel */}
        <div className="space-y-4">
          <textarea
            className="w-full p-4 text-sm border border-gray-300 rounded-lg shadow-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
            rows={10}
            placeholder="Enter reflection, thought, or symbolic text to compress into glyphs..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />

          <div className="flex flex-wrap gap-4 items-center">
            <select
              value={sourceLabel}
              onChange={(e) => setSourceLabel(e.target.value)}
              className="p-2 border border-gray-300 rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
            >
              <option value="manual">Manual</option>
              <option value="reflection">Reflection</option>
              <option value="tessaris">Tessaris</option>
            </select>
            <label className="inline-flex items-center space-x-2">
              <input
                type="checkbox"
                checked={injectToContainer}
                onChange={(e) => setInjectToContainer(e.target.checked)}
                className="form-checkbox"
              />
              <span className="text-sm">Inject into container</span>
            </label>
            <button
              onClick={handleSynthesize}
              disabled={!inputText || status === 'loading'}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {status === 'loading' ? 'Synthesizing...' : 'Compress to Glyphs'}
            </button>
          </div>
        </div>

        {/* 🧩 Glyph Results */}
        {(status === 'done' || (status === 'error' && glyphs)) && glyphs && (
          <div className="mt-6 space-y-2">
            <h2 className="text-xl font-semibold">Generated Glyphs:</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {glyphs.map((glyph, i) => (
                <div
                  key={i}
                  className="p-3 border rounded-lg bg-white dark:bg-gray-800 dark:border-gray-700 text-center"
                >
                  <code className="block text-lg">{glyph.symbol ?? glyph}</code>
                  {glyph.meaning && (
                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      {glyph.meaning}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {status === 'error' && !glyphs && (
          <div className="text-red-500 font-medium">
            Synthesis failed: {errorMessage ?? 'Unexpected error'}
          </div>
        )}

        {/* 🔭 Link to Multiverse Viewer */}
        <div className="pt-8 text-right">
          <a
            href="/aion/multiverse"
            className="text-sm text-blue-600 hover:underline"
          >
            🌌 View Multiverse Grid & Container Map →
          </a>
        </div>
      </div>
    </>
  )
}