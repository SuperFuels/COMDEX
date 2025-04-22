import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import useAuthRedirect from '@/hooks/useAuthRedirect';
import Navbar from '@/components/Navbar';

interface Product {
  id: number;
  title: string;
  origin_country: string;
  price_per_kg: number;
  category: string;
  image_url: string;
  description: string;
}

export default function BuyerDashboard() {
  useAuthRedirect('buyer'); // 🔐 Only buyers

  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await axios.get('http://localhost:8000/products');
        setProducts(response.data);
      } catch (err) {
        console.error('❌ Failed to fetch products', err);
        setError('Unable to load products');
      }
    };

    fetchProducts();
  }, []);

  const handleContact = (id: number) => {
    router.push(`/deals/create/${id}`);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="p-6 max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Available Products</h1>
        {error && <p className="text-red-500">{error}</p>}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {products.map((product) => (
            <div key={product.id} className="bg-white shadow rounded p-4">
              <img
                src={`http://localhost:8000${product.image_url}`}
                alt={product.title}
                className="w-full h-40 object-cover rounded mb-2"
                onError={(e) =>
                  ((e.target as HTMLImageElement).src = '/placeholder.jpg')
                }
              />
              <h2 className="text-lg font-semibold">{product.title}</h2>
              <p className="text-sm text-gray-700">{product.description}</p>
              <p className="text-sm text-gray-500">{product.origin_country}</p>
              <p className="text-lg font-bold">${product.price_per_kg}/kg</p>
              <button
                onClick={() => handleContact(product.id)}
                className="mt-3 w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Contact Supplier
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

