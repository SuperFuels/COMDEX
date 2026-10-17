import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BadgeCheck,
  BrainCircuit,
  Check,
  FileCheck2,
  Laptop,
  Network,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const researchLinks = [
  { label: "Glyph OS", href: "/glyph", copy: "A symbolic operating layer for structured machine work." },
  { label: "Compression", href: "/compression", copy: "Research into compact, portable representations of intelligence." },
  { label: "Symatics", href: "/symatics", copy: "Exploration of information, resonance and physical systems." },
  { label: "Photon Algebra", href: "/photon-algebra-demo", copy: "A mathematical language for describing and testing complex systems." },
  { label: "Photon Binary", href: "/photon-binary", copy: "Experimental work on new forms of machine representation." },
  { label: "SQI", href: "/sqi", copy: "A symbolic intelligence runtime for quantum-like reasoning on everyday hardware." },
  { label: "Sovereign QKD", href: "/sovereign-qkd", copy: "Secure communication research for sovereign agents and protected machine work." },
  { label: "Glyph Net", href: "/glyph-net", copy: "A network layer for exchanging structured intelligence across systems." },
  { label: "SLE Resonance", href: "/sle-resonance", copy: "Live research into resonance, stability and adaptive system behaviour." },
  { label: "RQC Awareness", href: "/rqc-awareness", copy: "An awareness horizon showing how AION detects change and returns to coherence." },
  { label: "AI", href: "/ai", copy: "A live proof-of-life view into AION's cognition, learning and system activity." },
  { label: "Cognition", href: "/phase7-calibration", copy: "Calibration tools for evaluating and developing AION's cognitive systems." },
  { label: "WirePack", href: "/wirepack", copy: "A deterministic transport protocol for moving structured meaning efficiently." },
  { label: "QFC Canvas", href: "/qfc-canvas", copy: "An interactive field lab for exploring coherence across live system telemetry." },
  { label: "Homeostasis", href: "/homeostasis", copy: "A live training gate for monitoring balance, stability and recovery." },
];

function Eyebrow({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <div className={`mb-4 text-[11px] font-black uppercase tracking-[0.2em] ${dark ? "text-blue-300" : "text-[#1748e5]"}`}>
      {children}
    </div>
  );
}

