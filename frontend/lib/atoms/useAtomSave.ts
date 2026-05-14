export async function saveAtom({ name, glyphs, sqi, patterns }: {
  name: string
  glyphs: any[]
  sqi?: number
  patterns?: string[]
}) {
  const res = await fetch("/photon/save_atom", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, glyphs, sqi, patterns }),
  })

  if (!res.ok) throw new Error("Atom save failed")
  return res.json()
}