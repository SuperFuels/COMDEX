import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';
import useAuthRedirect from '../hooks/useAuthRedirect'; // ✅ Protect page

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
      } catch (error: any) {
        console.error('❌ Failed to fetch products:', error);
        setAuthError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

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
            <div key={product.id} className="card bg-white p-4 rounded shadow">
              <img
                src={product.image_url}
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
            </div>
          ))}
        </div>
      )}
    </main>
  );
};

export default Dashboard;

