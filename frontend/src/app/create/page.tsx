"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import withAuth from "@/lib/withAuth";

function CreateProductPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    title: "",
    origin_country: "",
    price_per_kg: "",
    category: "",
    description: "",
    image_url: "",
  });

  const categories = [
    "Protein Powder",
    "Creatine",
    "BCAAs",
    "Pre-Workout",
    "Vitamins",
    "Healthy Snacks",
  ];

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/products/create", {
        ...form,
        price_per_kg: parseFloat(form.price_per_kg),
      });
      router.push("/dashboard");
    } catch (err) {
      alert("Error creating product.");
      console.error(err);
    }
  };

  return (
    <main className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-white">Create a New Product</h1>
      <form onSubmit={handleSubmit} className="form-card">
        <input
          type="text"
          name="title"
          placeholder="Title"
          value={form.title}
          onChange={handleChange}
          required
          className="input-field"
        />
        <input
          type="text"
          name="origin_country"
          placeholder="Origin Country"
          value={form.origin_country}
          onChange={handleChange}
          required
          className="input-field"
        />
        <select
          name="category"
          value={form.category}
          onChange={handleChange}
          required
          className="input-field"
        >
          <option value="">Select Category</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
        <textarea
          name="description"
          placeholder="Description"
          value={form.description}
          onChange={handleChange}
          required
          className="input-field"
        />
        <div>
          <label className="block mb-1 text-white font-medium">Image URL</label>
          <input
            type="text"
            name="image_url"
            placeholder="https://example.com/image.jpg"
            value={form.image_url}
            onChange={handleChange}
            className="input-field"
          />
          {form.image_url && (
            <img
              src={form.image_url}
              alt="Preview"
              className="mt-2 rounded border w-full max-h-48 object-cover"
            />
          )}
        </div>
        <input
          type="number"
          name="price_per_kg"
          placeholder="Price per kg (e.g. 22.5)"
          value={form.price_per_kg}
          onChange={handleChange}
          required
          className="input-field"
        />
        <button type="submit" className="btn-primary">
          Create Product
        </button>
      </form>
    </main>
  );
}

export default withAuth(CreateProductPage);

