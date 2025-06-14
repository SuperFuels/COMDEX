export default async function handler(req, res) {
  const apiRes = await fetch(\`\${process.env.BACKEND_URL}/shipments\`)
  const data = await apiRes.json()
  res.status(apiRes.status).json(data)
}
