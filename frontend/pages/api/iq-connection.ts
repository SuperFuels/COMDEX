import type { NextApiRequest, NextApiResponse } from 'next';
export default function handler(_req: NextApiRequest, res: NextApiResponse) {
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    mode: process.env.IQ_SHARED_DEMO_ENABLED === 'true' ? 'shared-simulated' : 'legacy-browser-demo',
    simulated: true,
  });
}
