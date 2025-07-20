'use client'

import { useState } from 'react'
import Head from 'next/head'
import api from '@/lib/api'

export default function GlyphSynthesisPage() {
  const [inputText, setInputText] = useState('')
  const [glyphs, setGlyphs] = useState<string[] | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [injectToContainer, setInjectToContainer] = useState(true)
  const [glyphTags, setGlyphTags] = useState('')
  const [sourceLabel, setSourceLabel] = useState('manual')

  const handleSynthesize = async () => {
    setStatus('loading')
    try {
      const res = await api.post('/aion/synthesize-glyphs', {
        input: inputText,
        source: sourceLabel,
        inject: injectToContainer,
        tags: glyphTags
          .split(',')
          .map(tag => tag.trim())
          .filter(Boolean),
      })
      setGlyphs(res.data.glyphs || [])
      setStatus('done')
    } catch (err) {
      console.error('Synthesis failed', err)
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

        <div className="space-y-4">
          <textarea
            className="w-full p-4 text-sm border border-gray-300 rounded-lg shadow-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
            rows={10}
            placeholder="Enter reflection, thought, or symbolic text to compress into glyphs..."
            value={inputText}
            onChange={e => setInputText(e.target.value)}
          />

          <div className="flex flex-wrap gap-4 items-center">
            <input
              type="text"
              placeholder="Optional tags (comma-separated)"
              value={glyphTags}
              onChange={e => setGlyphTags(e.target.value)}
              className="flex-1 min-w-[200px] p-2 border border-gray-300 rounded-lg text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
            />
            <select
              value={sourceLabel}
              onChange={e => setSourceLabel(e.target.value)}
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
                onChange={e => setInjectToContainer(e.target.checked)}
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

        {status === 'done' && glyphs && (
          <div className="mt-6 space-y-2">
            <h2 className="text-xl font-semibold">Generated Glyphs:</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {glyphs.map((glyph, i) => (
                <div
                  key={i}
                  className="p-3 border rounded-lg bg-white dark:bg-gray-800 dark:border-gray-700 text-center"
                >
                  <code className="block text-lg">{glyph}</code>
                </div>
              ))}
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="text-red-500 font-medium">Something went wrong during synthesis.</div>
        )}

        <div className="pt-8 text-right">
          <a
            href="/aion/avatar-runtime"
            className="text-sm text-blue-600 hover:underline"
          >
            🧠 View Live GlyphGrid Runtime →
          </a>
        </div>
      </div>
    </>
  )
}