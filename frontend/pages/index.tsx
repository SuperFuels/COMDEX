// frontend/pages/index.tsx
"use client";

import type { NextPage } from "next";
import { useMemo, useState } from "react";

type TabId = "glyph_os" | "symatics";

const Home: NextPage = () => {
  const tabs = useMemo(
    () =>
      [
        { id: "glyph_os" as const, label: "Glyph OS" },
        { id: "symatics" as const, label: "Symatics" },
        // add more tabs here later
      ] as const,
    [],
  );

  const [tab, setTab] = useState<TabId>("glyph_os");

  const tabBtn = (id: TabId, label: string) => {
    const active = tab === id;
    return (
      <button
        key={id}
        type="button"
        onClick={() => setTab(id)}
        aria-pressed={active}
        className={[
          "px-4 py-2 rounded-full text-sm font-medium",
          "bg-transparent",
          "hover:bg-black/5 dark:hover:bg-white/10",
          active ? "text-text" : "text-text/60",
        ].join(" ")}
        style={{
          // isolate from your global `button { border: 1px ... }`
          border: "none",
          padding: "0.55rem 1rem",
        }}
      >
        {label}
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-bg-page text-text-primary">
      <main className="min-h-screen flex items-center justify-center px-4">
        <section className="w-full max-w-[980px]">
          {/* Center card */}
          <div
            className="rounded-2xl bg-white dark:bg-gray-800 shadow"
            style={{
              border: "1px solid var(--border-light)",
            }}
          >
            {/* Tabs */}
            <div className="flex items-center justify-center px-4 pt-6">
              <div
                className="inline-flex items-center gap-1 rounded-full"
                style={{
                  border: "1px solid var(--border-light)",
                  background: "transparent",
                  padding: "0.25rem",
                }}
              >
                {tabs.map((t) => tabBtn(t.id, t.label))}
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-8 md:px-10 md:py-10">
              {tab === "glyph_os" && (
                <div className="space-y-6">
                  <div className="space-y-2">
                    <h1 className="text-2xl md:text-3xl font-semibold text-text">
                      Glyph OS
                    </h1>
                    <p className="text-text-secondary">
                      The language of symbols — compressed pipelines that preserve intent with less noise.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div
                      className="rounded-xl p-4"
                      style={{ border: "1px solid var(--border-light)" }}
                    >
                      <div className="text-sm font-semibold text-text mb-2">
                        Traditional (verbose steps)
                      </div>
                      <ul className="text-sm text-text-secondary space-y-1 list-disc pl-5">
                        <li>Get eggs</li>
                        <li>Crack eggs</li>
                        <li>Whisk</li>
                        <li>Heat pan</li>
                        <li>Add butter</li>
                        <li>Cook</li>
                        <li>Plate</li>
                      </ul>
                    </div>

                    <div
                      className="rounded-xl p-4 flex flex-col justify-between"
                      style={{ border: "1px solid var(--border-light)" }}
                    >
                      <div className="text-sm font-semibold text-text mb-2">
                        Glyph OS (compact pipeline)
                      </div>
                      <div className="text-2xl md:text-3xl font-semibold text-text tracking-tight">
                        🥚 → 🍳 → 🍽️
                      </div>
                      <div className="mt-2 text-sm text-text-secondary">
                        Ingredients → Cook → Serve
                      </div>
                    </div>

                    <div
                      className="rounded-xl p-4"
                      style={{ border: "1px solid var(--border-light)" }}
                    >
                      <div className="text-sm font-semibold text-text mb-2">
                        Docs (traditional)
                      </div>
                      <ul className="text-sm text-text-secondary space-y-1 list-disc pl-5">
                        <li>Open document</li>
                        <li>Find key points</li>
                        <li>Pull dates &amp; names</li>
                        <li>Write a clean summary</li>
                        <li>Save it</li>
                      </ul>
                    </div>

                    <div
                      className="rounded-xl p-4 flex flex-col justify-between"
                      style={{ border: "1px solid var(--border-light)" }}
                    >
                      <div className="text-sm font-semibold text-text mb-2">
                        Docs (Glyph OS)
                      </div>
                      <div className="text-2xl md:text-3xl font-semibold text-text tracking-tight">
                        📄 → ✨ → 🗂️
                      </div>
                      <div className="mt-2 text-sm text-text-secondary">
                        Document → Highlights → Filed
                      </div>
                    </div>
                  </div>

                  <div className="text-sm text-text-secondary">
                    <span className="font-semibold text-text">Same result.</span> Less noise.
                  </div>
                </div>
              )}

              {tab === "symatics" && (
                <div className="space-y-6">
                  <div className="space-y-2">
                    <h1 className="text-2xl md:text-3xl font-semibold text-text">
                      Symatics
                    </h1>
                    <p className="text-text-secondary">
                      Start with patterns, not numbers — operators that combine, link, reinforce, lock, and trigger action.
                    </p>
                  </div>

                  <div
                    className="rounded-xl p-5 text-center"
                    style={{ border: "1px solid var(--border-light)" }}
                  >
                    <div className="text-sm font-semibold text-text mb-3">
                      Pattern-first equation
                    </div>
                    <div className="text-3xl md:text-5xl font-semibold text-text">
                      🌊 + 🌊 = 🌊✨
                    </div>
                    <div className="mt-3 text-sm text-text-secondary">
                      Two waves combine into one stronger pattern.
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {[
                      "🌊 Wave — a real pattern",
                      "💡 Photon — a packet of pattern",
                      "⊕ Superpose — combine waves",
                      "↔ Entangle — link waves",
                      "⟲ Resonance — reinforce cycles",
                      "∇ Collapse — lock in a result",
                      "⇒ Trigger — turn into action",
                    ].map((s) => (
                      <div
                        key={s}
                        className="rounded-xl p-4 text-sm text-text"
                        style={{ border: "1px solid var(--border-light)" }}
                      >
                        {s}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Footer / placeholder for more tabs */}
            <div
              className="px-6 py-4 md:px-10 text-xs text-text-secondary"
              style={{ borderTop: "1px solid var(--border-light)" }}
            >
              More modules will appear here as additional tabs.
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Home;