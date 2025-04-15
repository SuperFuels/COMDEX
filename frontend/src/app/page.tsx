"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getProducts } from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import Link from "next/link";

export default function Home() {
  const [products, setProducts] = useState([]);
  const router = useRouter();

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getProducts();
        setProducts(res);
      } catch (err: any) {
        console.error("Error fetching products:", err);
        if (err.message === "Not authenticated") {
          alert("Please log in to view products.");
          router.push("/login");
        }
      }
    }

    fetchData();
  }, []);

  return (
    <main className="min-h-screen bg-black text-white p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">
          <span role="img" aria-label="test tube">
            🧪
          </span>{" "}
          COMDEX – Commodity Listings
        </h1>
        <div className="flex gap-4">
          <Link
            href="/create"
            className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
          >
            ➕ Create New Product
          </Link>
          <Link
            href="/deals/new"
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            📄 Create New Deal
          </Link>
          <Link
            href="/login"
            className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
          >
            🚪 Logout
          </Link>
        </div>
      </div>

      {products.length === 0 ? (
        <p className="text-gray-400">No products found.</p>
      ) : (
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 md:grid-cols-3">
          {products.map((product: any) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </main>
  );
}

