import dynamic from 'next/dynamic';
import Navbar from '@/components/Navbar';

const EscrowActions = dynamic(() => import('@/components/EscrowActions'), { ssr: false });

export default function EscrowTestPage() {
  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <main className="max-w-2xl mx-auto py-10 px-4 text-center">
        <h1 className="text-3xl font-bold mb-6">Escrow Action Test</h1>
        <EscrowActions />
      </main>
    </div>
  );
}

