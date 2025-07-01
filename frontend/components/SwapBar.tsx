// frontend/components/SwapBar.tsx
"use client"

import { useRouter } from 'next/router'
import { useState, FormEvent } from 'react'
import Image from 'next/image'

export default function SwapBar() {
  const router = useRouter()
  const [query, setQuery]         = useState('')
  const [amountIn, setAmountIn]   = useState('')
  const [amountOut, setAmountOut] = useState('')

  const submitSearch = (e: FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (q) router.push(`/search?query=${encodeURIComponent(q)}`)
  }

  return (
    <div className="sticky top-16 z-20 bg-white border-b border-border-light">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center space-x-4">
        {/* ─── Marketplace search ────────────── */}
        <form onSubmit={submitSearch} className="flex-1">
          <input
            type="text"
            placeholder="Search by title or category…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </form>

        {/* ─── From Amount Input ─────────────── */}
        <input
          type="number"
          value={amountIn}
          onChange={e => setAmountIn(e.target.value)}
          placeholder="0"
          className="w-20 sm:w-32 p-2 border border-gray-300 rounded-lg text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* ─── From Token Picker ─────────────── */}
        <button
          type="button"
          className="flex items-center border border-black rounded-lg px-2 py-1 hover:bg-gray-50"
          onClick={() => {/* open your “from” token picker */}}
        >
          <Image src="/tokens/usdt.svg" alt="USDT" width={20} height={20} />
          <span className="ml-1 text-sm font-medium">USDT</span>
        </button>

        <span className="text-2xl text-gray-400 select-none">→</span>

        {/* ─── To Amount Input ───────────────── */}
        <input
          type="number"
          value={amountOut}
          onChange={e => setAmountOut(e.target.value)}
          placeholder="0"
          className="w-20 sm:w-32 p-2 border border-gray-300 rounded-lg text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* ─── To Token Picker ───────────────── */}
        <button
          type="button"
          className="flex items-center border border-black rounded-lg px-2 py-1 hover:bg-gray-50"
          onClick={() => {/* open your “to” token picker */}}
        >
          <Image src="/tokens/glu.svg" alt="GLU" width={20} height={20} />
          <span className="ml-1 text-sm font-medium">$GLU</span>
        </button>

        {/* ─── Swap Button ───────────────────── */}
        <button
          onClick={() => router.push('/swap')}
          className="px-4 py-1 border border-black rounded-lg text-black text-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Swap
        </button>
      </div>
    </div>
  )
}