// frontend/pages/_app.tsx
'use client';

import '@/lib/api';             // axios instance config
import '@/styles/globals.css';  // Tailwind + globals
import type { AppProps } from 'next/app';
import { Inter } from 'next/font/google';
import { useEffect } from 'react';
import Navbar from '@/components/Navbar';

// Inter font (swap display for better CLS)
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
        <main className="flex-1 overflow-auto">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  );
}
