// Glyph_Net_Browser/src/components/AstHologramGuide.tsx
// AST → Glyphs → GHX → Hologram orientation guide (Dev Tools tab).

export default function AstHologramGuide() {
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
          Text → Glyphs → AST → GHX → Hologram
        </h2>
        <p
          style={{
            margin: 0,
            color: "#6b7280",
          }}
        >
          How Dev Tools turns code, logic, and text into ASTs, glyph graphs,
          GHX packets, and finally holograms.
        </p>
      </header>

      {/* 1. What AST actually is */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          1. What the AST layer actually is
        </h3>

        <p style={{ margin: "0 0 4px 0" }}>
          AST = <strong>Abstract Syntax Tree</strong>. Think of it as:
        </p>
        <p style={{ margin: "0 0 4px 0" }}>
          <em>&quot;Your code, but as a tree of meaning, not a blob of text.&quot;</em>
        </p>

        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            <code>if</code>, <code>and</code>, <code>or</code>, <code>-&gt;</code>, function
            calls, predicates, etc. become structured nodes.
          </li>
          <li>Glyphs are a compact, uniform alphabet for those nodes.</li>
          <li>
            <code>CodexAST</code>, logic trees, and Photon ASTs are all different views of
            the same underlying tree.
          </li>
        </ul>

        <p style={{ margin: "8px 0 0 0" }}>
          Instead of treating code as strings, the system treats it as a{" "}
          <strong>graph of ideas</strong>.
        </p>
      </section>

      {/* 2. End-to-end pipeline */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          2. End-to-end pipeline: from text to hologram
        </h3>

        <ol style={{ margin: 0, paddingLeft: 18 }}>
          <li style={{ marginBottom: 6 }}>
            <strong>Text / Code in Dev Tools</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                You type in the Dev Tools <strong>Text Editor</strong> (Photon, Python,
                CodexLang, or even NL).
              </li>
              <li>
                <code>PhotonEditor.tsx</code> can:
                <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                  <li>Translate <strong>Code → Glyph</strong> via /api/photon.</li>
                  <li>
                    Call <code>/api/ast</code> to build an AST and show it in the{" "}
                    <strong>AST Inspector</strong>.
                  </li>
                </ul>
              </li>
            </ul>
          </li>

          <li style={{ marginBottom: 6 }}>
            <strong>AST construction</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                <code>backend/api/ast_api.py</code> fan-outs by language:
                <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                  <li>
                    Python →{" "}
                    <code>parse_python_file_to_codex_ast()</code>
                  </li>
                  <li>
                    CodexLang →{" "}
                    <code>parse_codexlang_to_ast()</code>
                  </li>
                  <li>
                    Natural language →{" "}
                    <code>parse_nl_to_ast()</code>
                  </li>
                  <li>
                    Photon (optional) →{" "}
                    <code>parse_source()</code> from the Photon parser.
                  </li>
                </ul>
              </li>
              <li>
                All of these normalize into a <code>CodexAST</code> wrapper (
                <code>backend/modules/symbolic/codex_ast_types.py</code>).
              </li>
            </ul>
          </li>

          <li style={{ marginBottom: 6 }}>
            <strong>AST → glyph graph</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                <code>encode_codex_ast_to_glyphs()</code> (
                <code>codex_ast_encoder.py</code>) walks the AST and emits{" "}
                <strong>LogicGlyph</strong> objects.
              </li>
              <li>
                These encode logic, quantifiers, predicates, and symbolic calls in a
                uniform format the symbolic engine understands.
              </li>
            </ul>
          </li>

          <li style={{ marginBottom: 6 }}>
            <strong>Glyphs → GHX packet</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                <code>ghx_encoder.py</code>, <code>ghx_trace_encoder.py</code> bundle glyph
                events + traces into <strong>GHX packets</strong>.
              </li>
              <li>
                <code>ghx_packet_validator.py</code> and{" "}
                <code>ghx_bundle_validator.py</code> check structure, continuity, entropy,
                and safety.
              </li>
            </ul>
          </li>

          <li>
            <strong>GHX → hologram frames</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                <code>hologram_engine.py</code> and{" "}
                <code>hologram_integrator.py</code> turn GHX packets into normalized
                hologram snapshots.
              </li>
              <li>
                <code>holographic_renderer.py</code> +{" "}
                <code>holographic_trigger_controller.py</code> turn those snapshots into
                beams, nodes, and fields the visualization layer can render.
              </li>
              <li>
                <code>ghx_ws_interface.py</code>, <code>ghx_sync_layer.py</code>,{" "}
                <code>ghx_replay_broadcast.py</code> handle WebSocket streaming and replay.
              </li>
            </ul>
          </li>
        </ol>

        <p style={{ margin: "8px 0 0 0" }}>
          Result: a single path from editor text → AST → glyph graph → GHX packet →
          holographic field.
        </p>
      </section>

      {/* 3. Why this is useful */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          3. Why AST → Hologram actually matters
        </h3>

        <h4
          style={{
            margin: "4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          a) Safer, smarter refactors
        </h4>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            Renames and transforms operate on the <strong>tree</strong>, not regex.
          </li>
          <li>
            &quot;Rename this concept everywhere&quot; = walk the AST and glyph graph, not
            <code>grep</code>.
          </li>
          <li>
            Future: “inline this function”, “simplify this condition”, “show all calls
            with shots&nbsp;&gt;&nbsp;1024”.
          </li>
        </ul>

        <h4
          style={{
            margin: "10px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          b) Better search &amp; understanding
        </h4>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            Once code/logs/specs are AST+glyph, you can query semantics, not text:
          </li>
          <li style={{ marginTop: 4 }}>
            “Show me all places we assume <code>A -&gt; B</code>.”
          </li>
          <li>“Where do we call qqc_bridge.run with shots &gt; 1024?”</li>
          <li>“Which nodes entangle this symbol with that predicate?”</li>
        </ul>

        <h4
          style={{
            margin: "10px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          c) Visual debugging &amp; teaching
        </h4>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            <code>ast_viz.py</code> already exports Photon algebra trees to Graphviz /
            Mermaid.
          </li>
          <li>
            The AST API can mirror that for CodexAST: <code>/api/ast/visualize</code>{" "}
            → Mermaid text.
          </li>
          <li>
            You paste code / logic / Photon into Dev Tools → see the{" "}
            <strong>shape</strong> as a graph or hologram.
          </li>
        </ul>

        <h4
          style={{
            margin: "10px 0 4px 0",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          d) One engine across languages
        </h4>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li>
            Python, Photon, CodexLang, and even NL all converge into{" "}
            <code>CodexAST</code> → glyphs → GHX → hologram.
          </li>
          <li>
            That means one visualization + introspection story for{" "}
            <strong>code, specs, logs, and prompts</strong>.
          </li>
        </ul>
      </section>

      {/* 4. How Dev Tools uses this today */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          4. Dev Tools: how to use the AST &amp; Hologram path
        </h3>

        <ol style={{ margin: 0, paddingLeft: 18 }}>
          <li style={{ marginBottom: 6 }}>
            <strong>Open Dev Tools → Text Editor</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>Type Photon, Python, CodexLang, or NL snippets.</li>
              <li>
                Optionally hit <strong>Code → Glyph</strong> to see glyph compression.
              </li>
            </ul>
          </li>
          <li style={{ marginBottom: 6 }}>
            <strong>Click “View as AST”</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                The editor sends <code>{`{ source, language }`}</code> to{" "}
                <code>POST /api/ast</code>.
              </li>
              <li>
                The <strong>AST Inspector</strong> shows:
                <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                  <li>AST JSON (CodexAST view)</li>
                  <li>Glyph list (<code>LogicGlyph</code> graph)</li>
                  <li>Mermaid text (simple flowchart representation)</li>
                </ul>
              </li>
            </ul>
          </li>
          <li>
            <strong>Future: “Visualize as Hologram”</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>
                The AST + glyphs will be wrapped into a GHX bundle and sent through{" "}
                <code>hologram_engine.py</code>.
              </li>
              <li>
                The field is rendered in <strong>QuantumFieldCanvas</strong> /
                GHXVisualizer, driven over WebSocket by <code>ghx_ws_interface.py</code>{" "}
                and <code>ghx_sync_layer.py</code>.
              </li>
              <li>
                You’ll be able to scrub, replay, and branch from AST-derived beams just
                like any other QWave trail.
              </li>
            </ul>
          </li>
        </ol>
      </section>

      {/* 5. Mental model */}
      <section>
        <h3
          style={{
            margin: 0,
            marginBottom: 4,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          5. How to think about it
        </h3>

        <p style={{ margin: 0 }}>
          For a developer, the right mental model is:
        </p>

        <blockquote
          style={{
            margin: "8px 0 0 0",
            padding: "8px 10px",
            borderLeft: "3px solid #e5e7eb",
            background: "#f9fafb",
            borderRadius: 6,
            fontSize: 13,
          }}
        >
          <em>
            &quot;The Dev Tools editor isn&apos;t just a text box. It&apos;s a front
            door into a pipeline that turns everything I write into a graph the machine
            can understand, visualize, and eventually prove things about.&quot;
          </em>
        </blockquote>

        <p style={{ margin: "8px 0 0 0" }}>
          Compression (glyphs, GHX) is the side-effect.
          <br />
          <strong>Symbolic control and visual insight over your codebase is the main
          act.</strong>
        </p>
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
        End of AST → GHX → Hologram Guide.
      </footer>
    </div>
  );
}