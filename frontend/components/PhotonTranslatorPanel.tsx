// =====================================================
// 🌊 Photon → Glyph Translator Panel (SCI IDE Integrated)
// =====================================================
"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

export default function PhotonTranslatorPanel({
  input,
  translation,
}: {
  input?: string;
  translation?: string;
}) {
  // --------------------------------------------------
  // 🧠 Local + Prop-Linked State
  // --------------------------------------------------
  const [inputValue, setInputValue] = useState(
    input || "container_id = wave ⊕ resonance"
  );
  const [output, setOutput] = useState(translation || "");
  const [live, setLive] = useState(true);
  const [loading, setLoading] = useState(false);

  // Sync with external prop updates (from SCI editor)
  useEffect(() => {
    if (input !== undefined) setInputValue(input);
  }, [input]);

  useEffect(() => {
    if (translation !== undefined) setOutput(translation);
  }, [translation]);

  // --------------------------------------------------
  // 🔁 Fetch translation from backend
  // --------------------------------------------------
  async function translateLine(text: string) {
    if (!text.trim()) {
      setOutput("");
      return;
    }

    try {
      setLoading(true);
      const res = await fetch("/api/photon/translate_block", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: text }),
      });

      const data = await res.json();
      const translated = data.translated || data.output || "⚠️ Translation error";
      setOutput(translated);

      // 🌀 Trigger PhotonLensOverlay animation
      window.dispatchEvent(
        new CustomEvent("photon:run", { detail: { source: translated } })
      );
    } catch (err) {
      console.error("Translation error:", err);
      setOutput("⚠️ Translation failed");
    } finally {
      setLoading(false);
    }
  }

  // --------------------------------------------------
  // 💫 Live Translation Effect
  // --------------------------------------------------
  useEffect(() => {
    if (live) {
      const delay = setTimeout(() => translateLine(inputValue), 350);
      return () => clearTimeout(delay);
    }
  }, [inputValue, live]);

  // --------------------------------------------------
  // 🧩 UI
  // --------------------------------------------------
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
      {/* Left Panel — Human Plane */}
      <Card className="shadow-lg border border-gray-800 bg-black/60 text-white backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-xl">🧠 Human Plane</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="w-full h-48 bg-zinc-900 text-zinc-100 border border-zinc-700 rounded-lg p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />

          <div className="flex items-center justify-between mt-3">
            {/* Mode Toggle */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setLive(!live)}
                className={`px-3 py-1.5 text-sm rounded-md border transition ${
                  live
                    ? "bg-green-700 border-green-600 text-white"
                    : "bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700"
                }`}
              >
                {live ? "🟢 Live" : "⚫ Manual"}
              </button>
              <span className="text-sm text-zinc-300">Translate mode</span>
            </div>

            {/* Manual Translate Button */}
            {!live && (
              <Button
                onClick={() => translateLine(inputValue)}
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-1.5 rounded-md"
              >
                {loading ? "Translating…" : "Translate"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Right Panel — Glyph Plane */}
      <Card className="shadow-lg border border-gray-800 bg-gradient-to-br from-zinc-900 to-black text-white backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-xl">🌊 Glyph Plane</CardTitle>
        </CardHeader>
        <CardContent>
          <motion.pre
            key={output}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="w-full h-48 overflow-y-auto bg-zinc-950 text-lime-300 border border-zinc-800 rounded-lg p-3 font-mono text-sm"
          >
            {output || "…"}
          </motion.pre>
        </CardContent>
      </Card>
    </div>
  );
}