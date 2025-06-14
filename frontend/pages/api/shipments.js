export default async function handler(req, res) {
  // forward to your backend
  const apiRes = await fetch(
    `${process.env.BACKEND_URL}/shipments`
  );
  const data = await apiRes.json();
  return res.status(apiRes.status).json(data);
}
