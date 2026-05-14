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
              src="/tessaris_light_logo.svg"
              alt="Tessaris"
              width={120}
              height={34}
              priority
              className="block dark:hidden border-none"
            />
            <Image
              src="/tessaris_dark_logo.svg"
              alt="Tessaris"
              width={120}
              height={34}
              priority
              className="hidden dark:block border-none"
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