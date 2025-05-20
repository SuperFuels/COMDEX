// pages/_app.tsx
import '@/lib/api'                // ← ensure this runs before anything else
import '../styles/globals.css'
import type { AppProps } from 'next/app'
import { useEffect } from 'react'
import Navbar from '../components/Navbar'
import SwapBar from '../components/SwapBar'

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    console.log(
      '🔍 NEXT_PUBLIC_API_URL =',
      process.env.NEXT_PUBLIC_API_URL
    )
  }, [])

  return (
    <>
      {/* global navbar */}
      <Navbar />

      {/* sticky swap controls */}
      <div className="sticky top-16 z-20 bg-gray-50">
        <SwapBar />
      </div>

      {/* the actual page */}
      <Component {...pageProps} />
    </>
  )
}

