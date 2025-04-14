import React from "react";

interface ProductCardProps {
  product: {
    id: number;
    title: string;
    origin_country: string;
    price_per_kg: number;
    category: string;
    description: string;
    image_url: string;
  };
}

const ProductCard: React.FC<{ product: ProductCardProps["product"] }> = ({ product }) => {
  return (
    <div className="border rounded-2xl p-4 shadow-md bg-zinc-900 text-white w-full max-w-md mx-auto">
      <img
        src={product.image_url}
        alt={product.title}
        className="w-full h-48 object-cover rounded-xl mb-4"
      />
      <h2 className="text-xl font-bold">{product.title}</h2>
      <p><strong>Origin:</strong> {product.origin_country}</p>
      <p><strong>Price:</strong> ${product.price_per_kg.toFixed(2)} / kg</p>
      <p><strong>Category:</strong> {product.category}</p>
      <p className="text-sm text-gray-400 mt-2">{product.description}</p>
    </div>
  );
};

export default ProductCard;

