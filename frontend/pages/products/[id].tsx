import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from '@/components/Navbar';

interface Product {
  id: number;
  title: string;
  origin_country: string;
  category: string;
  description: string;
  price_per_kg: number;
  image_url?: string;
}

export default function ProductDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [product, setProduct] = useState<Product | null>(null);

  useEffect(() => {
    if (id) {
      axios
        .get(`http://localhost:8000/products/${id}`)
        .then((res) => setProduct(res.data))
        .catch(() => alert('Failed to fetch product'));
    }
  }, [id]);

  if (!product) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <p>Loading product...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <Navbar />

      <div className="max-w-4xl mx-auto p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <img
            src={`http://localhost:8000${product.image_url}`}
            alt={product.title}
            className="w-full h-80 object-cover rounded"
            onError={(e) => {
              (e.target as HTMLImageElement).src = '/placeholder.jpg';
            }}
          />

          <div>
            <h1 className="text-3xl font-bold mb-2">{product.title}</h1>
            <p className="text-pink-400 font-semibold text-xl mb-4">
              ${product.price_per_kg}/kg
            </p>
            <p className="text-sm text-gray-400 mb-2">
              Origin: {product.origin_country}
            </p>
            <p className="text-sm text-gray-400 mb-2">Category: {product.category}</p>
            <p className="mb-4">{product.description}</p>

            <button
              disabled
              className="bg-pink-600 text-white py-2 px-4 rounded hover:bg-pink-700 disabled:opacity-50"
            >
              Contact Seller (Login Required)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

