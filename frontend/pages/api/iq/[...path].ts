import type { NextApiRequest, NextApiResponse } from 'next';

export const config = { api: { bodyParser: { sizeLimit: '1mb' }, responseLimit: '2mb' } };

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  res.setHeader('Cache-Control', 'no-store');
  const origin = process.env.IQ_BACKEND_URL;
  const key = process.env.IQ_PROXY_KEY;
  const publicOrigin = process.env.IQ_PUBLIC_ORIGIN || 'https://tessaris.ai';
  if (process.env.IQ_SHARED_DEMO_ENABLED !== 'true' || !origin || !key) {
    return res.status(503).json({ detail: 'The shared IQ simulation is not connected yet.' });
  }
  let base: URL;
  try { base = new URL(origin); } catch { return res.status(503).json({ detail: "Invalid IQ service configuration." }); }
  if (base.protocol !== 'https:' || base.username || base.password || base.search || base.hash || !['', '/'].includes(base.pathname)) {
    return res.status(503).json({ detail: 'The shared IQ service configuration needs attention.' });
  }
  if (!['GET', 'POST', 'DELETE'].includes(req.method || '')) return res.status(405).end();
  if (req.method !== 'GET' && req.headers.origin !== publicOrigin) return res.status(403).json({ detail: 'Same-origin request required.' });
  const segments = req.query.path;
  if (!Array.isArray(segments) || segments.some(s => !/^[a-zA-Z0-9_-]+$/.test(s))) return res.status(400).end();
  const cookie = req.cookies['__Host-iq_demo'];
  const clientIP = process.env.VERCEL === '1' ? String(req.headers['x-vercel-forwarded-for'] || '').split(',')[0].trim() : req.socket.remoteAddress || 'unknown';
  try {
    const upstream = await fetch(`${base.origin}/api/iq/${segments.map(encodeURIComponent).join('/')}`, {
      method: req.method,
      redirect: 'error',
      signal: AbortSignal.timeout(15000),
      headers: {
        Accept: 'application/json', 'Content-Type': 'application/json',
        'X-IQ-Proxy-Key': key, 'X-IQ-Client-IP': clientIP, 'User-Agent': String(req.headers['user-agent'] || '').slice(0,512),
        ...(req.method === 'GET' ? {} : { Origin: publicOrigin }),
        ...(cookie && /^[a-zA-Z0-9_-]+$/.test(cookie) ? { Cookie: `__Host-iq_demo=${cookie}` } : {}),
      },
      ...(req.method === 'GET' ? {} : { body: JSON.stringify(req.body || {}) }),
    });
    if (!upstream.headers.get('content-type')?.includes('application/json')) throw Error('Unexpected upstream format');
    const data = await upstream.text();
    if (data.length > 2_000_000) throw Error('Response too large');
    const setCookie = upstream.headers.get('set-cookie');
    if (setCookie && setCookie.startsWith('__Host-iq_demo=')) res.setHeader('Set-Cookie', setCookie);
    res.status(upstream.status).setHeader('Content-Type', 'application/json');
    return res.send(data);
  } catch {
    return res.status(503).json({ detail: 'The IQ service is temporarily unavailable. If you submitted an action, retry its original confirmation; do not start a replacement order.' });
  }
}
