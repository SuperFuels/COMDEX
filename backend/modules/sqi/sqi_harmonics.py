'use client'

import { useEffect, useState } from 'react'
import Head from 'next/head'
import api from '@/lib/api' // your axios/fetch wrapper
import DriftPanel from '@/components/SQI/DriftPanel'

type Status = 'idle' | 'loading' | 'done' | 'error'

export default function GlyphSynthesisPage() {
  const [inputText, setInputText] = useState('')
  const [glyphs, setGlyphs] = useState<any[] | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [injectToContainer, setInjectToContainer] = useState(true)
  const [sourceLabel, setSourceLabel] = useState('manual')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Drift state
  const [containerPath, setContainerPath] = useState('backend/modules/dimensions/containers/test_container.dc.json')
  const [autoCheckDrift, setAutoCheckDrift] = useState(true)
  const [drift, setDrift] = useState<any | null>(null)
  const [driftLoading, setDriftLoading] = useState(false)
  const [driftErr, setDriftErr] = useState<string | null>(null)

  const handleGenerate = async () => {
    setStatus('loading')
    setErrorMessage(null)
    try {
      const res = await api.post('/glyphs/synthesize', {
        text: inputText,
        inject: injectToContainer,
        source: sourceLabel,
      })
      setGlyphs(res.data?.glyphs || [])
      setStatus('done')
      // optionally refresh drift after synthesis
      if (autoCheckDrift) await refreshDrift()
    } catch (err: any) {
      console.error(err)
      setErrorMessage(err?.response?.data?.detail || err.message || 'Error generating glyphs')
      setStatus('error')
    }
  }

  const refreshDrift = async () => {
    setDriftLoading(true)
    setDriftErr(null)
    try {
      // Assumes you exposed an endpoint that triggers compute_drift with --suggest
      // e.g. POST /api/sqi/drift  body: { container_path, suggest: true }
      const res = await api.post('/sqi/drift', {
        container_path: containerPath,
        suggest: true,
      })
      setDrift(res.data)
    } catch (err: any) {
      console.error(err)
      setDriftErr(err?.response?.data?.detail || err.message || 'Failed to compute drift')
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
        <title>Glyph Synthesis</title>
      </Head>

      <div className="max-w-5xl mx-auto p-6 space-y-6">
        {/* ===== SQI Drift Panel ===== */}
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

          {/* file path to compute drift against */}
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

          {/* Visual panel from your component */}
          <DriftPanel
            data={drift}
            loading={driftLoading}
            error={driftErr || undefined}
          />
        </div>

        {/* ===== Glyph Synthesis UI ===== */}
        <div className="rounded-lg border p-4 space-y-3">
          <h2 className="text-lg font-semibold">Glyph Synthesis</h2>

          <textarea
            className="w-full border rounded p-2 min-h-[140px]"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Enter text to synthesize into glyphs…"
          />

          <div className="flex items-center gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={injectToContainer}
                onChange={() => setInjectToContainer(!injectToContainer)}
              />
              Inject to container
            </label>
            <label className="flex items-center gap-2">
              Source:
              <input
                className="border rounded px-2 py-1"
                value={sourceLabel}
                onChange={(e) => setSourceLabel(e.target.value)}
              />
            </label>
            <button
              className="ml-auto px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
              onClick={handleGenerate}
              disabled={status === 'loading'}
            >
              {status === 'loading' ? 'Generating…' : 'Generate Glyphs'}
            </button>
          </div>

          {errorMessage && (
            <div className="text-red-600 text-sm">Error: {errorMessage}</div>
          )}

          {glyphs && glyphs.length > 0 && (
            <div className="mt-3 grid gap-3">
              {glyphs.map((g, i) => (
                <pre key={i} className="bg-gray-50 border rounded p-3 text-xs overflow-auto">
{JSON.stringify(g, null, 2)}
                </pre>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}