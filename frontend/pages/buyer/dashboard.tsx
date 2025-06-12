"use client"

import { useEffect, useState } from 'react'
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
  'Deal Flow',
  'Shipments',
  'Messages',
  'Escrow',
  'Contracts',
  'Suppliers',
  'Products',
]

export default function BuyerDashboard() {
  useAuthRedirect('buyer')

  // metrics state
  const [metrics, setMetrics]               = useState<BuyerMetrics | null>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [errorMetrics, setErrorMetrics]     = useState<string | null>(null)

  // terminal state
  const [queryText, setQueryText]           = useState('')
  const [analysisText, setAnalysisText]     = useState<string>('')
  const [chartData, setChartData]           = useState<ChartPoint[] | null>(null)
  const [searchResults, setSearchResults]   = useState<any[] | null>(null)
  const [nextPage, setNextPage]             = useState<number | null>(null)
  const [isProcessing, setIsProcessing]     = useState(false)

  // ── fetch metrics
  useEffect(() => {
    let mounted = true
    api.get<BuyerMetrics>('/buyer/dashboard')
      .then(r => mounted && setMetrics(r.data))
      .catch(() => {
        console.warn('Failed to fetch buyer metrics; using zeros fallback.')
        if (mounted) {
          setMetrics({
            totalSalesToday: 0,
            openOrders: 0,
            pendingEscrow: 0,
            availableProducts: 0,
            activeDeals: 0,
          })
        }
      })
      .finally(() => mounted && setLoadingMetrics(false))
    return () => { mounted = false }
  }, [])

  // ── terminal send
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
          headers: { 'Content-Type': 'application/json' },
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
    } catch (err) {
      console.error('Terminal query failed', err)
      setAnalysisText('❌ Sorry, something went wrong. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCommandTab = (label: string) => {
    setQueryText(label)
    setTimeout(handleSend, 50)
  }

  const loadNextPage = async () => {
    if (!nextPage) return
    setIsProcessing(true)
    try {
      const resp = await api.get<any[]>(
        `/products?search=${encodeURIComponent(queryText.trim())}&limit=10&page=${nextPage}`
      )
      const more = resp.data || []
      setSearchResults(prev => prev ? [...prev, ...more] : more)
      setNextPage(more.length === 10 ? nextPage + 1 : null)
    } catch (err) {
      console.error('Next page fetch failed', err)
    } finally {
      setIsProcessing(false)
    }
  }

  // ── loading / error
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
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-4">
        <div className="flex h-full">
          {/* ── Left Pane */}
          <div className="flex-1 overflow-y-auto pr-4 font-mono text-gray-800 text-sm">
            <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>
            {METRICS.map(mt => {
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
                {analysisText.split('\n').map((line, i) => (
                  <p key={i} className="mb-1">{line}</p>
                ))}
              </div>
            )}
          </div>

          {/* divider */}
          <div className="w-px bg-gray-300" />

          {/* ── Right Pane */}
          <div className="flex-1 overflow-y-auto pl-4">
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
                      onError={e => { (e.target as any).src = '/placeholder.jpg' }}
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
                      className="px-4 py-2 border border-black rounded text-sm hover:bg-gray-100 disabled:opacity-50"
                    >
                      {isProcessing ? 'Loading…' : 'Next Page'}
                    </button>
                  </div>
                )}
              </div>
            ) : chartData && chartData.length > 0 ? (
              <Chart
                data={chartData}
                height={Math.floor(window.innerHeight - 4*16 - 64)}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Select a button or ask a question to see visual output here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ── Footer Terminal */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-300 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-4">
          <div className="flex">
            {/* input */}
            <div className="w-[calc(50%-20px)] flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type a question (e.g. “Build my report”)"
                value={queryText}
                onKeyDown={handleKeyDown}
                onChange={e => setQueryText(e.target.value)}
                className="flex-1 py-2 px-4 border border-black rounded bg-white text-sm"
              />
              <button
                onClick={handleSend}
                disabled={isProcessing}
                className="py-2 px-4 bg-black text-white border border-black rounded text-sm hover:bg-gray-900 disabled:opacity-50"
              >
                {isProcessing ? 'Working…' : 'Send'}
              </button>
            </div>
            {/* tabs */}
            <div className="w-[50%] flex flex-wrap items-center space-x-2 pl-8">
              {COMMAND_TABS.map(label => (
                <button
                  key={label}
                  onClick={() => handleCommandTab(label)}
                  className="px-3 py-1 border border-black rounded-md text-sm hover:bg-gray-100"
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