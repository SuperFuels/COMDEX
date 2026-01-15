"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
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
  const containerRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (isOpen && containerRef.current && !containerRef.current.contains(e.target as Node)) onClose();
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
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-30 transition-opacity ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        ref={containerRef}
        className={`fixed inset-y-0 left-0 z-40 w-72 max-w-full
          bg-white dark:bg-gray-900 border-r border-gray-300 dark:border-gray-700
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
        aria-label="GlyphNet navigation"
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 pt-4 pb-2 border-b border-gray-300 dark:border-gray-700">
            <h2 className="text-xl font-semibold">GlyphNet</h2>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Close sidebar"
            >
              ✕
            </button>
          </div>

          {/* Nav */}
          <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
            {/* Pinned */}
            <div className="flex flex-col gap-2">
              <Link
                href="/"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🟢 Back to Site Home
              </Link>
              <button
                onClick={() => onGo("/devtools")}
                className="text-left py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🛠️ DevTools
              </button>
            </div>

            <section>
              <div className="mb-2 px-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                GlyphNet Pages
              </div>

              <div className="flex flex-col">
                {items.map((it) => (
                  <button
                    key={it.path}
                    onClick={() => onGo(it.path)}
                    className="flex items-center gap-2 py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-sm text-left"
                  >
                    <span className="w-5 text-center">{it.emoji ?? "•"}</span>
                    <span>{it.label}</span>
                  </button>
                ))}
              </div>
            </section>
          </nav>

          {/* Footer */}
          <div className="px-4 pb-4 border-t border-gray-300 dark:border-gray-700">
            <DarkModeToggle />
          </div>
        </div>
      </aside>
    </>
  );
}