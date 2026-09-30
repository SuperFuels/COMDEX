// frontend/components/GlyphNetNavbar.tsx
"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { ShellTabsBar } from "./Shell";

export default function GlyphNetNavbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-[#e5e7eb] bg-background text-text">
      <div className="mx-auto max-w-[1400px] px-3 sm:px-4 py-2">
        {/* mobile: stack, desktop: side-by-side */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <Link href="/" className="logo-link flex items-center shrink-0">
            <Image
              src="/tessaris-tesseract-rounded-loop.png"
              alt="Tessaris"
              width={174}
              height={58}
              priority
              className="block h-auto w-[148px] border-none sm:w-[174px]"
            />
          </Link>

          <div className="flex-1 flex justify-center sm:justify-end">
            <ShellTabsBar />
          </div>
        </div>
      </div>
    </header>
  );
}
