"use client";

import { useEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const smooth01 = (t: number) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));
const seg = (t: number, a: number, b: number) => clamp01((t - a) / Math.max(1e-6, b - a));

function fadeInOut(t: number, a0: number, a1: number, fade = 1.1) {
  const fin = smooth01(seg(t, a0, a0 + fade));
  const fout = 1 - smooth01(seg(t, a1 - fade, a1));
  return clamp01(fin * fout);
}

const FONT =
  "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";

function Panel({
  title,
  subtitle,
  lines,
  footer,
  accent,
  height,
  fontScale = 1,
}: {
  title: string;
  subtitle: string;
  lines: string[];
  footer: string;
  accent: string;
  height: number;
  fontScale?: number;
}) {
  return (
    <div
      style={{
        width: 520,
        height,
        padding: "14px 16px 12px",
        borderRadius: 18,
        border: "1px solid rgba(148,163,184,0.22)",
        background: "rgba(2,6,23,0.62)",
        color: "rgba(226,232,240,0.92)",
        fontFamily: FONT,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontWeight: 1000, fontSize: 18 * fontScale }}>{title}</div>
        <div style={{ fontSize: 14 * fontScale, opacity: 0.78 }}>{subtitle}</div>
      </div>

      <div style={{ marginTop: 12, borderTop: `1px solid ${accent}`, opacity: 0.85 }} />

      <div style={{ marginTop: 14, fontSize: 16 * fontScale, lineHeight: 1.38, flex: 1 }}>
        {lines.map((s, i) => (
          <div key={i} style={{ display: "flex", gap: 12, padding: "6px 0" }}>
            <span style={{ opacity: 0.55 }}>{String(i + 1).padStart(2, "0")}.</span>
            <span style={{ opacity: 0.98 }}>{s}</span>
          </div>
        ))}
      </div>

      <div style={{ borderTop: "1px solid rgba(148,163,184,0.18)" }} />
      <div style={{ marginTop: 12, fontSize: 16 * fontScale, fontWeight: 1000 }}>{footer}</div>
    </div>
  );
}

function GlyphPanel({
  title,
  rightGlyph,
  rightLabels,
  height,
  glyphSize = 56,
  fontScale = 1,
}: {
  title: string;
  rightGlyph: string;
  rightLabels: string;
  height: number;
  glyphSize?: number;
  fontScale?: number;
}) {
  const pulse = 0.5 + 0.5 * Math.sin(performance.now() * 0.0032);

  return (
    <div
      style={{
        width: 520,
        height,
        padding: "14px 16px 12px",
        borderRadius: 18,
        border: "1px solid rgba(148,163,184,0.22)",
        background: "rgba(2,6,23,0.62)",
        color: "rgba(226,232,240,0.92)",
        fontFamily: FONT,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontWeight: 1000, fontSize: 18 * fontScale }}>{title}</div>
        <div style={{ fontSize: 14 * fontScale, opacity: 0.78 }}>Tiny signal</div>
      </div>

      <div style={{ marginTop: 12, borderTop: "1px solid rgba(56,189,248,0.45)", opacity: 0.85 }} />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div
          style={{
            fontSize: glyphSize,
            fontWeight: 1000,
            textAlign: "center",
            letterSpacing: 0.8,
            filter: `drop-shadow(0 0 18px rgba(251,191,36,${0.20 + 0.18 * pulse}))`,
          }}
        >
          {rightGlyph}
        </div>

        <div style={{ marginTop: 12, textAlign: "center", fontSize: 16 * fontScale, opacity: 0.92 }}>
          {rightLabels}
        </div>
      </div>

      <div style={{ borderTop: "1px solid rgba(148,163,184,0.18)" }} />
      <div style={{ marginTop: 10, fontSize: 16 * fontScale, fontWeight: 1000, textAlign: "center" }}>
        Same result. Less noise.
      </div>
    </div>
  );
}

