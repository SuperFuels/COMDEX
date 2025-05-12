// utils/pdf.ts
import { jsPDF } from 'jspdf';

interface DealData {
  id: string;
  productTitle: string;
  buyerEmail: string;
  sellerEmail: string;
  quantityKg: number;
  pricePerKg: number;
  totalAmount: number;
  createdAt: string;
}

export const generateDealPDF = (deal: DealData) => {
  const doc = new jsPDF();

  doc.setFontSize(16);
  doc.text('Deal Summary', 20, 20);

  doc.setFontSize(12);
  doc.text(`Deal ID: ${deal.id}`, 20, 35);
  doc.text(`Product: ${deal.productTitle}`, 20, 45);
  doc.text(`Buyer: ${deal.buyerEmail}`, 20, 55);
  doc.text(`Seller: ${deal.sellerEmail}`, 20, 65);
  doc.text(`Quantity (kg): ${deal.quantityKg}`, 20, 75);
  doc.text(`Price per kg: $${deal.pricePerKg}`, 20, 85);
  doc.text(`Total Amount: $${deal.totalAmount}`, 20, 95);
  doc.text(`Created At: ${new Date(deal.createdAt).toLocaleString()}`, 20, 105);

  doc.save(`deal-${deal.id}.pdf`);
};

