"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createDeal } from "@/lib/api";

export default function CreateDealPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    buyer_email: "",
    supplier_email: "",
    product_title: "",
    quantity_kg: "",
    total_price: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createDeal({
        ...formData,
        quantity_kg: parseFloat(formData.quantity_kg),
        total_price: parseFloat(formData.total_price),
      });
      alert("Deal created successfully!");
      router.push("/");
    } catch (err: any) {
      console.error("Deal creation failed:", err);
      alert("Error creating deal.");
    }
  };

  return (
    <main className="min-h-screen bg-black text-white p-6">
      <h1 className="text-2xl font-bold mb-4">📄 Create New Deal</h1>
      <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
        <input
          type="email"
          name="buyer_email"
          placeholder="Buyer Email"
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <input
          type="email"
          name="supplier_email"
          placeholder="Supplier Email"
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <input
          type="text"
          name="product_title"
          placeholder="Product Title"
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <input
          type="number"
          name="quantity_kg"
          placeholder="Quantity (kg)"
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <input
          type="number"
          name="total_price"
          placeholder="Total Price"
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          💾 Save Deal
        </button>
      </form>
    </main>
  );
}

