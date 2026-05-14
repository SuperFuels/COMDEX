// Glyph_Net_Browser/src/components/DevPitch.tsx
// Developer-facing pitch: why bother converting code/logs to Photon glyphs?

export default function DevPitch() {
  return (
    <div
      style={{
        maxWidth: 840,
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: 16,
        fontSize: 13,
        color: "#111827",
      }}
    >
      <header>
        <h2 style={{ margin: 0, fontSize: 18 }}>Why Convert Your Code to Photon Glyphs?</h2>
        <p
          style={{
            margin: "4px 0 0",
            color: "#4b5563",
          }}
        >
          You&apos;re not just shaving bytes. You&apos;re upgrading how your codebase behaves
          over time.
        </p>
      </header>

      {/* 1. 10% compression */}
      <section
        style={{
          padding: 12,
          borderRadius: 10,
          background: "#ffffff",
          border: "1px solid #e5e7eb",
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: 15 }}>
          1. 10% Compression Sounds Small… Until You Do the Math
        </h3>
        <p style={{ marginTop: 4 }}>
          On a single repo, 10% feels like a nice-to-have:
        </p>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>1 MB → save 0.1 MB</li>
          <li>1 GB → save 100 MB</li>
          <li>10 GB → save 1 GB</li>
          <li>1 TB → save 100 GB</li>
        </ul>

        <p style={{ marginTop: 8 }}>Now apply that to:</p>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>build artifacts</li>
          <li>dependency caches</li>
          <li>logs + traces</li>
          <li>backups and cold storage</li>
        </ul>

        <p style={{ marginTop: 8 }}>
          Every clone, sync, deploy, backup, reindex, restore gets cheaper and faster, forever.
        </p>

        <p style={{ marginTop: 8 }}>And it&apos;s not just disk:</p>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>Less to send over the wire → faster pulls, CI, deploys.</li>
          <li>Less to scan → quicker indexing, search, analytics.</li>
          <li>Less to back up → lower infra cost multiplied over months/years.</li>
        </ul>

        <p style={{ marginTop: 8 }}>
          10% is boring on a single file. It&apos;s not boring on TB-scale histories.
        </p>
      </section>

      {/* 2. Code vs logs */}
      <section
        style={{
          padding: 12,
          borderRadius: 10,
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          display: "grid",
          gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
          gap: 12,
        }}
      >
        <div>
          <h3 style={{ marginTop: 0, fontSize: 15 }}>
            2. Code vs Logs: Where Photon Pays Off
          </h3>
          <h4 style={{ margin: "6px 0 4px", fontSize: 13 }}>
            Source Code (.photon, .ptn, .phn)
          </h4>
          <p style={{ marginTop: 4 }}>
            For code, the raw compression is only half the story:
          </p>
          <ul style={{ marginTop: 4, paddingLeft: 18 }}>
            <li>✅ Modest storage win.</li>
            <li>✅ Real bandwidth win (clones, CI, remote dev).</li>
            <li>✅ But the real value is symbolic.</li>
          </ul>
          <p style={{ marginTop: 8 }}>Photon gives you:</p>
          <ul style={{ marginTop: 4, paddingLeft: 18 }}>
            <li>
              Glyphs as a semantic layer – code becomes a structured, machine-native alphabet.
            </li>
            <li>
              Easier machine reasoning – refactors, analysis, transforms operate on stable glyphs,
              not messy ad-hoc text.
            </li>
            <li>
              A path to AST ↔ glyph IR – think auto-refactors, cross-lang bridges, intelligent
              search, code DNA.
            </li>
          </ul>
          <p style={{ marginTop: 8 }}>
            So: <strong>&quot;10% + richer semantics + importer + tooling&quot;</strong> ≫
            &nbsp;&quot;10% for its own sake&quot;.
          </p>
          <p style={{ marginTop: 4 }}>
            You&apos;re not just compressing Python – you&apos;re lifting it into a format that&apos;s
            easier for tools (and eventually agents) to understand and manipulate.
          </p>
        </div>

        <div>
          <h4 style={{ margin: "0 0 4px", fontSize: 13 }}>Logs / Traces / Events</h4>
          <p style={{ marginTop: 4 }}>
            For logs, 10% is a big deal:
          </p>
          <ul style={{ marginTop: 4, paddingLeft: 18 }}>
            <li>Logs accumulate forever.</li>
            <li>They&apos;re compressed again (gzip/ZSTD) downstream.</li>
            <li>Log infra cost scales almost linearly with bytes.</li>
          </ul>
          <p style={{ marginTop: 8 }}>Native 10% reduction before gzip:</p>
          <ul style={{ marginTop: 4, paddingLeft: 18 }}>
            <li>Compounds with standard compression.</li>
            <li>Lowers ingestion bandwidth (agents → collectors → central store).</li>
            <li>Reduces ongoing cost in S3 / ES / ClickHouse / Loki / &quot;$LOG_VENDOR&quot;.</li>
          </ul>
          <p style={{ marginTop: 8 }}>
            At multi-GB/day or TB/month, 10% is real money + real performance.
          </p>
        </div>
      </section>

      {/* 3. Compounding & symbolic wins */}
      <section
        style={{
          padding: 12,
          borderRadius: 10,
          background: "#ffffff",
          border: "1px solid #e5e7eb",
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: 15 }}>
          3. Compounding &amp; Symbolic Wins Over Time
        </h3>
        <p style={{ marginTop: 4 }}>
          The benefit isn&apos;t &quot;just 10% today&quot; – it&apos;s 10% less of everything,
          forever:
        </p>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>10% less to replicate.</li>
          <li>10% less to re-index.</li>
          <li>10% less to re-hydrate from cold storage.</li>
          <li>10% less to scan for analytics or security.</li>
        </ul>
        <p style={{ marginTop: 8 }}>
          Every operation on your code + logs gets slightly cheaper. Over months and years, that
          compounds hard.
        </p>
        <p style={{ marginTop: 8 }}>
          On top of that, glyph-ification gives you extra levers:
        </p>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>
            Semantic compression – uniform symbols mean better patterns, better clustering.
          </li>
          <li>
            Cross-file / cross-service transforms – rename, refactor, obfuscate, cluster at the
            glyph level.
          </li>
          <li>
            Better downstream compression – once the structure is regularized, traditional
            compressors usually get even better ratios on top.
          </li>
        </ul>
        <p style={{ marginTop: 8 }}>
          In other words, ~10% is actually the floor, not the ceiling.
        </p>
      </section>

      {/* 4. AST + Photon Editor: the real upgrade */}
      <section
        style={{
          padding: 12,
          borderRadius: 10,
          background: "#ffffff",
          border: "1px solid #e5e7eb",
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: 15 }}>
          4. AST + Photon Editor: Your Code as a Graph of Meaning
        </h3>

        <h4 style={{ margin: "6px 0 4px", fontSize: 13 }}>What the AST layer actually is</h4>
        <p style={{ marginTop: 4 }}>
          Think of an AST as <strong>your code, but as a tree of meaning, not a blob of text</strong>.
        </p>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>
            <code>if</code>, <code>and</code>, <code>or</code>, <code>-&gt;</code>, function calls,
            predicates, etc become nodes.
          </li>
          <li>
            Glyphs are just a compact, uniform alphabet for those nodes.
          </li>
          <li>
            Codex / Logic / Photon ASTs are different views over the same underlying structure.
          </li>
        </ul>
        <p style={{ marginTop: 8 }}>
          Instead of treating code as strings, you treat it as a <strong>graph of ideas</strong>.
        </p>

        <h4 style={{ margin: "12px 0 4px", fontSize: 13 }}>
          What wiring the Photon editor into this buys you
        </h4>
        <p style={{ marginTop: 4 }}>
          Today, the Photon editor can take <strong>Python or Photon text → glyphs</strong>.
          Your backend can take <strong>glyphs / CodexLang / NL → AST → LogicGlyph graphs</strong>.
        </p>
        <p style={{ marginTop: 6 }}>
          By connecting those, anything you write in the editor (Python, Photon, CodexLang, NL
          snippets) can be turned into a <strong>structured, symbolic object</strong> the rest of the
          system can reason about.
        </p>
        <p style={{ marginTop: 6 }}>
          That&apos;s the real upgrade. Compression is the side-effect.
        </p>

        <h4 style={{ margin: "12px 0 4px", fontSize: 13 }}>
          Concrete benefits for you as a developer
        </h4>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>
            <strong>Safer, smarter refactors</strong> – renames and transforms can work on meaning,
            not regex. &quot;Rename this concept everywhere&quot; = walk the AST graph, not grep.
          </li>
          <li style={{ marginTop: 4 }}>
            <strong>Better search &amp; understanding</strong> – once code/logs/specs are AST+glyph,
            you can ask things like &quot;show me all places we assume <code>A -&gt; B</code>&quot;
            or &quot;where do we call <code>qqc_bridge.run</code> with <code>shots &gt; 1024</code>
            ?&quot;.
          </li>
          <li style={{ marginTop: 4 }}>
            <strong>Visual debugging &amp; teaching</strong> – use the existing AST visualizers
            (<code>to_dot</code> / <code>to_mermaid</code>) to turn expressions into graphs and
            understand complex flows at a glance.
          </li>
          <li style={{ marginTop: 4 }}>
            <strong>One engine across languages</strong> – Python, Photon, CodexLang, even NL all
            converge into CodexAST / LogicGlyph. One symbolic engine can reason over code, specs,
            logs, and requirements.
          </li>
        </ul>

        <p style={{ marginTop: 8 }}>
          In your head, you can think of it like this:
          <br />
          <em>
            &quot;The Photon editor isn&apos;t just a fancy text box. It&apos;s the front door to a
            system that turns everything I write into a graph the machine can understand, visualize,
            and eventually prove things about.&quot;
          </em>
        </p>
      </section>

      {/* TL;DR */}
      <section
        style={{
          padding: 12,
          borderRadius: 10,
          background: "#eef2ff",
          border: "1px solid #c7d2fe",
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: 15 }}>TL;DR – Why You Should Convert</h3>
        <p style={{ marginTop: 4 }}>
          If you&apos;re thinking:
          <br />
          <em>&quot;Is 10% really worth wiring Photon into my stack?&quot;</em>
        </p>
        <p style={{ marginTop: 4 }}>The answer, at system scale, is yes:</p>
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          <li>
            You get immediate benefits in storage, bandwidth, and log volume.
          </li>
          <li>
            You get a structured, symbolic representation your tools can actually reason about.
          </li>
          <li>
            You keep Python compatibility – the importer makes <code>.photon</code> feel like{" "}
            <code>.py</code>.
          </li>
          <li>
            You&apos;re positioning your codebase for a future where glyph-aware tools/agents can
            optimize, refactor, and analyze code natively.
          </li>
        </ul>
        <p style={{ marginTop: 8 }}>
          Photon isn&apos;t &quot;just a compressor&quot;.
          <br />
          It&apos;s a semantic upgrade path for your code and logs, and the 10%+ space win is your
          first visible symptom of that.
        </p>
      </section>
    </div>
  );
}