'use client';

import '@/lib/api';
import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import { Inter } from 'next/font/google';
import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';

import Navbar from '@/components/Navbar'; // keep legacy site navbar
import HUDOverlay from '@/components/HUD/HUDOverlay';

const inter = Inter({ subsets: ['latin'], display: 'swap' });

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();

  // Hide legacy navbar on GlyphNet (GlyphNet mounts its own navbar)
  const hideNavbar =
    router.asPath.startsWith('/glyphnet') ||
    router.pathname.startsWith('/glyphnet');

  // Navbar now requires onOpenSidebar (safe no-op unless you wire a sidebar)
  const onOpenSidebar = useCallback(() => {
    // no-op for now
    // (later you can set a sidebar state here)
  }, []);

  useEffect(() => {
    console.log('🔍 NEXT_PUBLIC_API_URL =', process.env.NEXT_PUBLIC_API_URL);
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      localStorage.removeItem('manualDisconnect');
    }
  }, []);

  return (
    <div className={`${inter.className} flex min-h-screen bg-bg-page text-text-primary`}>
      <HUDOverlay />

      <div className="flex-1 flex flex-col">
        {!hideNavbar && <Navbar onOpenSidebar={onOpenSidebar} />}

        <main className="flex-1 overflow-auto relative">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  );
}