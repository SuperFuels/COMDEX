"use client";

import { useEffect, useState } from "react";
import { getUsers, getProducts, deleteUser, deleteProduct } from "@/lib/api";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import withAuth from "@/lib/withAuth";

function AdminDashboard() {
  const [users, setUsers] = useState([]);
  const [products, setProducts] = useState([]);
  const router = useRouter();

  // Fetch users and products
  useEffect(() => {
    async function fetchAdminData() {
      try {
        const userRes = await getUsers();
        setUsers(userRes);
        const productRes = await getProducts();
        setProducts(productRes);
      } catch (err) {
        console.error("Failed to fetch data", err);
        router.push("/login");
      }
    }
    fetchAdminData();
  }, []);

  const handleDeleteUser = async (userId: number) => {
    const confirm = window.confirm("Are you sure you want to delete this user?");
    if (!confirm) return;

    try {
      await deleteUser(userId);
      setUsers((prev) => prev.filter((user: any) => user.id !== userId));
    } catch (err) {
      console.error("Error deleting user", err);
    }
  };

  const handleDeleteProduct = async (productId: number) => {
    const confirm = window.confirm("Are you sure you want to delete this product?");
    if (!confirm) return;

    try {
      await deleteProduct(productId);
      setProducts((prev) => prev.filter((product: any) => product.id !== productId));
    } catch (err) {
      console.error("Error deleting product", err);
    }
  };

  return (
    <>
      <Header />
      <main className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        </div>

        <h2 className="text-2xl font-semibold mb-4">Users</h2>
        {users.length === 0 ? (
          <p>No users found.</p>
        ) : (
          <div className="space-y-4">
            {users.map((user: any) => (
              <div
                key={user.id}
                className="bg-white text-black p-4 rounded shadow-md"
              >
                <p><strong>Email:</strong> {user.email}</p>
                <button
                  onClick={() => handleDeleteUser(user.id)}
                  className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded"
                >
                  🗑️ Delete User
                </button>
              </div>
            ))}
          </div>
        )}

        <h2 className="text-2xl font-semibold mt-6 mb-4">Products</h2>
        {products.length === 0 ? (
          <p>No products found.</p>
        ) : (
          <div className="space-y-4">
            {products.map((product: any) => (
              <div
                key={product.id}
                className="bg-white text-black p-4 rounded shadow-md"
              >
                <p><strong>Title:</strong> {product.title}</p>
                <p><strong>Price:</strong> ${product.price_per_kg} / kg</p>
                <button
                  onClick={() => handleDeleteProduct(product.id)}
                  className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded"
                >
                  🗑️ Delete Product
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}

export default withAuth(AdminDashboard);

