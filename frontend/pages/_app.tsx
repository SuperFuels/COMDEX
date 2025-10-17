'use client';

import '@/lib/api';             // axios instance config
import '@/styles/globals.css';  // Tailwind + globals
import type { AppProps } from 'next/app';
import { Inter } from 'next/font/google';
import { useEffect } from 'react';
import Navbar from '@/components/Navbar';
import ResonancePulseWidget from '@/components/GHX/ResonancePulseWidget'; // ✅ updated import (note capital GHX)

// Inter font setup (swap display for better CLS)
const inter = Inter({ subsets: ['latin'], display: 'swap' });

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    console.log('🔍 NEXT_PUBLIC_API_URL =', process.env.NEXT_PUBLIC_API_URL);

    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      localStorage.removeItem('manualDisconnect');
    }
  }, []);

  return (
    <div className={`${inter.className} flex min-h-screen bg-bg-page text-text-primary`}>
      <div className="flex-1 flex flex-col">
        {/* Global Navbar */}
        <Navbar />

        {/* Page Content */}
        <main className="flex-1 overflow-auto relative">
          <Component {...pageProps} />

          {/* Optional — global live resonance overlay (can be removed later) */}
          <div className="absolute bottom-8 right-8 w-72 h-72 z-50">
            <ResonancePulseWidget />
          </div>
        </main>
      </div>
    </div>
  );
}