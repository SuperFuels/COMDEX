'use client'

import { useState } from 'react'
import Head from 'next/head'
import api from '@/lib/api'

export async function getServerSideProps() {
  return { props: {} };
}

export default function CodexPlayground() {
  const [code, setCode] = useState('')
  const [result, setResult] = useState<any | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleExecute = async () => {
    setStatus('loading')
    setErrorMessage(null)
    try {
      const res = await api.post('aion/codex-playground', {
        code,
        container: 'codex_playground.dc.json',
        source: 'manual',
      })

      if (res.data.success) {
        setResult(res.data.result)
        setStatus('done')
      } else {
        setResult(null)
        setErrorMessage(res.data.error || 'Unknown error')
        setStatus('error')
      }
    } catch (err) {
      setErrorMessage('Network/server failure')
      setStatus('error')
    }
  }

  return (
    <>
      <Head>
        <title>CodexLang Playground • AION</title>
      </Head>
      <div className="p-8 max-w-5xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold flex items-center space-x-2">
          <span>📜 CodexLang Playground</span>
        </h1>

        {/* ⌨️ Code Input Panel */}
        <div className="space-y-4">
          <textarea
            className="w-full p-4 text-sm border border-gray-300 rounded-lg shadow-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
            rows={10}
            placeholder="Type CodexLang code here. Example: IF ☯ THEN → 🧠"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />

          <button
            onClick={handleExecute}
            disabled={!code || status === 'loading'}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {status === 'loading' ? 'Running...' : 'Execute CodexLang'}
          </button>
        </div>

        {/* ✅ Result Display */}
        {status === 'done' && result && (
          <div className="mt-6 space-y-4">
            <h2 className="text-xl font-semibold">🧠 Execution Output</h2>
            <pre className="p-4 bg-gray-100 dark:bg-gray-900 rounded-md text-sm whitespace-pre-wrap">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}

        {/* ❌ Error Display */}
        {status === 'error' && (
          <div className="text-red-500 font-medium">
            Execution failed: {errorMessage ?? 'Unexpected error'}
          </div>
        )}

        {/* 🔗 Link to Glyph Synthesis */}
        <div className="pt-8 text-right">
          <a
            href="/aion/synthesis"
            className="text-sm text-blue-600 hover:underline"
          >
            🧬 Switch to Glyph Synthesis Lab →
          </a>
        </div>
      </div>
    </>
  )
}