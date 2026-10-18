"use client";

import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { FormEvent, useMemo, useState } from "react";
import { ArrowLeft, Check, Send } from "lucide-react";

type FormStatus = "idle" | "submitting" | "success" | "error";

function queryValue(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] || "" : value || "";
}

export default function WaitlistPage() {
  const router = useRouter();
  const plan = useMemo(() => queryValue(router.query.plan), [router.query.plan]);
  const credits = useMemo(() => queryValue(router.query.credits), [router.query.credits]);
  const [status, setStatus] = useState<FormStatus>("idle");
  const [error, setError] = useState("");

  async function submitWaitlist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setError("");

    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());

    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...values, plan, credits }),
      });

      if (!response.ok) throw new Error("submission_failed");
      form.reset();
      setStatus("success");
    } catch {
      setError("We could not submit your request just now. Please try again shortly.");
      setStatus("error");
    }
  }

  return (
    <>
      <Head>
        <title>Join the waitlist — Tessaris</title>
        <meta name="description" content="Join the Tessaris launch waitlist and tell us a little about your business." />
      </Head>

      <main className="h-[calc(100vh-72px)] min-h-[calc(100vh-72px)] overflow-y-auto overscroll-y-contain bg-[#f7faff] px-5 py-12 text-[#071329] sm:px-8 sm:py-20">
        <div className="mx-auto grid max-w-[1120px] overflow-hidden rounded-[30px] border border-slate-200 bg-white shadow-[0_28px_80px_rgba(7,19,41,.10)] lg:grid-cols-[.82fr_1.18fr]">
          <section className="bg-[#071329] px-7 py-10 text-white sm:px-10 sm:py-14">
            <div className="text-[11px] font-black uppercase tracking-[.2em] text-blue-300">Tessaris launch</div>
            <h1 className="mt-5 text-balance text-4xl font-black leading-[1.02] tracking-[-.045em] sm:text-5xl">
              Join the waitlist for Si.
            </h1>
            <p className="mt-6 text-base leading-7 text-slate-300">
              Tell us about your business and what you want Tessaris to help run. We will contact you as launch access becomes available.
            </p>
            <div className="mt-9 grid gap-4 text-sm font-semibold text-slate-200">
              {["Early launch updates", "A conversation about your business needs", "No payment or commitment"].map((item) => (
                <div key={item} className="flex items-center gap-3"><Check size={17} className="text-[#36d7c1]" />{item}</div>
              ))}
            </div>
            {(plan || credits) && (
              <div className="mt-10 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                Interest carried over from pricing: <strong className="text-white">{plan || "Tessaris"}{credits ? ` · ${credits} credits` : ""}</strong>
              </div>
            )}
          </section>

          <section className="px-6 py-9 sm:px-10 sm:py-12">
            {status === "success" ? (
              <div className="flex min-h-[520px] flex-col items-center justify-center text-center">
                <div className="grid h-16 w-16 place-items-center rounded-full bg-emerald-50 text-emerald-700"><Check size={30} /></div>
                <h2 className="mt-6 text-3xl font-black tracking-[-.035em]">You are on the waitlist.</h2>
                <p className="mt-3 max-w-md leading-7 text-slate-600">Thank you. Your details have reached the Tessaris launch team and we will be in touch.</p>
                <Link href="/" className="mt-8 inline-flex items-center gap-2 !border-0 !bg-transparent font-extrabold !text-[#1748e5]"><ArrowLeft size={17} />Back to Tessaris</Link>
              </div>
            ) : (
              <form onSubmit={submitWaitlist} className="grid gap-5">
                <div><h2 className="text-2xl font-black tracking-[-.03em]">Tell us about you</h2><p className="mt-2 text-sm leading-6 text-slate-600">Fields marked with * are required.</p></div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <label className="grid gap-2 text-sm font-bold">Your name *<input required name="name" maxLength={120} autoComplete="name" className="min-h-12 rounded-xl border border-slate-300 px-4 font-medium outline-none transition focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100" /></label>
                  <label className="grid gap-2 text-sm font-bold">Work email *<input required name="email" type="email" maxLength={254} autoComplete="email" className="min-h-12 rounded-xl border border-slate-300 px-4 font-medium outline-none transition focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100" /></label>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <label className="grid gap-2 text-sm font-bold">Business name *<input required name="businessName" maxLength={160} autoComplete="organization" className="min-h-12 rounded-xl border border-slate-300 px-4 font-medium outline-none transition focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100" /></label>
                  <label className="grid gap-2 text-sm font-bold">Phone<input name="phone" type="tel" maxLength={60} autoComplete="tel" className="min-h-12 rounded-xl border border-slate-300 px-4 font-medium outline-none transition focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100" /></label>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <label className="grid gap-2 text-sm font-bold">Your role<input name="role" maxLength={120} autoComplete="organization-title" placeholder="Founder, director, operations…" className="min-h-12 rounded-xl border border-slate-300 px-4 font-medium outline-none transition placeholder:text-slate-400 focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100" /></label>
                  <label className="grid gap-2 text-sm font-bold">Business size<select name="businessSize" defaultValue="" className="min-h-12 rounded-xl border border-slate-300 bg-white px-4 font-medium outline-none transition focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100"><option value="" disabled>Select a range</option><option>Just me</option><option>2–10 people</option><option>11–50 people</option><option>51–250 people</option><option>251+ people</option></select></label>
                </div>

                <label className="grid gap-2 text-sm font-bold">What would you most like Si to help with?<select name="interest" defaultValue="" className="min-h-12 rounded-xl border border-slate-300 bg-white px-4 font-medium outline-none transition focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100"><option value="" disabled>Select an area</option><option>Running the whole business</option><option>Sales and customer relationships</option><option>Marketing</option><option>Finance</option><option>Operations and scheduling</option><option>Customer support</option><option>Automating repeatable work</option><option>Something else</option></select></label>

                <label className="grid gap-2 text-sm font-bold">Anything else we should know?<textarea name="message" maxLength={2000} rows={4} className="rounded-xl border border-slate-300 px-4 py-3 font-medium outline-none transition focus:border-[#1748e5] focus:ring-4 focus:ring-blue-100" /></label>

                <label className="absolute -left-[9999px]" aria-hidden="true">Website<input name="website" tabIndex={-1} autoComplete="off" /></label>

                {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">{error}</p>}

                <button type="submit" disabled={status === "submitting"} className="inline-flex min-h-13 items-center justify-center gap-2 rounded-full !border-0 !bg-[#1748e5] px-6 py-3 font-extrabold !text-white shadow-[0_14px_30px_rgba(23,72,229,.22)] transition hover:!bg-[#1039bc] disabled:cursor-wait disabled:opacity-60">
                  {status === "submitting" ? "Joining…" : "Join the waitlist"}<Send size={17} />
                </button>
                <p className="text-center text-xs leading-5 text-slate-500">We will use these details only to respond about Tessaris launch access.</p>
              </form>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
