// frontend/components/SwapBar.tsx

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
    <div className="sticky top-16 z-20 bg-background-header dark:bg-background-dark border-b border-border-light">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center space-x-3">
        {/* ─── Marketplace search ───────────────────────────────────────── */}
        <form onSubmit={submitSearch} className="flex-1">
          <input
            type="text"
            placeholder="Search by title or category…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="
              w-full h-10
              px-3
              border border-text-primary dark:border-text-secondary
              bg-transparent
              text-text-primary dark:text-text-secondary
              rounded-full
              focus:outline-none focus:ring-2 focus:ring-primary
            "
          />
        </form>

        {/* ─── Amount In input ─────────────────────────────────────────── */}
        <input
          type="number"
          value={amountIn}
          onChange={(e) => setAmountIn(e.target.value)}
          placeholder="0"
          className="
            w-20 sm:w-28 h-10
            px-3
            border border-text-primary dark:border-text-secondary
            bg-transparent
            text-center text-text-primary dark:text-text-secondary
            rounded-lg
            focus:outline-none focus:ring-2 focus:ring-primary
          "
        />

        {/* ─── “From” token picker ────────────────────────────────────── */}
        <button
          type="button"
          onClick={() => {
            /* open your “from” token picker */
          }}
          className="
            flex items-center h-10
            px-3
            border border-text-primary dark:border-text-secondary
            bg-transparent
            rounded-lg
            hover:bg-gray-50 dark:hover:bg-gray-800
            transition
          "
        >
          <Image src="/tokens/usdt.svg" alt="USDT" width={20} height={20} />
          <span className="ml-1 text-text-primary dark:text-text-secondary text-sm">
            USDT
          </span>
        </button>

        {/* ─── Arrow icon ───────────────────────────────────────────────── */}
        <span className="text-xl text-border-light dark:text-border-dark select-none">
          →
        </span>

        {/* ─── Amount Out input ────────────────────────────────────────── */}
        <input
          type="number"
          value={amountOut}
          onChange={(e) => setAmountOut(e.target.value)}
          placeholder="0"
          className="
            w-20 sm:w-28 h-10
            px-3
            border border-text-primary dark:border-text-secondary
            bg-transparent
            text-center text-text-primary dark:text-text-secondary
            rounded-lg
            focus:outline-none focus:ring-2 focus:ring-primary
          "
        />

        {/* ─── “To” token picker ──────────────────────────────────────── */}
        <button
          type="button"
          onClick={() => {
            /* open your “to” token picker */
          }}
          className="
            flex items-center h-10
            px-3
            border border-text-primary dark:border-text-secondary
            bg-transparent
            rounded-lg
            hover:bg-gray-50 dark:hover:bg-gray-800
            transition
          "
        >
          <Image src="/tokens/glu.svg" alt="GLU" width={20} height={20} />
          <span className="ml-1 text-text-primary dark:text-text-secondary text-sm">
            $GLU
          </span>
        </button>

        {/* ─── “Swap” button ───────────────────────────────────────────── */}
        <button
          onClick={() => router.push('/swap')}
          className="
            h-10
            px-4
            border border-text-primary dark:border-text-secondary
            bg-transparent
            text-text-primary dark:text-text-secondary
            rounded-lg
            hover:bg-gray-50 dark:hover:bg-gray-800
            focus:outline-none focus:ring-2 focus:ring-primary
            transition
          "
        >
          Swap
        </button>
      </div>
    </div>
  )
}