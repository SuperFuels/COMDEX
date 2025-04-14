import React from "react";

interface Product {
  id: number;
  title: string;
  origin_country: string;
  price_per_kg: number;
  category: string;
  description: string;
  image_url: string;
}

const ProductCard: React.FC<{ product: Product }> = ({ product }) => {
  return (
    <div className="border p-4 rounded-lg shadow-md bg-white text-black w-full max-w-md">
      <img src={product.image_url} alt={product.title} className="w-full h-48 object-cover rounded mb-4" />
      <h2 className="text-xl font-bold">{product.title}</h2>
      <p><strong>Category:</strong> {product.category}</p>
      <p><strong>Origin:</strong> {product.origin_country}</p>
      <p><strong>Price:</strong> ${product.price_per_kg} / kg</p>
      <p className="mt-2 text-sm text-gray-600">{product.description}</p>
    </div>
  );
};

export default ProductCard;

