import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import axios from 'axios';
import useAuthRedirect from '@/hooks/useAuthRedirect';

export default function EditProductPage() {
  useAuthRedirect('supplier'); // ✅ Only allow suppliers

  const router = useRouter();
  const { id } = router.query;
  const [product, setProduct] = useState<any>(null);
  const [formData, setFormData] = useState({
    title: '',
    origin_country: '',
    category: '',
    description: '',
    price_per_kg: '',
  });
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token || !id) return;

    axios
      .get(`http://localhost:8000/products/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => {
        setProduct(res.data);
        setFormData({
          title: res.data.title,
          origin_country: res.data.origin_country,
          category: res.data.category,
          description: res.data.description,
          price_per_kg: res.data.price_per_kg.toString(),
        });
      })
      .catch(() => {
        setError('⚠️ Could not fetch product or unauthorized.');
      });
  }, [id]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    try {
      await axios.put(`http://localhost:8000/products/${id}`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || '❌ Update failed');
    }
  };

  if (!product && !error) return <p className="p-6">Loading...</p>;

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Edit Product</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          name="title"
          value={formData.title}
          onChange={handleChange}
          placeholder="Title"
          className="w-full p-2 border rounded"
          required
        />
        <input
          name="origin_country"
          value={formData.origin_country}
          onChange={handleChange}
          placeholder="Country of Origin"
          className="w-full p-2 border rounded"
          required
        />
        <input
          name="category"
          value={formData.category}
          onChange={handleChange}
          placeholder="Category"
          className="w-full p-2 border rounded"
          required
        />
        <input
          name="description"
          value={formData.description}
          onChange={handleChange}
          placeholder="Description"
          className="w-full p-2 border rounded"
          required
        />
        <input
          name="price_per_kg"
          value={formData.price_per_kg}
          onChange={handleChange}
          placeholder="Price per KG"
          type="number"
          step="0.01"
          className="w-full p-2 border rounded"
          required
        />
        <button
          type="submit"
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        >
          Update Product
        </button>
      </form>
    </div>
  );
}

