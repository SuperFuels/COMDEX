// frontend/pages/login.tsx

import React, { useState } from 'react'
import { useRouter } from 'next/router'
import api from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // 1) Send credentials as URL-encoded form data
      const params = new URLSearchParams({
        email,
        password,
      })

      // 2) Hit /auth/login
      const { data } = await api.post(
        '/auth/login',
        params,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      )

      // 3) Store and set the JWT on our axios instance
      const token = data.access_token
      localStorage.setItem('token', token)
      api.defaults.headers.common.Authorization = `Bearer ${token}`

      // 4) Fetch the user’s role
      const profileRes = await api.get<{ role: string }>('/auth/profile')
      const role       = profileRes.data.role

      // 5) Redirect based on role
      if (role === 'admin') {
        router.push('/admin/dashboard')
      } else if (role === 'supplier') {
        router.push('/dashboard')
      } else if (role === 'buyer') {
        router.push('/buyer/dashboard')
      } else {
        router.push('/')
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (detail) {
        setError(
          Array.isArray(detail)
            ? detail.map((d: any) => d.msg).join(', ')
            : detail
        )
      } else {
        setError('Login failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <form
        onSubmit={handleLogin}
        className="bg-white p-6 rounded shadow-md w-full max-w-sm"
      >
        <h1 className="text-2xl font-bold mb-4 text-center">Login</h1>

        {error && (
          <p className="text-red-500 mb-4 text-sm text-center">{error}</p>
        )}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="border p-2 w-full mb-4 rounded"
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="border p-2 w-full mb-4 rounded"
        />

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-2 rounded text-white ${
            loading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? 'Logging in…' : 'Login'}
        </button>
      </form>
    </div>
  )
}