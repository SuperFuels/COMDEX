import { useEffect, useState } from 'react';
import axios from 'axios';

interface Product {
  id: number;
  title: string;
  description: string;
  price_per_kg: number;
  origin_country: string;
  image_url: string;
  category: string;
}

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    axios.get('http://localhost:8000/products')
      .then((res) => setProducts(res.data))
      .catch((err) => console.error('❌ Failed to load products', err));
  }, []);

  const filteredProducts = products.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase()) ||
    p.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white text-gray-900 min-h-screen">

      {/* Swap UI */}
      <div className="flex flex-col items-center justify-center pt-12 px-4">
        <h1 className="text-3xl font-bold mb-4 text-center">Swap COMDEX Assets</h1>
        <div className="bg-gray-100 border border-gray-300 rounded-lg p-4 w-full max-w-sm shadow">
          <input
            type="text"
            placeholder="0"
            disabled
            className="w-full mb-2 p-2 rounded bg-white border border-gray-300 text-center"
          />
          <input
            type="text"
            placeholder="0"
            disabled
            className="w-full mb-2 p-2 rounded bg-white border border-gray-300 text-center"
          />
          <button
            className="w-full py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            disabled
          >
            Coming Soon
          </button>
        </div>
      </div>

      {/* Marketplace */}
      <div className="px-6 py-12 max-w-6xl mx-auto">
        <div className="mb-6 text-center">
          <h2 className="text-2xl font-bold mb-2">Explore the Marketplace</h2>
          <input
            type="text"
            placeholder="Search by title or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md mx-auto p-2 border border-gray-300 rounded"
          />
        </div>

        {filteredProducts.length === 0 ? (
          <p className="text-center text-gray-500">No products found.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {filteredProducts.map((product) => (
              <div
                key={product.id}
                className="bg-white border border-gray-200 p-4 rounded shadow h-full"
              >
                <img
                  src={
                    product.image_url.startsWith('http')
                      ? product.image_url
                      : `http://localhost:8000/${product.image_url}`
                  }
                  alt={product.title}
                  className="h-48 w-full object-cover rounded mb-2"
                  onError={(e) => {
                    e.currentTarget.src = '/placeholder.jpg';
                  }}
                />
                <h3 className="font-semibold text-lg">{product.title}</h3>
                <p className="text-sm text-gray-700">{product.origin_country}</p>
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

