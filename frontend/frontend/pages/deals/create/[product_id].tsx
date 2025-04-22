import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import useAuthRedirect from '@/hooks/useAuthRedirect';

export default function CreateDealPage() {
  useAuthRedirect('buyer'); // 🔒 Only buyers can access this page

  const router = useRouter();
  const { product_id } = router.query;
  const [quantityKg, setQuantityKg] = useState('');
  const [error, setError] = useState('');
  const [product, setProduct] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token || !product_id) return;

    axios
      .get(`http://localhost:8000/products/${product_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => {
        setProduct(res.data);
      })
      .catch(() => {
        setError('❌ Failed to load product data');
      });
  }, [product_id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      await axios.post(
        `http://localhost:8000/deals/create`,
        {
          product_id: Number(product_id),
          quantity_kg: Number(quantityKg),
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      router.push('/deals'); // Redirect to deals page
    } catch (err: any) {
      setError(err.response?.data?.detail || '❌ Deal creation failed');
    }
  };

  if (!product) return <p className="p-6">Loading...</p>;

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <main className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Create Deal with Supplier</h1>
        {error && <p className="text-red-600">{error}</p>}
        <div className="bg-white shadow p-4 rounded mb-6">
          <p><strong>Product:</strong> {product.title}</p>
          <p><strong>Price per KG:</strong> ${product.price_per_kg}</p>
          <p><strong>Supplier:</strong> {product.owner_email}</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="number"
            step="0.01"
            min="1"
            placeholder="Quantity (KG)"
            value={quantityKg}
            onChange={(e) => setQuantityKg(e.target.value)}
            className="w-full border border-gray-300 p-2 rounded"
            required
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Submit Deal
          </button>
        </form>
      </main>
    </div>
  );
}

