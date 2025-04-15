"use client"

import { useState } from "react"
import { registerUser } from "@/lib/api"
import { useRouter } from "next/navigation"

export default function RegisterPage() {
  const router = useRouter()

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  })

  const [error, setError] = useState("")

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleRegister = async () => {
    try {
      await registerUser(form)
      alert("Registration successful!")
      router.push("/login")
    } catch (err: any) {
      console.error("Registration error:", err)
      setError(err.response?.data?.detail || "Registration failed")
    }
  }

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded shadow text-black">
      <h1 className="text-2xl font-bold mb-4">Register</h1>

      {error && (
        <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">
          {error}
        </div>
      )}

      <input
        type="text"
        name="name"
        placeholder="Full Name"
        className="w-full p-2 mb-3 border rounded"
        value={form.name}
        onChange={handleChange}
      />

      <input
        type="email"
        name="email"
        placeholder="Email"
        className="w-full p-2 mb-3 border rounded"
        value={form.email}
        onChange={handleChange}
      />

      <input
        type="password"
        name="password"
        placeholder="Password"
        className="w-full p-2 mb-4 border rounded"
        value={form.password}
        onChange={handleChange}
      />

      <button
        onClick={handleRegister}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded"
      >
        Register
      </button>
    </div>
  )
}

