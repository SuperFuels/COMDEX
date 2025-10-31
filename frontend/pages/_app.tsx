'use client';

import '@/lib/api';                     // axios instance config
import '@/styles/globals.css';          // Tailwind + globals
import type { AppProps } from 'next/app';
import { Inter } from 'next/font/google';
import { useEffect } from 'react';

import Navbar from '@/components/Navbar';
import ResonancePulseWidget from '@/components/GHX/ResonancePulseWidget';
import HUDOverlay from "@/components/HUD/HUDOverlay";   // ✅ Added

// Inter font setup
const inter = Inter({ subsets: ['latin'], display: 'swap' });

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    console.log('🔍 NEXT_PUBLIC_API_URL =', process.env.NEXT_PUBLIC_API_URL);

    // ✅ clear “manualDisconnect” only if wallet token exists
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      localStorage.removeItem('manualDisconnect');
    }
  }, []);

  return (
    <div className={`${inter.className} flex min-h-screen bg-bg-page text-text-primary`}>
      {/* ✅ HUD overlay lives at root – pulses, system events */}
      <HUDOverlay />

      <div className="flex-1 flex flex-col">
        {/* ✅ Global Navbar */}
        <Navbar />

        <main className="flex-1 overflow-auto relative">
          <Component {...pageProps} />

          {/* ✅ Global live resonance scope */}
          <div className="absolute bottom-8 right-8 w-72 h-72 z-50">
            <ResonancePulseWidget />
          </div>
        </main>
      </div>
    </div>
  );
}