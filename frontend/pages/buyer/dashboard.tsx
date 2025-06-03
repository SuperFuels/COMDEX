// pages/buyer/dashboard.tsx
import { useEffect, useState, useRef } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

// ─── BuyerMetrics type definition ─────────────────────────────────────
interface BuyerMetrics {
  totalSalesToday: number
  openOrders: number
  pendingEscrow: number
  availableProducts: number
  activeDeals: number
}

// ─── Five metrics with labels/colors ──────────────────────────────────
const METRICS = [
  { key: 'totalSalesToday',   label: 'Sales Today',        color: 'text-blue-600' },
  { key: 'openOrders',        label: 'Open Orders',        color: 'text-green-600' },
  { key: 'pendingEscrow',     label: 'Pending Escrow',     color: 'text-purple-600' },
  { key: 'availableProducts', label: 'Available Products', color: 'text-green-600' },
  { key: 'activeDeals',       label: 'Active Deals',       color: 'text-blue-600' },
]

// ─── Command‐button labels (will prefill+send) ───────────────────────
const COMMAND_TABS = [
  'Deal Flow',
  'Shipments',
  'Messages',
  'Escrow',
  'Contracts',
  'Suppliers',
  'Products',
]

export default function BuyerDashboard() {
  // 1) Only “buyer” can view this page
  useAuthRedirect('buyer')

  // 2) State for buyer metrics
  const [metrics, setMetrics]             = useState<BuyerMetrics | null>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [errorMetrics, setErrorMetrics]     = useState<string | null>(null)

  // 3) State for AI terminal
  const [queryText, setQueryText]         = useState('')
  const [analysisText, setAnalysisText]   = useState<string>('')
  const [chartData, setChartData]         = useState<ChartPoint[] | null>(null)
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [nextPage, setNextPage]           = useState<number | null>(null)
  const [isProcessing, setIsProcessing]   = useState(false)

  // 4) On‐mount: fetch buyer metrics
  useEffect(() => {
    let isMounted = true
    async function fetchMetrics() {
      try {
        // Suppose your backend has GET /api/buyer/dashboard → BuyerMetrics
        const res = await api.get<BuyerMetrics>('/buyer/dashboard')
        if (isMounted) {
          setMetrics(res.data)
        }
      } catch (err) {
        console.warn('Failed to fetch buyer metrics; using zeros fallback.')
        if (isMounted) {
          setMetrics({
            totalSalesToday: 0,
            openOrders: 0,
            pendingEscrow: 0,
            availableProducts: 0,
            activeDeals: 0,
          })
        }
      } finally {
        if (isMounted) setLoadingMetrics(false)
      }
    }
    fetchMetrics()
    return () => {
      isMounted = false
    }
  }, [])

  // 5) Send / Enter handler
  const handleSend = async () => {
    if (!queryText.trim()) return
    setIsProcessing(true)
    setAnalysisText('')
    setChartData(null)
    setSearchResults(null)
    setNextPage(null)

    try {
      const resp = await fetch('/api/terminal/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: queryText.trim() }),
      })
      const json = await resp.json()

      // Always show analysisText on the left
      setAnalysisText(json.analysisText || '')

      // If this is a product search, json.visualPayload.products is an array
      if (Array.isArray((json.visualPayload as any).products)) {
        setSearchResults((json.visualPayload as any).products)
        setNextPage((json.visualPayload as any).nextPage ?? null)
      }
      // If LLM returned chartData instead, store that
      else if (Array.isArray((json.visualPayload as any).chartData)) {
        setChartData((json.visualPayload as any).chartData)
      }
    } catch (err) {
      console.error('Terminal query failed', err)
      setAnalysisText('❌ Sorry, something went wrong. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  // 6) If user presses Enter in the input field
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  // 7) Clicking on one of the COMMAND_TABS
  const handleCommandTab = (label: string) => {
    setQueryText(label)
    // slight delay so input updates before sending
    setTimeout(() => {
      handleSend()
    }, 50)
  }

  // 8) “Next Page” for product searches
  const loadNextPage = async () => {
    if (!nextPage) return
    setIsProcessing(true)
    try {
      const resp = await api.get<any[]>(
        `/products?search=${encodeURIComponent(queryText.trim())}&limit=10&page=${nextPage}`
      )
      const more = resp.data || []
      setSearchResults(prev => (prev ? [...prev, ...more] : more))
      setNextPage(more.length === 10 ? nextPage + 1 : null)
    } catch (err) {
      console.error('Next page fetch failed', err)
    } finally {
      setIsProcessing(false)
    }
  }

  // 9) Loading / error states for metrics
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

  // At this point, metrics is non-null
  const m = metrics!

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      {/* ─── Spacer for sticky Navbar (height = 4rem) ────────────────── */}
      <div className="h-16" />

      {/* ─── Main “Text | Visual” area ──────────────────────────────── */}
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* ── Left Pane: Greeting, metrics, AI analysis ─────────── */}
          <div className="flex-1 overflow-y-auto pr-2">
            <div className="h-full font-mono text-gray-800 text-sm">
              {/* Greeting */}
              <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>
              {/* Metrics */}
              {METRICS.map((mt) => {
                const rawVal = (m as any)[mt.key] ?? 0
                return (
                  <p key={mt.key} className="mb-1">
                    <span>“{mt.label}”: </span>
                    <span className={mt.color}>{rawVal}</span>
                  </p>
                )
              })}

              {/* AI’s analysisText (once returned) */}
              {analysisText && (
                <div className="mt-4 space-y-1">
                  {analysisText.split('\n').map((line, idx) => (
                    <p key={idx} className="mb-1">{line}</p>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── Vertical Divider ─────────────────────────────────────── */}
          <div className="w-px bg-gray-300" />

          {/* ── Right Pane: Chart or Product List ───────────────────── */}
          <div className="flex-1 overflow-y-auto pl-2">
            {searchResults ? (
              <div className="space-y-4">
                {searchResults.map((prod, i) => (
                  <div
                    key={i}
                    className="bg-white p-3 rounded shadow flex items-center space-x-3"
                  >
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL}${prod.image_url}`}
                      alt={prod.title}
                      className="h-16 w-16 object-cover rounded"
                      onError={(e) => { (e.target as any).src = '/placeholder.jpg' }}
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
                      onClick={loadNextPage}
                      disabled={isProcessing}
                      className="
                        px-4 py-2
                        border border-black rounded
                        text-sm text-black
                        hover:bg-gray-100
                        disabled:opacity-50 disabled:cursor-not-allowed
                      "
                    >
                      {isProcessing ? 'Loading…' : 'Next Page'}
                    </button>
                  </div>
                )}
              </div>
            ) : chartData && chartData.length > 0 ? (
              <Chart
                data={chartData}
                height={Math.floor(window.innerHeight - 4 * 16 - 64)}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Select a button or ask a question to see visual output here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── Fixed Bottom “Terminal” Bar ───────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-300 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2">
          <div className="flex">
            {/* LEFT HALF: Input + Send */}
            <div className="w-[calc(50%-20px)] flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type a question (e.g. “Build my report”)"
                value={queryText}
                onKeyDown={handleKeyDown}
                onChange={e => setQueryText(e.target.value)}
                className="
                  flex-1
                  py-2 px-4
                  border border-black rounded
                  bg-white
                  text-sm text-black
                  placeholder-gray-400
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                "
              />
              <button
                onClick={handleSend}
                disabled={isProcessing}
                className="
                  py-2 px-4
                  bg-black text-white
                  border border-black rounded
                  text-sm
                  hover:bg-gray-900
                  disabled:opacity-50 disabled:cursor-not-allowed
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
                  transition
                "
              >
                {isProcessing ? 'Working…' : 'Send'}
              </button>
            </div>

            {/* RIGHT HALF: Buyers’ Command Buttons (shifted 40px) */}
            <div className="w-[50%] flex flex-wrap items-center space-x-2 pl-10">
              {COMMAND_TABS.map((label) => (
                <button
                  key={label}
                  onClick={() => handleCommandTab(label)}
                  className="
                    px-3 py-1
                    border border-black rounded-md
                    text-sm text-black
                    hover:bg-gray-100
                    focus:outline-none
                  "
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}