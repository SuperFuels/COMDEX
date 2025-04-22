// pages/deals/create/[product_id].tsx

import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import useAuthRedirect from '@/hooks/useAuthRedirect';

export default function CreateDealPage() {
  useAuthRedirect('buyer'); // 🔒 Only buyers can access

  const router = useRouter();
  const { product_id } = router.query;
  const [quantity, setQuantity] = useState('');
  const [product, setProduct] = useState<any>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token || !product_id) return;

    axios
      .get(`http://localhost:8000/products/${product_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => setProduct(res.data))
      .catch(() => setError('Unable to load product info.'));
  }, [product_id]);

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    if (!token || !quantity) return;

    try {
      await axios.post(
        'http://localhost:8000/deals/create',
        {
          product_id: Number(product_id),
          quantity_kg: Number(quantity),
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      setSuccess(true);
      setTimeout(() => router.push('/dashboard'), 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || '❌ Deal creation failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-4">🤝 Create Deal</h1>
        {product && (
          <div className="mb-4 p-4 border rounded bg-white">
            <h2 className="text-xl font-semibold">{product.title}</h2>
            <p className="text-gray-700">{product.description}</p>
            <p className="text-sm text-gray-500">{product.origin_country}</p>
            <p className="text-lg font-bold">${product.price_per_kg}/kg</p>
          </div>
        )}

        {error && <p className="text-red-600 mb-2">{error}</p>}
        {success && <p className="text-green-600 mb-2">✅ Deal created!</p>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="number"
            name="quantity"
            placeholder="Quantity (kg)"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded"
            required
          />
          <button
            type="submit"
            className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Submit Deal
          </button>
        </form>
      </main>
    </div>
  );
}

