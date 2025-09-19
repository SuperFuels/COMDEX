// frontend/pages/_app.tsx
import type { AppProps } from 'next/app'

// Side-effect imports first:
import '@/lib/api'             // axios baseURL, interceptors, etc. (must be SSR-safe)
import '@/styles/globals.css'  // tailwind + CSS variables

import { useEffect } from 'react'
import Navbar from '@/components/Navbar'

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    // Debug API URL in the browser only
    // eslint-disable-next-line no-console
    console.log('🔍 NEXT_PUBLIC_API_URL =', process.env.NEXT_PUBLIC_API_URL)

    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      localStorage.removeItem('manualDisconnect')
    }
  }, [])

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* If Navbar is sticky or fixed with a known height (e.g. h-14), 
         give main a matching top padding so content isn't hidden. */}
      <Navbar />

      {/* Make page area scrollable and not collapsed by flex parents */}
      <main className="min-h-0 overflow-auto">
        <Component {...pageProps} />
      </main>
    </div>
  )
}