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
  products: {
    id: number
    title: string
    description: string
    price_per_kg: number
    origin_country: string
    image_url: string
  }[]
}

export default function SupplierDashboard() {
  useAuthRedirect('supplier')

  const [data, setData] = useState<SupplierData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // terminal state
  const [queryText, setQueryText] = useState('')
  const [analysisText, setAnalysisText] = useState('')
  const [chartData, setChartData] = useState<ChartPoint[] | null>(null)
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  // which tab
  const [selectedTab, setSelectedTab] = useState<string>('')

  useEffect(() => {
    let mounted = true
    api.get<SupplierData>('/supplier/dashboard')
      .then(r => mounted && setData(r.data))
      .catch(e => mounted && setError(e.message))
      .finally(() => mounted && setLoading(false))
    return () => { mounted = false }
  }, [])

  const handleSend = async () => {
    if (!queryText.trim()) return
    setIsProcessing(true)
    setAnalysisText('')
    setChartData(null)
    setSearchResults(null)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ prompt: queryText.trim() })
        }
      )
      const json = await res.json()
      setAnalysisText(json.analysisText || '')
      // if visualPayload.products
      if (Array.isArray(json.visualPayload.products)) {
        setSearchResults(json.visualPayload.products)
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData)
      }
    } catch {
      setAnalysisText('❌ Something went wrong. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const tabs = ['Sales','Marketing','Operations','Shipments','Financials','Clients']

  const metricsOutput = data ? [
    { label:'Sales Today', value:data.totalSalesToday, color:'text-blue-600' },
    { label:'Active Listings', value:data.activeListings, color:'text-green-600' },
    { label:'Open Orders', value:data.openOrders, color:'text-green-600' },
    { label:'30d Proceeds', value:`£${data.proceeds30d}`, color:'text-blue-600' },
    { label:'Feedback', value:data.feedbackRating, color:'text-purple-600' },
  ] : []

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-bg-page"><p className="text-text-secondary">Loading…</p></div>
  if (error || !data) return <div className="min-h-screen flex items-center justify-center bg-bg-page"><p className="text-red-600">{error}</p></div>

  // sample fallback chart if needed:
  const sampleChart: ChartPoint[] = data.products.map((p,i)=>({
    time: Math.floor(Date.now()/1000) - (data.products.length - i)*3600,
    value: p.price_per_kg
  }))

  return (
    <div className="bg-bg-page min-h-screen flex flex-col">
      <div className="h-16" />
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* left */}
          <div className="flex-1 overflow-auto pr-2 font-mono text-text dark:text-text-secondary text-sm">
            <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
            {metricsOutput.map((m)=>(
              <p key={m.label} className="mb-1">
                <span>{`“${m.label}”: `}</span>
                <span className={m.color}>{m.value}</span>
              </p>
            ))}

            {/* AI text */}
            {selectedTab && !queryText && (
              <div className="mt-4">
                <p className="italic text-text-secondary">Select a tab or type a question…</p>
              </div>
            )}
            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((l,i)=><p key={i} className="mb-1">{l}</p>)}
              </div>
            )}
          </div>

          <div className="w-px bg-border-light dark:bg-gray-700" />

          {/* right */}
          <div className="flex-1 overflow-auto pl-2">
            {searchResults ? (
              <div className="space-y-4">
                {searchResults.map((item,i)=>(
                  <pre key={i} className="bg-white p-3 rounded shadow text-xs">
                    {JSON.stringify(item,null,2)}
                  </pre>
                ))}
              </div>
            ) : (chartData || sampleChart).length > 0 ? (
              <Chart
                data={chartData || sampleChart}
                height={Math.floor(window.innerHeight - 4*16 - 64)}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-text-secondary">
                <p>Select a tab or ask a question to see visual output here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-border-light dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2">
          <div className="flex">
            <div className="w-[calc(50%-20px)] flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type a question (e.g. “Build my report”)"
                value={queryText}
                onKeyDown={handleKeyDown}
                onChange={e=>setQueryText(e.target.value)}
                className="flex-1 py-2 px-4 border border-black rounded bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSend}
                disabled={isProcessing}
                className="py-2 px-4 bg-black text-white border border-black rounded hover:bg-gray-900 disabled:opacity-50"
              >
                {isProcessing ? 'Working…' : 'Send'}
              </button>
            </div>
            <div className="w-[50%] flex space-x-2 pl-4">
              {tabs.map(tab=>(
                <button
                  key={tab}
                  onClick={()=>{
                    setSelectedTab(tab)
                    setQueryText(tab.toLowerCase())
                    setTimeout(handleSend,50)
                  }}
                  className="py-2 px-4 text-sm font-medium border border-black rounded bg-white dark:bg-gray-900 hover:bg-gray-100"
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}