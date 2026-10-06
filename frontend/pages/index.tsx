import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BadgeCheck,
  Bot,
  BrainCircuit,
  BriefcaseBusiness,
  CalendarClock,
  ChartNoAxesCombined,
  Check,
  CircleDollarSign,
  FileCheck2,
  Headphones,
  Laptop,
  Megaphone,
  Network,
  PhoneCall,
  Scale,
  ShieldCheck,
  Sparkles,
  UsersRound,
  Workflow,
} from "lucide-react";

type Outcome = {
  icon: LucideIcon;
  title: string;
  promise: string;
  outcomes: string[];
};

const outcomes: Outcome[] = [
  {
    icon: PhoneCall,
    title: "Sales",
    promise: "More opportunities followed up. Fewer leads left waiting.",
    outcomes: ["Track results and next steps", "Handle inbound and outbound calls", "Confirm and follow up appointments"],
  },
  {
    icon: Megaphone,
    title: "Marketing",
    promise: "A marketing team that keeps creating, publishing and improving.",
    outcomes: ["Create content, images and video", "Use your brand voice and personas", "Schedule, measure and adapt campaigns"],
  },
  {
    icon: BriefcaseBusiness,
    title: "Operations",
    promise: "One operational lead coordinating the work across your business.",
    outcomes: ["Coordinate specialist agents", "Surface delays and exceptions", "Keep priorities moving"],
  },
  {
    icon: CircleDollarSign,
    title: "Finance",
    promise: "A clearer financial position without waiting for month end.",
    outcomes: ["Reconcile transactions", "Work through invoices and expenses", "Explain performance and risk"],
  },
  {
    icon: Headphones,
    title: "Customer support",
    promise: "Customers get answers while serious issues reach the right person.",
    outcomes: ["Handle incoming enquiries", "Track cases to resolution", "Escalate major issues to operations"],
  },
  {
    icon: UsersRound,
    title: "People",
    promise: "Your people operations stay current as the business changes.",
    outcomes: ["Manage people records", "Track movement and responsibilities", "Support routine people workflows"],
  },
  {
    icon: Scale,
    title: "Legal",
    promise: "Day-to-day legal questions and documents get an intelligent first pass.",
    outcomes: ["Review business documents", "Identify obligations and risk", "Prepare issues for expert review"],
  },
  {
    icon: Workflow,
    title: "Automation suite",
    promise: "Repeatable digital work keeps moving, even when your team is offline.",
    outcomes: ["Connect triggers, tools and agents", "Route decisions and approvals", "Run business processes 24/7"],
  },
  {
    icon: ShieldCheck,
    title: "Cybersecurity",
    promise: "Your technology stack is monitored continuously, not only after something goes wrong.",
    outcomes: ["Watch systems and access 24/7", "Identify suspicious activity and risk", "Escalate threats for rapid action"],
  },
  {
    icon: ChartNoAxesCombined,
    title: "Project management",
    promise: "Projects keep moving because ownership, deadlines and blockers remain visible.",
    outcomes: ["Coordinate tasks and responsibilities", "Track milestones and delivery", "Surface blockers and overdue work"],
  },
];

const operatingTools: Array<{ icon: LucideIcon; title: string; copy: string }> = [
  { icon: Network, title: "Built-in CRM", copy: "Customers, conversations, opportunities and outcomes stay connected." },
  { icon: CalendarClock, title: "Work & scheduling", copy: "Appointments, work and follow-ups move from plan to action." },
  { icon: ChartNoAxesCombined, title: "Project management", copy: "See ownership, progress, blockers and the next useful action." },
  { icon: Bot, title: "Agent Market", copy: "Prepare your business for secure agent-to-agent discovery and transactions." },
];

const footerLinks = [
  { label: "Launch", href: "/launch" },
  { label: "AION Business", href: "/aion-business", public: false },
  { label: "Glyph OS", href: "/glyph" },
  { label: "Compression", href: "/compression" },
  { label: "Symatics", href: "/symatics" },
  { label: "Photon Algebra", href: "/photon-algebra-demo" },
  { label: "Photon Binary", href: "/photon-binary" },
];

