// frontend/tabs/glyph/GlyphOSWorkbench.tsx
"use client";

import { useMemo, useRef, useState } from "react";

type Policy = "deterministic" | "conservative" | "aggressive";

type TraceStep = {
  id: string;
  op: string;
  detail?: string;
  io?: { in?: any; out?: any };
  cost?: number; // arbitrary “compute units”
  ms?: number; // simulated time
};

type DemoPreset = {
  key: string;
  title: string;
  subtitle: string;
  words: {
    nl: string;
    json: string;
  };
  wire: any; // canonical meaning-shape (json)
  run: (policy: Policy) => TraceStep[];
};

function seededRng(seed: number) {
  // deterministic PRNG
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}

function prettyJson(x: any) {
  return JSON.stringify(x, null, 2);
}

function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n));
}

function stepCost(base: number, jitter: number, r: () => number) {
  return Math.round(base + (r() - 0.5) * jitter);
}

function stepMs(base: number, jitter: number, r: () => number) {
  return Math.round(base + (r() - 0.5) * jitter);
}

const PRESETS: readonly DemoPreset[] = [
  {
    key: "doc_intel",
    title: "Document Intelligence",
    subtitle: "Scan → extract → brief → store → notify (with deterministic trace)",
    words: {
      nl: [
        "Open the document.",
        "Identify key entities (people, orgs, dates).",
        "Create a short summary.",
        'Save it into the "Research/Briefs" folder.',
        "Notify me with the summary and a link.",
      ].join("\n"),
      json: prettyJson({
        steps: [
          { tool: "doc.open", args: { id: "$doc" } },
          { tool: "nlp.extract_entities", args: { text: "$doc.text" } },
          { tool: "nlp.summarize", args: { text: "$doc.text", max_tokens: 140 } },
          { tool: "storage.write", args: { path: "Research/Briefs/$doc.id.md", content: "$summary" } },
          { tool: "notify.send", args: { channel: "me", text: "$summary", link: "$path" } },
        ],
      }),
    },
    wire: {
      Π: "doc-intel:v1",
      "→": [
        { ingest: { doc: "$DOC" } },
        {
          "⊕": [
            { extract: { entities: true } },
            { summarize: { style: "brief", limit: 140 } },
          ],
        },
        { store: { path: "Research/Briefs/{doc.id}.md" } },
        { notify: { to: "me", include: ["summary", "link"] } },
        { "∇": { collapse: "policy" } },
      ],
    },
    run: (policy) => {
      const seed = policy === "deterministic" ? 101 : policy === "conservative" ? 202 : 303;
      const r = seededRng(seed);

      const docId = Math.floor(r() * 9000 + 1000).toString(16);
      const textLen = Math.floor(r() * 12000 + 9000);

      const entities = {
        persons: Math.floor(r() * 6 + 6),
        orgs: Math.floor(r() * 6 + 4),
        dates: Math.floor(r() * 10 + 6),
      };

      const summaryLen = Math.floor(r() * 35 + 110);

      const base: TraceStep[] = [
        {
          id: "1",
          op: "Π doc-intel:v1",
          detail: "start",
          io: { in: { $DOC: "paper.pdf" }, out: { run_id: `run_${docId}` } },
          cost: stepCost(6, 2, r),
          ms: stepMs(40, 20, r),
        },
        {
          id: "2",
          op: "ingest(doc)",
          io: { in: { file: "paper.pdf" }, out: { "doc.id": docId, "text.len": textLen } },
          cost: stepCost(18, 6, r),
          ms: stepMs(110, 40, r),
        },
        {
          id: "3a",
          op: "extract(entities)",
          detail: "⊕ parallel",
          io: { in: { "text.len": textLen }, out: entities },
          cost: stepCost(22, 10, r),
          ms: stepMs(140, 60, r),
        },
        {
          id: "3b",
          op: "summarize(brief,140)",
          detail: "⊕ parallel",
          io: { in: { "text.len": textLen }, out: { "summary.len": summaryLen } },
          cost: stepCost(26, 12, r),
          ms: stepMs(180, 70, r),
        },
        {
          id: "4",
          op: "store(path)",
          io: { in: { folder: "Research/Briefs", docId }, out: { path: `Research/Briefs/${docId}.md` } },
          cost: stepCost(10, 4, r),
          ms: stepMs(60, 20, r),
        },
        {
          id: "5",
          op: "notify(me)",
          io: { in: { channel: "me" }, out: { sent: true } },
          cost: stepCost(8, 2, r),
          ms: stepMs(50, 20, r),
        },
      ];

      // collapse/policy tail
      const risk = clamp(Math.round((entities.orgs + entities.persons) * 2 + r() * 8), 8, 42);
      const costTotal = base.reduce((a, s) => a + (s.cost || 0), 0);

      let next_action: string;
      let auto_execute: boolean;

      if (policy === "deterministic") {
        auto_execute = true;
        next_action = "commit";
      } else if (policy === "conservative") {
        auto_execute = costTotal < 90 && risk < 24;
        next_action = auto_execute ? "commit" : "request_approval";
      } else {
        auto_execute = true;
        next_action = "chain_followup";
      }

      const tail: TraceStep[] = [
        {
          id: "6",
          op: "∇ collapse(policy)",
          io: {
            in: { policy, risk, cost_total: costTotal },
            out: { auto_execute, next_action },
          },
          cost: stepCost(5, 2, r),
          ms: stepMs(40, 20, r),
        },
        {
          id: "7",
          op: "result",
          detail: auto_execute
            ? `Brief stored + notification sent. next_action=${next_action}`
            : "Execution paused. next_action=request_approval",
          io: {
            out: {
              stored: true,
              notified: true,
              next_action,
            },
          },
          cost: 0,
          ms: stepMs(20, 10, r),
        },
      ];

      return [...base, ...tail];
    },
  },

  {
    key: "ops_auto",
    title: "Ops Automation",
    subtitle: "Check → decide → page → open incident (policy controls gate)",
    words: {
      nl: [
        "Check the service status.",
        "If degraded, page on-call and open an incident.",
        "Otherwise log and exit.",
      ].join("\n"),
      json: prettyJson({
        steps: [
          { tool: "status.check", args: { service: "glyphnet-api" } },
          { tool: "policy.decide", args: { threshold: "degraded" } },
          { tool: "pager.page", args: { team: "on-call" } },
          { tool: "incident.open", args: { sev: 2 } },
        ],
      }),
    },
    wire: {
      Π: "ops-auto:v1",
      "→": [
        { sense: { service: "glyphnet-api" } },
        { decide: { gate: "policy" } },
        { act: { on: "degraded", then: ["page(on-call)", "open_incident(sev2)"] } },
        { "∇": { collapse: "policy" } },
      ],
    },
    run: (policy) => {
      const seed = policy === "deterministic" ? 111 : policy === "conservative" ? 222 : 333;
      const r = seededRng(seed);

      const statusRoll = r();
      const status = statusRoll > 0.72 ? "degraded" : statusRoll > 0.92 ? "down" : "ok";

      const base: TraceStep[] = [
        { id: "1", op: "Π ops-auto:v1", detail: "start", cost: stepCost(5, 2, r), ms: stepMs(35, 15, r) },
        {
          id: "2",
          op: "sense(status)",
          io: { in: { service: "glyphnet-api" }, out: { status } },
          cost: stepCost(14, 6, r),
          ms: stepMs(95, 35, r),
        },
      ];

      const risk = status === "down" ? 40 : status === "degraded" ? 26 : 8;

      let allow: boolean;
      if (policy === "deterministic") allow = status !== "ok";
      else if (policy === "conservative") allow = status === "down";
      else allow = status !== "ok";

      const tail: TraceStep[] = [
        {
          id: "3",
          op: "decide(gate=policy)",
          io: { in: { policy, status, risk }, out: { allow_actions: allow } },
          cost: stepCost(6, 3, r),
          ms: stepMs(45, 20, r),
        },
      ];

      if (allow && status !== "ok") {
        tail.push(
          {
            id: "4",
            op: "page(on-call)",
            io: { out: { paged: true } },
            cost: stepCost(10, 4, r),
            ms: stepMs(70, 30, r),
          },
          {
            id: "5",
            op: "open_incident(sev2)",
            io: { out: { incident_id: `INC-${Math.floor(r() * 9000 + 1000)}` } },
            cost: stepCost(12, 4, r),
            ms: stepMs(80, 30, r),
          },
        );
      } else {
        tail.push({
          id: "4",
          op: "log",
          detail: status === "ok" ? "status ok → exit" : "policy blocked → request approval",
          io: { out: { status, action: status === "ok" ? "exit" : "request_approval" } },
          cost: stepCost(3, 1, r),
          ms: stepMs(25, 10, r),
        });
      }

      tail.push({
        id: "6",
        op: "∇ collapse(policy)",
        io: { out: { next_action: allow ? "commit" : status === "ok" ? "noop" : "request_approval" } },
        cost: stepCost(4, 2, r),
        ms: stepMs(35, 15, r),
      });

      return [...base, ...tail];
    },
  },

  {
    key: "schedule",
    title: "Scheduling",
    subtitle: "Find slot → propose → send (policy governs outreach)",
    words: {
      nl: [
        "Find a 30-minute slot next week.",
        "Propose 3 options.",
        "Send them to Sarah.",
      ].join("\n"),
      json: prettyJson({
        steps: [
          { tool: "calendar.find_slots", args: { duration_min: 30, window: "next_week" } },
          { tool: "calendar.pick", args: { count: 3 } },
          { tool: "email.send", args: { to: "sarah", template: "propose_times" } },
        ],
      }),
    },
    wire: {
      Π: "schedule:v1",
      "→": [
        { query: { calendar: "primary", window: "next_week", duration: "30m" } },
        { select: { count: 3 } },
        { notify: { to: "sarah", channel: "email" } },
        { "∇": { collapse: "policy" } },
      ],
    },
    run: (policy) => {
      const seed = policy === "deterministic" ? 121 : policy === "conservative" ? 242 : 363;
      const r = seededRng(seed);

      const slots = Array.from({ length: 7 }, (_, i) => ({
        day: `D+${i + 1}`,
        times: Math.floor(r() * 4 + 1),
      }));
      const picks = slots
        .filter((s) => s.times > 1)
        .slice(0, 3)
        .map((s, idx) => `${s.day} • ${["10:00", "11:30", "14:00"][idx]}`);

      const base: TraceStep[] = [
        { id: "1", op: "Π schedule:v1", detail: "start", cost: stepCost(5, 2, r), ms: stepMs(30, 15, r) },
        {
          id: "2",
          op: "query(calendar)",
          io: { in: { window: "next_week", duration: "30m" }, out: { candidates: slots } },
          cost: stepCost(16, 7, r),
          ms: stepMs(110, 45, r),
        },
        {
          id: "3",
          op: "select(3)",
          io: { out: { proposals: picks.length ? picks : ["(no slots found)"] } },
          cost: stepCost(8, 3, r),
          ms: stepMs(55, 20, r),
        },
      ];

      const risk = 18; // outreach-ish
      const allowSend = policy !== "conservative"; // conservative asks approval before emailing

      const tail: TraceStep[] = [
        {
          id: "4",
          op: "notify(email)",
          io: { in: { to: "sarah" }, out: { sent: allowSend } },
          cost: stepCost(10, 4, r),
          ms: stepMs(80, 30, r),
        },
        {
          id: "5",
          op: "∇ collapse(policy)",
          io: {
            in: { policy, risk },
            out: { next_action: allowSend ? "commit" : "request_approval" },
          },
          cost: stepCost(4, 2, r),
          ms: stepMs(35, 15, r),
        },
      ];

      return [...base, ...tail];
    },
  },
] as const;

