import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Navbar from '@/components/Navbar';

export default function CreateProductPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    title: '',
    origin_country: '',
    category: '',
    description: '',
    price_per_kg: '',
    image: null as File | null,
  });
  const [error, setError] = useState('');
  const [token, setToken] = useState('');

  // 🔒 Redirect non-suppliers
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (!storedToken) {
      router.push('/login');
      return;
    }
    setToken(storedToken);

    axios
      .get('http://localhost:8000/auth/role', {
        headers: { Authorization: `Bearer ${storedToken}` },
      })
      .then((res) => {
        if (res.data.role !== 'supplier') {
          router.push('/');
        }
      })
      .catch(() => {
        router.push('/');
      });
  }, [router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, files } = e.target;
    if (name === 'image' && files) {
      setFormData({ ...formData, image: files[0] });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const data = new FormData();
    data.append('title', formData.title);
    data.append('origin_country', formData.origin_country);
    data.append('category', formData.category);
    data.append('description', formData.description);
    data.append('price_per_kg', formData.price_per_kg);
    if (formData.image) data.append('image', formData.image);

    try {
      await axios.post('http://localhost:8000/products/create', data, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || '❌ Upload failed.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-4">Upload New Product</h1>
        {error && <p className="text-red-600 mb-2">{error}</p>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            name="title"
            placeholder="Title"
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            required
          />
          <input
            name="origin_country"
            placeholder="Country of Origin"
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            required
          />
          <input
            name="category"
            placeholder="Category (e.g. whey)"
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            required
          />
          <input
            name="description"
            placeholder="Description"
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            required
          />
          <input
            name="price_per_kg"
            type="number"
            step="0.01"
            placeholder="Price per KG"
            onChange={handleChange}
            className="w-full border border-gray-300 p-2 rounded"
            required
          />
          <input
            name="image"
            type="file"
            accept="image/*"
            onChange={handleChange}
            className="w-full"
            required
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Upload
          </button>
        </form>
      </main>
    </div>
  );
}

