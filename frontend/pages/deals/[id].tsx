// pages/deals/[id].tsx
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import { jsPDF } from 'jspdf';
import axios from 'axios';
import Sidebar from '@/components/Sidebar';

interface Deal {
  id: number;
  product_title: string;
  buyer_email: string;
  supplier_email: string;
  quantity_kg: number;
  total_price: number;
  created_at: string;
}

export default function DealPage() {
  const router = useRouter();
  const { id } = router.query;
  const [deal, setDeal] = useState<Deal | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (id) {
      axios
        .get(`http://localhost:8000/deals/${id}`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        })
        .then((res) => setDeal(res.data))
        .catch((err) => {
          console.error('❌ Failed to fetch deal:', err);
          setError('Failed to load deal');
        });
    }
  }, [id]);

  const exportPDF = () => {
    if (!deal) return;
    const doc = new jsPDF();
    doc.text('🧾 Deal Summary', 20, 20);
    doc.text(`Product: ${deal.product_title}`, 20, 40);
    doc.text(`Buyer: ${deal.buyer_email}`, 20, 50);
    doc.text(`Supplier: ${deal.supplier_email}`, 20, 60);
    doc.text(`Quantity (kg): ${deal.quantity_kg}`, 20, 70);
    doc.text(`Total Price: $${deal.total_price}`, 20, 80);
    doc.text(`Created: ${new Date(deal.created_at).toLocaleString()}`, 20, 90);
    doc.save(`deal_${deal.id}.pdf`);
  };

  return (
    <div className="flex">
      <Sidebar />
      <main className="w-full p-6 bg-gray-50 min-h-screen">
        <h1 className="text-2xl font-bold mb-6">Deal Details</h1>

        {error && <p className="text-red-500 mb-4">{error}</p>}

        {!deal ? (
          <p>Loading...</p>
        ) : (
          <div className="bg-white shadow p-6 rounded space-y-2">
            <p><strong>Product:</strong> {deal.product_title}</p>
            <p><strong>Buyer:</strong> {deal.buyer_email}</p>
            <p><strong>Supplier:</strong> {deal.supplier_email}</p>
            <p><strong>Quantity (kg):</strong> {deal.quantity_kg}</p>
            <p><strong>Total Price:</strong> ${deal.total_price}</p>
            <p><strong>Created:</strong> {new Date(deal.created_at).toLocaleString()}</p>
            <button
              onClick={exportPDF}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Export PDF
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

