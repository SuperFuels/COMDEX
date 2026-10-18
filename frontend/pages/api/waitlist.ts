import type { NextApiRequest, NextApiResponse } from "next";

const WAITLIST_RECIPIENT = "kevin.robinson101@gmail.com";
const RESEND_ENDPOINT = "https://api.resend.com/emails";
const MAX_LENGTHS = {
  name: 120,
  email: 254,
  businessName: 160,
  phone: 60,
  role: 120,
  businessSize: 80,
  interest: 160,
  message: 2000,
  plan: 40,
  credits: 20,
} as const;

type WaitlistField = keyof typeof MAX_LENGTHS;

function cleanField(value: unknown, field: WaitlistField): string {
  return typeof value === "string"
    ? value.trim().replace(/\r\n?/g, "\n").slice(0, MAX_LENGTHS[field])
    : "";
}

function isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function safeHeader(value: string): string {
  return value.replace(/[\r\n]+/g, " ").trim();
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "method_not_allowed" });
  }

  const honeypot = typeof req.body?.website === "string" ? req.body.website.trim() : "";
  if (honeypot) {
    return res.status(200).json({ ok: true });
  }

  const name = cleanField(req.body?.name, "name");
  const email = cleanField(req.body?.email, "email").toLowerCase();
  const businessName = cleanField(req.body?.businessName, "businessName");
  const phone = cleanField(req.body?.phone, "phone");
  const role = cleanField(req.body?.role, "role");
  const businessSize = cleanField(req.body?.businessSize, "businessSize");
  const interest = cleanField(req.body?.interest, "interest");
  const message = cleanField(req.body?.message, "message");
  const plan = cleanField(req.body?.plan, "plan");
  const credits = cleanField(req.body?.credits, "credits");

  if (!name || !email || !businessName || !isEmail(email)) {
    return res.status(400).json({ error: "required_fields_invalid" });
  }

  const apiKey = process.env.RESEND_API_KEY?.trim();
  const from = process.env.TESSARIS_WAITLIST_FROM_EMAIL?.trim()
    || process.env.RESEND_FROM_EMAIL?.trim()
    || "Tessaris Waitlist <onboarding@resend.dev>";

  if (!apiKey) {
    return res.status(503).json({ error: "waitlist_email_not_configured" });
  }

  const lines = [
    "New Tessaris launch waitlist request",
    "",
    `Name: ${name}`,
    `Email: ${email}`,
    `Business: ${businessName}`,
    `Phone: ${phone || "Not supplied"}`,
    `Role: ${role || "Not supplied"}`,
    `Business size: ${businessSize || "Not supplied"}`,
    `Main interest: ${interest || "Not supplied"}`,
    `Selected plan: ${plan || "Not selected"}`,
    `Selected credits: ${credits || "Not selected"}`,
    "",
    "Message:",
    message || "No additional message supplied.",
    "",
    `Received: ${new Date().toISOString()}`,
  ];

  try {
    const providerResponse = await fetch(RESEND_ENDPOINT, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to: [WAITLIST_RECIPIENT],
        reply_to: email,
        subject: `Waitlist: ${safeHeader(businessName)} — ${safeHeader(name)}`,
        text: lines.join("\n"),
      }),
    });

    if (!providerResponse.ok) {
      return res.status(502).json({ error: "waitlist_email_delivery_failed" });
    }

    return res.status(200).json({ ok: true });
  } catch {
    return res.status(502).json({ error: "waitlist_email_delivery_failed" });
  }
}
