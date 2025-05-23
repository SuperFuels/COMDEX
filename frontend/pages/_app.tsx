// pages/_app.tsx

import '@/lib/api'                // ← configure your axios instance first
import '../styles/globals.css'
import type { AppProps } from 'next/app'
import { useEffect } from 'react'
import Navbar from '../components/Navbar'
import SwapBar from '../components/SwapBar'

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    // debug your API URL
    console.log('🔍 NEXT_PUBLIC_API_URL =', process.env.NEXT_PUBLIC_API_URL)

    // if user still has a JWT, clear the manual-disconnect flag
    // so they’ll auto-reconnect their wallet on page reload
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      localStorage.removeItem('manualDisconnect')
    }
  }, [])

  return (
    <>
      {/* global navbar */}
      <Navbar />

      {/* sticky swap controls */}
      <div className="sticky top-16 z-20 bg-gray-50">
        <SwapBar />
      </div>

      {/* app pages */}
      <Component {...pageProps} />
    </>
  )
}
