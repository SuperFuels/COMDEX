"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function TessarisNavbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex min-h-[72px] max-w-[1240px] items-center justify-between gap-5 px-5 sm:px-8">
        <Link href="/" aria-label="Tessaris home" className="logo-link shrink-0 !border-0 !bg-transparent !p-0 max-[440px]:w-9 max-[440px]:overflow-hidden">
          <Image
            src="/tessaris-tesseract-rounded-loop.png"
            alt="Tessaris"
            width={174}
            height={58}
            priority
            className="block h-auto w-[142px] max-w-none border-none sm:w-[164px]"
          />
        </Link>

        <nav aria-label="Primary navigation" className="flex items-center gap-1 sm:gap-3">
          <Link href="/market" className="!border-0 !bg-transparent px-3 py-2 text-sm font-bold !text-slate-600 transition hover:!text-[#1748e5]">
            Market
          </Link>
          <Link href="/pricing" className="!border-0 !bg-transparent px-3 py-2 text-sm font-bold !text-slate-600 transition hover:!text-[#1748e5]">
            Pricing
          </Link>
          <Link
            href="/register"
            className="ml-1 inline-flex items-center gap-2 rounded-full !border-0 !bg-[#1748e5] px-4 py-2.5 text-sm font-extrabold !text-white shadow-[0_8px_22px_rgba(23,72,229,.2)] transition hover:!bg-[#1039bc] sm:px-5"
          >
            <span className="hidden sm:inline">Join the launch</span>
            <span className="sm:hidden">Join</span>
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </nav>
      </div>
    </header>
  );
}
