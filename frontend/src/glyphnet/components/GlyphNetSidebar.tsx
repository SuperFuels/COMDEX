"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { DarkModeToggle } from "../../../components/DarkModeToggle";

type Item = { label: string; path: string; emoji?: string };

export default function GlyphNetSidebar({
  isOpen,
  onClose,
  items,
  onGo,
}: {
  isOpen: boolean;
  onClose: () => void;
  items: Item[];
  onGo: (path: string) => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside the panel (when open)
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (!isOpen) return;
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  // Close on hash route change (HashRouter navigation)
  useEffect(() => {
    const h = () => isOpen && onClose();
    window.addEventListener("hashchange", h);
    return () => window.removeEventListener("hashchange", h);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Left rail (always visible, ChatGPT-style) */}
      <div
        className="
          fixed left-0 top-0 z-[80] h-screen w-14
          border-r border-border bg-background
          flex flex-col items-center
          pt-3 pb-3
        "
        aria-label="GlyphNet rail"
      >
        {/* Top "G" button */}
        <div className="relative group">
          <button
            type="button"
            onClick={() => (isOpen ? onClose() : onGo("/devtools"))}
            className="
              h-10 w-10 rounded-lg border border-border
              bg-background hover:bg-button-light/40 dark:hover:bg-button-dark/40
              grid place-items-center
            "
            aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
            title={isOpen ? "Close" : "Open"}
          >
            {/* Use your G.svg if present; otherwise fallback to text */}
            <Image src="/G.svg" alt="G" width={24} height={24} />
          </button>

          {/* Hover hint (like ChatGPT) */}
          <div
            className="
              pointer-events-none absolute left-12 top-1/2 -translate-y-1/2
              opacity-0 group-hover:opacity-100 transition-opacity
              rounded-md border border-border bg-background px-2 py-1 text-xs text-text shadow
              whitespace-nowrap
            "
          >
            {isOpen ? "Close" : "Open sidebar"}
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Bottom avatar-ish circle (optional vibe) */}
        <div className="h-10 w-10 rounded-full border border-border grid place-items-center text-xs text-text/70">
          GN
        </div>
      </div>

      {/* Backdrop when open */}
      <div
        className={`fixed inset-0 z-[70] bg-black/40 transition-opacity ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />

      {/* Expanding panel */}
      <aside
        ref={panelRef}
        className={`
          fixed top-0 left-14 z-[90] h-screen w-80 max-w-[90vw]
          border-r border-border bg-background text-text
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        aria-label="GlyphNet sidebar"
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-border">
            <div className="text-lg font-semibold">GlyphNet</div>
            <button
              onClick={onClose}
              className="h-9 w-9 grid place-items-center rounded-lg border border-border hover:bg-button-light/40 dark:hover:bg-button-dark/40"
              aria-label="Close sidebar"
              title="Close"
            >
              ✕
            </button>
          </div>

          {/* Nav */}
          <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
            {/* Pinned */}
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
              <div className="mb-2 px-2 text-xs uppercase tracking-wide text-text/50">
                GlyphNet Pages
              </div>

              <div className="flex flex-col">
                {items.map((it) => (
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

          {/* Footer */}
          <div className="px-4 py-4 border-t border-border">
            <DarkModeToggle />
          </div>
        </div>
      </aside>

      {/* Push main content right so it doesn't sit under the rail */}
      <style jsx global>{`
        body {
          padding-left: 56px; /* w-14 */
        }
      `}</style>
    </>
  );
}