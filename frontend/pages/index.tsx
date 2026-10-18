import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarClock,
  ChartNoAxesCombined,
  Check,
  CircleDollarSign,
  FileCheck2,
  Headphones,
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
    outcomes: ["Coordinate work across the business", "Surface delays and exceptions", "Keep priorities moving"],
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
    outcomes: ["Connect apps, triggers and business rules", "Route work to the right place", "Run business processes 24/7"],
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
  { icon: FileCheck2, title: "Business records", copy: "Documents, decisions and completed work stay organised and easy to find." },
];

function Eyebrow({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <div className={`mb-4 text-[11px] font-black uppercase tracking-[0.2em] ${dark ? "text-blue-300" : "text-[#1748e5]"}`}>
      {children}
    </div>
  );
}

function AutoHeightIframe({ title, src, className }: { title: string; src: string; className: string }) {
  const frameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;

    let observer: ResizeObserver | undefined;
    const syncHeight = () => {
      const document = frame.contentDocument;
      if (!document) return;
      const height = Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight ?? 0);
      if (height > 0 && frame.style.height !== `${height}px`) frame.style.height = `${height}px`;
    };
    const observeContent = () => {
      observer?.disconnect();
      syncHeight();
      const document = frame.contentDocument;
      if (!document) return;
      observer = new ResizeObserver(syncHeight);
      observer.observe(document.documentElement);
      if (document.body) observer.observe(document.body);
    };

    frame.addEventListener("load", observeContent);
    if (frame.contentDocument?.readyState === "complete") observeContent();
    window.addEventListener("resize", syncHeight);
    return () => {
      frame.removeEventListener("load", observeContent);
      window.removeEventListener("resize", syncHeight);
      observer?.disconnect();
    };
  }, []);

  return <iframe ref={frameRef} title={title} src={src} className={className} loading="lazy" scrolling="no" />;
}

