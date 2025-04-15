"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { loginUser } from "@/lib/api"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email || !password) {
      setError("Please fill in all fields.")
      return
    }

    try {
      const data = await loginUser({ email, password })
      localStorage.setItem("token", data.access_token)
      router.push("/")
    } catch (err: any) {
      console.error("Login failed", err)
      setError(err?.response?.data?.detail || "Login failed.")
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-black">
      <form onSubmit={handleLogin} className="bg-gray-900 p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-4 text-white">🔐 Login</h1>

        {error && <p className="text-red-500 mb-4">{error}</p>}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full p-2 mb-4 rounded bg-black text-white border border-gray-700"
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full p-2 mb-6 rounded bg-black text-white border border-gray-700"
        />

        <button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded font-semibold"
        >
          🔓 Login
        </button>
      </form>
    </div>
  )
}

