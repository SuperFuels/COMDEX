// frontend/pages/buyer/dashboard.tsx

import { useEffect, useState } from 'react'
import { NextPage } from 'next'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import { ChartPoint } from '@/components/Chart'

// NOTE: We are not actually rendering the Chart here anymore; 
// the “visual” pane is a placeholder. If you want to render real charts,
// you can re‐import Chart and pass it data to the right‐hand pane.
 
type BuyerTab =
  | 'dealFlow'
  | 'shipments'
  | 'messages'
  | 'escrow'
  | 'contracts'
  | 'suppliers'
  | 'products'

const BUYER_BUTTONS: { key: BuyerTab; label: string }[] = [
  { key: 'dealFlow',  label: 'Deal Flow' },
  { key: 'shipments', label: 'Shipments' },
  { key: 'messages',  label: 'Messages' },
  { key: 'escrow',    label: 'Escrow' },
  { key: 'contracts', label: 'Contracts' },
  { key: 'suppliers', label: 'Suppliers' },
  { key: 'products',  label: 'Products' },
]

const BuyerDashboard: NextPage = () => {
  // 1) Enforce login + buyer role
  useAuthRedirect('buyer')

  // 2) We’ll fetch some dummy data so we can display a greeting and metrics.
  //    In a real app, you might fetch buyer‐specific stats like “Active Orders Today” etc.
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [metrics, setMetrics] = useState<{
    salesToday: number
    openOrders: number
    activeShipments: number
    escrowBalance: number
  }>({
    salesToday: 0,
    openOrders: 0,
    activeShipments: 0,
    escrowBalance: 0,
  })

  useEffect(() => {
    async function loadBuyerMetrics() {
      try {
        // Example of fetching buyer‐specific data; replace with your real endpoints:
        // const res = await api.get('/buyer/metrics')
        // setMetrics(res.data)
        // For now, we’ll leave dummy zeroes:
        setMetrics({
          salesToday: 0,
          openOrders: 0,
          activeShipments: 0,
          escrowBalance: 0,
        })
      } catch (e) {
        console.error('Failed to load buyer metrics', e)
        setError('Failed to load dashboard data.')
      } finally {
        setLoading(false)
      }
    }
    loadBuyerMetrics()
  }, [])

  // 3) Terminal state:
  const [terminalInput, setTerminalInput]   = useState('')
  const [terminalOutput, setTerminalOutput] = useState<string>(
    `Hello, Buyer — welcome to Central Command.\n` +
    `“Sales Today”: ${metrics.salesToday}\n` +
    `“Open Orders”: ${metrics.openOrders}\n` +
    `“Active Shipments”: ${metrics.activeShipments}\n` +
    `“Escrow Balance”: £${metrics.escrowBalance}\n\n` +
    `Select one of the buttons below, or type a question in the input bar.`
  )

  // 4) “Visual” side placeholder:
  const [visualContent, setVisualContent] = useState<string>(
    'Select a button or ask a question to see visual output here.'
  )

  // 5) When a buyer‐button is clicked, update terminal & visual panes:
  const handleButtonClick = (tabKey: BuyerTab) => {
    // In a full implementation, you’d fetch real data & render. Here we just stub:
    switch (tabKey) {
      case 'dealFlow':
        setTerminalOutput(
          `→ Fetching Deal Flow…\n` +
          `You have no active deals right now.`
        )
        setVisualContent('📈 No active deals to visualize.')
        break
      case 'shipments':
        setTerminalOutput(
          `→ Checking active shipments…\n` +
          `You have ${metrics.activeShipments} shipments in progress.`
        )
        setVisualContent('📦 No shipments to display graph of.')
        break
      case 'messages':
        setTerminalOutput(
          `→ Opening your messages…\n` +
          `You have no new messages.`
        )
        setVisualContent('✉️ Inbox is empty.')
        break
      case 'escrow':
        setTerminalOutput(
          `→ Checking escrow balance…\n` +
          `Your current escrow balance is £${metrics.escrowBalance}.`
        )
        setVisualContent('🔒 Escrow: £' + metrics.escrowBalance)
        break
      case 'contracts':
        setTerminalOutput(
          `→ Fetching contracts…\n` +
          `No contracts available.`
        )
        setVisualContent('📝 No contracts to show.')
        break
      case 'suppliers':
        setTerminalOutput(
          `→ Fetching supplier list…\n` +
          `No suppliers found.`
        )
        setVisualContent('🏷️ Supplier list is empty.')
        break
      case 'products':
        setTerminalOutput(
          `→ Fetching available products…\n` +
          `No products currently listed.`
        )
        setVisualContent('🛍️ No products to display.')
        break
      default:
        setTerminalOutput(`Unknown button clicked.`)
        setVisualContent('')
        break
    }
  }

  // 6) When “Send” is clicked, pretend to send the terminalInput to an AI, then clear input:
  const handleSend = () => {
    if (!terminalInput.trim()) return
    // Stub: in a real app, send `terminalInput` to an AI endpoint.
    const userText = terminalInput.trim()
    setTerminalOutput((prev) =>
      prev +
      `\n\n> ${userText}\n` +
      `AI: Sorry, I can’t actually process that in this stub.`
    )
    setTerminalInput('')
    // Optionally update visualContent if needed:
    setVisualContent('🤖 (AI visual output stub)')
  }

  // 7) Loading / error states:
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  return (
    // Outer wrapper ensures we can have a fixed bottom bar overlapping content.
    <div className="bg-gray-50 min-h-screen relative">

      {/* Spacer for sticky navbar (height: 4rem) */}
      <div className="h-16" />

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* Main split area: Text Terminal (left) | Visual Output (right)            */}
      {/* We add 20px padding on either side to widen the usable area by 40px total */}
      <div className="flex" style={{ margin: '0 20px' }}>
        {/* Left half: Text terminal output */}
        <div className="flex-1 border-r border-gray-300 p-4 overflow-auto" style={{ height: 'calc(100vh - 4rem - 4rem)' }}>
          {/* “calc(100vh - navbarHeight - terminalBarHeight)” */}
          <pre className="font-mono text-sm whitespace-pre-wrap text-gray-800">
            {terminalOutput}
          </pre>
        </div>

        {/* Right half: Visual area */}
        <div className="flex-1 p-4 overflow-auto" style={{ height: 'calc(100vh - 4rem - 4rem)' }}>
          <div className="h-full flex items-center justify-center text-gray-500 text-sm">
            {visualContent}
          </div>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* Fixed terminal bar at bottom */}
      <div
        className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-300 p-4 flex items-center"
        style={{ margin: '0 20px', height: '4rem' }}
      >
        {/* Left: Text input + Send button */}
        <div className="flex items-center flex-1">
          <input
            type="text"
            placeholder={`Type a question (e.g. “Build my sales report”)`}
            value={terminalInput}
            onChange={(e) => setTerminalInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSend()
              }
            }}
            className="
              flex-1
              h-12
              px-4
              border border-black
              rounded-l-md
              text-gray-700
              placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
          />
          <button
            onClick={handleSend}
            className="
              h-12
              px-6
              bg-black
              text-white
              font-medium
              rounded-r-md
              hover:bg-gray-800
              focus:outline-none focus:ring-2 focus:ring-blue-400
              ml-2
            "
          >
            Send
          </button>
        </div>

        {/* Right: Buyer‐specific buttons */}
        <div className="flex space-x-2 ml-4">
          {BUYER_BUTTONS.map((btn) => (
            <button
              key={btn.key}
              onClick={() => handleButtonClick(btn.key)}
              className="
                border border-black
                rounded-md
                px-3 py-2
                bg-white
                text-gray-800
                hover:bg-gray-100
                focus:outline-none focus:ring-2 focus:ring-blue-400
              "
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default BuyerDashboard