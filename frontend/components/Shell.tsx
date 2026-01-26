// frontend/components/Shell.tsx
"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/router";
import TabDock, { type TabDef } from "./TabDock";

export const TABS: readonly TabDef[] = [
  { key: "launch", label: "Launch", href: "/launch" },
  { key: "glyph", label: "Glyph OS", href: "/glyph" },
  { key: "compression", label: "Compression", href: "/compression" },
  { key: "symatics", label: "Symatics", href: "/symatics" },
  { key: "photon-algebra-demo", label: "Photon Algebra", href: "/photon-algebra-demo" },
  { key: "photon_binary", label: "Photon Binary", href: "/photon-binary" },
  { key: "sqi", label: "SQI", href: "/sqi" },
  { key: "sovereign_qkd", label: "Sovereign QKD", href: "/sovereign-qkd" },
  { key: "glyph_net", label: "Glyph Net", href: "/glyph-net" },
  { key: "sle_resonance", label: "SLE Resonance", href: "/sle-resonance" },
  { key: "rqc_awareness", label: "RQC Awareness", href: "/rqc-awareness" },
  { key: "ai", label: "AI", href: "/ai" },
  { key: "phase7-calibration", label: "Cognition", href: "/phase7-calibration" },
  { key: "wirepack", label: "WirePack", href: "/wirepack" },
  { key: "qfc_canvas", label: "QFC Canvas", href: "/qfc-canvas" },
];

function normalizeKeyAgainstTabs(k: string | undefined, tabs: readonly TabDef[]) {
  const raw = (k || "").trim();
  if (!raw) return "";

  if (tabs.some((t) => t.key === raw)) return raw;

  const alt = raw.replace(/-/g, "_");
  if (tabs.some((t) => t.key === alt)) return alt;

  return raw;
}

function getActiveKeyFromPath(pathname: string): string {
  const p = (pathname || "/").split("?")[0].split("#")[0];

  const exact = TABS.find((t) => t.href === p);
  if (exact) return exact.key;

  const nested = TABS
    .slice()
    .sort((a, b) => b.href.length - a.href.length)
    .find((t) => t.href !== "/" && p.startsWith(t.href + "/"));
  if (nested) return nested.key;

  return "glyph";
}

/** ✅ Tabs bar meant to be mounted inside the navbar (mobile scroll). */
export function ShellTabsBar({ activeKey }: { activeKey?: string }) {
  const router = useRouter();
  const derivedKey = getActiveKeyFromPath(router.asPath || router.pathname || "/");
  const key =
    normalizeKeyAgainstTabs(activeKey, TABS) ||
    normalizeKeyAgainstTabs(derivedKey, TABS) ||
    "glyph";

  return (
    <div className="w-full overflow-x-auto overflow-y-hidden">
      <div className="min-w-max">
        <TabDock tabs={TABS} activeKey={key} />
      </div>
    </div>
  );
}

export default function Shell({
  children,
  activeKey,
  hideHud = false,
  className = "",
  maxWidth = "max-w-[1400px]",
  tabsInNavbar = true, // ✅ default: tabs live in navbar now
}: {
  children: ReactNode;
  activeKey?: string;
  hideHud?: boolean;
  className?: string;
  maxWidth?: string;
  tabsInNavbar?: boolean;
}) {
  const router = useRouter();
  const derivedKey = getActiveKeyFromPath(router.asPath || router.pathname || "/");
  const key =
    normalizeKeyAgainstTabs(activeKey, TABS) ||
    normalizeKeyAgainstTabs(derivedKey, TABS) ||
    "glyph";

  return (
    <div
      className={`min-h-screen bg-[#f5f5f7] text-[#1d1d1f] selection:bg-blue-100 font-sans antialiased ${className}`}
    >
      {/* ✅ single scroll container */}
      <div className="h-screen overflow-y-auto overflow-x-hidden">
        <main
          className={[
            "relative z-10 flex flex-col items-center justify-start min-h-full",
            "w-full",
            "px-4 sm:px-6 md:px-10",
            maxWidth,
            "mx-auto",
            "pt-6 pb-24", // smaller top padding since tabs are in navbar
          ].join(" ")}
        >
          {/* ✅ Tabs moved to navbar */}
          {!tabsInNavbar && <TabDock tabs={TABS} activeKey={key} />}

          <div className="w-full">
            <div key={key} className="animate-tab-change">
              {children}
            </div>
          </div>

          <footer className="mt-16 flex flex-col sm:flex-row gap-3 sm:gap-6 w-full justify-center">
            <button className="px-8 py-3 bg-black text-white rounded-full font-semibold text-base hover:bg-gray-800 transition-all">
              Launch GlyphNet
            </button>
            <button className="px-8 py-3 border-2 border-black text-black rounded-full font-semibold text-base hover:bg-black hover:text-white transition-all">
              View Multiverse
            </button>
          </footer>
        </main>
      </div>

      {!hideHud && (
        <div className="fixed bottom-4 right-4 sm:bottom-8 sm:right-8 p-3 bg-white/80 border border-gray-200 rounded-2xl backdrop-blur-xl text-[10px] font-bold text-gray-400 tracking-wider shadow-lg">
          <div className="flex gap-4 uppercase">
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