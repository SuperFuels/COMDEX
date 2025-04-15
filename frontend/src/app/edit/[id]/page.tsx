// src/app/edit/[id]/page.tsx
"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useParams } from "next/navigation"
import { getProducts, updateProduct } from "@/lib/api"

export default function EditPage() {
  const router = useRouter()
  const { id } = useParams()

  const [form, setForm] = useState({
    title: "",
    origin_country: "",
    price_per_kg: "",
    category: "",
    description: "",
    image_url: ""
  })

  useEffect(() => {
    async function fetchProduct() {
      try {
        const products = await getProducts()
        const product = products.find((p: any) => p.id === parseInt(id as string))
        if (product) {
          setForm(product)
        }
      } catch (err) {
        alert("Failed to load product")
      }
    }

    if (id) {
      fetchProduct()
    }
  }, [id])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const token = localStorage.getItem("token")
      await updateProduct(Number(id), form, token!)
      alert("Product updated!")
      router.push("/")
    } catch (err) {
      console.error(err)
      alert("Failed to update")
    }
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">✏️ Edit Product</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          name="title"
          value={form.title}
          onChange={handleChange}
          placeholder="Product title"
          className="w-full border p-2 rounded bg-black text-white"
        />
        <input
          name="origin_country"
          value={form.origin_country}
          onChange={handleChange}
          placeholder="Origin country"
          className="w-full border p-2 rounded bg-black text-white"
        />
        <input
          name="price_per_kg"
          value={form.price_per_kg}
          onChange={handleChange}
          placeholder="Price per kg"
          className="w-full border p-2 rounded bg-black text-white"
        />
        <input
          name="category"
          value={form.category}
          onChange={handleChange}
          placeholder="Category"
          className="w-full border p-2 rounded bg-black text-white"
        />
        <textarea
          name="description"
          value={form.description}
          onChange={handleChange}
          placeholder="Description"
          className="w-full border p-2 rounded bg-black text-white"
        />
        <input
          name="image_url"
          value={form.image_url}
          onChange={handleChange}
          placeholder="Image URL"
          className="w-full border p-2 rounded bg-black text-white"
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          💾 Save Changes
        </button>
      </form>
    </div>
  )
}

