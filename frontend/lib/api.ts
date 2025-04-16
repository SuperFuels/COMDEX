const BASE_URL = 'http://127.0.0.1:8000';

const api = {
  get: async (path: string, token?: string) => {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.json();
  },
  post: async (path: string, data: any, token?: string) => {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify(data),
    });
    return res.json();
  },
  put: async (path: string, data: any, token?: string) => {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify(data),
    });
    return res.json();
  },
  delete: async (path: string, token?: string) => {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.json();
  },
};

export default api;

