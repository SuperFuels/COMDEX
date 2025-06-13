// File: frontend/pages/buyer/dashboard.tsx
"use client"

import { useEffect, useRef, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

interface BuyerMetrics {
  totalSalesToday: number
  openOrders: number
  pendingEscrow: number
  availableProducts: number
  activeDeals: number
}

const METRICS = [
  { key: 'totalSalesToday',   label: 'Sales Today',        color: 'text-blue-600' },
  { key: 'openOrders',        label: 'Open Orders',        color: 'text-green-600' },
  { key: 'pendingEscrow',     label: 'Pending Escrow',     color: 'text-purple-600' },
  { key: 'availableProducts', label: 'Available Products', color: 'text-green-600' },
  { key: 'activeDeals',       label: 'Active Deals',       color: 'text-blue-600' },
]

const COMMAND_TABS = [
  'Deal Flow','Shipments','Messages','Escrow',
  'Contracts','Suppliers','Products',
]

export default function BuyerDashboard() {
  useAuthRedirect('buyer')

  // ── Metrics state ────────────────────────────────────────────
  const [metrics, setMetrics]               = useState<BuyerMetrics | null>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [errorMetrics, setErrorMetrics]     = useState<string | null>(null)

  // ── Terminal state ───────────────────────────────────────────
  const [queryText, setQueryText]         = useState('')
  const [analysisText, setAnalysisText]   = useState('')
  const [chartData, setChartData]         = useState<ChartPoint[] | null>(null)
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [nextPage, setNextPage]           = useState<number | null>(null)
  const [isProcessing, setIsProcessing]   = useState(false)

  // ── Split‐pane state ──────────────────────────────────────────
  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState<number>(window.innerWidth / 2)
  const dragging = useRef(false)

  // initialize to 50% of container
  useEffect(() => {
    const el = containerRef.current
    if (el) setDividerX(el.clientWidth / 2)
  }, [containerRef.current])

  // drag handlers
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const { left, width } = containerRef.current.getBoundingClientRect()
      let x = e.clientX - left
      x = Math.max(100, Math.min(width - 100, x))  // keep 100px min widths
      setDividerX(x)
    }
    const onMouseUp = () => { dragging.current = false }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  const onDividerMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
  }

  // ── Fetch buyer metrics ────────────────────────────────────────
  useEffect(() => {
    let m = true
    api.get<BuyerMetrics>('/buyer/dashboard')
      .then(r => m && setMetrics(r.data))
      .catch(() => {
        if (m) {
          setMetrics({
            totalSalesToday: 0,
            openOrders: 0,
            pendingEscrow: 0,
            availableProducts: 0,
            activeDeals: 0,
          })
        }
      })
      .finally(() => m && setLoadingMetrics(false))
    return () => { m = false }
  }, [])

  // ── Terminal “Send” ───────────────────────────────────────────
  const handleSend = async () => {
    if (!queryText.trim()) return
    setIsProcessing(true)
    setAnalysisText('')
    setChartData(null)
    setSearchResults(null)
    setNextPage(null)
    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type':'application/json' },
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = await resp.json()
      setAnalysisText(json.analysisText || '')
      if (Array.isArray(json.visualPayload.products)) {
        setSearchResults(json.visualPayload.products)
        setNextPage((json.visualPayload as any).nextPage ?? null)
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData!)
      }
    } catch {
      setAnalysisText('❌ Something went wrong.')
    } finally {
      setIsProcessing(false)
    }
  }
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); handleSend() }
  }
  const handleTab = (label: string) => {
    setQueryText(label)
    setTimeout(handleSend, 50)
  }

  // ── Loading / Errors ──────────────────────────────────────────
  if (loadingMetrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }
  if (errorMetrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{errorMetrics}</p>
      </div>
    )
  }

  const m = metrics!

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-4">
        <div ref={containerRef} className="flex h-[calc(100vh-4rem-4rem)] relative">
          {/* ── Left Pane ─────────────────────────────── */}
          <div
            className="overflow-auto pr-4 font-mono text-gray-800 text-sm"
            style={{ width: dividerX }}
          >
            <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>
            {METRICS.map((mt) => {
              const val = (m as any)[mt.key] ?? 0
              return (
                <p key={mt.key} className="mb-1">
                  <span>“{mt.label}”: </span>
                  <span className={mt.color}>{val}</span>
                </p>
              )
            })}
            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((line,i) => (
                  <p key={i} className="mb-1">{line}</p>
                ))}
              </div>
            )}
          </div>

          {/* ── Divider ───────────────────────────────── */}
          <div
            onMouseDown={onDividerMouseDown}
            className="hover:bg-blue-500 bg-gray-300"
            style={{
              cursor: 'col-resize',
              width: 6,
              marginLeft: -3,
              zIndex: 10,
            }}
          />

          {/* ── Right Pane ────────────────────────────── */}
          <div
            className="overflow-auto pl-4 flex-1"
          >
            {searchResults ? (
              <div className="space-y-4">
                {searchResults.map((prod,i) => (
                  <div
                    key={i}
                    className="bg-white p-3 rounded shadow flex items-center space-x-3"
                  >
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL}${prod.image_url}`}
                      alt={prod.title}
                      className="h-16 w-16 object-cover rounded"
                      onError={(e)=>{(e.target as any).src='/placeholder.jpg'}}
                    />
                    <div>
                      <h3 className="font-semibold">{prod.title}</h3>
                      <p className="text-sm text-gray-600">{prod.description}</p>
                      <p className="text-sm text-gray-500">
                        £{prod.price_per_kg}/kg · {prod.origin_country}
                      </p>
                    </div>
                  </div>
                ))}
                {nextPage && (
                  <div className="text-center">
                    <button
                      onClick={async () => {
                        setIsProcessing(true)
                        try {
                          const resp = await api.get<any[]>(
                            `/products?search=${encodeURIComponent(queryText.trim())}&limit=10&page=${nextPage}`
                          )
                          const more = resp.data || []
                          setSearchResults(prev => prev ? [...prev, ...more] : more)
                          setNextPage(more.length===10 ? nextPage+1 : null)
                        } finally {
                          setIsProcessing(false)
                        }
                      }}
                      disabled={isProcessing}
                      className="px-4 py-2 border rounded hover:bg-gray-100 disabled:opacity-50"
                    >
                      {isProcessing ? 'Loading…' : 'Next Page'}
                    </button>
                  </div>
                )}
              </div>
            ) : chartData && chartData.length > 0 ? (
              <Chart
                data={chartData}
                height={window.innerHeight - (4*16) - 64}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Select a tab or ask a question…</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-4 flex">
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 border rounded py-2 px-4 text-sm"
            />
            <button
              onClick={handleSend}
              disabled={isProcessing}
              className="bg-black text-white border rounded py-2 px-4 hover:bg-gray-900 disabled:opacity-50"
            >
              {isProcessing ? 'Working…' : 'Send'}
            </button>
          </div>
          <div className="w-[50%] flex space-x-2 pl-4">
            {COMMAND_TABS.map(tab => (
              <button
                key={tab}
                onClick={() => handleTab(tab)}
                className="border rounded px-3 py-1 text-sm hover:bg-gray-100"
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