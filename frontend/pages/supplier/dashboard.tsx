'use client'

import { useEffect, useRef, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'
import styles from './dashboard.module.css'

type SupplierMetrics = {
  totalSalesToday: number
  activeListings: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
}

type TerminalPayload = {
  analysisText: string
  visualPayload: {
    products?: any[]
    chartData?: ChartPoint[]
  }
}

const COMMAND_TABS = ['Sales','Marketing','Operations','Shipments','Financials','Clients']

export default function SupplierDashboard() {
  useAuthRedirect('supplier')

  const [metrics, setMetrics] = useState<SupplierMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [queryText, setQueryText]   = useState('')
  const [analysisText, setAnalysis] = useState('')
  const [chartData, setChartData]   = useState<ChartPoint[] | null>(null)
  const [results, setResults]       = useState<any[] | null>(null)
  const [working, setWorking]       = useState(false)

  // Split‐pane
  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState(0)
  const dragging = useRef(false)

  // center divider on mount
  useEffect(() => {
    const w = containerRef.current?.clientWidth ?? 0
    setDividerX(w / 2)
  }, [])

  // drag logic
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const { left, width } = containerRef.current.getBoundingClientRect()
      let x = e.clientX - left
      const min = width * 0.25, max = width * 0.75
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

  // fetch metrics
  useEffect(() => {
    let active = true
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r => active && setMetrics(r.data))
      .catch(e => active && setError(e.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  // terminal query
  const sendQuery = async () => {
    if (!queryText.trim()) return
    setWorking(true)
    setAnalysis('')
    setResults(null)
    setChartData(null)

    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: queryText.trim() })
        }
      )
      const json = await resp.json() as TerminalPayload
      setAnalysis(json.analysisText || '')
      if (Array.isArray(json.visualPayload.products)) {
        setResults(json.visualPayload.products)
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData)
      }
    } catch {
      setAnalysis('❌ Something went wrong.')
    } finally {
      setWorking(false)
    }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); sendQuery() }
  }
  const onTabClick = (label: string) => {
    setQueryText(label)
    setTimeout(sendQuery, 50)
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <p>Loading…</p>
      </div>
    )
  }
  if (error || !metrics) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      {/* edge-to-edge main */}
      <main className="flex-1 w-full">
        <div ref={containerRef} className="relative flex h-[calc(100vh-8rem)]">
          {/* Left Pane */}
          <div
            className={styles.leftPane}
            style={{ width: dividerX }}
          >
            <p className="mb-2">Hello, Supplier — welcome.</p>
            <p>Sales Today: <span className="text-blue-600">{metrics.totalSalesToday}</span></p>
            <p>Active Listings: <span className="text-green-600">{metrics.activeListings}</span></p>
            <p>Open Orders: <span className="text-green-600">{metrics.openOrders}</span></p>
            <p>30d Proceeds: <span className="text-blue-600">£{metrics.proceeds30d}</span></p>
            <p>Feedback: <span className="text-purple-600">{metrics.feedbackRating}</span></p>

            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((l,i) => <p key={i}>{l}</p>)}
              </div>
            )}
          </div>

          {/* Divider */}
          <div
            onMouseDown={onDividerDown}
            className={styles.splitter}
            style={{ left: dividerX - 3 }}
          />

          {/* Right Pane */}
          <div
            className={styles.rightPane}
            style={{
              position: 'absolute',
              top: 0,
              left: dividerX,
              width: `calc(100% - ${dividerX}px)`,
              height: '100%',
            }}
          >
            {results ? (
              results.map((item,i) => (
                <div key={i} className={styles.messageContainer}>
                  <pre className="text-xs">{JSON.stringify(item, null, 2)}</pre>
                </div>
              ))
            ) : chartData && chartData.length ? (
              <Chart
                data={chartData}
                height={(containerRef.current?.clientHeight ?? 0) - 64}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Select a tab or ask a question to see visual output here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* bottom bar */}
      <footer className={styles.bottomBar}>
        <div className={styles.inputGroup}>
          <input
            type="text"
            placeholder="Type a question…"
            value={queryText}
            onChange={e => setQueryText(e.target.value)}
            onKeyDown={onKey}
          />
          <button onClick={sendQuery} disabled={working}>
            {working ? 'Working…' : 'Send'}
          </button>
        </div>
        <div className="flex space-x-2">
          {COMMAND_TABS.map(label => (
            <button
              key={label}
              onClick={() => onTabClick(label)}
              className="px-3 py-1 border rounded text-sm"
            >
              {label}
            </button>
          ))}
        </div>
      </footer>
    </div>
  )
}