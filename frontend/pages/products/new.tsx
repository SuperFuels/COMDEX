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
    image_url: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    try {
      await axios.post('http://localhost:8000/products', form, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      router.push('/dashboard');
    } catch (err) {
      alert('Failed to create product');
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
        />
        <textarea
          name="description"
          placeholder="Description"
          onChange={handleChange}
          className="input"
        />
        <input
          type="number"
          name="price_per_kg"
          placeholder="Price per kg"
          onChange={handleChange}
          className="input"
        />
        <input
          type="text"
          name="origin_country"
          placeholder="Origin Country"
          onChange={handleChange}
          className="input"
        />
        <input
          type="text"
          name="image_url"
          placeholder="Image URL"
          onChange={handleChange}
          className="input"
        />
        <button type="submit" className="btn btn-primary w-full">
          Submit
        </button>
      </form>
    </div>
  );
}

