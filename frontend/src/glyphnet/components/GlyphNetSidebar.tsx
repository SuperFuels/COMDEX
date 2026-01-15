"use client";

import React, { useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { DarkModeToggle } from "../../../components/DarkModeToggle";

type Item = { label: string; path: string; emoji?: string };

export default function GlyphNetSidebar({
  isOpen,
  onOpen,
  onClose,
  items,
  onGo,
}: {
  isOpen: boolean;
  onOpen: () => void;
  onClose: () => void;
  items: Item[];
  onGo: (path: string) => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside panel
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (isOpen && panelRef.current && !panelRef.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  // Close on hash route change
  useEffect(() => {
    const h = () => isOpen && onClose();
    window.addEventListener("hashchange", h);
    return () => window.removeEventListener("hashchange", h);
  }, [isOpen, onClose]);

  const safeItems: Item[] =
    items && items.length
      ? items
      : [
          { label: "DevTools", path: "/devtools", emoji: "🛠️" },
          { label: "Ledger", path: "/ledger", emoji: "📒" },
          { label: "Docs", path: "/docs", emoji: "📚" },
        ];

  return (
    <>
      {/* Always-on left rail */}
      <div
        aria-label="GlyphNet rail"
        className={[
          "fixed left-0 top-0 z-[80] h-screen w-14",
          "border-r border-border bg-background",
          "flex flex-col items-center justify-between py-3",
          "select-none",
        ].join(" ")}
      >
        {/* Top: G button toggles OPEN/CLOSE */}
        <div className="relative group">
          <button
            type="button"
            onClick={() => (isOpen ? onClose() : onOpen())}
            className="h-10 w-10 rounded-xl border border-border bg-background grid place-items-center hover:bg-button-light/40 dark:hover:bg-button-dark/40"
            aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
            title={isOpen ? "Close sidebar" : "Open sidebar"}
          >
            <Image src="/G.svg" alt="G" width={28} height={28} />
          </button>

          {/* Hover tooltip */}
          <div className="pointer-events-none absolute left-14 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="rounded-lg border border-border bg-background px-2 py-1 text-xs text-text shadow-sm whitespace-nowrap">
              {isOpen ? "Close sidebar" : "Open sidebar"}
            </div>
          </div>
        </div>

        {/* Bottom: theme toggle */}
        <div className="pb-1">
          <DarkModeToggle />
        </div>
      </div>

      {/* Backdrop */}
      <div
        className={[
          "fixed inset-0 z-[70] bg-black/40 transition-opacity",
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
        ].join(" ")}
        onClick={onClose}
      />

      {/* Slide-out panel */}
      <aside
        ref={panelRef}
        aria-label="GlyphNet navigation"
        className={[
          "fixed top-0 left-14 z-[75] h-screen w-80 max-w-[80vw]",
          "border-r border-border bg-background",
          "transform transition-transform duration-200 ease-out",
          isOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between px-4 py-4 border-b border-border">
            <div className="text-lg font-semibold">GlyphNet</div>
            <button
              onClick={onClose}
              className="h-9 w-9 rounded-lg border border-border hover:bg-button-light/40 dark:hover:bg-button-dark/40"
              aria-label="Close sidebar"
              title="Close"
            >
              ✕
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto px-4 py-5 space-y-6">
            <div className="flex flex-col gap-2">
              <Link
                href="/"
                className="block py-2 px-3 rounded-lg border border-border hover:bg-button-light/40 dark:hover:bg-button-dark/40 font-medium"
              >
                🟢 Back to Site Home
              </Link>

              <button
                onClick={() => onGo("/devtools")}
                className="text-left py-2 px-3 rounded-lg border border-border hover:bg-button-light/40 dark:hover:bg-button-dark/40 font-medium"
              >
                🛠️ DevTools
              </button>
            </div>

            <section>
              <div className="mb-2 px-1 text-xs uppercase tracking-wide text-text/60">
                GlyphNet Pages
              </div>

              <div className="flex flex-col">
                {safeItems.map((it) => (
                  <button
                    key={it.path}
                    onClick={() => onGo(it.path)}
                    className="flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-button-light/40 dark:hover:bg-button-dark/40 text-sm text-left"
                  >
                    <span className="w-5 text-center">{it.emoji ?? "•"}</span>
                    <span>{it.label}</span>
                  </button>
                ))}
              </div>
            </section>
          </nav>

          <div className="px-4 py-4 border-t border-border text-xs text-text/60">© Tessaris</div>
        </div>
      </aside>
    </>
  );
}