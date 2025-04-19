// pages/products/new.tsx
import { useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';

export default function NewProduct() {
  const router = useRouter();
  const [form, setForm] = useState({
    title: '',
    description: '',
    price_per_kg: '',
    origin_country: '',
    category: '',
  });
  const [imageFile, setImageFile] = useState<File | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImageFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    const formData = new FormData();

    Object.entries(form).forEach(([key, value]) => {
      formData.append(key, value);
    });

    if (imageFile) {
      formData.append('image', imageFile);
    }

    try {
      await axios.post('http://localhost:8000/products/create', formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });
      router.push('/dashboard');
    } catch (err) {
      console.error(err);
      alert('❌ Failed to create product');
    }
  };

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Create New Product</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          name="title"
          placeholder="Title"
          onChange={handleChange}
          className="input"
          required
        />
        <textarea
          name="description"
          placeholder="Description"
          onChange={handleChange}
          className="input"
          required
        />
        <input
          type="number"
          name="price_per_kg"
          placeholder="Price per kg"
          onChange={handleChange}
          className="input"
          required
        />
        <input
          type="text"
          name="origin_country"
          placeholder="Origin Country"
          onChange={handleChange}
          className="input"
          required
        />
        <input
          type="text"
          name="category"
          placeholder="Category"
          onChange={handleChange}
          className="input"
          required
        />
        <input
          type="file"
          name="image"
          onChange={handleImageChange}
          className="input"
          accept="image/*"
          required
        />
        <button type="submit" className="btn btn-primary w-full">
          Submit
        </button>
      </form>
    </div>
  );
}

