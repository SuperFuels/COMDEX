// pages/deals/[id].tsx
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import { jsPDF } from 'jspdf';
import axios from 'axios';

interface Deal {
  id: string;
  productTitle: string;
  buyerEmail: string;
  sellerEmail: string;
  quantityKg: number;
  pricePerKg: number;
  totalAmount: number;
  createdAt: string;
}

export default function DealPage() {
  const router = useRouter();
  const { id } = router.query;
  const [deal, setDeal] = useState<Deal | null>(null);

  useEffect(() => {
    if (id) {
      axios.get(`http://localhost:8000/deals/${id}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      .then((res) => setDeal(res.data))
      .catch((err) => console.error('Failed to fetch deal', err));
    }
  }, [id]);

  const exportPDF = () => {
    if (!deal) return;
    const doc = new jsPDF();
    doc.text('Deal Summary', 20, 20);
    doc.text(`Product: ${deal.productTitle}`, 20, 40);
    doc.text(`Buyer: ${deal.buyerEmail}`, 20, 50);
    doc.text(`Seller: ${deal.sellerEmail}`, 20, 60);
    doc.text(`Quantity (kg): ${deal.quantityKg}`, 20, 70);
    doc.text(`Price per kg: $${deal.pricePerKg}`,

