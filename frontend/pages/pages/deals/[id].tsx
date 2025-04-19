// pages/deals/[id].tsx
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { getToken } from '@/utils/auth';
import jsPDF from 'jspdf';

interface Deal {
  id: number;
  buyer_email: string;
  product_title: string;
  price: number;
  quantity_kg: number;
  total_cost: number;
}

export default function DealDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [deal, setDeal] = useState<Deal | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchDeal = async () => {
      const token = getToken();
      try {
        const response = await axios.get(`http://localhost:8000/deals/${id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        setDeal(response.data);
      } catch (error) {
        console.error('Failed to fetch deal', error);
      }
    };

    fetchDeal();
  }, [id]);

  const exportPDF = () => {
    if (!deal) return;
    const doc = new jsPDF();
    doc.text(`Deal Summary`, 10, 10);
    doc.text(`Buyer: ${deal.buyer_email}`, 10, 20);
    doc.text(`Product: ${deal.product_title}`, 10, 30);
    doc.text(`Quantity: ${deal.quantity_kg} kg`, 10, 40);
    doc.text(`Price: $${deal.price}/kg`, 10, 50);
    doc.text(`Total: $${deal.total_cost}`, 10, 60);
    doc.save(`deal_${deal.id}.pdf`);
  };

  if (!deal) return <p>Loading deal...</p>;

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Deal Detail</h1>
      <p><strong>Buyer:</strong> {deal.buyer_email}</p>
      <p><strong>Product:</strong> {deal.product_title}</p>
      <p><strong>Quantity:</strong> {deal.quantity_kg} kg</p>
      <p><strong>Price:</strong> ${deal.price}/kg</p>
      <p><strong>Total Cost:</strong> ${deal.total_cost}</p>
      <button onClick={exportPDF} className="btn btn-primary mt-4">
        Download PDF
      </button>
    </div>
  );
}

