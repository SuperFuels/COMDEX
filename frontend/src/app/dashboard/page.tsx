"use client";

import { useEffect, useState } from "react";
import { getUserProducts, deleteProduct } from "@/lib/api";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Header from "@/components/Header";

function DashboardPage() {
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

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <>
      <Header />
      <main className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">📦 Your Dashboard</h1>
          <div className="flex gap-3">
            <Link
              href="/create"
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              ➕ Create Product
            </Link>
            <Link
              href="/deals/new"
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
            >
              🤝 Create Deal
            </Link>
            <button
              onClick={handleLogout}
              className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded"
            >
              🚪 Logout
            </button>
          </div>
        </div>

        {products.length === 0 ? (
          <div className="text-center text-gray-400 mt-20">
            <p className="mb-4">You haven’t listed any products yet.</p>
            <Link
              href="/create"
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              ➕ Create your first product
            </Link>
          </div>
        ) : (
          <>
            <p className="text-gray-500 mb-4">
              Showing {products.length} product{products.length !== 1 ? "s" : ""}
            </p>
            <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 md:grid-cols-3">
              {products.map((product: any) => (
                <div
                  key={product.id}
                  className="bg-white text-black p-4 rounded shadow"
                >
                  <h2 className="text-xl font-semibold mb-1">{product.title}</h2>
                  <p>Category: {product.category || "N/A"}</p>
                  <p>Origin: {product.origin_country}</p>
                  <p>Price: ${product.price_per_kg} / kg</p>
                  <div className="flex gap-2 mt-4">
                    <Link
                      href={`/edit/${product.id}`}
                      className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1 rounded"
                    >
                      ✏️ Edit
                    </Link>
                    <button
                      onClick={() => handleDelete(product.id)}
                      className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded"
                    >
                      🗑️ Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}

export default DashboardPage;