function Eyebrow({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <div className={`mb-4 text-[11px] font-black uppercase tracking-[0.2em] ${dark ? "text-blue-300" : "text-[#1748e5]"}`}>
      {children}
    </div>
  );
}

export default function HomePage() {
  return (
    <>
      <Head>
        <title>Tessaris — The AI operating system for your business</title>
        <meta
          name="description"
          content="Give every core function an AI team, coordinate it from one intelligent boardroom and keep your business moving with Tessaris."
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
                  alt="Tessaris spatial boardroom with AION and specialist AI models meeting around the business table"
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
                  <Sparkles size={14} aria-hidden="true" /> The business operating system
                </div>
                <h1 className="mx-auto max-w-4xl text-balance text-5xl font-black leading-[.96] tracking-[-.055em] sm:text-7xl lg:text-[78px]">
                  Your business gets an <span className="text-[#1748e5]">AI workforce.</span>
                </h1>
                <p className="mx-auto mt-7 max-w-3xl text-balance text-lg leading-8 text-slate-600 sm:text-xl">
                  Tessaris gives every core function its own specialist agents—then coordinates them as one business. Sales follows up. Marketing keeps creating. Finance stays current. Operations keeps everything moving.
                </p>
                <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
                  <Link href="/register" className="group inline-flex min-h-14 items-center justify-center gap-3 rounded-full !border-0 !bg-[#1748e5] px-7 py-3 text-base font-extrabold !text-white shadow-[0_16px_38px_rgba(23,72,229,.24)] transition hover:!bg-[#1039bc]">
                    Join the launch <ArrowRight size={18} className="transition group-hover:translate-x-1" />
                  </Link>
                  <a href="#outcomes" className="inline-flex min-h-14 items-center justify-center rounded-full border border-slate-300 !bg-white px-7 py-3 text-base font-extrabold !text-[#071329] transition hover:border-blue-300 hover:!bg-blue-50">See what it runs</a>
                </div>
                <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm font-semibold text-slate-600">
                  {["Runs locally", "Works with your models", "Human approval built in"].map((item) => <span key={item} className="inline-flex items-center gap-2"><Check size={16} className="text-[#18a690]" />{item}</span>)}
                </div>
              </div>
            </div>
          </section>

          <section className="border-b border-slate-200 bg-[#071329] px-5 py-8 text-white sm:px-8">
            <div className="mx-auto grid max-w-[1240px] gap-5 text-center sm:grid-cols-3">
              {[
                ["One system", "Every core function connected"],
                ["Your intelligence", "Local models or expert APIs"],
                ["Always working", "Agents and automations, 24/7"],
              ].map(([title, copy]) => (
                <div key={title} className="border-white/10 sm:border-r sm:last:border-0">
                  <div className="text-lg font-black">{title}</div><div className="mt-1 text-sm text-slate-400">{copy}</div>
                </div>
              ))}
            </div>
          </section>

          <section aria-label="Interactive business automation story" className="border-b border-slate-200 bg-white px-2 py-12 sm:px-5 lg:py-16">
            <div className="mx-auto max-w-[1380px] overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_22px_70px_rgba(7,19,41,.08)]">
              <iframe
                title="Tessaris business automation demonstration"
                src="/concepts/business-automation/index.html"
                className="block h-[1480px] w-full border-0 sm:h-[1040px] lg:h-[840px]"
                loading="lazy"
              />
            </div>
          </section>

          <section id="outcomes" className="scroll-mt-24 bg-[#f7f9fc] px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="max-w-3xl">
                <Eyebrow>An AI team for every function</Eyebrow>
                <h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">Not more software to manage. More work completed.</h2>
                <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">You speak to each Pilot naturally. It understands the outcome, uses the tools and business data available to it, and keeps consequential actions behind your approval.</p>
              </div>
              <div className="mt-12 grid gap-4 md:grid-cols-2">
                {outcomes.map(({ icon: Icon, title, promise, outcomes: bullets }) => (
                  <article key={title} className="group rounded-[26px] border border-slate-200 bg-white p-6 shadow-[0_10px_35px_rgba(7,19,41,.04)] transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-[0_18px_50px_rgba(23,72,229,.10)] sm:p-8">
                    <div className="flex items-start gap-4">
                      <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-blue-50 text-[#1748e5]"><Icon size={23} /></div>
                      <div><h3 className="text-xl font-black">{title}</h3><p className="mt-2 text-lg font-bold leading-7 text-slate-700">{promise}</p></div>
                    </div>
                    <div className="mt-6 grid gap-2 border-t border-slate-100 pt-5 sm:grid-cols-3">
                      {bullets.map((bullet) => <div key={bullet} className="flex gap-2 text-sm leading-5 text-slate-600"><Check size={15} className="mt-0.5 shrink-0 text-[#18a690]" />{bullet}</div>)}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="relative overflow-hidden bg-[#071329] px-5 py-20 text-white sm:px-8 lg:py-28">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_75%_30%,rgba(23,105,255,.22),transparent_32%)]" />
            <div className="relative mx-auto max-w-[1240px]">
              <div className="max-w-4xl">
                <Eyebrow dark>The intelligence boardroom</Eyebrow>
                <h2 className="text-balance text-4xl font-black leading-[1.02] tracking-[-.045em] sm:text-6xl">A board that watches the whole business—not one dashboard at a time.</h2>
                <p className="mt-6 text-lg leading-8 text-slate-300">Bring AION together with your preferred local and API models in a spatial 3D/4D boardroom. They examine the same business plan, challenge the evidence and turn decisions into coordinated work for your agents.</p>
                <ul className="mt-7 grid gap-3 text-sm font-semibold text-slate-200 sm:grid-cols-3">
                  {["Real-time intelligence across departments", "Model experts called only when their strengths are needed", "Results checked against the plan and adjusted continuously"].map((item) => <li key={item} className="flex gap-3"><BadgeCheck size={18} className="mt-0.5 shrink-0 text-blue-300" />{item}</li>)}
                </ul>
              </div>

              <figure className="mt-12 overflow-hidden rounded-[30px] border border-white/15 bg-[#102141] shadow-[0_34px_90px_rgba(0,0,0,.35)]">
                <div className="relative aspect-[3216/1334] w-full">
                  <Image src="/tessaris-spatial-boardroom-clean.png" alt="Tessaris spatial AI boardroom with four intelligent agents meeting around a central table" fill sizes="(max-width: 1280px) 100vw, 1240px" className="object-cover" />
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-[#071329]/90 to-transparent" />
                  <div className="absolute bottom-4 left-4 right-4 flex flex-col gap-3 sm:bottom-6 sm:left-6 sm:right-6 sm:flex-row sm:items-end sm:justify-between">
                    <div className="rounded-2xl border border-white/15 bg-[#071329]/80 px-4 py-3 backdrop-blur-md">
                      <div className="text-[9px] font-black uppercase tracking-[.2em] text-blue-300">Live board session</div>
                      <div className="mt-1 text-sm font-extrabold text-white sm:text-base">AION and your chosen models working on the same business decision</div>
                    </div>
                    <div className="hidden rounded-full border border-white/15 bg-[#071329]/80 px-4 py-2 text-[10px] font-black uppercase tracking-[.15em] text-slate-200 backdrop-blur-md sm:block">Spatial 3D / 4D boardroom</div>
                  </div>
                </div>
              </figure>
            </div>
          </section>

          <section id="model-rack" className="scroll-mt-24 px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="grid items-center gap-12 lg:grid-cols-[.82fr_1.18fr]">
              <div>
                <Eyebrow>Private by design</Eyebrow>
                <h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">The models work for your business. Your business does not belong to the models.</h2>
                <p className="mt-6 text-lg leading-8 text-slate-600">Run Tessaris on your own machine. Keep open models on removable SD cards, build a physical library of specialist intelligence, and call a favourite AI API only when a job genuinely needs it.</p>
                <div className="mt-7 inline-flex items-center gap-3 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-extrabold text-blue-800"><BadgeCheck size={18} /> A whole model rack. A few cards. Your machine.</div>
              </div>
              <figure className="overflow-hidden rounded-[30px] border border-slate-200 bg-[#071329] shadow-[0_28px_70px_rgba(7,19,41,.18)]">
                <div className="relative aspect-[16/10]">
                  <Image src="/tessaris-open-model-card-rack.png" alt="Compact Tessaris rack holding SD cards labelled with open AI models including Kimi, DeepSeek and Qwen" fill sizes="(max-width: 1024px) 100vw, 720px" className="object-cover" />
                </div>
                <figcaption className="flex flex-col gap-2 border-t border-white/10 px-6 py-5 text-white sm:flex-row sm:items-center sm:justify-between">
                  <div><div className="text-[10px] font-black uppercase tracking-[.19em] text-blue-300">Local intelligence library</div><div className="mt-1 font-extrabold">Swap in the right model for the work.</div></div>
                  <div className="text-xs text-slate-400">Private · removable · expandable</div>
                </figcaption>
              </figure>
              </div>

              <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  [BrainCircuit, "AION", "The in-house intelligence that coordinates your business context and agents."],
                  [Laptop, "Local LLM", "Private day-to-day reasoning without sending every task to the cloud."],
                  [Network, "SD model rack", "Keep a physical library of open models and use each where it performs best."],
                  [Sparkles, "Expert APIs", "Bring in advanced external intelligence for selected jobs."],
                ].map(([Icon, title, copy]) => {
                  const CardIcon = Icon as LucideIcon;
                  return <article key={title as string} className="rounded-3xl border border-slate-200 bg-[#f7f9fc] p-6"><CardIcon size={24} className="text-[#1748e5]" /><h3 className="mt-7 text-lg font-black">{title as string}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{copy as string}</p></article>;
                })}
              </div>
            </div>
          </section>

          <section aria-label="Meet your AI company" className="border-y border-slate-200 bg-white px-2 py-12 sm:px-5 lg:py-16">
            <div className="mx-auto max-w-[1380px] overflow-hidden rounded-[30px] border border-slate-200 bg-white shadow-[0_22px_70px_rgba(7,19,41,.08)]">
              <iframe
                title="Meet your Tessaris AI company"
                src="/concepts/business-automation/team.html"
                className="block h-[1780px] w-full border-0 sm:h-[1320px] lg:h-[980px]"
                loading="lazy"
              />
            </div>
          </section>

          <section className="border-y border-slate-200 bg-[#f7f9fc] px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="max-w-3xl"><Eyebrow>The operating layer</Eyebrow><h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">The tools your agents need are already in the room.</h2><p className="mt-5 text-lg leading-8 text-slate-600">Plan the work, keep the customer record, automate the process and prepare your business for a market where agents can transact with agents.</p></div>

              <article className="mt-12 overflow-hidden rounded-[30px] border border-blue-200 bg-white shadow-[0_20px_55px_rgba(23,72,229,.10)]">
                <div className="grid items-center gap-8 p-6 sm:p-8 lg:grid-cols-[.7fr_1.3fr] lg:p-10">
                  <div>
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-blue-50 text-[#1748e5]"><Workflow size={24} /></div>
                    <div className="mt-7 text-[10px] font-black uppercase tracking-[.2em] text-[#1748e5]">Automation suite</div>
                    <h3 className="mt-3 text-balance text-3xl font-black leading-tight tracking-[-.03em] sm:text-4xl">Automate almost any task or digital process.</h3>
                    <p className="mt-4 text-base leading-7 text-slate-600">Build a workflow once and let it keep working around the clock—connecting apps, business rules and AI decisions without losing control.</p>
                    <div className="mt-6 grid gap-3 text-sm font-semibold text-slate-700">
                      {["Connect triggers, tools and specialist agents", "Route work with AI and keep approvals where needed", "Run repeatable processes 24/7"].map((item) => <div key={item} className="flex gap-3"><Check size={17} className="mt-0.5 shrink-0 text-[#18a690]" />{item}</div>)}
                    </div>
                  </div>
                  <figure className="overflow-hidden rounded-[22px] border border-slate-200 bg-[#f7f9fc]">
                    <div className="relative aspect-[16/9]">
                      <Image src="/tessaris-automation-pipeline.png" alt="Tessaris automation pipeline connecting an email trigger, Mailchimp and an AI enquiry router" fill sizes="(max-width: 1024px) 100vw, 720px" className="object-cover object-center" />
                    </div>
                    <figcaption className="border-t border-slate-200 px-5 py-4 text-xs font-bold text-slate-500">A live business workflow: trigger, action, AI routing and governed execution.</figcaption>
                  </figure>
                </div>
              </article>

              <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {operatingTools.map(({ icon: Icon, title, copy }) => <article key={title} className="rounded-3xl border border-slate-200 bg-white p-6"><Icon size={22} className="text-[#1748e5]" /><h3 className="mt-8 text-lg font-black">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{copy}</p></article>)}
              </div>
            </div>
          </section>

          <section className="px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px] overflow-hidden rounded-[34px] bg-[#1748e5] px-6 py-14 text-center text-white shadow-[0_28px_80px_rgba(23,72,229,.22)] sm:px-12 lg:py-20">
              <div className="mx-auto max-w-3xl"><div className="text-[11px] font-black uppercase tracking-[.2em] text-blue-100">A business that can keep moving</div><h2 className="mt-5 text-balance text-4xl font-black leading-[1.02] tracking-[-.045em] sm:text-6xl">Put advanced intelligence at the centre of your business.</h2><p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-blue-100">Start with the departments you need now. Connect your models, data and tools. Let Tessaris turn the plan into coordinated work.</p><div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row"><Link href="/register" className="inline-flex min-h-14 items-center justify-center gap-3 rounded-full !border-0 !bg-white px-7 py-3 font-extrabold !text-[#1748e5]">Join the launch <ArrowRight size={18} /></Link><Link href="/pricing" className="inline-flex min-h-14 items-center justify-center rounded-full border border-white/30 !bg-transparent px-7 py-3 font-extrabold !text-white hover:!bg-white/10">View pricing</Link></div></div>
            </div>
          </section>
        </main>

        <footer className="border-t border-slate-200 bg-[#071329] px-5 py-14 text-white sm:px-8">
          <div className="mx-auto max-w-[1240px]">
            <div className="grid gap-10 border-b border-white/10 pb-10 md:grid-cols-[1.3fr_.7fr_1fr]">
              <div><div className="text-xl font-black">Tessaris</div><p className="mt-3 max-w-sm text-sm leading-6 text-slate-400">The AI operating system that connects intelligence, agents and the day-to-day work of running a business.</p></div>
              <div><div className="text-[10px] font-black uppercase tracking-[.18em] text-slate-500">Explore</div><div className="mt-4 grid gap-3 text-sm font-bold"><Link href="/market" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Market</Link><Link href="/pricing" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Pricing</Link></div></div>
              <div><div className="text-[10px] font-black uppercase tracking-[.18em] text-slate-500">Tessaris technology</div><div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">{footerLinks.map((link) => link.public === false ? <span key={link.href} className="font-semibold text-slate-500">{link.label}</span> : <Link key={link.href} href={link.href} className="!border-0 !bg-transparent !p-0 !font-semibold !text-slate-400 hover:!text-white">{link.label}</Link>)}</div></div>
            </div>
            <div className="flex flex-col gap-3 pt-7 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between"><span>© 2026 Tessaris. Advanced intelligence, working for your business.</span><span className="inline-flex items-center gap-2"><FileCheck2 size={14} /> Human approval for consequential actions</span></div>
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
