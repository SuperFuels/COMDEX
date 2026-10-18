import Link from "next/link";

export default function ArticlesFooter() {
  return (
    <footer className="border-t border-slate-200 bg-[#071329] px-5 py-12 text-white sm:px-8">
      <div className="mx-auto flex max-w-[1120px] flex-col gap-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xl font-black">Tessaris</div>
          <p className="mt-3 max-w-lg text-sm leading-6 text-slate-400">
            Product updates, research results and announcements from the team building an AI workforce for owner-led businesses.
          </p>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-bold">
          <Link href="/" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Tessaris</Link>
          <Link href="/aion" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Si</Link>
          <Link href="/articles" className="!border-0 !bg-transparent !p-0 !text-white">Articles</Link>
          <Link href="/pricing" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Pricing</Link>
        </div>
      </div>
    </footer>
  );
}
