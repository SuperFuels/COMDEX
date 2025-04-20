import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';
import useAuthRedirect from '../hooks/useAuthRedirect';

interface Product {
  id: number;
  title: string;
  description: string;
  price_per_kg: number;
  origin_country: string;
  image_url: string;
}

const Dashboard = () => {
  useAuthRedirect(); // ✅ Redirect if not logged in
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      console.warn('⚠️ No token found in localStorage');
      setAuthError(true);
      setLoading(false);
      return;
    }

    const fetchProducts = async () => {
      try {
        const response = await axios.get('http://localhost:8000/products/me', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        setProducts(response.data);
      } catch (error) {
        console.error('❌ Failed to fetch products:', error);
        setAuthError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  const handleEdit = (id: number) => {
    router.push(`/products/edit/${id}`);
  };

  const handleDelete = async (id: number) => {
    const token = localStorage.getItem('token');
    const confirmDelete = window.confirm('Are you sure you want to delete this product?');
    if (!confirmDelete) return;

    try {
      await axios.delete(`http://localhost:8000/products/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setProducts(products.filter((p) => p.id !== id));
    } catch (error) {
      console.error('❌ Delete failed:', error);
      alert('Failed to delete product');
    }
  };

  if (loading) {
    return (
      <main className="p-6 w-full bg-gray-50 min-h-screen">
        <p>Loading your products...</p>
      </main>
    );
  }

  if (authError) {
    return (
      <main className="p-6 w-full bg-gray-50 min-h-screen text-center">
        <p className="text-red-500 font-semibold">
          ⚠️ Unauthorized. Please{' '}
          <a className="underline text-blue-600" href="/login">login</a>.
        </p>
      </main>
    );
  }

  return (
    <main className="p-6 w-full bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-4">My Product Listings</h1>
      {products.length === 0 ? (
        <p>No products found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {products.map((product) => (
            <div key={product.id} className="bg-white p-4 rounded shadow">
              <img
                src={`http://localhost:8000/uploaded_images/${product.image_url.split('/').pop()}`}
                alt={product.title}
                className="h-40 w-full object-cover rounded mb-2"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/placeholder.jpg';
                }}
              />
              <h2 className="text-xl font-semibold">{product.title}</h2>
              <p className="text-sm text-gray-700 mb-1">{product.description}</p>
              <p className="text-sm text-gray-500 mb-1">{product.origin_country}</p>
              <p className="text-lg font-bold">${product.price_per_kg}/kg</p>
              <div className="flex justify-between mt-4">
                <button
                  onClick={() => handleEdit(product.id)}
                  className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(product.id)}
                  className="text-sm bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
};

export default Dashboard;

