// frontend/components/SwapBar.tsx
import { useRouter } from 'next/router'
import { useState, FormEvent } from 'react'
import Image from 'next/image'

export default function SwapBar() {
  const router = useRouter()
  const [query, setQuery]       = useState('')
  const [amountIn, setAmountIn] = useState('')
  const [amountOut, setAmountOut] = useState('')

  const submitSearch = (e: FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (q) router.push(`/search?query=${encodeURIComponent(q)}`)
  }

  return (
    <div className="sticky top-16 z-20 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center space-x-4">
        {/* ─── Marketplace search ─── */}
        <form onSubmit={submitSearch} className="flex-1">
          <input
            type="text"
            placeholder="Search by title or category…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </form>

        {/* ─── Swap inputs & selectors ─── */}
        <input
          type="number"
          value={amountIn}
          onChange={e => setAmountIn(e.target.value)}
          placeholder="0"
          className="w-20 sm:w-32 p-2 border border-gray-300 rounded-lg text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="button"
          className="flex items-center border border-gray-300 rounded-lg px-2 py-1 hover:bg-gray-50"
          onClick={() => {/* open your “from” token picker */}}
        >
          <Image src="/tokens/usdt.svg" alt="USDT" width={20} height={20} />
          <span className="ml-1 text-sm font-medium">USDT</span>
        </button>

        <span className="text-2xl text-gray-400 select-none">→</span>

        <input
          type="number"
          value={amountOut}
          onChange={e => setAmountOut(e.target.value)}
          placeholder="0"
          className="w-20 sm:w-32 p-2 border border-gray-300 rounded-lg text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="button"
          className="flex items-center border border-gray-300 rounded-lg px-2 py-1 hover:bg-gray-50"
          onClick={() => {/* open your “to” token picker */}}
        >
          <Image src="/tokens/glu.svg" alt="GLU" width={20} height={20} />
          <span className="ml-1 text-sm font-medium">$GLU</span>
        </button>

        {/* ─── Swap button ─── */}
        <button
          onClick={() => router.push('/swap')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Swap
        </button>
      </div>
    </div>
  )
}

