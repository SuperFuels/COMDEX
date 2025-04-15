"use client";

import { useEffect, useState } from "react";
import { getUserProducts, deleteProduct } from "@/lib/api";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function DashboardPage() {
  const [products, setProducts] = useState([]);
  const router = useRouter();

  useEffect(() => {
    async function fetchProducts() {
      try {
        const res = await getUserProducts();
        setProducts(res);
      } catch (err) {
        console.error(err);
        alert("Please log in to view your dashboard.");
        router.push("/login");
      }
    }
    fetchProducts();
  }, []);

  const handleDelete = async (id: number) => {
    const confirm = window.confirm("Are you sure you want to delete this product?");
    if (!confirm) return;

    try {
      await deleteProduct(id);
      setProducts((prev) => prev.filter((p: any) => p.id !== id));
    } catch (err) {
      console.error(err);
      alert("Error deleting product.");
    }
  };

  return (
    <main className="p-6">
      <h1 className="text-3xl font-bold mb-6">📦 Your Listings</h1>

      {products.length === 0 ? (
        <p>You haven’t listed any products yet.</p>
      ) : (
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 md:grid-cols-3">
          {products.map((product: any) => (
            <div key={product.id} className="bg-white text-black p-4 rounded shadow-lg">
              <h2 className="text-xl font-semibold">{product.title}</h2>
              <p>Category: {product.category}</p>
              <p>Origin: {product.origin_country}</p>
              <p>Price: ${product.price_per_kg} / kg</p>
              <div className="flex gap-2 mt-4">
                <Link
                  href={`/edit/${product.id}`}
                  className="bg-blue-600 text-white px-3 py-1 rounded"
                >
                  ✏️ Edit
                </Link>
                <button
                  onClick={() => handleDelete(product.id)}
                  className="bg-red-600 text-white px-3 py-1 rounded"
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

