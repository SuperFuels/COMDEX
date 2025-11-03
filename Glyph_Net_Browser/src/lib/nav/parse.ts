// /src/lib/nav/parse.ts
// Simple normalizer → structured target

export type Target =
  | { kind: "http"; href: string }
  | { kind: "wormhole"; name: string; href: string } // href: wormhole://<name>.tp
  | { kind: "dimension"; path: string; href: string }; // href: dimension://<path>

function ensureHttp(url: string) {
  if (/^https?:\/\//i.test(url)) return url;
  if (url.startsWith("www.")) return `https://${url}`;
  return `https://${url}`;
}

export function parseAddress(input: string): Target {
  let v = (input || "").trim();

  // explicit http(s)
  if (/^https?:\/\//i.test(v) || v.startsWith("www.")) {
    return { kind: "http", href: ensureHttp(v) };
  }

  // explicit dimension://, ucs://, glyph://  → treat as "dimension" for now
  if (/^(dimension|ucs|glyph):\/\//i.test(v)) {
    const scheme = v.split("://", 1)[0].toLowerCase();
    const path = v.replace(/^[a-z]+:\/\//i, "");
    // Preserve original scheme in href; UI router can refine later
    return { kind: "dimension", path, href: `${scheme}://${path}` };
  }

  // explicit wormhole glyph or .tp name OR bare word (default to wormhole)
  if (/^🌀/u.test(v) || /\.tp$/i.test(v) || !v.includes(".")) {
    v = v.replace(/^🌀/u, "");
    const name = v.endsWith(".tp") ? v : `${v}.tp`;
    return { kind: "wormhole", name, href: `wormhole://${name.toLowerCase()}` };
  }

  // fallback: domain-ish → http
  return { kind: "http", href: ensureHttp(v) };
}

/* ---------- Optional backward-compat types (if anything still imports them) ---------- */
export type NavScheme = "dimension" | "ucs" | "glyph" | "wormhole" | "www" | "http";
export type NavTarget =
  | { scheme: "www" | "http"; raw: string; url: string }
  | { scheme: "wormhole"; raw: string; host: string }
  | { scheme: "dimension" | "ucs" | "glyph"; raw: string; path: string };

export function toNavTarget(t: Target): NavTarget {
  switch (t.kind) {
    case "http":
      return { scheme: "www", raw: t.href, url: t.href };
    case "wormhole":
      return { scheme: "wormhole", raw: t.href, host: t.name };
    case "dimension": {
      const s = (t.href.split("://", 1)[0] || "").toLowerCase();
      // Restrict to the only schemes allowed for this return branch
      const scheme: "dimension" | "ucs" | "glyph" =
        s === "ucs" ? "ucs" : s === "glyph" ? "glyph" : "dimension";
      return { scheme, raw: t.href, path: t.path };
    }
  }
}