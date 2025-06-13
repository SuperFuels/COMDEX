'use client'

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

  // ── Metrics
  const [metrics, setMetrics]               = useState<BuyerMetrics | null>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [errorMetrics, setErrorMetrics]     = useState<string | null>(null)

  // ── Terminal state
  const [queryText, setQueryText]         = useState('')
  const [analysisText, setAnalysisText]   = useState('')
  const [chartData, setChartData]         = useState<ChartPoint[] | null>(null)
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [nextPage, setNextPage]           = useState<number | null>(null)
  const [isProcessing, setIsProcessing]   = useState(false)

  // ── Split-pane
  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState(0)
  const dragging = useRef(false)

  useEffect(() => {
    const w = containerRef.current?.clientWidth ?? 0
    setDividerX(w / 2)
  }, [])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const { left, width } = containerRef.current.getBoundingClientRect()
      let x = e.clientX - left
      const min = width * 0.25
      const max = width * 0.75
      x = Math.max(min, Math.min(max, x))
      setDividerX(x)
    }
    const onUp = () => { dragging.current = false }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  const onDividerDown = (e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
  }

  // ── Fetch buyer metrics
  useEffect(() => {
    let active = true
    api.get<BuyerMetrics>('/buyer/dashboard')
      .then(r => active && setMetrics(r.data))
      .catch(() => {
        if (active) {
          console.warn('Metrics fetch failed; defaulting zeros.')
          setMetrics({
            totalSalesToday: 0,
            openOrders: 0,
            pendingEscrow: 0,
            availableProducts: 0,
            activeDeals: 0,
          })
        }
      })
      .finally(() => active && setLoadingMetrics(false))
    return () => { active = false }
  }, [])

  // ── Terminal send
  const sendQuery = async () => {
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
          body: JSON.stringify({ prompt: queryText.trim() })
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
      setAnalysisText('❌ Something went wrong. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }
  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); sendQuery() }
  }
  const onTabClick = (label: string) => {
    setQueryText(label)
    setTimeout(sendQuery, 50)
  }
  const loadMore = async () => {
    if (!nextPage) return
    setIsProcessing(true)
    try {
      const resp = await api.get<any[]>(
        `/products?search=${encodeURIComponent(queryText)}&limit=10&page=${nextPage}`
      )
      const more = resp.data || []
      setSearchResults(prev => prev ? [...prev, ...more] : more)
      setNextPage(more.length===10 ? nextPage+1 : null)
    } finally {
      setIsProcessing(false)
    }
  }

  // ── Render
  if (loadingMetrics) {
    return <div className="h-screen flex items-center justify-center bg-gray-50">
      <p>Loading…</p>
    </div>
  }
  if (errorMetrics || !metrics) {
    return <div className="h-screen flex items-center justify-center bg-gray-50">
      <p className="text-red-500">{errorMetrics}</p>
    </div>
  }
  const m = metrics!

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-4">
        <div ref={containerRef} className="relative flex h-[calc(100vh-8rem)]">

          {/* Left Pane */}
          <div
            className="overflow-auto pr-4 font-mono text-gray-800 text-sm"
            style={{ width: dividerX }}
          >
            <p className="mb-2">Hello, Buyer — welcome.</p>
            {METRICS.map(mt => (
              <p key={mt.key} className="mb-1">
                <span>“{mt.label}”: </span>
                <span className={mt.color}>{(m as any)[mt.key]}</span>
              </p>
            ))}
            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((l,i)=><p key={i}>{l}</p>)}
              </div>
            )}
          </div>

          {/* Divider */}
          <div
            onMouseDown={onDividerDown}
            className="bg-gray-300 hover:bg-blue-500"
            style={{ cursor:'col-resize', width:6, marginLeft:-3, zIndex:10 }}
          />

          {/* Right Pane */}
          <div className="flex-1 overflow-auto pl-4">
            {searchResults ? (
              <>
                {searchResults.map((p,i)=>(
                  <div key={i} className="bg-white p-3 rounded shadow mb-2 flex items-center space-x-3">
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL}${p.image_url}`}
                      alt={p.title}
                      className="h-16 w-16 object-cover rounded"
                      onError={e=>{(e.target as any).src='/placeholder.jpg'}}
                    />
                    <div>
                      <h3 className="font-semibold">{p.title}</h3>
                      <p className="text-sm">{p.description}</p>
                      <p className="text-sm">£{p.price_per_kg}/kg · {p.origin_country}</p>
                    </div>
                  </div>
                ))}
                {nextPage && (
                  <button
                    onClick={loadMore}
                    disabled={isProcessing}
                    className="px-4 py-2 border rounded"
                  >
                    {isProcessing ? 'Loading…' : 'Next Page'}
                  </button>
                )}
              </>
            ) : chartData && chartData.length > 0 ? (
              <Chart
                data={chartData}
                height={(containerRef.current?.clientHeight ?? 0) - 64}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Ask a question or pick a tab to see data here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-4 flex">
          <div
            className="flex items-center space-x-2"
            style={{ width: dividerX - 20 }}
          >
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e=>setQueryText(e.target.value)}
              onKeyDown={onKeyDown}
              className="flex-1 py-2 px-4 border rounded"
            />
            <button
              onClick={sendQuery}
              disabled={isProcessing}
              className="py-2 px-4 bg-black text-white rounded"
            >
              {isProcessing ? 'Working…' : 'Send'}
            </button>
          </div>
          <div className="flex-1 flex justify-end space-x-2">
            {COMMAND_TABS.map(label => (
              <button
                key={label}
                onClick={()=>onTabClick(label)}
                className="px-3 py-1 border rounded text-sm"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}