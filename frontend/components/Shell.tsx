// frontend/components/Shell.tsx
"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/router";
import TabDock, { type TabDef } from "./TabDock";

const TABS: readonly TabDef[] = [
  { key: "glyph", label: "Glyph OS", href: "/glyph" },
  { key: "symatics", label: "Symatics", href: "/symatics" },
  { key: "compression", label: "Compression", href: "/compression" },
  { key: "data", label: "Data", href: "/data" },
  { key: "sqi", label: "SQI", href: "/sqi" },
  { key: "photon_algebra", label: "Photon Algebra", href: "/photon-algebra" },
  { key: "photon_binary", label: "Photon Binary", href: "/photon-binary" },
  { key: "glyph_net", label: "Glyph Net", href: "/glyph-net" },
  { key: "toe", label: "Theory Of Everything", href: "/toe" },
  { key: "multiverse", label: "Multiverse", href: "/multiverse" },
  { key: "glyph_chain", label: "Glyph Chain", href: "/glyph-chain" },
  { key: "ptn", label: ".ptn", href: "/ptn" },
  { key: "photon", label: "Photon", href: "/photon" },
  { key: "ai", label: "AI", href: "/ai" },
];

function getActiveKeyFromPath(pathname: string): string {
  const p = pathname.split("?")[0].split("#")[0];

  const exact = TABS.find((t) => t.href === p);
  if (exact) return exact.key;

  const nested = TABS
    .slice()
    .sort((a, b) => b.href.length - a.href.length)
    .find((t) => t.href !== "/" && p.startsWith(t.href + "/"));
  if (nested) return nested.key;

  if (p === "/") return "glyph";
  return "glyph";
}

type MaxWidthClass =
  | "max-w-5xl"
  | "max-w-6xl"
  | "max-w-7xl"
  | "max-w-screen-xl"
  | `max-w-[${string}]`;

export default function Shell({
  children,
  activeKey,
  hideHud = false,
  className = "",
  maxWidth = "max-w-7xl", // ✅ sensible default: fixes squashed panels
}: {
  children: ReactNode;
  activeKey?: string;
  hideHud?: boolean;
  className?: string;
  maxWidth?: MaxWidthClass;
}) {
  const router = useRouter();
  const derivedKey = getActiveKeyFromPath(router.asPath || router.pathname || "/");
  const key = activeKey || derivedKey;

  return (
    <div
      className={`min-h-screen bg-[#f5f5f7] text-[#1d1d1f] selection:bg-blue-100 font-sans antialiased ${className}`}
    >
      <div className="h-screen overflow-y-auto">
        <main
          className={`relative z-10 flex flex-col items-center justify-start min-h-full px-6 ${maxWidth} mx-auto py-16 pb-32`}
        >
          <TabDock tabs={TABS} activeKey={key} />

          <div className="w-full">
            <div key={key} className="animate-tab-change">
              {children}
            </div>
          </div>

          <footer className="mt-24 flex gap-6">
            <button className="px-12 py-4 bg-black text-white rounded-full font-semibold text-lg hover:bg-gray-800 transition-all">
              Launch GlyphNet
            </button>
            <button className="px-12 py-4 border-2 border-black text-black rounded-full font-semibold text-lg hover:bg-black hover:text-white transition-all">
              View Multiverse
            </button>
          </footer>
        </main>
      </div>

      {!hideHud && (
        <div className="fixed bottom-8 right-8 p-4 bg-white/80 border border-gray-200 rounded-2xl backdrop-blur-xl text-[11px] font-bold text-gray-400 tracking-wider shadow-lg">
          <div className="flex gap-6 uppercase">
            <span>Space: Pause</span>
            <span>1-4: Glyph</span>
            <span>5-8: Symatics</span>
            <span className="text-[#0071e3]">R: Restart</span>
          </div>
        </div>
      )}
    </div>
  );
}