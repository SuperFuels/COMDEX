import Head from "next/head";
import Link from "next/link";
import type { CSSProperties } from "react";
import {
  ArrowRight,
  BadgeEuro,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  Check,
  Database,
  Gamepad2,
  Headphones,
  ListTodo,
  Mail,
  Megaphone,
  MessageCircle,
  PackageCheck,
  Navigation,
  ReceiptText,
  Search,
  ShieldCheck,
  ShoppingCart,
  Smartphone,
  Sparkles,
  Tv,
  UsersRound,
} from "lucide-react";

const personalJourney = [
  { icon: Tv, command: "Pilot, open Netflix", result: "Netflix opens on the TV" },
  { icon: Search, command: "Find this online", result: "Pilot compares the best options" },
  { icon: ShoppingCart, command: "Order that one", result: "Exact purchase ready for phone approval" },
  { icon: Gamepad2, command: "Pilot, open games", result: "Cloud games appear—no console required" },
  { icon: Smartphone, command: "Use my phone", result: "Your phone becomes the private controller" },
];

const businessJourney = [
  { icon: MessageCircle, title: "Lead arrives", detail: "Website · 22:41" },
  { icon: Mail, title: "Pilot responds", detail: "Helpful reply sent" },
  { icon: Database, title: "Sales updated", detail: "CRM lead created" },
  { icon: Megaphone, title: "Source matched", detail: "Campaign attributed" },
  { icon: BadgeEuro, title: "Sale confirmed", detail: "Order converted" },
  { icon: PackageCheck, title: "Operations acts", detail: "Dispatch prepared" },
  { icon: Headphones, title: "Customer cared for", detail: "Questions handled" },
  { icon: ReceiptText, title: "Finance closes", detail: "Invoice reconciled" },
  { icon: ChartNoAxesCombined, title: "AION learns", detail: "Spend recommendation" },
  { icon: BriefcaseBusiness, title: "CEO briefed", detail: "Outcome delivered" },
];

