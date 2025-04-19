// pages/_app.tsx
import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import Navbar from '@/components/Navbar';
import Sidebar from '@/components/Sidebar';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-100 text-gray-900">
      {/* Global Navbar */}
      <Navbar />

      {/* Main Content Area with Sidebar + Page */}
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-grow p-6 overflow-y-auto">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  );
}

