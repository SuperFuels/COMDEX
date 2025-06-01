// frontend/pages/_app.tsx

import '@/lib/api'                // ← configure your axios instance first
import '@/styles/globals.css'     // ← Tailwind + your custom globals
import type { AppProps } from 'next/app'
import { useEffect } from 'react'
import Navbar from '@/components/Navbar'
// (We have removed the SwapBar import because the mobile swap-bar is no longer needed)

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
        {/* ─── Global Navbar (sticky at top) ─────────────────────────── */}
        <Navbar />

        {/*
          ─── Page Content ───────────────────────────────────────────
          We add padding-top so that the <Navbar> (which is height h-16 = 4rem)
          does not cover up the page content beneath it.
        */}
        <main className="flex-1 bg-bg-page pt-16">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  )
}