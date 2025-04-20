import { useEffect, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const params = new URLSearchParams();
      params.append('email', email);
      params.append('password', password);

      const response = await axios.post(
        'http://localhost:8000/auth/login',
        params,
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        }
      );

      const token = response.data.access_token;
      localStorage.setItem('token', token);

      // 🔐 Decode user email from token if needed
      const base64Payload = token.split('.')[1];
      const payload = JSON.parse(atob(base64Payload));
      const userEmail = payload.sub;

      // 🔍 Get user role from backend
      const roleRes = await axios.get('http://localhost:8000/auth/role', {
        headers: { Authorization: `Bearer ${token}` },
      });

      const role = roleRes.data.role;

      // 🎯 Redirect based on role
      if (role === 'admin') {
        router.push('/admin/dashboard');
      } else if (role === 'supplier') {
        router.push('/supplier/dashboard');
      } else {
        router.push('/dashboard');
      }

    } catch (err: any) {
      if (err?.response?.data?.detail) {
        const detail = err.response.data.detail;
        setError(
          Array.isArray(detail)
            ? detail.map((d: any) => d.msg).join(', ')
            : detail
        );
      } else {
        setError('Login failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

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
          className="border p-2 w-full mb-4 rounded"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          type="password"
          placeholder="Password"
          className="border p-2 w-full mb-4 rounded"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 w-full rounded hover:bg-blue-700"
          disabled={loading}
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>

        <p className="mt-4 text-sm text-center">
          Don’t have an account?{' '}
          <Link href="/register" className="text-blue-600 hover:underline">
            Register
          </Link>
        </p>
      </form>
    </div>
  );
}

