'use client'

import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

type SupplierMetrics = {
  totalSalesToday: number
  activeListings: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
}

const COMMAND_TABS = ['Sales','Marketing','Operations','Shipments','Financials','Clients']

export default function SupplierDashboard() {
  useAuthRedirect('supplier')

  const [metrics, setMetrics] = useState<SupplierMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string|null>(null)

  useEffect(() => {
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r => setMetrics(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="h-screen flex items-center justify-center">Loading…</div>
  if (error || !metrics) return <div className="h-screen flex items-center justify-center text-red-500">{error||'Unknown error'}</div>

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col pb-16"> {/* pb-16 reserves space for fixed footer */}
      <main className="flex-1">
        <div className="flex h-[calc(100vh-4rem)]"> {/* 4rem = footer height */}
          
          {/* ── Left Pane */}
          <div className="w-1/2 bg-white p-6 overflow-auto border-r border-gray-200">
            <h2 className="text-xl font-semibold mb-4">Hello, Supplier — welcome.</h2>
            <p>Sales Today: <span className="text-blue-600">{metrics.totalSalesToday}</span></p>
            <p>Active Listings: <span className="text-green-600">{metrics.activeListings}</span></p>
            <p>Open Orders: <span className="text-green-600">{metrics.openOrders}</span></p>
            <p>30d Proceeds: <span className="text-blue-600">£{metrics.proceeds30d}</span></p>
            <p>Feedback: <span className="text-purple-600">{metrics.feedbackRating}</span></p>
          </div>

          {/* ── Right Pane */}
          <div className="w-1/2 bg-white p-6 overflow-auto">
            <div className="h-full flex items-center justify-center text-gray-500">
              <p>Select a tab or ask a question to see visual output here.</p>
            </div>
          </div>
        </div>
      </main>

      {/* ── Fixed Footer */}
      <footer className="fixed bottom-0 left-0 w-full h-16 bg-white border-t border-gray-200 flex items-center px-6 space-x-4 z-50">
        <input
          type="text"
          className="flex-1 border rounded px-4 py-2"
          placeholder="Type a question…"
        />
        <button className="px-4 py-2 bg-blue-600 text-white rounded">Send</button>
        {COMMAND_TABS.map(tab => (
          <button key={tab} className="px-3 py-1 border rounded text-sm">
            {tab}
          </button>
        ))}
      </footer>
    </div>
  )
}