// frontend/pages/_app.tsx

import '@/lib/api'                // ← configure your axios instance first
import '@/styles/globals.css'     // ← pull in Tailwind + your custom globals
import type { AppProps } from 'next/app'
import { useEffect } from 'react'
import Navbar from '@/components/Navbar'
import SwapBar from '@/components/SwapBar'

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    // Debug your API URL
    console.log('🔍 NEXT_PUBLIC_API_URL =', process.env.NEXT_PUBLIC_API_URL)

    // If user still has a JWT, clear the manual-disconnect flag
    // so they’ll auto-reconnect their wallet on page reload
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      localStorage.removeItem('manualDisconnect')
    }
  }, [])

  return (
    <div className="flex min-h-screen">
      {/* We do NOT render <Sidebar /> here, because Navbar controls it. */}

      <div className="flex-1 flex flex-col">
        {/* ─── Global Navbar (white bg in light mode / dark bg in dark mode) ─── */}
        <Navbar />

        {/* 
          ─── Sticky SwapBar (only shown on mobile) ──────────────────────────
          We hide this at md: and above so that desktop no longer has
          the duplicated swap row. On smaller viewports, it remains visible.
        */}
        <div className="sticky top-16 z-20 bg-background-header dark:bg-background-dark md:hidden">
          <SwapBar />
        </div>

        {/* ─── Page Content ─────────────────────────────────────────────────── */}
        <main className="flex-1 bg-bg-page">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  )
}