function VsCard({
  alpha,
  leftTitle,
  leftSubtitle,
  leftLines,
  rightTitle,
  rightGlyph,
  rightLabels,
  panelHeight,
  glyphSize,
  fontScale,
}: {
  alpha: number;
  leftTitle: string;
  leftSubtitle: string;
  leftLines: string[];
  rightTitle: string;
  rightGlyph: string;
  rightLabels: string;
  panelHeight: number;
  glyphSize: number;
  fontScale: number;
}) {
  return (
    <div
      style={{
        width: "min(1480px, 95vw)",
        padding: "22px 22px 20px",
        borderRadius: 22,
        border: "1px solid rgba(148,163,184,0.22)",
        background: "rgba(2,6,23,0.58)",
        opacity: alpha,
        transform: `translateY(${(1 - alpha) * 10}px)`,
      }}
    >
      <div style={{ display: "flex", gap: 20, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
        <Panel
          title={leftTitle}
          subtitle={leftSubtitle}
          lines={leftLines}
          footer="Same result."
          accent="rgba(248,113,113,0.35)"
          height={panelHeight}
          fontScale={fontScale}
        />

        <div
          style={{
            width: 80,
            textAlign: "center",
            fontFamily: FONT,
            fontWeight: 1000,
            fontSize: 22 * fontScale,
            color: "rgba(226,232,240,0.9)",
            opacity: 0.92,
          }}
        >
          VS
        </div>

        <GlyphPanel
          title={rightTitle}
          rightGlyph={rightGlyph}
          rightLabels={rightLabels}
          height={panelHeight}
          glyphSize={glyphSize}
          fontScale={fontScale}
        />
      </div>
    </div>
  );
}

function Card({
  children,
  alpha,
  width = "min(1180px, 94vw)",
  bg = "rgba(2,6,23,0.72)",
  pad = "14px 16px 12px",
}: {
  children: React.ReactNode;
  alpha: number;
  width?: string;
  bg?: string;
  pad?: string;
}) {
  return (
    <div
      style={{
        position: "fixed",
        left: "50%",
        top: "50%",
        width,
        maxHeight: "76vh",
        transform: `translate(-50%, -50%) translateY(${(1 - alpha) * 10}px)`,
        opacity: alpha,
        pointerEvents: "none",
        borderRadius: 22,
        border: "1px solid rgba(148,163,184,0.22)",
        background: bg,
        padding: pad,
        color: "rgba(248,250,252,0.96)",
        fontFamily: FONT,
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

export default function QFCDemoGlyphOS({ frame }: { frame: any }) {
  const tRef = useRef(0);
  const [paused, setPaused] = useState(false);

  // Glyph OS block (4 scenes)
  const G0 = [0, 8] as const; // Glyph OS title
  const G1 = [8, 18] as const; // Hello Multiverse
  const G2 = [18, 28] as const; // VS cooking
  const G3 = [28, 38] as const; // VS docs

  // Symatics block (4 scenes now)
  const S0 = [38, 48] as const; // Symatics title
  const S1 = [48, 58] as const; // Traditional math story
  const S2 = [58, 66] as const; // Symatics equation ONLY
  const S3 = [66, 76] as const; // Symatics “super powers” ONLY

  const END = S3[1];

  const jumpTo = (s: number) => (tRef.current = s);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        setPaused((p) => !p);
      }
      if (e.key === "1") jumpTo(G0[0]);
      if (e.key === "2") jumpTo(G1[0]);
      if (e.key === "3") jumpTo(G2[0]);
      if (e.key === "4") jumpTo(G3[0]);
      if (e.key === "5") jumpTo(S0[0]);
      if (e.key === "6") jumpTo(S1[0]);
      if (e.key === "7") jumpTo(S2[0]);
      if (e.key === "8") jumpTo(S3[0]);
      if (e.key.toLowerCase() === "r") jumpTo(0);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useFrame((_s, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    if (!paused) tRef.current += dtc;
    if (tRef.current > END) tRef.current = END;
  });

  const t = tRef.current;

  const aG0 = fadeInOut(t, G0[0], G0[1], 1.2);
  const aG1 = fadeInOut(t, G1[0], G1[1], 1.2);
  const aG2 = fadeInOut(t, G2[0], G2[1], 1.2);
  const aG3 = fadeInOut(t, G3[0], G3[1], 1.2);

  const aS0 = fadeInOut(t, S0[0], S0[1], 1.2);
  const aS1 = fadeInOut(t, S1[0], S1[1], 1.2);
  const aS2 = fadeInOut(t, S2[0], S2[1], 1.2);
  const aS3 = fadeInOut(t, S3[0], S3[1], 1.2);

  const cookingTraditional = ["Get eggs", "Crack eggs", "Whisk", "Heat pan", "Add butter", "Cook", "Plate"];
  const docsTraditional = ["Open document", "Find key points", "Pull dates & names", "Write a clean summary", "Save it"];

  const tradMathLines = ["Counting sheep → 1, 2, 3…", "Numbers: 0–9", "Operators: +  −  ×  ÷", "Great for: “how many”"];

  const symPowers = [
    "🌊 Wave — a real pattern",
    "💡 Photon — a packet of pattern",
    "⊕ Superpose — combine waves",
    "↔ Entangle — link waves",
    "⟲ Resonance — reinforce cycles",
    "∇ Collapse — lock in a result",
    "⇒ Trigger — turn into action",
  ];

  const PANEL_H = 420;
  const FONT_SCALE = 1.15;
  const GLYPH_SIZE = 64;

  return (
    <group>
      <DreiHtml fullscreen>
        <div style={{ position: "fixed", inset: 0, pointerEvents: "none" }}>
          {/* HUD bottom-right */}
          <div
            style={{
              position: "fixed",
              right: 18,
              bottom: 18,
              width: 520,
              padding: "12px 14px",
              borderRadius: 14,
              border: "1px solid rgba(148,163,184,0.22)",
              background: "rgba(2,6,23,0.62)",
              color: "rgba(226,232,240,0.90)",
              fontFamily: FONT,
              fontSize: 12,
              lineHeight: 1.25,
              opacity: 0.92,
            }}
          >
            <div style={{ fontWeight: 1000, marginBottom: 6 }}>Demo Controls</div>
            <div style={{ opacity: 0.9 }}>
              SPACE: pause/play · 1–4: Glyph OS · 5–8: Symatics · R: restart
            </div>
          </div>

          {/* CENTER STAGE */}
          <div
            style={{
              position: "fixed",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 18,
            }}
          >
            {/* G0 — Glyph OS title */}
            <div
              style={{
                position: "absolute",
                width: "min(1220px, 94vw)",
                height: "min(320px, 42vh)",
                padding: "34px 26px",
                borderRadius: 22,
                border: "1px solid rgba(148,163,184,0.22)",
                background: "rgba(2,6,23,0.72)",
                opacity: aG0,
                transform: `translateY(${(1 - aG0) * 10}px)`,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
              }}
            >
              <div
                style={{
                  fontFamily: FONT,
                  color: "rgba(226,232,240,0.97)",
                  fontWeight: 1000,
                  fontSize: 82,
                  letterSpacing: 1.2,
                  textAlign: "center",
                  lineHeight: 1.0,
                }}
              >
                Glyph OS
              </div>

              <div
                style={{
                  marginTop: 14,
                  textAlign: "center",
                  color: "rgba(226,232,240,0.88)",
                  fontFamily: FONT,
                  fontSize: 20,
                  fontWeight: 900,
                }}
              >
                The Language of Symbols. The Speed of Light.
              </div>

              <div
                style={{
                  marginTop: 14,
                  textAlign: "center",
                  color: "rgba(226,232,240,0.82)",
                  fontFamily: FONT,
                  fontSize: 16,
                  fontWeight: 800,
                  opacity: 0.95,
                }}
              >
                An operating system built in symbols, executes at the speed of light, compressed for AI.....
              </div>
            </div>

            {/* G1 — Hello Multiverse */}
            <div
              style={{
                position: "absolute",
                width: "min(1220px, 94vw)",
                padding: "30px 22px",
                borderRadius: 22,
                border: "1px solid rgba(148,163,184,0.22)",
                background: "rgba(2,6,23,0.60)",
                opacity: aG1,
                transform: `translateY(${(1 - aG1) * 10}px)`,
              }}
            >
              <div style={{ textAlign: "center", fontFamily: FONT }}>
                <div style={{ fontSize: 56, fontWeight: 1000, color: "rgba(226,232,240,0.96)" }}>
                  Hello Multiverse
                </div>

                <div
                  style={{
                    marginTop: 10,
                    fontSize: 64,
                    fontWeight: 1000,
                    color: "rgba(255,255,255,0.98)",
                    textShadow: "0 0 18px rgba(255,255,255,0.18)",
                  }}
                >
                  ＝
                </div>

                <div style={{ marginTop: 12, fontSize: 78, fontWeight: 1000 }}>👋 🌐</div>
              </div>
            </div>

            {/* G2 — VS Cooking */}
            <div style={{ position: "absolute" }}>
              <VsCard
                alpha={aG2}
                leftTitle="Traditional way"
                leftSubtitle="Paragraph of steps"
                leftLines={cookingTraditional}
                rightTitle="Glyph OS way"
                rightGlyph={"🥚  →  🍳  →  🍽️"}
                rightLabels={"Ingredients → Cook → Serve"}
                panelHeight={PANEL_H}
                glyphSize={GLYPH_SIZE}
                fontScale={FONT_SCALE}
              />
            </div>

            {/* G3 — VS Docs */}
            <div style={{ position: "absolute" }}>
              <VsCard
                alpha={aG3}
                leftTitle="Traditional way"
                leftSubtitle="Paragraph of steps"
                leftLines={docsTraditional}
                rightTitle="Glyph OS way"
                rightGlyph={"📄  →  ✨  →  🗂️"}
                rightLabels={"Document → Highlights → Filed"}
                panelHeight={PANEL_H}
                glyphSize={GLYPH_SIZE}
                fontScale={FONT_SCALE}
              />
            </div>

            {/* S0 — SYMATICS title */}
            <div
              style={{
                position: "absolute",
                width: "min(1220px, 94vw)",
                height: "min(320px, 42vh)",
                padding: "34px 26px",
                borderRadius: 22,
                border: "1px solid rgba(148,163,184,0.22)",
                background: "rgba(2,6,23,0.72)",
                opacity: aS0,
                transform: `translateY(${(1 - aS0) * 10}px)`,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
              }}
            >
              <div
                style={{
                  fontFamily: FONT,
                  color: "rgba(226,232,240,0.97)",
                  fontWeight: 1000,
                  fontSize: 82,
                  letterSpacing: 1.2,
                  textAlign: "center",
                  lineHeight: 1.0,
                }}
              >
                SYMATICS
              </div>

              <div
                style={{
                  marginTop: 14,
                  textAlign: "center",
                  color: "rgba(226,232,240,0.88)",
                  fontFamily: FONT,
                  fontSize: 20,
                  fontWeight: 900,
                }}
              >
                Tessaris AI discovered the missing mathematics.
              </div>

              <div
                style={{
                  marginTop: 14,
                  textAlign: "center",
                  color: "rgba(226,232,240,0.86)",
                  fontFamily: FONT,
                  fontSize: 18,
                  fontWeight: 900,
                }}
              >
                So why can’t we calculate how the universe works?
              </div>
            </div>

            {/* S1 — Traditional math story */}
            <div style={{ position: "absolute" }}>
              <VsCard
                alpha={aS1}
                leftTitle="A person in a field"
                leftSubtitle="Counting sheep"
                leftLines={tradMathLines}
                rightTitle="Traditional math"
                rightGlyph={"0 1 2 3 4 5 6 7 8 9"}
                rightLabels={"+  −  ×  ÷"}
                panelHeight={PANEL_H}
                glyphSize={52}
                fontScale={FONT_SCALE}
              />
            </div>

            {/* S2 — Equation ONLY */}
            <Card alpha={aS2} bg="rgba(2,6,23,0.72)" pad="18px 18px 16px">
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 34, fontWeight: 1000, letterSpacing: 0.8 }}>Start with patterns, not numbers.</div>

                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 52, fontWeight: 1000 }}>🌊&nbsp;&nbsp;+&nbsp;&nbsp;🌊</div>

                  <div
                    style={{
                      marginTop: 6,
                      fontSize: 44,
                      fontWeight: 1000,
                      color: "rgba(255,255,255,0.98)",
                      textShadow: "0 0 14px rgba(255,255,255,0.14)",
                    }}
                  >
                    ＝
                  </div>

                  <div style={{ marginTop: 8, fontSize: 52, fontWeight: 1000 }}>🌊✨</div>

                  <div style={{ marginTop: 12, fontSize: 18, fontWeight: 900, opacity: 0.92 }}>
                    Two waves combine into one stronger pattern.
                  </div>
                </div>
              </div>
            </Card>

            {/* S3 — Super powers ONLY */}
            <Card alpha={aS3} bg="rgba(2,6,23,0.62)" pad="16px 16px 14px">
              <div style={{ fontSize: 20, fontWeight: 1000, opacity: 0.96, marginBottom: 12 }}>
                Symatics “super powers”
              </div>

              <div
                style={{
                  maxHeight: "min(56vh, 520px)",
                  overflow: "auto",
                  paddingRight: 6,
                }}
              >
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: 10,
                    fontSize: 18,
                    lineHeight: 1.35,
                  }}
                >
                  {symPowers.map((s, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "12px 14px",
                        borderRadius: 14,
                        border: "1px solid rgba(148,163,184,0.18)",
                        background: "rgba(2,6,23,0.40)",
                        color: "rgba(248,250,252,0.94)",
                        fontWeight: 900,
                      }}
                    >
                      {s}
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </DreiHtml>
    </group>
  );
}
