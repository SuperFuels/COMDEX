'use client'

import { useEffect, useState } from 'react'
import Head from 'next/head'
import api from '@/lib/api'
import DriftPanel from '@/components/SQI/DriftPanel'
import KGList from '@/components/SQI/KGList'

type Status = 'idle' | 'loading' | 'done' | 'error'

export default function GlyphSynthesisPage() {
  // ---- existing synthesis state ----
  const [inputText, setInputText] = useState('')
  const [glyphs, setGlyphs] = useState<any[] | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [injectToContainer, setInjectToContainer] = useState(true)
  const [sourceLabel, setSourceLabel] = useState('manual')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // ---- drift state (for DriftPanel) ----
  const [containerPath, setContainerPath] = useState(
    'backend/modules/dimensions/containers/test_container.dc.json'
  )
  const [autoCheckDrift, setAutoCheckDrift] = useState(true)
  const [drift, setDrift] = useState<any | null>(null)
  const [driftLoading, setDriftLoading] = useState(false)
  const [driftErr, setDriftErr] = useState<string | null>(null)

  // == actions ==
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

      if (res.data?.success) {
        setGlyphs(res.data.glyphs || [])
        setStatus('done')
      } else {
        setGlyphs(res.data?.glyphs || [])
        setErrorMessage(res.data?.error || 'Unknown synthesis error')
        setStatus('error')
      }

      if (autoCheckDrift) {
        await refreshDrift()
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Network or server error')
      setStatus('error')
    }
  }

  const refreshDrift = async () => {
    setDriftLoading(true)
    setDriftErr(null)
    try {
      // backend should expose POST /sqi/drift
      const res = await api.post('/sqi/drift', {
        container_path: containerPath,
        suggest: true,
      })
      setDrift(res.data)
    } catch (err: any) {
      setDriftErr(err?.response?.data?.detail || err?.message || 'Failed to compute drift')
    } finally {
      setDriftLoading(false)
    }
  }

  useEffect(() => {
    if (autoCheckDrift) refreshDrift()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoCheckDrift, containerPath])

  return (
    <>
      <Head>
        <title>Glyph Compression • AION</title>
      </Head>

      <div className="p-8 max-w-6xl mx-auto space-y-8">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <span>🧬 Glyph Synthesis Lab</span>
        </h1>

        {/* ===== top row: synthesis form + KG sidebar ===== */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* --- Left / main: Synthesis form --- */}
          <div className="lg:col-span-2 space-y-4">
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

              <label className="inline-flex items-center gap-2">
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

            {/* Results */}
            {(status === 'done' || (status === 'error' && glyphs)) && glyphs && (
              <div className="mt-6 space-y-2">
                <h2 className="text-xl font-semibold">Generated Glyphs</h2>
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
          </div>

          {/* --- Right / sidebar: KG list --- */}
          <aside className="space-y-4">
            <div className="rounded-lg border p-4">
              <h3 className="font-semibold mb-2">Knowledge Graph</h3>
              {/* render as-is; your component defines its own data fetching/props */}
              <KGList />
            </div>
          </aside>
        </div>

        {/* ===== Drift section ===== */}
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">SQI Drift & Harmonics</h2>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoCheckDrift}
                onChange={(e) => setAutoCheckDrift(e.target.checked)}
              />
              Auto-check drift
            </label>
          </div>

          <div className="flex gap-2">
            <input
              className="flex-1 border rounded px-2 py-1"
              value={containerPath}
              onChange={(e) => setContainerPath(e.target.value)}
              placeholder="backend/modules/dimensions/containers/test_container.dc.json"
            />
            <button
              className="px-3 py-1 rounded bg-gray-800 text-white disabled:opacity-50"
              onClick={refreshDrift}
              disabled={driftLoading}
            >
              {driftLoading ? 'Checking…' : 'Refresh'}
            </button>
          </div>

          <DriftPanel data={drift} loading={driftLoading} error={driftErr || undefined} />
        </div>

        {/* link to multiverse */}
        <div className="pt-4 text-right">
          <a href="/aion/multiverse" className="text-sm text-blue-600 hover:underline">
            🌌 View Multiverse Grid & Container Map →
          </a>
        </div>
      </div>
    </>
  )
}