// pages/_app.tsx
import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import Navbar from '@/components/Navbar';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-100 text-gray-900">
      {/* Global Navbar */}
      <Navbar />

      {/* Page Content */}
      <main className="flex-grow p-6">
        <Component {...pageProps} />
      </main>
    </div>
  );
}

