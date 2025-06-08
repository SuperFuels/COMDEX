// File: frontend/pages/supplier/dashboard.tsx

import { useEffect, useState, useRef } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import Chart, { ChartPoint } from '@/components/Chart'
import api from '@/lib/api'

type SupplierData = {
  totalSalesToday: number
  activeListings: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
  // you may have other fields here...
}

type TableRow = Record<string, any>

export default function SupplierDashboard() {
  // ─── Auth & initial data ────────────────────────────────────────────────
  useAuthRedirect('supplier')
  const [data, setData]     = useState<SupplierData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true
    api.get<SupplierData>('/supplier/dashboard')
      .then(res => { if (isMounted) setData(res.data) })
      .catch(err => { if (isMounted) setError(err.message) })
      .finally(() => { if (isMounted) setLoading(false) })
    return () => { isMounted = false }
  }, [])

  if (loading || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading dashboard…</p>
      </div>
    )
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  // ─── Metrics output ─────────────────────────────────────────────────────
  const metricsOutput = [
    { label: 'Sales Today',    value: data.totalSalesToday, color: 'text-blue-600' },
    { label: 'Active Listings', value: data.activeListings, color: 'text-green-600' },
    { label: 'Open Orders',     value: data.openOrders,    color: 'text-green-600' },
    { label: '30d Proceeds',    value: `£${data.proceeds30d}`, color: 'text-blue-600' },
    { label: 'Feedback',        value: data.feedbackRating,   color: 'text-purple-600' },
  ]

  // ─── Terminal state ─────────────────────────────────────────────────────
  const COMMAND_TABS = [
    'Sales',
    'Marketing',
    'Operations',
    'Shipments',
    'Financials',
    'Clients',
  ]
  const [queryText, setQueryText]         = useState('')
  const [analysisText, setAnalysisText]   = useState('')
  const [chartData, setChartData]         = useState<ChartPoint[]|null>(null)
  const [tableData, setTableData]         = useState<TableRow[]|null>(null)
  const [isProcessing, setIsProcessing]   = useState(false)
  const leftPaneRef = useRef<HTMLDivElement>(null)

  // ─── Send prompt to backend ─────────────────────────────────────────────
  const handleSend = async () => {
    if (!queryText.trim()) return
    setIsProcessing(true)
    setAnalysisText('')
    setChartData(null)
    setTableData(null)

    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = await resp.json()
      setAnalysisText(json.text || '')

      // decide which visual to show
      if (Array.isArray(json.visualPayload?.products)) {
        setTableData(json.visualPayload.products)
      } else if (Array.isArray(json.visualPayload?.chartData)) {
        setChartData(json.visualPayload.chartData)
      } else if (Array.isArray(json.visualPayload?.suppliers)) {
        setTableData(json.visualPayload.suppliers)
      }
    } catch (err) {
      console.error(err)
      setAnalysisText('❌ Sorry, something went wrong. Please try again.')
    } finally {
      setIsProcessing(false)
      // scroll left pane to bottom to show analysis
      setTimeout(() => leftPaneRef.current?.scrollTo(0, leftPaneRef.current.scrollHeight), 50)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTab = (tab: string) => {
    setQueryText(tab)
    setTimeout(handleSend, 50)
  }

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="bg-bg-page min-h-screen flex flex-col">
      <div className="h-16" />

      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* ── Left Pane ─────────────────────────────────────── */}
          <div
            ref={leftPaneRef}
            className="flex-1 overflow-auto pr-2 font-mono text-text-secondary text-sm"
          >
            <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
            {metricsOutput.map(m => (
              <p key={m.label} className="mb-1">
                <span>“{m.label}”: </span>
                <span className={m.color}>{m.value}</span>
              </p>
            ))}

            {/* AI analysis text */}
            {analysisText ? (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((line, i) => (
                  <p key={i} className="mb-1">{line}</p>
                ))}
              </div>
            ) : (
              <p className="italic text-text-secondary mt-4">
                Select a button or type a question below…
              </p>
            )}
          </div>

          {/* ── Divider ───────────────────────────────────────── */}
          <div className="w-px bg-border-light dark:bg-gray-700" />

          {/* ── Right Pane ────────────────────────────────────── */}
          <div className="flex-1 overflow-auto pl-2">
            {chartData && chartData.length > 0 ? (
              <Chart
                data={chartData}
                height={Math.floor(window.innerHeight - 4 * 16 - 64)}
              />
            ) : tableData && tableData.length > 0 ? (
              <table className="min-w-full bg-white">
                <thead>
                  <tr>
                    {Object.keys(tableData[0]).map(h => (
                      <th key={h} className="p-2 border">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tableData.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-100">
                      {Object.values(row).map((v, j) => (
                        <td key={j} className="p-2 border">{String(v)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="h-full flex items-center justify-center text-text-secondary italic">
                No visual output yet.
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── Bottom Bar ───────────────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-border-light dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2 flex">
          {/* Input + Send */}
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question (e.g. “Build my sales report”)"
              className="flex-1 py-2 px-4 border rounded bg-white dark:bg-gray-900"
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              onClick={handleSend}
              disabled={isProcessing}
              className="py-2 px-4 bg-black text-white rounded disabled:opacity-50"
            >
              {isProcessing ? 'Working…' : 'Send'}
            </button>
          </div>

          {/* Command Buttons */}
          <div className="w-[50%] flex flex-wrap items-center space-x-2 pl-4">
            {COMMAND_TABS.map(tab => (
              <button
                key={tab}
                onClick={() => handleTab(tab)}
                className="py-2 px-4 text-sm border rounded bg-white dark:bg-gray-900"
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}