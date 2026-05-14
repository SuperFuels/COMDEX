// Glyph_Net_Browser/src/components/PhotonGuide.tsx
// Photon Language & File Types orientation guide (Dev Tools tab).

export default function PhotonGuide() {
  return (
    <div
      style={{
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
        fontSize: 13,
        color: "#111827",
        lineHeight: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* Title */}
      <header>
        <h2
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 18,
            fontWeight: 600,
          }}
        >
          Tessaris Photon Language — Orientation Guide
        </h2>
        <p
          style={{
            margin: 0,
            color: "#6b7280",
          }}
        >
          Photon lives in two layers: Photon pages/capsules (.ptn / .phn) and
          glyph-compressed Python (.photon / .pthon).
        </p>
      </header>

      {/* 0. Meta / frontmatter example */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          0. Page frontmatter (.ptn example)
        </h3>
        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`# ---
# page:
#   id: photon_language_guide
#   kind: doc
#   title: "Photon Language & File Types"
#   version: 1
#   tags: [photon, language, docs]
#   owner: tessaris.core
#   status: draft
# ---`}
        </pre>
        <p style={{ margin: "8px 0 0 0" }}>
          This YAML-in-comments style header is used by page validators and
          tooling. The Photon parser itself ignores it.
        </p>
      </section>

      {/* 1. Two layers */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          1. Two layers: Photon vs glyph-compressed Python
        </h3>

        <ol style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            <strong>Photon Language / Pages</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>Human-authorable “super language”.</li>
              <li>
                Files: <code>.ptn</code> (Photon Page) and <code>.phn</code>{" "}
                (Photon Capsule).
              </li>
              <li>Executed by the Photon runtime (page runner / executor).</li>
              <li>Talks to GlyphNet, QQC, SQI, KG, etc.</li>
            </ul>
          </li>
          <li style={{ marginTop: 8 }}>
            <strong>Glyph-compressed Python</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>Host Python code stored as glyphs.</li>
              <li>
                Files: <code>.photon</code> (and alias <code>.pthon</code>).
              </li>
              <li>
                Expanded back to normal Python by the Photon import hook at
                import time.
              </li>
              <li>Python thinks it’s importing a normal .py module.</li>
            </ul>
          </li>
        </ol>

        <p style={{ margin: "8px 0 0 0" }}>
          You can use both in the same project: Photon pages orchestrate,
          Python modules implement.
        </p>
      </section>

      {/* 2. File types quick reference */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          2. File Types (Quick Reference)
        </h3>

        <h4
          style={{
            margin: "4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          2.1 Photon Page / Capsule
        </h4>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            <code>.ptn</code> — <strong>Photon Page</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>Wiki-style composite document.</li>
              <li>Can mix narrative text, diagrams, inline Photon, KG refs.</li>
              <li>Run via Photon Page Runner.</li>
            </ul>
          </li>
          <li style={{ marginTop: 6 }}>
            <code>.phn</code> — <strong>Photon Capsule</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>Atomic executable Photon unit.</li>
              <li>
                Strict schema (
                <code>photon_capsule_schema.json</code>).
              </li>
              <li>
                Validated by <code>photon_capsule_validator.py</code>.
              </li>
              <li>Executed by <code>photon_executor.py</code>.</li>
            </ul>
          </li>
        </ul>

        <p style={{ margin: "8px 0 0 0" }}>
          Typical workflow: draft ideas in <code>.ptn</code>, factor stable
          behavior into <code>.phn</code> capsules. Pages call capsules;
          capsules call runtimes.
        </p>

        <h4
          style={{
            margin: "12px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          2.2 Glyph-Compressed Python
        </h4>

        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            <code>.photon</code> / <code>.pthon</code> — one-to-one, reversible
            encoding of Python using glyph tokens.
          </li>
          <li>Still Python; Photon Language is not involved here.</li>
          <li>
            Expanded at import time by the Photon importer (
            <code>backend/modules/photonlang/importer.py</code>).
          </li>
        </ul>

        <p style={{ margin: "8px 0 0 0" }}>
          Import hook: reads <code>.photon</code>, expands tokens → Python,
          optionally expands Symatics ops, normalizes/sanitizes, compiles to
          bytecode. Goal: Python never knows it wasn’t reading .py.
        </p>
      </section>

      {/* 3. Photon Page syntax */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          3. Photon Page Syntax (human-friendly core)
        </h3>

        <p style={{ margin: "0 0 4px 0" }}>
          Photon Page syntax is intentionally light. Most content can be plain
          text; Photon statements are sprinkled where needed. The parser (
          <code>backend/modules/photonlang/parser.py</code>) understands a small
          grammar:
        </p>

        {/* 3.1 Imports */}
        <h4
          style={{
            margin: "8px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          3.1 Imports
        </h4>

        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`import glyphnet, photon_algebra, quantum_canvas

from glyphnet v1 import warp_channel, resonance_map
from photon.page import PhotonPageRunner`}
        </pre>
        <ul style={{ margin: "4px 0 0 0", paddingLeft: 16 }}>
          <li>
            <code>import X, Y</code> — basic module import.
          </li>
          <li>
            <code>from M v1 import name</code> — import from a specific version.
          </li>
          <li>Relative imports (from .local import foo) are valid.</li>
        </ul>

        {/* 3.2 Wormhole imports */}
        <h4
          style={{
            margin: "10px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          3.2 Wormhole Imports
        </h4>

        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`from (wormhole: "ucs://root/photon/qqc/bridge") import qqc_bridge
from wormhole:ucs://root/photon/pages/core import main_page`}
        </pre>
        <p style={{ margin: "4px 0 0 0" }}>
          Both forms route into <code>WormholeImport(uri, name)</code> AST
          nodes. Semantics: bind the local name to the capsule at that URI.
        </p>

        {/* 3.3 Glyph operators */}
        <h4
          style={{
            margin: "10px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          3.3 Glyph Operators
        </h4>

        <p style={{ margin: "0 0 4px 0" }}>
          Photon reserves symbolic operators (loaded from{" "}
          <code>photon_reserved_map.json</code>):
        </p>

        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`⊕              # composition / emit / combine
μ              # measurement / micro step
π              # period / modulation
⟲ {freq=1.1}   # standing-wave loop with parameters
↔              # entanglement / bidirectional link
∇              # gradient / flow`}
        </pre>

        <p style={{ margin: "4px 0 0 0" }}>
          Contiguous runs of operator glyphs are parsed as <code>GLYPHSEQ</code>
          :
        </p>

        <pre
          style={{
            margin: "4px 0 0 0",
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`⊕               # GlyphInit("⊕")
μπ             # GlyphInit("μπ")
⟲ {freq=0.8}   # GlyphStmt("⟲", {"freq": 0.8})`}
        </pre>

        {/* 3.4 Send / Save */}
        <h4
          style={{
            margin: "10px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          3.4 Send / Save
        </h4>

        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`send stream through wormhole "ucs://local/session/primary"
save as "initial_state"
save as snapshot_state`}
        </pre>
        <p style={{ margin: "4px 0 0 0" }}>
          Parsed as <code>SendThrough(obj, uri)</code> and{" "}
          <code>SaveAs(...)</code>.
        </p>

        {/* 3.5 Calls & attrs */}
        <h4
          style={{
            margin: "10px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          3.5 Calls & Attributes
        </h4>

        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`⊕(warp_channel, resonance_map)
qqc_bridge.run(session="live")
quantum_canvas.field.render()`}
        </pre>
        <p style={{ margin: "4px 0 0 0" }}>
          Supported: names, attributes (<code>x.y</code> / <code>x.y.z</code>),
          and calls (<code>f()</code>, <code>f(a, b=3)</code>,{" "}
          <code>x.y()</code>, <code>x.y(z).t</code>).
        </p>
      </section>

      {/* 4. DevTools Photon editor */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          4. Dev Tools Photon Editor
        </h3>

        <p style={{ margin: "0 0 4px 0" }}>
          In <strong>Dev Tools → Text Editor</strong>:
        </p>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>Left pane: SOURCE (.ptn / Python).</li>
          <li>Right pane: TRANSLATED GLYPHS.</li>
          <li>
            <strong>Language selector</strong>:
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                <code>Photon (.ptn)</code> — treat content as Photon / .ptn
                text, using the legacy Photon translator.
              </li>
              <li>
                <code>Python</code> — token-aware Python→glyph translation (
                <code>PhotonTranslator(language="python")</code>).
              </li>
            </ul>
          </li>
        </ul>

        <p style={{ margin: "8px 0 4px 0" }}>
          Buttons:
          <br />
          <strong>Code → Glyph</strong>
        </p>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            For Photon: line-by-line legacy translator.
          </li>
          <li>
            For Python: tokenizes with <code>tokenize</code>, maps keywords /
            ops via <code>python_token_map.json</code>, glyphifies strings and
            comments via the Lexicon & glyph_map.
          </li>
        </ul>

        <p style={{ margin: "8px 0 4px 0" }}>
          <strong>Glyph → Code</strong>
        </p>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            Sends glyph stream to <code>/api/photon/translate_reverse</code>.
          </li>
          <li>Attempts to reconstruct Photon-like source.</li>
        </ul>

        <p style={{ margin: "8px 0 0 0" }}>
          Use cases: draft .ptn pages, inspect Python compression, test
          round-trips.
        </p>
      </section>

      {/* 5. Writing Photon pages example */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          5. Writing Photon Pages in Practice (.ptn pattern)
        </h3>

        <pre
          style={{
            margin: 0,
            padding: 8,
            borderRadius: 6,
            background: "#111827",
            color: "#e5e7eb",
            fontSize: 12,
            overflowX: "auto",
          }}
        >
{`# ---
# page:
#   id: my_first_photon_page
#   kind: doc
#   title: "My First Photon Page"
#   version: 1
# ---

# 1. Narrative

This page orchestrates a simple QQC run and records results.

# 2. Imports

import photon_algebra_runtime, photon_page_runner
from (wormhole: "ucs://root/photon/qqc/core") import qqc_core

# 3. Setup

⊕ init_session
qqc_core.bootstrap()

# 4. Run

⊕ run_experiment {shots=128}
send qqc_core.results through wormhole "ucs://local/results/inbox"

save as "qqc_demo_run"`}
        </pre>

        <p style={{ margin: "8px 0 0 0" }}>
          The meta block is comment-wrapped YAML; validators read it, parser
          ignores it. Mix narrative and executable Photon statements freely.
        </p>
      </section>

      {/* 6. Internals */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          6. Internals (engine / maintainer mental model)
        </h3>

        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            <strong>Photon parser</strong>
            <br />
            <code>backend/modules/photonlang/parser.py</code>
            <br />
            Photon source (.ptn / .phn) → AST (Program, GlyphStmt, SendThrough,
            …).
          </li>
          <li style={{ marginTop: 6 }}>
            <strong>Photon executor</strong>
            <br />
            <code>photon_executor.py</code>
            <br />
            Walks AST / capsules and dispatches into Photon Algebra Runtime,
            PhotonMemoryGrid, SQI/QQC bridges, Symatics/Warp, etc.
          </li>
          <li style={{ marginTop: 6 }}>
            <strong>Photon Page runner</strong>
            <br />
            <code>photon_page_spec.py</code>,{" "}
            <code>photon_page_validator.py</code>, <code>PhotonPageRunner</code>
            .
            <br />
            Validates <code>.ptn</code>, resolves imports (local & wormhole),
            schedules capsules onto runtime.
          </li>
          <li style={{ marginTop: 6 }}>
            <strong>Glyph-compressed Python importer</strong>
            <br />
            <code>backend/modules/photonlang/importer.py</code>
            <br />
            Discovers <code>.photon</code> / <code>.pthon</code>, expands glyph
            tokens → Python, normalizes, enforces policy (SHA256 / allow-list),
            compiles & executes.
          </li>
          <li style={{ marginTop: 6 }}>
            <strong>Dev Tools Photon Editor</strong>
            <br />
            Frontend:{" "}
            <code>Glyph_Net_Browser/src/components/PhotonEditor.tsx</code>.
            <br />
            Backend: <code>/api/photon/translate</code>,{" "}
            <code>/api/photon/translate_reverse</code>.
            <br />
            Local scratchpad using{" "}
            <code>PhotonTranslator(language="photon" | "python")</code> and the
            shared Lexicon index.
          </li>
        </ul>
      </section>

      {/* 7. Where to go next */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          7. Where to Go Next
        </h3>

        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            Write small <code>.ptn</code> pages that import a known capsule,
            run a simple operator sequence, and send results through a local
            wormhole URI.
          </li>
          <li>
            Experiment with plain English in comments/strings → see which words
            lexicon-glyphify.
          </li>
          <li>
            Paste Python snippets in <strong>Python</strong> mode → gauge
            compression vs readability.
          </li>
          <li>
            When a page stabilizes, factor the executable core into{" "}
            <code>.phn</code> capsules, leaving the <code>.ptn</code> as
            orchestration + documentation.
          </li>
        </ul>
      </section>

      <footer
        style={{
          marginTop: 8,
          paddingTop: 8,
          borderTop: "1px solid #e5e7eb",
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        End of Photon Language Guide (.ptn).
      </footer>
    </div>
  );
}