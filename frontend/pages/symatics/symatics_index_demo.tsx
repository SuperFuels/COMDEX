// frontend/pages/symatics/index.tsx
'use client'

import dynamic from 'next/dynamic'
import Head from 'next/head'

// Dynamically import your dashboard so it renders only in the browser
const SymaticsDashboard = dynamic(() => import('@/symatics_dashboard/App'), { ssr: false })

export default function SymaticsPage() {
  return (
    <>
      <Head>
        <title>Tessaris Symatics Dashboard</title>
        <meta
          name="description"
          content="Real-time symbolic resonance visualizer for Tessaris AION/QQC."
        />
      </Head>

      <main className="flex flex-col items-center justify-center min-h-screen bg-black text-white">
        <SymaticsDashboard />
      </main>
    </>
  )
}