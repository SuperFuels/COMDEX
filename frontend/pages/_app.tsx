// frontend/pages/_app.tsx
import type { AppProps } from 'next/app'
import { Inter } from 'next/font/google'

// Side-effect imports (must be before any component code)
import '@/lib/api'            // axios baseURL & interceptors (SSR-safe)
import '@/styles/globals.css' // tailwind + CSS variables

import { useEffect } from 'react'
import Navbar from '@/components/Navbar'

// Load Inter and attach its class to the app root
const inter = Inter({ subsets: ['latin'], display: 'swap' })

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
    <div className={`${inter.className} min-h-screen bg-background text-foreground`}>
      {/* Sticky navbar at the top */}
      <Navbar />

      {/* Page content */}
      <main className="min-h-0 overflow-auto">
        <Component {...pageProps} />
      </main>
    </div>
  )
}