function Pill({
  active,
  children,
  onClick,
}: {
  active?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 rounded-full text-xs font-semibold transition-all border ${
        active
          ? "bg-[#0071e3] text-white border-[#0071e3] shadow-sm"
          : "bg-white/70 text-gray-600 border-gray-200 hover:text-black"
      }`}
    >
      {children}
    </button>
  );
}

function CodePane({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[2rem] border border-gray-100 bg-white overflow-hidden shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100 flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-bold text-gray-800">{title}</div>
          {subtitle ? <div className="text-xs text-gray-400 mt-1">{subtitle}</div> : null}
        </div>
      </div>
      <div className="bg-[#fafafa]">{children}</div>
    </div>
  );
}

function MonoBlock({
  text,
  linesMin = 12,
}: {
  text: string;
  linesMin?: number;
}) {
  const lines = Math.max(linesMin, text.split("\n").length);
  return (
    <div className="flex font-mono text-[13px] leading-6">
      <div className="select-none text-right text-gray-300 bg-white/40 border-r border-gray-100 px-4 py-4 min-w-[3rem]">
        {Array.from({ length: lines }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      <pre className="flex-1 whitespace-pre-wrap break-words px-4 py-4 text-gray-800">{text}</pre>
    </div>
  );
}

function TraceView({
  steps,
  animKey,
  running,
}: {
  steps: TraceStep[];
  animKey: number;
  running: boolean;
}) {
  // CSS-only “stagger” via inline style (no external libs)
  return (
    <div key={animKey} className="p-5 md:p-6 space-y-3">
      {steps.length === 0 ? (
        <div className="text-sm text-gray-400 py-10 text-center">
          Press <span className="font-semibold text-gray-600">Run</span> to generate a deterministic trace.
        </div>
      ) : (
        steps.map((s, idx) => {
          const delay = Math.min(0.06 * idx, 0.8);
          return (
            <div
              key={s.id}
              className={`rounded-2xl border border-gray-100 bg-white shadow-sm px-5 py-4 ${
                running ? "opacity-0 animate-in fade-in slide-in-from-bottom-2" : ""
              }`}
              style={running ? ({ animationDelay: `${delay}s` } as any) : undefined}
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">{s.id}</div>
                  <div className="text-sm font-semibold text-gray-800">{s.op}</div>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-gray-400 font-bold">
                  {typeof s.cost === "number" ? <span>{s.cost} cu</span> : null}
                  {typeof s.ms === "number" ? <span>{s.ms} ms</span> : null}
                </div>
              </div>

              {s.detail ? <div className="text-xs text-gray-500 mt-2">{s.detail}</div> : null}

              {s.io ? (
                <div className="mt-3 grid md:grid-cols-2 gap-3">
                  <div className="rounded-xl bg-[#fafafa] border border-gray-100 p-3">
                    <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-2">
                      in
                    </div>
                    <pre className="font-mono text-[11px] leading-5 text-gray-700 whitespace-pre-wrap break-words">
                      {s.io.in ? JSON.stringify(s.io.in, null, 2) : "—"}
                    </pre>
                  </div>
                  <div className="rounded-xl bg-[#fafafa] border border-gray-100 p-3">
                    <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-2">
                      out
                    </div>
                    <pre className="font-mono text-[11px] leading-5 text-gray-700 whitespace-pre-wrap break-words">
                      {s.io.out ? JSON.stringify(s.io.out, null, 2) : "—"}
                    </pre>
                  </div>
                </div>
              ) : null}
            </div>
          );
        })
      )}
    </div>
  );
}

export default function GlyphOSWorkbench() {
  const [presetKey, setPresetKey] = useState(PRESETS[0].key);
  const [policy, setPolicy] = useState<Policy>("deterministic");
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [animKey, setAnimKey] = useState(0);
  const [running, setRunning] = useState(false);

  const preset = useMemo(
    () => PRESETS.find((p) => p.key === presetKey) || PRESETS[0],
    [presetKey],
  );

  const lastRunRef = useRef<{ presetKey: string; policy: Policy } | null>(null);

  const run = () => {
    setRunning(true);
    const steps = preset.run(policy);
    setTrace(steps);
    setAnimKey((k) => k + 1);
    lastRunRef.current = { presetKey, policy };

    // stop “running” after animation finishes
    window.setTimeout(() => setRunning(false), 950);
  };

  const replay = () => {
    // Replay the most recent run with same preset+policy for deterministic feel.
    const last = lastRunRef.current;
    if (!last) return run();

    setRunning(true);
    const p = PRESETS.find((x) => x.key === last.presetKey) || PRESETS[0];
    const steps = p.run(last.policy);
    setTrace(steps);
    setAnimKey((k) => k + 1);

    window.setTimeout(() => setRunning(false), 950);
  };

  const wireText = useMemo(() => prettyJson(preset.wire), [preset.wire]);

  return (
    <section className="space-y-10">
      <div className="text-center space-y-5">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Glyph OS</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Compressed <span className="text-black font-medium">meaning</span>. Deterministic{" "}
          <span className="text-black font-medium">execution</span>.
        </p>
        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
          Intent → Glyph-wire (canonical meaning-shape) → deterministic trace → next action (policy).
        </p>
      </div>

      {/* Preset picker */}
      <div className="bg-white rounded-[2.5rem] border border-gray-100 shadow-xl shadow-gray-200/50 p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div>
            <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Demo presets</div>
            <div className="text-xl font-semibold text-gray-800 mt-2">{preset.title}</div>
            <div className="text-sm text-gray-500 mt-1">{preset.subtitle}</div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {PRESETS.map((p) => (
              <Pill key={p.key} active={p.key === presetKey} onClick={() => setPresetKey(p.key)}>
                {p.title}
              </Pill>
            ))}
          </div>
        </div>

        <div className="mt-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mr-2">Policy</div>
            <Pill active={policy === "deterministic"} onClick={() => setPolicy("deterministic")}>
              Deterministic
            </Pill>
            <Pill active={policy === "conservative"} onClick={() => setPolicy("conservative")}>
              Conservative
            </Pill>
            <Pill active={policy === "aggressive"} onClick={() => setPolicy("aggressive")}>
              Aggressive
            </Pill>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={replay}
              className="px-6 py-2.5 rounded-full text-sm font-semibold bg-white border border-gray-200 text-gray-700 hover:text-black hover:shadow-sm transition"
            >
              Replay
            </button>
            <button
              type="button"
              onClick={run}
              className="px-8 py-2.5 rounded-full text-sm font-semibold bg-[#0071e3] text-white shadow-md hover:brightness-110 transition"
            >
              Run
            </button>
          </div>
        </div>
      </div>

      {/* 3-pane core */}
      <div className="grid lg:grid-cols-3 gap-8">
        <CodePane title="Words" subtitle="Verbose intent (what most systems require)">
          <div className="p-6 space-y-4">
            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Natural language</div>
              </div>
              <MonoBlock text={preset.words.nl} linesMin={10} />
            </div>

            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Typical pipeline JSON</div>
              </div>
              <MonoBlock text={preset.words.json} linesMin={14} />
            </div>
          </div>
        </CodePane>

        <CodePane title="Glyph-wire" subtitle="Canonical meaning-shape (portable + stable)">
          <div className="p-6 space-y-4">
            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Wire format</div>
                <div className="text-[10px] text-[#0071e3] font-bold uppercase tracking-widest">
                  small • stable • replayable
                </div>
              </div>
              <MonoBlock text={wireText} linesMin={22} />
            </div>

            <div className="rounded-2xl bg-blue-50/60 border border-blue-100 p-4">
              <div className="text-xs font-bold text-gray-500 uppercase tracking-widest">Why this matters</div>
              <div className="mt-2 text-sm text-gray-600 leading-relaxed">
                This isn’t “shorter text.” It’s a compact, deterministic meaning-shape that can be executed, audited,
                replayed, and governed by policy.
              </div>
            </div>
          </div>
        </CodePane>

        <CodePane title="Trace" subtitle="Deterministic execution + audit trail">
          <TraceView steps={trace} animKey={animKey} running={running} />
        </CodePane>
      </div>
    </section>
  );
}