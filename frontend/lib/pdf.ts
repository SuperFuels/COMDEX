// utils/pdf.ts
import jsPDF from 'jspdf';

export const generateDealPDF = (deal: any) => {
  const doc = new jsPDF();

  doc.setFontSize(18);
  doc.text('COMDEX Deal Summary', 20, 20);

  doc.setFontSize(12);
  doc.text(`Deal ID: ${deal.id}`, 20, 40);
  doc.text(`Buyer: ${deal.buyer_name}`, 20, 50);
  doc.text(`Seller: ${deal.seller_name}`, 20, 60);
  doc.text(`Product: ${deal.product_title}`, 20, 70);
  doc.text(`Quantity: ${deal.quantity} kg`, 20, 80);
  doc.text(`Total Price: $${deal.total_price}`, 20, 90);
  doc.text(`Date: ${new Date(deal.created_at).toLocaleDateString()}`, 20, 100);

  doc.save(`COMDEX_Deal_${deal.id}.pdf`);
};

