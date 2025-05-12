// pages/_app.tsx
import '../styles/globals.css'
import type { AppProps } from 'next/app'
import Navbar from '../components/Navbar'
import SwapBar from '../components/SwapBar'

export default function MyApp({ Component, pageProps }: AppProps) {
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

