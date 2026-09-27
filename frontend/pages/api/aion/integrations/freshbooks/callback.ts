import type { NextApiRequest, NextApiResponse } from "next";

const LOCAL_CALLBACK =
  "http://127.0.0.1:8080/api/aion/integrations/freshbooks/callback";
const MAX_OAUTH_VALUE_LENGTH = 4096;

function singleQueryValue(value: string | string[] | undefined): string | null {
  if (typeof value !== "string" || value.length === 0) return null;
  if (value.length > MAX_OAUTH_VALUE_LENGTH) return null;
  return value;
}

/**
 * FreshBooks requires an HTTPS redirect URI. Tessaris runs its accounting
 * connector locally, so this public endpoint relays only the OAuth response
 * back to the local service. The local backend validates the one-time state
 * before exchanging the authorisation code and storing credentials.
 */
export default function handler(req: NextApiRequest, res: NextApiResponse) {
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.setHeader("Referrer-Policy", "no-referrer");

  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).end("Method not allowed");
  }

  const state = singleQueryValue(req.query.state);
  const code = singleQueryValue(req.query.code);
  const error = singleQueryValue(req.query.error);
  const errorDescription = singleQueryValue(req.query.error_description);

  if (!state || (!code && !error)) {
    return res.status(400).end("Invalid FreshBooks callback");
  }

  const localUrl = new URL(LOCAL_CALLBACK);
  localUrl.searchParams.set("state", state);

  if (code) localUrl.searchParams.set("code", code);
  if (error) localUrl.searchParams.set("error", error);
  if (errorDescription) {
    localUrl.searchParams.set("error_description", errorDescription);
  }

  return res.redirect(302, localUrl.toString());
}
