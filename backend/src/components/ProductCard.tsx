type Product = {
  title: string
  origin_country: string
  category: string
  description: string
  image_url: string
  price_per_kg: number
}

export default function ProductCard({ product }: { product: Product }) {
  return (
    <div className="border border-gray-600 bg-gray-900 text-white p-4 rounded-xl shadow-md hover:shadow-lg transition w-full max-w-sm">
      <img
        src={product.image_url}
        alt={product.title}
        className="w-full h-48 object-cover rounded-md mb-4"
      />
      <h2 className="text-xl font-bold mb-1">{product.title}</h2>
      <p className="text-sm text-gray-400 mb-1">🌍 Origin: {product.origin_country}</p>
      <p className="text-sm text-gray-400 mb-1">📦 Category: {product.category}</p>
      <p className="text-sm text-gray-300 mb-3">📝 {product.description}</p>
      <p className="text-lg font-semibold">💲{product.price_per_kg.toFixed(2)} / kg</p>
    </div>
  )
}