export default function AionPage() {
  return (
    <>
      <Head>
        <title>AION — The intelligence system behind Tessaris</title>
        <meta
          name="description"
          content="Explore AION, the governed intelligence and execution system behind Tessaris, including local models, model routing, business context, tools, memory and evidence."
        />
      </Head>

      <div className="tessaris-launch h-[calc(100vh-72px)] overflow-y-auto overflow-x-hidden bg-white text-[#071329]">
        <main>
          <section className="relative isolate overflow-hidden border-b border-slate-200 bg-[#f7faff] px-3 pb-20 pt-5 sm:px-6 lg:pb-28">
            <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_16%_60%,rgba(23,72,229,.12),transparent_32%),radial-gradient(circle_at_88%_80%,rgba(24,184,164,.11),transparent_28%)]" />
            <div className="mx-auto max-w-[1380px]">
              <div className="relative min-h-[330px] overflow-hidden rounded-[26px] border border-blue-100 bg-[#b9d2eb] shadow-[0_24px_70px_rgba(7,19,41,.16)] sm:min-h-[430px] lg:min-h-[560px]">
                <Image
                  src="/tessaris-spatial-boardroom-clean.png"
                  alt="AION coordinating specialist local and frontier AI models in the Tessaris intelligence boardroom"
                  fill
                  priority
                  sizes="(max-width: 768px) 100vw, 1380px"
                  className="object-cover object-center"
                />
                <div className="absolute left-[9%] top-[43%] -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">AION</div>
                <div className="absolute left-[41.5%] top-[39%] -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">Gemini</div>
                <div className="absolute left-[58%] top-[39%] -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">OpenAI</div>
                <div className="absolute left-[90%] top-[43%] -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">Qwen</div>
              </div>

              <div className="relative z-10 mx-auto -mt-2 max-w-[1060px] rounded-[30px] border border-slate-200 bg-white px-6 py-10 text-center shadow-[0_24px_70px_rgba(7,19,41,.10)] sm:-mt-10 sm:px-12 sm:py-14 lg:-mt-16">
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-[11px] font-black uppercase tracking-[0.18em] text-blue-700">
                  <Sparkles size={14} aria-hidden="true" /> The intelligence behind Tessaris
                </div>
                <h1 className="mx-auto max-w-4xl text-balance text-5xl font-black leading-[.96] tracking-[-.055em] sm:text-7xl lg:text-[78px]">
                  Intelligence that can <span className="text-[#1748e5]">coordinate and act.</span>
                </h1>
                <p className="mx-auto mt-7 max-w-3xl text-balance text-lg leading-8 text-slate-600 sm:text-xl">
                  AION brings business context, selected AI models, tools, memory and human-set authority into one governed system. It coordinates specialised intelligence and turns decisions into accountable work.
                </p>
                <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
                  <a href="#architecture" className="group inline-flex min-h-14 items-center justify-center gap-3 rounded-full !border-0 !bg-[#1748e5] px-7 py-3 text-base font-extrabold !text-white shadow-[0_16px_38px_rgba(23,72,229,.24)] transition hover:!bg-[#1039bc]">
                    Explore AION <ArrowRight size={18} className="transition group-hover:translate-x-1" />
                  </a>
                  <Link href="/" className="inline-flex min-h-14 items-center justify-center rounded-full border border-slate-300 !bg-white px-7 py-3 text-base font-extrabold !text-[#071329] transition hover:border-blue-300 hover:!bg-blue-50">See Tessaris for business</Link>
                </div>
                <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm font-semibold text-slate-600">
                  {["Local and frontier models", "Human-set authority", "Evidence for completed work"].map((item) => <span key={item} className="inline-flex items-center gap-2"><Check size={16} className="text-[#18a690]" />{item}</span>)}
                </div>
              </div>
            </div>
          </section>

          <section id="architecture" className="relative scroll-mt-24 overflow-hidden bg-[#071329] px-5 py-20 text-white sm:px-8 lg:py-28">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_75%_30%,rgba(23,105,255,.22),transparent_32%)]" />
            <div className="relative mx-auto max-w-[1240px]">
              <div className="max-w-4xl">
                <Eyebrow dark>The intelligence boardroom</Eyebrow>
                <h2 className="text-balance text-4xl font-black leading-[1.02] tracking-[-.045em] sm:text-6xl">A board that watches the whole business—not one dashboard at a time.</h2>
                <p className="mt-6 text-lg leading-8 text-slate-300">AION can bring selected local and API models into the same business context. Each contributes where it is strongest while AION coordinates the decision, authority and resulting work.</p>
                <ul className="mt-7 grid gap-3 text-sm font-semibold text-slate-200 sm:grid-cols-3">
                  {["Shared context across departments", "Specialists called only when useful", "Results checked against the plan"].map((item) => <li key={item} className="flex gap-3"><BadgeCheck size={18} className="mt-0.5 shrink-0 text-blue-300" />{item}</li>)}
                </ul>
              </div>

              <figure className="mt-12 overflow-hidden rounded-[30px] border border-white/15 bg-[#102141] shadow-[0_34px_90px_rgba(0,0,0,.35)]">
                <div className="relative aspect-[3216/1334] w-full">
                  <Image src="/tessaris-spatial-boardroom-clean.png" alt="AION and selected AI models in the Tessaris spatial intelligence boardroom" fill sizes="(max-width: 1280px) 100vw, 1240px" className="object-cover" />
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-[#071329]/90 to-transparent" />
                  <div className="absolute bottom-4 left-4 right-4 flex flex-col gap-3 sm:bottom-6 sm:left-6 sm:right-6 sm:flex-row sm:items-end sm:justify-between">
                    <div className="rounded-2xl border border-white/15 bg-[#071329]/80 px-4 py-3 backdrop-blur-md">
                      <div className="text-[9px] font-black uppercase tracking-[.2em] text-blue-300">Intelligence boardroom</div>
                      <div className="mt-1 text-sm font-extrabold text-white sm:text-base">AION and selected models working on the same decision</div>
                    </div>
                    <div className="hidden rounded-full border border-white/15 bg-[#071329]/80 px-4 py-2 text-[10px] font-black uppercase tracking-[.15em] text-slate-200 backdrop-blur-md sm:block">Spatial 3D / 4D environment</div>
                  </div>
                </div>
              </figure>
            </div>
          </section>

          <section id="model-rack" className="scroll-mt-24 px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="grid items-center gap-12 lg:grid-cols-[.82fr_1.18fr]">
                <div>
                  <Eyebrow>Owner-controlled intelligence</Eyebrow>
                  <h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">Use the right intelligence without surrendering control.</h2>
                  <p className="mt-6 text-lg leading-8 text-slate-600">AION is designed to combine compatible open models running locally with selected external model services. Portable model libraries on owner-controlled storage have been demonstrated internally; the complete customer download and verification flow remains in validation.</p>
                  <div className="mt-7 inline-flex items-center gap-3 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-extrabold text-blue-800"><BadgeCheck size={18} /> Local-model capability demonstrated · customer packaging in validation</div>
                </div>
                <figure className="overflow-hidden rounded-[30px] border border-slate-200 bg-[#071329] shadow-[0_28px_70px_rgba(7,19,41,.18)]">
                  <div className="relative aspect-[16/10]">
                    <Image src="/tessaris-open-model-card-rack.png" alt="Concept for a portable AION library of open AI models on removable storage" fill sizes="(max-width: 1024px) 100vw, 720px" className="object-cover" />
                  </div>
                  <figcaption className="flex flex-col gap-2 border-t border-white/10 px-6 py-5 text-white sm:flex-row sm:items-center sm:justify-between">
                    <div><div className="text-[10px] font-black uppercase tracking-[.19em] text-blue-300">Portable model library</div><div className="mt-1 font-extrabold">Select the right model for the work and the device.</div></div>
                    <div className="text-xs text-slate-400">Private · removable · expandable</div>
                  </figcaption>
                </figure>
              </div>

              <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  [BrainCircuit, "AION", "Coordinates business context, specialist intelligence, tools and authority."],
                  [Laptop, "Local models", "Compatible open models can handle selected work on owner-controlled hardware."],
                  [Network, "Portable libraries", "Verified model packages can be organised for compatible devices and roles."],
                  [Sparkles, "Expert APIs", "External intelligence can be called for selected work when its strengths are needed."],
                ].map(([Icon, title, copy]) => {
                  const CardIcon = Icon as LucideIcon;
                  return <article key={title as string} className="rounded-3xl border border-slate-200 bg-[#f7f9fc] p-6"><CardIcon size={24} className="text-[#1748e5]" /><h3 className="mt-7 text-lg font-black">{title as string}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{copy as string}</p></article>;
                })}
              </div>
            </div>
          </section>

          <section className="border-y border-slate-200 bg-[#f7f9fc] px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="max-w-4xl">
                <Eyebrow>Governed execution</Eyebrow>
                <h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">Authority is set by people. Work is accompanied by evidence.</h2>
                <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-600">AION is designed around explicit authority, selected tools and inspectable outcomes. The owner decides what can run automatically, which actions need review and what information each part of the system may use.</p>
              </div>
              <div className="mt-12 grid gap-4 md:grid-cols-3">
                {[
                  [ShieldCheck, "Human-set authority", "People define the boundaries, permissions and escalation rules."],
                  [BrainCircuit, "Coordinated intelligence", "Different models and tools contribute through one controlled operating context."],
                  [FileCheck2, "Evidence and recovery", "Important work can be traced, checked and recovered rather than disappearing into a chat."],
                ].map(([Icon, title, copy]) => {
                  const CardIcon = Icon as LucideIcon;
                  return <article key={title as string} className="rounded-[26px] border border-slate-200 bg-white p-7"><CardIcon size={24} className="text-[#1748e5]" /><h3 className="mt-8 text-xl font-black">{title as string}</h3><p className="mt-3 text-sm leading-6 text-slate-600">{copy as string}</p></article>;
                })}
              </div>
            </div>
          </section>

          <section className="px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="max-w-4xl"><Eyebrow>A wider intelligence programme</Eyebrow><h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">AION extends beyond one business application.</h2><p className="mt-5 max-w-3xl text-lg leading-8 text-slate-600">Tessaris is AION&apos;s principal commercial use case. The wider programme explores symbolic systems, portable intelligence, compression, mathematics and new forms of machine representation.</p></div>
              <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {researchLinks.map((item) => <Link key={item.href} href={item.href} className="group rounded-[26px] border border-slate-200 !bg-white p-7 !text-[#071329] shadow-[0_10px_35px_rgba(7,19,41,.04)] transition hover:-translate-y-1 hover:border-blue-200"><div className="text-xl font-black">{item.label}</div><p className="mt-3 text-sm leading-6 text-slate-600">{item.copy}</p><div className="mt-7 inline-flex items-center gap-2 text-sm font-extrabold text-[#1748e5]">Explore <ArrowRight size={16} className="transition group-hover:translate-x-1" /></div></Link>)}
              </div>
            </div>
          </section>

          <section className="px-5 pb-20 sm:px-8 lg:pb-28">
            <div className="mx-auto max-w-[1240px] overflow-hidden rounded-[34px] bg-[#1748e5] px-6 py-14 text-center text-white shadow-[0_28px_80px_rgba(23,72,229,.22)] sm:px-12 lg:py-20">
              <div className="mx-auto max-w-3xl"><div className="text-[11px] font-black uppercase tracking-[.2em] text-blue-100">Commercial use in the real world</div><h2 className="mt-5 text-balance text-4xl font-black leading-[1.02] tracking-[-.045em] sm:text-6xl">See what AION powers inside Tessaris.</h2><p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-blue-100">Tessaris turns AION&apos;s intelligence and execution capabilities into an AI workforce for owner-led businesses.</p><div className="mt-9"><Link href="/" className="inline-flex min-h-14 items-center justify-center gap-3 rounded-full !border-0 !bg-white px-7 py-3 font-extrabold !text-[#1748e5]">Explore Tessaris <ArrowRight size={18} /></Link></div></div>
            </div>
          </section>
        </main>

        <footer className="border-t border-slate-200 bg-[#071329] px-5 py-14 text-white sm:px-8">
          <div className="mx-auto max-w-[1240px]">
            <div className="grid gap-10 border-b border-white/10 pb-10 md:grid-cols-[1.4fr_.6fr]">
              <div><div className="text-xl font-black">AION by Tessaris</div><p className="mt-3 max-w-md text-sm leading-6 text-slate-400">A governed intelligence and execution system combining selected models, business context, tools, memory, authority and evidence.</p></div>
              <div><div className="text-[10px] font-black uppercase tracking-[.18em] text-slate-500">Explore</div><div className="mt-4 grid gap-3 text-sm font-bold"><Link href="/" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Tessaris for business</Link><Link href="/pricing" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Pricing</Link><Link href="/privacy" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Privacy Policy</Link><Link href="/terms" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Terms of Service</Link></div></div>
            </div>
            <div className="flex flex-col gap-3 pt-7 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between"><span>© 2026 Tessaris. AION research and product development.</span><span className="inline-flex items-center gap-2"><FileCheck2 size={14} /> Claims reflect current release status</span></div>
          </div>
        </footer>

        <style jsx global>{`
          .tessaris-launch { scroll-behavior: smooth; }
          .tessaris-launch h1, .tessaris-launch h2, .tessaris-launch h3 { text-wrap: balance; }
          @media (prefers-reduced-motion: reduce) { .tessaris-launch { scroll-behavior: auto; } }
        `}</style>
      </div>
    </>
  );
}
