import { useEffect, useState } from 'react';
import axios from 'axios';
import useAuthRedirect from '@/hooks/useAuthRedirect'; // ✅ Route guard

interface Product {
  id: number;
  title: string;
  category: string;
  origin_country: string;
  price_per_kg: number;
  image_url: string;
}

export default function SupplierDashboard() {
  useAuthRedirect('supplier'); // 🔒 Only suppliers allowed

  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    axios
      .get('http://localhost:8000/products/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => setProducts(res.data))
      .catch((err) => console.error('❌ Failed to fetch products', err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900">
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">📦 My Products</h1>
          <a
            href="/products/new"
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition"
          >
            + Sell Product
          </a>
        </div>

        {products.length === 0 ? (
          <p className="text-gray-500">No products listed yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {products.map((product) => (
              <div
                key={product.id}
                className="bg-white p-4 rounded shadow border border-gray-200"
              >
                <img
                  src={`http://localhost:8000/${product.image_url}`}
                  alt={product.title}
                  className="h-40 w-full object-cover rounded mb-2"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = '/placeholder.jpg';
                  }}
                />
                <h2 className="text-lg font-semibold">{product.title}</h2>
                <p className="text-sm text-gray-600">{product.origin_country}</p>
                <p className="text-sm text-gray-500">{product.category}</p>
                <p className="font-bold mt-1">${product.price_per_kg}/kg</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

