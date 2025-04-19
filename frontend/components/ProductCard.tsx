import React from 'react';

interface ProductProps {
  id: number;
  title: string;
  description: string;
  price_per_kg: number;
  origin_country: string;
  image_url: string;
}

const ProductCard: React.FC<ProductProps> = ({
  id,
  title,
  description,
  price_per_kg,
  origin_country,
  image_url,
}) => {
  return (
    <div className="border rounded shadow p-4">
      <img src={image_url} alt={title} className="h-40 w-full object-cover mb-2" />
      <h2 className="text-xl font-bold">{title}</h2>
      <p className="text-gray-600 text-sm mb-2">{origin_country}</p>
      <p className="text-gray-800">{description}</p>
      <p className="font-bold mt-2">${price_per_kg}/kg</p>
    </div>
  );
};

export default ProductCard;

