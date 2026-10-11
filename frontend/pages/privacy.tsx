import Head from "next/head";
import Link from "next/link";

export default function PrivacyPolicy() {
  return <>
    <Head><title>Privacy Policy — Tessaris</title><meta name="description" content="How Tessaris handles account, connection and service data." /></Head>
    <main className="min-h-screen bg-[#f7faff] px-5 py-12 text-[#071329] sm:px-8">
      <article className="mx-auto max-w-4xl rounded-[28px] border border-slate-200 bg-white p-7 shadow-[0_20px_60px_rgba(7,19,41,.08)] sm:p-12">
        <Link href="/" className="text-sm font-extrabold text-[#1748e5]">← Tessaris</Link>
        <p className="mt-8 text-xs font-black uppercase tracking-[.18em] text-[#1748e5]">Legal</p>
        <h1 className="mt-3 text-4xl font-black tracking-[-.04em] sm:text-6xl">Privacy Policy</h1>
        <p className="mt-4 text-sm font-semibold text-slate-500">Effective 11 October 2026</p>
        <div className="mt-10 space-y-8 text-base leading-7 text-slate-700">
          <section><h2 className="text-xl font-black text-[#071329]">Who we are</h2><p className="mt-2">Tessaris AI Ltd (“Tessaris”, “we”, “us”) provides an AI business operating system. Tessaris is responsible for the personal information it collects for operating its website, accounts and connected-service features.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Information we process</h2><p className="mt-2">Depending on the features you use, we process account and contact details, service settings, support communications, security and diagnostic records, and information made available by business services that you deliberately connect. For social connections this can include profile identifiers, profile statistics, posts or videos, and engagement statistics. Tessaris does not ask for your social-media password.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Why we process it</h2><p className="mt-2">We use this information to provide and secure the service, complete requested connections, show verified business evidence and analytics, respond to support requests, prevent misuse, and meet legal obligations. We process information needed to perform our service agreement, with your consent where required, and for legitimate interests such as security and service improvement.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Connected services</h2><p className="mt-2">A connection starts only when an authorised user chooses a provider and approves its permission screen. Access tokens are stored in the operating system’s protected credential vault where the local Tessaris product supports it. Tessaris requests only the scopes shown during authorisation. Publishing or advertising actions remain separately approval-gated. You may revoke a connection in Tessaris or through the provider.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Sharing and international processing</h2><p className="mt-2">We disclose information only to service providers needed to operate Tessaris, to a connected provider at your request, or where law requires it. Connected providers process information under their own terms and privacy policies. Some providers may process information outside your country and use lawful transfer safeguards where required.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Retention and security</h2><p className="mt-2">We retain information only for as long as needed for the purposes above, the lifetime of an active account or connection, and any necessary legal, security or dispute period. You can disconnect a provider to remove Tessaris access. We use access controls, encryption in transit and protected credential storage appropriate to the service.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Your rights</h2><p className="mt-2">Subject to applicable law, you may ask for access, correction, deletion, restriction or portability of your personal information, or object to certain processing. You may withdraw consent at any time without affecting earlier lawful processing. You may also complain to your local data-protection authority.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Questions and requests</h2><p className="mt-2">Contact Tessaris AI Ltd through the support or account-contact channel supplied with the Tessaris service. We may update this notice as the product or legal requirements change and will publish the current version here.</p></section>
        </div>
      </article>
    </main>
  </>;
}
