// frontend/components/Shell.tsx
"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/router";
import TabDock, { type TabDef } from "./TabDock";

// ✅ Only show these two tabs
export const TABS: readonly TabDef[] = [
  { key: "launch", label: "Launch", href: "/launch" },
  { key: "glyph", label: "Glyph OS", href: "/glyph" },
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

  // ✅ default to glyph for any unknown routes
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
  className = "",
  maxWidth = "max-w-[1400px]",
  tabsInNavbar = true, // ✅ default: tabs live in navbar now
}: {
  children: ReactNode;
  activeKey?: string;
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
            "pt-6 pb-24",
          ].join(" ")}
        >
          {/* ✅ Tabs moved to navbar */}
          {!tabsInNavbar && <TabDock tabs={TABS} activeKey={key} />}

          <div className="w-full">
            <div key={key} className="animate-tab-change">
              {children}
            </div>
          </div>

          {/* ✅ removed footer buttons */}
          {/* ✅ removed bottom-right HUD overlay */}
        </main>
      </div>
    </div>
  );
}