export default function HomePage() {
  return (
    <>
      <Head>
        <title>Tessaris — Your business gets an AI workforce</title>
        <meta
          name="description"
          content="Give Sales, Marketing, Finance and Operations their own AI teams, coordinated as one business with Tessaris."
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
                  alt="The Tessaris AI workforce coordinating work around one business table"
                  fill
                  priority
                  sizes="(max-width: 768px) 100vw, 1380px"
                  className="object-cover object-center"
                />
                <div className="absolute inset-x-3 top-4 z-10 flex justify-center sm:top-6">
                  <div className="max-w-[680px] rounded-2xl border border-white/70 bg-[#071329]/88 px-5 py-3 text-center text-white shadow-xl backdrop-blur-md sm:px-8 sm:py-4">
                    <div className="text-[9px] font-black uppercase tracking-[.2em] text-blue-200 sm:text-[11px]">The intelligence boardroom</div>
                    <div className="mt-1 text-sm font-black sm:text-xl">Your board of superintelligent AI advisers</div>
                  </div>
                </div>
                <div className="absolute left-[9%] top-[43%] z-10 -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">Si</div>
                <div className="absolute left-[41.5%] top-[39%] z-10 -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">DeepSeek</div>
                <div className="absolute left-[58%] top-[39%] z-10 -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">Gemini</div>
                <div className="absolute left-[90%] top-[43%] z-10 -translate-x-1/2 -translate-y-full rounded-full border border-white/70 bg-[#071329]/85 px-2.5 py-1 text-[9px] font-black uppercase tracking-[.12em] text-white shadow-lg backdrop-blur-md sm:px-4 sm:py-2 sm:text-xs">Qwen</div>
              </div>

              <div className="relative z-10 mx-auto -mt-2 max-w-[1060px] rounded-[30px] border border-slate-200 bg-white px-6 py-10 text-center shadow-[0_24px_70px_rgba(7,19,41,.10)] sm:-mt-10 sm:px-12 sm:py-14 lg:-mt-16">
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-[11px] font-black uppercase tracking-[0.18em] text-blue-700">
                  <Sparkles size={14} aria-hidden="true" /> The business operating system
                </div>
                <h1 className="mx-auto max-w-4xl text-balance text-5xl font-black leading-[.96] tracking-[-.055em] sm:text-7xl lg:text-[78px]">
                  Your business gets an <span className="text-[#1748e5]">AI workforce.</span>
                </h1>
                <p className="mx-auto mt-7 max-w-3xl text-balance text-lg leading-8 text-slate-600 sm:text-xl">
                  Tessaris gives every core function its own AI team—then coordinates them as one business. Sales follows up. Marketing keeps creating. Finance stays current. Operations keeps everything moving.
                </p>
                <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
                  <Link href="/waitlist" className="group inline-flex min-h-14 items-center justify-center gap-3 rounded-full !border-0 !bg-[#1748e5] px-7 py-3 text-base font-extrabold !text-white shadow-[0_16px_38px_rgba(23,72,229,.24)] transition hover:!bg-[#1039bc]">
                    Join the waitlist <ArrowRight size={18} className="transition group-hover:translate-x-1" />
                  </Link>
                  <a href="#outcomes" className="inline-flex min-h-14 items-center justify-center rounded-full border border-slate-300 !bg-white px-7 py-3 text-base font-extrabold !text-[#071329] transition hover:border-blue-300 hover:!bg-blue-50">See what it can do</a>
                </div>
                <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm font-semibold text-slate-600">
                  {["Built for owner-led businesses", "Works within your rules", "Keeps routine work moving"].map((item) => <span key={item} className="inline-flex items-center gap-2"><Check size={16} className="text-[#18a690]" />{item}</span>)}
                </div>
              </div>
            </div>
          </section>

          <section className="border-b border-slate-200 bg-[#071329] px-5 py-8 text-white sm:px-8">
            <div className="mx-auto grid max-w-[1240px] gap-5 text-center sm:grid-cols-3">
              {[
                ["One business", "Every core function connected"],
                ["Your rules", "You decide what runs automatically"],
                ["Always working", "Routine work keeps moving 24/7"],
              ].map(([title, copy]) => (
                <div key={title} className="border-white/10 sm:border-r sm:last:border-0">
                  <div className="text-lg font-black">{title}</div><div className="mt-1 text-sm text-slate-400">{copy}</div>
                </div>
              ))}
            </div>
          </section>

          <section aria-label="Interactive business automation story" className="border-b border-slate-200 bg-white px-2 py-12 sm:px-5 lg:py-16">
            <div className="mx-auto max-w-[1380px] overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_22px_70px_rgba(7,19,41,.08)]">
              <AutoHeightIframe
                title="Tessaris business automation demonstration"
                src="/concepts/business-automation/index.html"
                className="block h-[1480px] w-full border-0 sm:h-[1040px] lg:h-[840px]"
              />
            </div>
          </section>

          <section id="outcomes" className="scroll-mt-24 bg-[#f7f9fc] px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="max-w-3xl">
                <Eyebrow>An AI team for every function</Eyebrow>
                <h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">Not more software to manage. More work completed.</h2>
                <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">Tell each AI team the outcome you need. You decide what Tessaris can complete automatically and when it should bring a decision back to you.</p>
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

          <section aria-label="Meet your AI company" className="border-y border-slate-200 bg-white px-2 py-12 sm:px-5 lg:py-16">
            <div className="mx-auto max-w-[1380px] overflow-hidden rounded-[30px] border border-slate-200 bg-white shadow-[0_22px_70px_rgba(7,19,41,.08)]">
              <AutoHeightIframe
                title="Meet your Tessaris AI company"
                src="/concepts/business-automation/team.html"
                className="block h-[1780px] w-full border-0 sm:h-[1320px] lg:h-[980px]"
              />
            </div>
          </section>

          <section className="border-y border-slate-200 bg-[#f7f9fc] px-5 py-20 sm:px-8 lg:py-28">
            <div className="mx-auto max-w-[1240px]">
              <div className="max-w-3xl"><Eyebrow>One place to run the business</Eyebrow><h2 className="text-balance text-4xl font-black leading-[1.03] tracking-[-.04em] sm:text-6xl">The tools your AI workforce needs are already connected.</h2><p className="mt-5 text-lg leading-8 text-slate-600">Plan the work, keep customer information together, automate repeatable processes and see what needs your attention.</p></div>

              <article className="mt-12 overflow-hidden rounded-[30px] border border-blue-200 bg-white shadow-[0_20px_55px_rgba(23,72,229,.10)]">
                <div className="grid items-center gap-8 p-6 sm:p-8 lg:grid-cols-[.7fr_1.3fr] lg:p-10">
                  <div>
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-blue-50 text-[#1748e5]"><Workflow size={24} /></div>
                    <div className="mt-7 text-[10px] font-black uppercase tracking-[.2em] text-[#1748e5]">Automation suite</div>
                    <h3 className="mt-3 text-balance text-3xl font-black leading-tight tracking-[-.03em] sm:text-4xl">Automate almost any task or digital process.</h3>
                    <p className="mt-4 text-base leading-7 text-slate-600">Build a process once and let it keep working around the clock—connecting your apps, business rules and AI teams.</p>
                    <div className="mt-6 grid gap-3 text-sm font-semibold text-slate-700">
                      {["Connect apps, triggers and business rules", "Choose what runs automatically and when you step in", "Keep repeatable processes moving 24/7"].map((item) => <div key={item} className="flex gap-3"><Check size={17} className="mt-0.5 shrink-0 text-[#18a690]" />{item}</div>)}
                    </div>
                  </div>
                  <figure className="overflow-hidden rounded-[22px] border border-slate-200 bg-[#f7f9fc]">
                    <div className="relative aspect-[16/9]">
                      <Image src="/tessaris-automation-pipeline.png" alt="Tessaris automation pipeline connecting an email trigger, Mailchimp and an AI enquiry router" fill sizes="(max-width: 1024px) 100vw, 720px" className="object-cover object-center" />
                    </div>
                    <figcaption className="border-t border-slate-200 px-5 py-4 text-xs font-bold text-slate-500">A business workflow moving an enquiry from arrival to the right next action.</figcaption>
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
              <div className="mx-auto max-w-3xl"><div className="text-[11px] font-black uppercase tracking-[.2em] text-blue-100">A business that can keep moving</div><h2 className="mt-5 text-balance text-4xl font-black leading-[1.02] tracking-[-.045em] sm:text-6xl">Give your business the team it has been missing.</h2><p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-blue-100">Start with the functions you need most. Set the rules once, and let Tessaris turn priorities into coordinated work.</p><div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row"><Link href="/waitlist" className="inline-flex min-h-14 items-center justify-center gap-3 rounded-full !border-0 !bg-white px-7 py-3 font-extrabold !text-[#1748e5]">Join the waitlist <ArrowRight size={18} /></Link><Link href="/pricing" className="inline-flex min-h-14 items-center justify-center rounded-full border border-white/30 !bg-transparent px-7 py-3 font-extrabold !text-white hover:!bg-white/10">View pricing</Link></div></div>
            </div>
          </section>
        </main>

        <footer className="border-t border-slate-200 bg-[#071329] px-5 py-14 text-white sm:px-8">
          <div className="mx-auto max-w-[1240px]">
            <div className="grid gap-10 border-b border-white/10 pb-10 md:grid-cols-[1.4fr_.6fr]">
              <div><div className="text-xl font-black">Tessaris</div><p className="mt-3 max-w-sm text-sm leading-6 text-slate-400">The business operating system that gives every core function its own AI team and coordinates them as one business.</p></div>
              <div><div className="text-[10px] font-black uppercase tracking-[.18em] text-slate-500">Explore</div><div className="mt-4 grid gap-3 text-sm font-bold"><Link href="/market" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Market</Link><Link href="/pricing" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Pricing</Link><Link href="/aion" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Si</Link><Link href="/privacy" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Privacy Policy</Link><Link href="/terms" className="!border-0 !bg-transparent !p-0 !text-slate-300 hover:!text-white">Terms of Service</Link></div></div>
            </div>
            <div className="flex flex-col gap-3 pt-7 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between"><span>© 2026 Tessaris. Your business gets an AI workforce.</span><span className="inline-flex items-center gap-2"><FileCheck2 size={14} /> Works within your rules</span></div>
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
