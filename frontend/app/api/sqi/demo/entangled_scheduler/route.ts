import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const backend = (process.env.SQI_BACKEND_URL || "").replace(/\/$/, "");
  if (!backend) {
    return NextResponse.json(
      { detail: "SQI_BACKEND_URL is not set (no backend to call)." },
      { status: 503 }
    );
  }

  const body = await req.json().catch(() => ({}));
  const url = `${backend}/api/sqi/demo/entangled_scheduler`;

  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const text = await r.text();
  return new NextResponse(text, {
    status: r.status,
    headers: {
      "content-type": r.headers.get("content-type") || "application/json",
    },
  });
}