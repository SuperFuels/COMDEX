import { useState } from 'react';
import axios from 'axios';
import Sidebar from '@/components/Sidebar';
import { useRouter } from 'next/router';

export default function NewDealForm() {
  const router = useRouter();

  const [buyer_email, setBuyerEmail] = useState('');
  const [supplier_email, setSupplierEmail] = useState('');
  const [product_title, setProductTitle] = useState('');
  const [quantity_kg, setQuantityKg] = useState(0);
  const [total_price, setTotalPrice] = useState(0);
  const [status, setStatus] = useState('negotiation');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem('token');

    try {
      const response = await axios.post(
        'http://localhost:8000/deals/create',
        {
          buyer_email,
          supplier_email,
          product_title,
          quantity_kg,
          total_price,
          status,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      setSuccess(`✅ Deal created! ID: ${response.data.id}`);
      setError('');

      // Optional: Redirect after short delay
      setTimeout(() => {
        router.push('/deals');
      }, 1500);
    } catch (err: any) {
      setError('❌ Failed to create deal.');
      setSuccess('');
      console.error(err);
    }
  };

  return (
    <div className="flex">
      <Sidebar />
      <main className="w-full p-6 bg-gray-50 min-h-screen">
        <h1 className="text-2xl font-bold mb-4">Create New Deal</h1>

        {error && <p className="text-red-500 mb-4">{error}</p>}
        {success && <p className="text-green-600 mb-4">{success}</p>}

        <form onSubmit={handleSubmit} className="space-y-4 bg-white p-6 rounded shadow-md">
          <input
            type="email"
            placeholder="Buyer Email"
            value={buyer_email}
            onChange={(e) => setBuyerEmail(e.target.value)}
            className="w-full border p-2 rounded"
            required
          />
          <input
            type="email"
            placeholder="Supplier Email"
            value={supplier_email}
            onChange={(e) => setSupplierEmail(e.target.value)}
            className="w-full border p-2 rounded"
            required
          />
          <input
            type="text"
            placeholder="Product Title"
            value={product_title}
            onChange={(e) => setProductTitle(e.target.value)}
            className="w-full border p-2 rounded"
            required
          />
          <input
            type="number"
            placeholder="Quantity (kg)"
            value={quantity_kg}
            onChange={(e) => setQuantityKg(Number(e.target.value))}
            className="w-full border p-2 rounded"
            required
          />
          <input
            type="number"
            placeholder="Total Price"
            value={total_price}
            onChange={(e) => setTotalPrice(Number(e.target.value))}
            className="w-full border p-2 rounded"
            required
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full border p-2 rounded"
          >
            <option value="negotiation">Negotiation</option>
            <option value="confirmed">Confirmed</option>
            <option value="completed">Completed</option>
          </select>

          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Create Deal
          </button>
        </form>
      </main>
    </div>
  );
}

