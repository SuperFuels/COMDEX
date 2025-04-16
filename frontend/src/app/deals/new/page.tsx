"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { createDeal } from "@/lib/api";
import withAuth from "@/lib/withAuth";

function CreateDealPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const product_id = searchParams.get("product_id");
  const seller_id = searchParams.get("seller_id");

  const [formData, setFormData] = useState({
    product_id: product_id || "",
    seller_id: seller_id || "",
    quantity_kg: "",
    agreed_price: "",
    currency: "USD",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createDeal({
        product_id: parseInt(formData.product_id),
        seller_id: parseInt(formData.seller_id),
        quantity_kg: parseFloat(formData.quantity_kg),
        agreed_price: parseFloat(formData.agreed_price),
        currency: formData.currency,
      });
      alert("✅ Deal created successfully!");
      router.push("/dashboard");
    } catch (err: any) {
      console.error("❌ Deal creation failed:", err);
      alert("Error creating deal.");
    }
  };

  return (
    <main className="min-h-screen bg-black text-white p-6">
      <h1 className="text-2xl font-bold mb-4">🤝 Create New Deal</h1>
      <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
        <input
          type="number"
          name="quantity_kg"
          placeholder="Quantity (kg)"
          value={formData.quantity_kg}
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <input
          type="number"
          name="agreed_price"
          placeholder="Total Agreed Price"
          value={formData.agreed_price}
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <input
          type="text"
          name="currency"
          placeholder="Currency (e.g. USD)"
          value={formData.currency}
          onChange={handleChange}
          required
          className="w-full p-2 rounded text-black"
        />
        <button
          type="submit"
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
        >
          💾 Submit Deal
        </button>
      </form>
    </main>
  );
}

export default withAuth(CreateDealPage);

