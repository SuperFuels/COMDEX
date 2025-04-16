"use client"

import { useRouter } from "next/navigation"
import Link from "next/link"
import { deleteProduct, downloadDealPdf } from "@/lib/api"

export default function ProductCard({ product }: { product: any }) {
  const router = useRouter()

  const handleDelete = async () => {
    const confirm = window.confirm("Are you sure you want to delete this product?")
    if (!confirm) return

    try {
      await deleteProduct(product.id)
      alert("Product deleted!")
      router.refresh() // Re-fetch data
    } catch (err) {
      console.error("Delete failed", err)
      alert("Failed to delete product.")
    }
  }

  const handleDownloadPdf = async () => {
    const token = localStorage.getItem("token")
    if (!token) return alert("Not authenticated")

    const dealId = product.deal_id || product.id // fallback for testing
    try {
      await downloadDealPdf(dealId, token)
    } catch (error) {
      console.error("PDF download failed", error)
      alert("Failed to download PDF.")
    }
  }

  return (
    <div className="border rounded p-4 shadow bg-white text-black">
      <h2 className="text-xl font-bold mb-2">{product.title}</h2>
      <p className="text-sm text-gray-600">Origin: {product.origin_country}</p>
      <p className="text-sm text-gray-600">Certifications: {product.certifications || 'N/A'}</p>
      <p className="text-sm text-gray-600">
        Price: ${product.price_per_kg} / kg
      </p>
      <p className="mt-2">{product.description}</p>

      {product.image_url && (
        <img
          src={product.image_url}
          alt={product.title}
          className="w-full h-48 object-cover mt-2 rounded"
        />
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Link
          href={`/edit/${product.id}`}
          className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1 rounded"
        >
          ✏️ Edit
        </Link>
        <button
          onClick={handleDelete}
          className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded"
        >
          🗑️ Delete
        </button>
        <button
          onClick={handleDownloadPdf}
          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
        >
          📄 Download PDF
        </button>
        <Link
          href={`/deals/new?product_id=${product.id}&seller_id=${product.seller_id}`}
          className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded"
        >
          🤝 Create Deal
        </Link>
      </div>
    </div>
  )
}

