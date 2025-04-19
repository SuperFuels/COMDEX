// pages/products/[id].tsx
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import axios from 'axios';

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

  if (!product) return <p>Loading...</p>;

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">{product.title}</h1>
      {product.image_url && (
        <img
          src={product.image_url}
          alt={product.title}
          className="w-64 h-64 object-cover mb-4"
        />
      )}
      <p className="mb-2"><strong>Category:</strong> {product.category}</p>
      <p className="mb-2"><strong>Origin:</strong> {product.origin_country}</p>
      <p className="mb-2"><strong>Description:</strong> {product.description}</p>
      <p className="mb-2"><strong>Price per KG:</strong> ${product.price_per_kg}</p>
    </div>
  );
}

