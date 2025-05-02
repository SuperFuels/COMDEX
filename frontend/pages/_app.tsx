// frontend/pages/_app.tsx

import '../styles/globals.css'
import type { AppProps } from 'next/app'
import Navbar from '@/components/Navbar'
import SwapPanel from '@/components/Swap'

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <>
      <Navbar />
      {/* only one SwapPanel here, sticks under Navbar on every page */}
      <SwapPanel />
      <Component {...pageProps} />
    </>
  )
}

export default MyApp

