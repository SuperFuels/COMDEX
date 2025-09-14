// frontend/pages/_app.tsx
'use client';

import '@/lib/api';             // ← configure your axios instance first
import '@/styles/globals.css';  // ← Tailwind + your custom globals
import type { AppProps } from 'next/app';
import { useEffect } from 'react';
import Navbar from '@/components/Navbar';

export default function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    // Debug your API URL
    console.log('🔍 NEXT_PUBLIC_API_URL =', process.env.NEXT_PUBLIC_API_URL);

    // If user still has a JWT, clear the manual-disconnect flag
    // so they’ll auto-reconnect their wallet on page reload
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      localStorage.removeItem('manualDisconnect');
    }
  }, []);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar is controlled by Navbar itself, so we do NOT render <Sidebar /> here */}
      <div className="flex-1 flex flex-col">
        {/* ─── Global Navbar (sticky at top) ─────────────────────────── */}
        <Navbar />

        {/* ─── Page Content ─────────────────────────────────────────── */}
        <main className="flex-1 bg-background">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  );
}