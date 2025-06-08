// File: frontend/pages/buyer/dashboard.tsx

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

  // buyer metrics
  const [metrics, setMetrics]               = useState<BuyerMetrics | null>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [errorMetrics, setErrorMetrics]     = useState<string | null>(null)

  // terminal
  const [queryText, setQueryText]         = useState('')
  const [analysisText, setAnalysisText]   = useState<string>('')
  const [chartData, setChartData]         = useState<ChartPoint[] | null>(null)
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [suppliers, setSuppliers]         = useState<any[] | null>(null)
  const [nextPage, setNextPage]           = useState<number | null>(null)
  const [isProcessing, setIsProcessing]   = useState(false)

  // fetch buyer metrics
  useEffect(() => {
    let mounted = true
    api.get<BuyerMetrics>('/buyer/dashboard')
      .then(r => mounted && setMetrics(r.data))
      .catch(() => {
        console.warn('Using zeros fallback')
        mounted && setMetrics({
          totalSalesToday:0, openOrders:0,
          pendingEscrow:0, availableProducts:0, activeDeals:0
        })
      })
      .finally(() => mounted && setLoadingMetrics(false))
    return () => { mounted = false }
  }, [])

  // send / enter handler
  const handleSend = async () => {
    if (!queryText.trim()) return

    setIsProcessing(true)
    setAnalysisText('')
    setChartData(null)
    setSearchResults(null)
    setSuppliers(null)
    setNextPage(null)

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: queryText.trim() }),
        }
      )
      const json = await res.json()

      setAnalysisText(json.text || '')

      // if products returned
      if (Array.isArray(json.products)) {
        setSearchResults(json.products)
      }
      // if suppliers returned
      if (Array.isArray(json.suppliers)) {
        setSuppliers(json.suppliers)
      }

      // (If you later add pagination/nextPage to the response, handle it here)
    } catch (err) {
      console.error('Terminal query failed', err)
      setAnalysisText('❌ Sorry, something went wrong. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  // enter key
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  // command tabs
  const handleCommandTab = (label: string) => {
    setQueryText(label)
    setTimeout(handleSend, 50)
  }

  if (loadingMetrics) {
    return <div className="min-h-screen...">Loading dashboard…</div>
  }
  if (errorMetrics) {
    return <div className="min-h-screen..."><p>{errorMetrics}</p></div>
  }

  const m = metrics!

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <div className="h-16" />
      <main className="flex-1...">
        <div className="flex...">
          {/* Left pane */}
          <div className="flex-1...">
            <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>
            {METRICS.map(mt => (
              <p key={mt.key} className="mb-1">
                <span>“{mt.label}”: </span>
                <span className={mt.color}>{(m as any)[mt.key] ?? 0}</span>
              </p>
            ))}
            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((line, i) => (
                  <p key={i} className="mb-1">{line}</p>
                ))}
              </div>
            )}
          </div>

          <div className="w-px bg-gray-300" />

          {/* Right pane */}
          <div className="flex-1...">
            {searchResults ? (
              <div className="space-y-4">
                {searchResults.map((prod,i)=>(
                  <div key={i} className="bg-white p-3...">
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL}${prod.image_url}`}
                      alt={prod.title}
                      className="h-16 w-16..."
                      onError={e=>{(e.target as any).src='/placeholder.jpg'}}
                    />
                    <div>
                      <h3 className="font-semibold">{prod.title}</h3>
                      <p className="text-sm text-gray-600">
                        {prod.description}
                      </p>
                      <p className="text-sm text-gray-500">
                        £{prod.price_per_kg}/kg · {prod.origin_country}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : suppliers ? (
              <div className="space-y-4">
                {suppliers.map((s,i)=>(
                  <div key={i} className="bg-white p-3...">
                    <h3 className="font-semibold">{s.name}</h3>
                    <p>Rating: {s.rating}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-full...">
                <p>Select a command or ask a question...</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer input bar */}
      <footer className="fixed bottom-0...">
        <div className="max-w... px-2">
          <div className="flex">
            <div className="w-[calc(50%-20px)] flex items-center...">
              <input
                type="text"
                placeholder="Type a question…"
                value={queryText}
                onKeyDown={handleKeyDown}
                onChange={e=>setQueryText(e.target.value)}
                className="flex-1 py-2 px-4 border..."
              />
              <button
                onClick={handleSend}
                disabled={isProcessing}
                className="py-2 px-4 bg-black text-white..."
              >
                {isProcessing ? 'Working…' : 'Send'}
              </button>
            </div>
            <div className="w-[50%] flex flex-wrap items-center... pl-10">
              {COMMAND_TABS.map(label=>(
                <button
                  key={label}
                  onClick={()=>handleCommandTab(label)}
                  className="px-3 py-1 border rounded-md..."
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