// src/lib/nav/parse.ts

// ───────────────────────────────────────────────────────────────
// Classifier model (used by the command bar)

export type AddrKind = "http" | "wormhole" | "container";

/** Minimal classifier result for quick routing decisions. */
export function classifyAddress(raw: string): { kind: AddrKind; target: string } {
  let s = String(raw || "").trim();

  // strip optional wormhole emoji prefix
  if (/^🌀/u.test(s)) s = s.replace(/^🌀/u, "");

  // direct SPA hash → container
  //   #/container/kevin__home  |  /#/container/kevin__home
  if (/#\/container\/[^/\s]+$/i.test(s)) {
    const id = s.replace(/^.*#\/container\//, "");
    return { kind: "container", target: decodeURIComponent(id) };
  }

  // explicit http(s)
  if (/^https?:\/\//i.test(s)) return { kind: "http", target: s };

  // explicit wormhole protocol
  if (/^wormhole:\/\//i.test(s)) {
    const name = s.replace(/^wormhole:\/\//i, "").toLowerCase();
    return { kind: "wormhole", target: name.endsWith(".tp") ? name : `${name}.tp` };
  }

  // explicit local schemes that carry a container id in the tail
  // e.g. ucs://local/kevin__home, dimension://kevin__kg_personal
  const m = s.match(/^(dimension|ucs|glyph):\/\/(.+)$/i);
  if (m) {
    const tail = m[2].replace(/\/+$/, "");
    const id = tail.split("/").pop() || tail;
    return { kind: "container", target: id };
  }

  // @username → username__home
  if (/^@[a-z0-9._-]+$/i.test(s)) {
    return { kind: "container", target: s.slice(1) + "__home" };
  }

  // canonical container id patterns
  if (/^[a-z0-9._-]+__(home|kg_personal|kg_work)$/i.test(s)) {
    return { kind: "container", target: s };
  }

  // single token (no TLD) → treat as container alias/id
  if (/^[a-z0-9._-]+$/i.test(s) && !/\.[a-z]{2,}$/i.test(s)) {
    return { kind: "container", target: s };
  }

  // .tp names → wormhole
  if (/^[a-z0-9.-]+\.tp$/i.test(s)) {
    return { kind: "wormhole", target: s.toLowerCase() };
  }

  // bare domain → http
  if (/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(s)) {
    return { kind: "http", target: `https://${s}` };
  }

  // fallback → http search/pass-through
  return { kind: "http", target: ensureHttp(s) };
}

// ───────────────────────────────────────────────────────────────
// Router model (legacy + container added)

export type Target =
  | { kind: "http"; href: string }
  | { kind: "wormhole"; name: string; href: string }
  | { kind: "dimension"; path: string; href: string }
  | { kind: "container"; id: string; href: string };   // ✅ new

/** Main parser used by routeNav – returns a Target (now includes container). */
export function parseAddress(input: string): Target {
  const { kind, target } = classifyAddress(input);

  switch (kind) {
    case "http":
      return { kind: "http", href: ensureHttp(target) };

    case "wormhole": {
      const name = target.endsWith(".tp") ? target : `${target}.tp`;
      return { kind: "wormhole", name, href: `wormhole://${name}` };
    }

    case "container": {
      const id = target;
      return { kind: "container", id, href: `#/container/${encodeURIComponent(id)}` };
    }
  }
}

// ───────────────────────────────────────────────────────────────
// Legacy compatibility shims (kept for older imports)

export type NavScheme = "dimension" | "ucs" | "glyph" | "wormhole" | "www" | "http";
export type NavTarget =
  | { scheme: "www" | "http"; raw: string; url: string }
  | { scheme: "wormhole"; raw: string; host: string }
  | { scheme: "dimension" | "ucs" | "glyph"; raw: string; path: string };

/** Older callers expect only http | wormhole | dimension. Keep them working. */
export function parseAddressLegacy(input: string): Target {
  const r = parseAddress(input);

  if (r.kind === "http" || r.kind === "wormhole") return r;

  // If a real "dimension" sneaks in, just return it unchanged (defensive).
  if (r.kind === "dimension") return r;

  // ✅ container → legacy "dimension" (ucs) shape
  const id = r.id;
  return { kind: "dimension", path: id, href: `ucs://local/${id}` };
}

/** Convert a Target to a UI-friendly NavTarget. */
export function toNavTarget(t: Target): NavTarget {
  if (t.kind === "http") {
    return { scheme: "www", raw: t.href, url: t.href };
  }

  if (t.kind === "wormhole") {
    return { scheme: "wormhole", raw: t.href, host: t.name };
  }

  if (t.kind === "dimension") {
    const s = (t.href.split("://", 1)[0] || "").toLowerCase();
    const scheme: "dimension" | "ucs" | "glyph" =
      s === "ucs" ? "ucs" : s === "glyph" ? "glyph" : "dimension";
    return { scheme, raw: t.href, path: t.path };
  }

  // container (new) → present as legacy ucs-shape for old consumers
  const href = `ucs://local/${t.id}`;
  return { scheme: "ucs", raw: href, path: t.id };
}

// Alias for any very old imports
export { parseAddressLegacy as legacyParseAddress };

// ───────────────────────────────────────────────────────────────
// Internals

function ensureHttp(u: string) {
  if (/^https?:\/\//i.test(u)) return u;
  if (u.startsWith("www.")) return `https://${u}`;
  return `https://${u}`;
}