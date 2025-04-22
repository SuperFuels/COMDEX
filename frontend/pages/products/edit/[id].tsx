import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Navbar from '@/components/Navbar'; // ✅ Include Navbar

interface ProductForm {
  title: string;
  description: string;
  price_per_kg: string;
  origin_country: string;
  category: string;
}

export default function EditProductPage() {
  const router = useRouter();
  const { id } = router.query;
  const [form, setForm] = useState<ProductForm>({
    title: '',
    description: '',
    price_per_kg: '',
    origin_country: '',
    category: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token || !id) return;

    const fetchProduct = async () => {
      try {
        const res = await axios.get(`http://localhost:8000/products/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setForm(res.data);
      } catch {
        setError('❌ Failed to load product');
      } finally {
        setLoading(false);
      }
    };

    fetchProduct();
  }, [id]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    try {
      await axios.put(`http://localhost:8000/products/${id}`, form, {
        headers: { Authorization: `Bearer ${token}` },
      });
      router.push('/dashboard');
    } catch (err) {
      setError('❌ Failed to update product');
    }
  };

  if (loading) {
    return <div className="p-6">Loading product details...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar /> {/* ✅ Navbar added */}
      <div className="max-w-xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-4">✏️ Edit Product</h1>
        {error && <p className="text-red-500 mb-2">{error}</p>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            name="title"
            value={form.title}
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            placeholder="Title"
            required
          />
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            placeholder="Description"
            rows={4}
            required
          />
          <input
            type="text"
            name="category"
            value={form.category}
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            placeholder="Category"
            required
          />
          <input
            type="text"
            name="origin_country"
            value={form.origin_country}
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            placeholder="Origin Country"
            required
          />
          <input
            type="number"
            name="price_per_kg"
            value={form.price_per_kg}
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            placeholder="Price per kg"
            required
          />
          <button
            type="submit"
            className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 w-full"
          >
            ✅ Update Product
          </button>
        </form>
      </div>
    </div>
  );
}