export default function HomePage() {
  return (
    <>
      <Head>
        <title>Tessaris — Your intelligence, working for you</title>
        <meta
          name="description"
          content="Personal Pilot, Business Pilot and secure workspaces powered by customer-owned AION intelligence."
        />
      </Head>

      <div className="tessaris-home h-[calc(100vh-64px)] overflow-y-auto overflow-x-hidden bg-[#f7f9fc] text-[#0b1730]">
        <main>
          <section className="relative isolate min-h-[760px] overflow-hidden border-b border-slate-200/80 bg-white px-5 pb-20 pt-20 sm:px-8 lg:pt-28">
            <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_50%_10%,rgba(38,109,255,0.13),transparent_31%),radial-gradient(circle_at_88%_68%,rgba(19,179,177,0.10),transparent_26%)]" />
            <div className="mx-auto max-w-[1180px]">
              <div className="mx-auto max-w-4xl text-center">
                <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-[11px] font-extrabold uppercase tracking-[0.19em] text-blue-700">
                  <Sparkles size={14} aria-hidden="true" />
                  Your own intelligence
                </div>
                <h1 className="text-balance text-5xl font-black leading-[0.96] tracking-[-0.055em] text-[#071329] sm:text-7xl lg:text-[92px]">
                  Life works better
                  <span className="block text-[#1266e8]">with a Pilot.</span>
                </h1>
                <p className="mx-auto mt-7 max-w-2xl text-balance text-lg leading-8 text-slate-600 sm:text-xl">
                  One private intelligence that helps at home, works beside you and can run the repetitive parts of a business—without making you live inside another app.
                </p>
                <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
                  <a href="#choose-pilot" className="group inline-flex min-h-14 items-center gap-3 rounded-full !border-0 !bg-[#1266e8] px-7 py-3 text-base font-bold !text-white shadow-[0_16px_38px_rgba(18,102,232,0.24)] transition hover:!bg-[#0d54c5]">
                    Find my Pilot <ArrowRight size={18} className="transition group-hover:translate-x-1" />
                  </a>
                  <Link href="/aion-business" className="inline-flex min-h-14 items-center rounded-full !border !border-slate-300 !bg-white px-7 py-3 text-base font-bold !text-[#0b1730] shadow-sm hover:!border-slate-400 hover:!bg-slate-50">
                    Automate my business
                  </Link>
                </div>
              </div>

              <div id="choose-pilot" className="mt-20 grid gap-5 lg:grid-cols-3">
                <a href="#personal-pilot" className="group !rounded-[28px] !border !border-blue-200 !bg-[#eef5ff] p-7 text-left !text-[#0b1730] shadow-[0_20px_65px_rgba(28,73,137,0.08)] transition duration-300 hover:-translate-y-1 hover:!border-blue-400 hover:!bg-[#e8f1ff] sm:p-8">
                  <div className="mb-10 flex items-start justify-between">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl bg-blue-600 text-white"><Sparkles size={22} /></span>
                    <ArrowRight size={20} className="text-blue-600 transition group-hover:translate-x-1" />
                  </div>
                  <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-blue-700">Pilot for me</p>
                  <h2 className="mt-3 text-3xl font-black tracking-[-0.035em]">Make everyday life feel futuristic.</h2>
                  <p className="mt-4 leading-7 text-slate-600">Talk to your TV, play, shop, learn and control your home. The useful things—and the genuinely fun ones.</p>
                </a>

                <a href="#business-pilot" className="group !rounded-[28px] !border !border-[#14233d] !bg-[#071329] p-7 text-left !text-white shadow-[0_20px_65px_rgba(7,19,41,0.17)] transition duration-300 hover:-translate-y-1 hover:!bg-[#0a1d3a] sm:p-8">
                  <div className="mb-10 flex items-start justify-between">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#18b8a4] text-[#061b27]"><BriefcaseBusiness size={22} /></span>
                    <ArrowRight size={20} className="text-[#55dfca] transition group-hover:translate-x-1" />
                  </div>
                  <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-[#55dfca]">Business Pilot</p>
                  <h2 className="mt-3 text-3xl font-black tracking-[-0.035em]">Put intelligent employees on the night shift.</h2>
                  <p className="mt-4 leading-7 text-slate-300">Automate the work that never stops. Keep the decisions, approvals and company knowledge yours.</p>
                </a>

                <a href="#workspace" className="group !rounded-[28px] !border !border-amber-200 !bg-[#fff8eb] p-7 text-left !text-[#0b1730] shadow-[0_20px_65px_rgba(113,77,18,0.07)] transition duration-300 hover:-translate-y-1 hover:!border-amber-400 hover:!bg-[#fff4df] sm:p-8">
                  <div className="mb-10 flex items-start justify-between">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#ffbb3c] text-[#352000]"><UsersRound size={22} /></span>
                    <ArrowRight size={20} className="text-amber-700 transition group-hover:translate-x-1" />
                  </div>
                  <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-amber-700">Pilot Workspace</p>
                  <h2 className="mt-3 text-3xl font-black tracking-[-0.035em]">Do your best work without losing your own space.</h2>
                  <p className="mt-4 leading-7 text-slate-600">Join a company, client or project with exactly the access you need—and your own Pilot beside you.</p>
                </a>
              </div>
            </div>
          </section>

          <section id="personal-pilot" className="scroll-mt-24 px-5 py-24 sm:px-8 lg:py-32">
            <div className="mx-auto grid max-w-[1180px] items-center gap-14 lg:grid-cols-[0.9fr_1.1fr]">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-blue-700">Personal Pilot</p>
                <h2 className="mt-4 text-4xl font-black leading-tight tracking-[-0.045em] sm:text-6xl">Your home already has screens. Give them intelligence.</h2>
                <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">Pilot turns the television, phone and computer you already own into one voice-controlled personal system. It can handle the ordinary—but it should also make technology feel exciting again.</p>
                <Link href="/pilot/mobile" className="mt-8 inline-flex items-center gap-2 rounded-full !border-0 !bg-[#1266e8] px-6 py-3 font-bold !text-white hover:!bg-[#0d54c5]">Explore Personal Pilot <ArrowRight size={17} /></Link>
              </div>

              <div className="rounded-[34px] border border-slate-200 bg-white p-4 shadow-[0_28px_90px_rgba(16,43,82,0.12)] sm:p-6">
                <div className="rounded-[26px] bg-[#09162c] p-5 text-white sm:p-7">
                  <div className="flex items-center justify-between border-b border-white/10 pb-5">
                    <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-300">Ordinary smart TV</p><p className="mt-1 text-xl font-black">Now it has a Pilot.</p></div>
                    <span className="personal-listening-dot h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_18px_#34d399]" />
                  </div>

                  <div className="mt-5 space-y-2">
                    {personalJourney.map(({ icon: Icon, command, result }, index) => (
                      <div key={command} className="personal-journey-step grid grid-cols-[34px_1fr] items-center gap-x-3 rounded-2xl border border-white/10 bg-white/[0.055] px-3 py-2.5" style={{ "--personal-index": index } as CSSProperties}>
                        <span className="personal-journey-icon row-span-2 grid h-8 w-8 place-items-center rounded-full bg-blue-400/10 text-blue-300"><Icon size={15} /></span>
                        <p className="text-xs font-extrabold text-white">“{command}”</p>
                        <p className="text-[10px] leading-4 text-slate-400">{result}</p>
                      </div>
                    ))}
                  </div>

                  <div className="personal-handoff mt-4 overflow-hidden rounded-2xl border border-blue-300/20 bg-[#0c2040] p-4">
                    <div className="flex items-center gap-3">
                      <span className="grid h-9 w-9 place-items-center rounded-full bg-blue-500 text-white"><ListTodo size={17} /></span>
                      <div><p className="text-xs font-black">“Send Becca a task to pick up milk.”</p><p className="mt-0.5 text-[10px] text-blue-200">Kevin’s Pilot sends the task</p></div>
                    </div>
                    <div className="my-3 flex items-center gap-2 pl-4 text-blue-300" aria-hidden="true"><span className="h-px flex-1 bg-blue-300/20" /><ArrowRight size={15} /><span className="h-px flex-1 bg-blue-300/20" /></div>
                    <div className="flex items-center gap-3 rounded-xl bg-white p-3 text-[#0b1730]">
                      <span className="grid h-9 w-9 place-items-center rounded-full bg-amber-100 text-amber-700"><Navigation size={17} /></span>
                      <div className="min-w-0 flex-1"><p className="text-xs font-black">Becca’s Pilot</p><p className="mt-0.5 text-[10px] text-slate-500">Pick up milk on the way home?</p></div>
                      <span className="rounded-full bg-blue-600 px-3 py-1.5 text-[10px] font-black text-white">Route me</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section id="business-pilot" className="scroll-mt-24 bg-[#071329] px-5 py-24 text-white sm:px-8 lg:py-32">
            <div className="mx-auto grid max-w-[1180px] gap-14 lg:grid-cols-2 lg:items-center">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-[#55dfca]">Business Pilot</p>
                <h2 className="mt-4 text-4xl font-black leading-tight tracking-[-0.045em] sm:text-6xl">Your business does not stop when you log off.</h2>
                <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">Give sales, marketing, finance, operations and support their own governed AI agents. They can prepare and act around the clock while consequential decisions stay approval-gated.</p>
                <Link href="/aion-business" className="mt-8 inline-flex items-center gap-2 rounded-full !border-0 !bg-[#55dfca] px-6 py-3 font-bold !text-[#062333] hover:!bg-[#7de8d8]">See Business Pilot <ArrowRight size={17} /></Link>
              </div>
              <div className="business-journey rounded-[30px] border border-white/10 bg-white/[0.055] p-5 sm:p-8" aria-label="Animated journey of a lead through Business Pilot">
                <div className="mb-6 flex items-center justify-between gap-4">
                  <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-[#55dfca]">Live business journey</p><p className="mt-1 text-2xl font-black">One lead. Every step handled.</p></div>
                  <span className="business-live-badge shrink-0 rounded-full bg-emerald-400/15 px-3 py-1.5 text-xs font-bold text-emerald-300">Pilot working</span>
                </div>
                <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#061126] px-3 py-5">
                  <div className="business-progress absolute left-7 right-7 top-[42px] h-px bg-white/10" aria-hidden="true"><span /></div>
                  <div className="relative grid grid-cols-2 gap-2 sm:grid-cols-5">
                    {businessJourney.map(({ icon: Icon, title, detail }, index) => (
                      <div key={title} className="business-journey-step rounded-xl border border-white/[0.08] bg-white/[0.045] p-3" style={{ "--journey-index": index } as CSSProperties}>
                        <span className="business-step-icon grid h-8 w-8 place-items-center rounded-full bg-white/10 text-slate-400"><Icon size={15} /></span>
                        <p className="mt-3 text-xs font-extrabold leading-4 text-white">{title}</p>
                        <p className="mt-1 text-[10px] leading-4 text-slate-500">{detail}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-400">
                  <span className="inline-flex items-center gap-2"><Check size={13} className="text-[#55dfca]" /> Customer updated</span>
                  <span className="inline-flex items-center gap-2"><Check size={13} className="text-[#55dfca]" /> Departments coordinated</span>
                  <span className="inline-flex items-center gap-2"><Check size={13} className="text-[#55dfca]" /> Every action traceable</span>
                </div>
              </div>
            </div>
          </section>

          <section id="workspace" className="scroll-mt-24 bg-white px-5 py-24 sm:px-8 lg:py-32">
            <div className="mx-auto max-w-[1040px] text-center">
              <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-amber-700">Pilot Workspace</p>
              <h2 className="mx-auto mt-4 max-w-4xl text-balance text-4xl font-black leading-tight tracking-[-0.045em] sm:text-6xl">One place to work with a company, a client or a project.</h2>
              <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-600">You do not need to own a business to have a Pilot. Accept an invitation, see what needs your attention, ask the company’s intelligence and approve only what your role allows.</p>
              <div className="mt-12 grid gap-4 text-left sm:grid-cols-3">
                {[
                  ["01", "Your own space", "Personal information stays separate from every company you work with."],
                  ["02", "The right access", "See only the projects, files and decisions that belong to your role."],
                  ["03", "Pilot beside you", "Brief, research, review and delegate without digging through five systems."],
                ].map(([number, title, copy], index) => (
                  <div key={number} className="workspace-flow-step rounded-3xl border border-slate-200 bg-[#f8fafc] p-6" style={{ "--workspace-index": index } as CSSProperties}>
                    <span className="text-xs font-black tracking-[0.15em] text-amber-600">{number}</span>
                    <h3 className="mt-8 text-xl font-black">{title}</h3>
                    <p className="mt-3 leading-7 text-slate-600">{copy}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="border-t border-slate-200 bg-[#f3f6fb] px-5 py-20 sm:px-8">
            <div className="mx-auto flex max-w-[1180px] flex-col gap-8 rounded-[34px] border border-slate-200 bg-white p-8 shadow-[0_24px_70px_rgba(15,45,90,0.08)] sm:p-12 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-2xl">
                <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-[0.2em] text-blue-700"><ShieldCheck size={17} /> Tessaris / AION</div>
                <h2 className="mt-4 text-3xl font-black tracking-[-0.04em] sm:text-4xl">The intelligence underneath belongs to you.</h2>
                <p className="mt-4 leading-7 text-slate-600">AION is the private second brain connecting every Pilot. It remembers what matters, routes work to the right intelligence and keeps models replaceable.</p>
              </div>
              <Link href="/aion-business" className="inline-flex shrink-0 items-center gap-2 rounded-full !border !border-slate-300 !bg-white px-6 py-3 font-bold !text-[#0b1730] hover:!border-blue-400 hover:!text-blue-700">How AION works <ArrowRight size={17} /></Link>
            </div>
          </section>
        </main>

        <footer className="border-t border-slate-200 bg-white px-5 py-8 sm:px-8">
          <div className="mx-auto flex max-w-[1180px] flex-col gap-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <span className="font-black italic text-[#0b1730]">Tessaris</span>
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>Personal Pilot • Business Pilot • Pilot Workspace • AION</span>
              <Link href="/legacy" className="font-semibold text-slate-500 underline decoration-slate-300 underline-offset-4 hover:text-blue-700">
                Previous Tessaris site
              </Link>
            </span>
          </div>
        </footer>

        <style jsx global>{`
          @keyframes business-step-pulse {
            0%, 7% { border-color: rgba(85, 223, 202, 0.72); background: rgba(85, 223, 202, 0.14); transform: translateY(-2px); }
            12%, 100% { border-color: rgba(255, 255, 255, 0.08); background: rgba(255, 255, 255, 0.045); transform: translateY(0); }
          }
          @keyframes business-icon-pulse {
            0%, 7% { background: #55dfca; color: #062333; box-shadow: 0 0 22px rgba(85, 223, 202, 0.45); }
            12%, 100% { background: rgba(255, 255, 255, 0.10); color: #94a3b8; box-shadow: none; }
          }
          @keyframes business-progress-run {
            from { transform: translateX(-105%); }
            to { transform: translateX(520%); }
          }
          @keyframes business-live {
            50% { opacity: 0.55; }
          }
          @keyframes personal-step-pulse {
            0%, 13% { border-color: rgba(96, 165, 250, 0.76); background: rgba(59, 130, 246, 0.17); transform: translateX(4px); }
            21%, 100% { border-color: rgba(255, 255, 255, 0.10); background: rgba(255, 255, 255, 0.055); transform: translateX(0); }
          }
          @keyframes personal-icon-pulse {
            0%, 13% { background: #60a5fa; color: #071329; box-shadow: 0 0 18px rgba(96, 165, 250, 0.48); }
            21%, 100% { background: rgba(96, 165, 250, 0.10); color: #93c5fd; box-shadow: none; }
          }
          @keyframes personal-handoff-pulse {
            0%, 75% { border-color: rgba(147, 197, 253, 0.20); transform: scale(1); }
            82%, 94% { border-color: rgba(85, 223, 202, 0.72); transform: scale(1.012); }
            100% { border-color: rgba(147, 197, 253, 0.20); transform: scale(1); }
          }
          @keyframes workspace-step-pulse {
            0%, 24% { border-color: rgba(245, 158, 11, 0.55); box-shadow: 0 14px 36px rgba(180, 119, 18, 0.10); transform: translateY(-3px); }
            33%, 100% { border-color: rgb(226 232 240); box-shadow: none; transform: translateY(0); }
          }
          .business-journey-step {
            animation: business-step-pulse 10s ease-in-out infinite;
            animation-delay: calc(var(--journey-index) * 1s);
            transition: border-color 220ms ease, background 220ms ease, transform 220ms ease;
          }
          .business-step-icon {
            animation: business-icon-pulse 10s ease-in-out infinite;
            animation-delay: calc(var(--journey-index) * 1s);
          }
          .business-progress { overflow: hidden; }
          .business-progress span {
            display: block;
            width: 20%;
            height: 100%;
            background: linear-gradient(90deg, transparent, #55dfca, transparent);
            animation: business-progress-run 3.4s linear infinite;
          }
          .business-live-badge { animation: business-live 1.4s ease-in-out infinite; }
          .personal-journey-step {
            animation: personal-step-pulse 7.5s ease-in-out infinite;
            animation-delay: calc(var(--personal-index) * 1.15s);
          }
          .personal-journey-icon {
            animation: personal-icon-pulse 7.5s ease-in-out infinite;
            animation-delay: calc(var(--personal-index) * 1.15s);
          }
          .personal-handoff { animation: personal-handoff-pulse 7.5s ease-in-out infinite; }
          .personal-listening-dot { animation: business-live 1.4s ease-in-out infinite; }
          .workspace-flow-step {
            animation: workspace-step-pulse 6s ease-in-out infinite;
            animation-delay: calc(var(--workspace-index) * 2s);
          }
          @media (prefers-reduced-motion: reduce) {
            .business-journey-step, .business-step-icon, .business-progress span, .business-live-badge, .personal-journey-step, .personal-journey-icon, .personal-handoff, .personal-listening-dot, .workspace-flow-step { animation: none !important; }
          }
        `}</style>
      </div>
    </>
  );
}
