// src/utils/nameService.ts
// Single source of truth for WA/WN name helpers

export type GraphKey = "personal" | "work";

/** Canonicalize graph keys. Anything not 'work' becomes 'personal'. */
export function canonKG(v: string | null | undefined): GraphKey {
  return (String(v || "").toLowerCase() === "work") ? "work" : "personal";
}

/** Collapse whitespace, strip punctuation, and casefold for matching. */
export function canonLabelKey(label: string): string {
  return String(label || "")
    .toLowerCase()
    .normalize("NFKC")
    .replace(/[\p{P}\p{S}]+/gu, " ")   // drop punctuation/symbols
    .replace(/\s+/g, " ")              // collapse spaces
    .trim();
}

/** Slug for constructing a WA when we don't have one yet. */
function slugify(label: string): string {
  return canonLabelKey(label)
    .replace(/\s+/g, "-")              // spaces → hyphen
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "") || "user";
}

/** Canonicalize a WA string into `ucs://<realm>/<id>`; lower-case and strip junk. */
export function canonWA(raw: string): string {
  if (!raw) return "";
  let s = String(raw).trim();

  // If user typed a packed link or extra scheme, try to find the ucs:// part
  const m = s.match(/ucs:\/\/[^ \t\r\n]+/);
  if (m) s = m[0];

  // Ensure scheme
  if (!/^ucs:\/\//i.test(s)) s = "ucs://" + s;

  // Lower-case and remove trailing slashes
  s = s.toLowerCase().replace(/\/+$/g, "");
  // Normalize multiple slashes in the path
  s = s.replace(/^ucs:\/\/+/, "ucs://").replace(/\/\/+/g, "/");
  return s;
}

/** Pretty label suggestion from a WA (only used when we don't have a saved alias). */
export function labelFromWA(wa: string): string {
  const s = canonWA(wa);
  const after = s.replace(/^ucs:\/\//, "");
  const parts = after.split("/");
  const id = parts.slice(1).join("/") || parts[0] || s;
  const nice = id.replace(/[-_]+/g, " ").trim();
  return nice ? nice.replace(/\b\w/g, c => c.toUpperCase()) : s;
}

/* ------------------------- Alias storage (per graph) ------------------------ */

type Book = {
  // best-known label by WA
  byWA: Record<string, { label: string; updatedAt: number }>;
  // reverse lookup for quick label → WA (canonical label key)
  byLabel: Record<string, string>;
};

function keyFor(kg: GraphKey) { return `gnet:aliases:${kg}`; }

function loadBook(kg: GraphKey): Book {
  try {
    const raw = localStorage.getItem(keyFor(kg));
    if (raw) return JSON.parse(raw) as Book;
  } catch {}
  return { byWA: {}, byLabel: {} };
}

function saveBook(kg: GraphKey, b: Book) {
  try { localStorage.setItem(keyFor(kg), JSON.stringify(b)); } catch {}
}

/** Persist the best-known label for a WA (and keep reverse mapping). */
export function saveBestLabel(kg: GraphKey, wa: string, label: string) {
  const book = loadBook(kg);
  const w = canonWA(wa);
  const lbl = (label || "").trim();
  if (!w || !lbl) return;

  book.byWA[w] = { label: lbl, updatedAt: Date.now() };
  book.byLabel[canonLabelKey(lbl)] = w;
  saveBook(kg, book);
}

/** Look up the best-known label for a WA, else a pretty fallback. */
export function getLabelForWA(kg: GraphKey, wa: string): string {
  const book = loadBook(kg);
  const w = canonWA(wa);
  return book.byWA[w]?.label || labelFromWA(w);
}

/** Try to resolve an input (label, WA, or label@kg) to { wa, label, kg }.
 *  - If input is already a WA → return canonical WA + known/best label.
 *  - If input is a label → use alias table; else synthesize WA via slug.
 *  - Persists label↔WA for future de-duplication.
 */
export function resolveLabelToWA(
  _base: string,                 // kept for future server-side resolution
  kg: GraphKey,
  rawInput: string
): { wa: string; label: string; kg: GraphKey } {
  let input = String(rawInput || "").trim();

  // Allow "Alice @ work" style
  const at = input.lastIndexOf("@");
  if (at > 0 && at < input.length - 1) {
    const rhs = input.slice(at + 1);
    const lhs = input.slice(0, at);
    kg = canonKG(rhs);
    input = lhs.trim();
  }

  // If this is already a WA, we're done
  if (/^ucs:\/\//i.test(input) || input.startsWith("ucs://")) {
    const wa = canonWA(input);
    const label = getLabelForWA(kg, wa);
    // Remember the association in case label changed upstream
    saveBestLabel(kg, wa, label);
    return { wa, label, kg };
  }

  // Otherwise treat as a human label and look up known alias
  const book = loadBook(kg);
  const key = canonLabelKey(input);
  const knownWA = book.byLabel[key];

  const wa = knownWA || canonWA(`wave.tp/${slugify(input)}`);

  // Persist best-known label mapping
  saveBestLabel(kg, wa, input);

  return { wa, label: input, kg };
}