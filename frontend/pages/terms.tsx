import Head from "next/head";
import Link from "next/link";

export default function TermsOfService() {
  return <>
    <Head><title>Terms of Service — Tessaris</title><meta name="description" content="Terms governing use of Tessaris." /></Head>
    <main className="min-h-screen bg-[#f7faff] px-5 py-12 text-[#071329] sm:px-8">
      <article className="mx-auto max-w-4xl rounded-[28px] border border-slate-200 bg-white p-7 shadow-[0_20px_60px_rgba(7,19,41,.08)] sm:p-12">
        <Link href="/" className="text-sm font-extrabold text-[#1748e5]">← Tessaris</Link>
        <p className="mt-8 text-xs font-black uppercase tracking-[.18em] text-[#1748e5]">Legal</p>
        <h1 className="mt-3 text-4xl font-black tracking-[-.04em] sm:text-6xl">Terms of Service</h1>
        <p className="mt-4 text-sm font-semibold text-slate-500">Effective 11 October 2026</p>
        <div className="mt-10 space-y-8 text-base leading-7 text-slate-700">
          <section><h2 className="text-xl font-black text-[#071329]">Agreement</h2><p className="mt-2">These terms govern access to Tessaris, an AI business operating system provided by Tessaris AI Ltd. By creating an account or using the service, you agree to these terms and our Privacy Policy. If you use Tessaris for an organisation, you confirm that you can bind that organisation.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Using Tessaris</h2><p className="mt-2">You must provide accurate information, protect access to your account and use Tessaris lawfully. You remain responsible for your business decisions, content, connected accounts and approvals. Do not use Tessaris to infringe rights, access systems without authority, distribute harmful material or evade provider rules.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">AI output and approvals</h2><p className="mt-2">AI-generated output may be incomplete or inaccurate and must be reviewed before use. Tessaris is designed to keep consequential external actions approval-gated, but you remain responsible for checking drafts, analytics, instructions and actions before approving them. Tessaris does not provide legal, financial, medical or other regulated professional advice.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Connected services</h2><p className="mt-2">When you connect a third-party service, you authorise Tessaris to use the permissions you select for your requested features. The third party’s own terms and policies also apply. You may disconnect a service at any time. We are not responsible for third-party availability, changes, content or decisions.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Your content</h2><p className="mt-2">You retain ownership of your content. You grant Tessaris the limited rights needed to host, process and transmit it solely to provide, secure and improve the service as configured by you. You confirm that you have the necessary rights and permissions for content and connected business data.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Availability and changes</h2><p className="mt-2">We may improve, change, suspend or discontinue features, including integrations that depend on third-party platforms. We aim to operate Tessaris with reasonable care but do not promise uninterrupted or error-free availability. Beta and preview features may change or be withdrawn.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Suspension and termination</h2><p className="mt-2">You may stop using Tessaris and disconnect services at any time. We may restrict or terminate access where reasonably necessary for security, unlawful use, material breach or protection of Tessaris, users or third parties. Provisions that by their nature should survive termination will continue.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Liability</h2><p className="mt-2">To the maximum extent permitted by law, Tessaris AI Ltd is not liable for indirect or consequential loss, lost profits or loss caused by unreviewed AI output, user-approved actions or third-party services. Nothing in these terms excludes liability that cannot lawfully be excluded.</p></section>
          <section><h2 className="text-xl font-black text-[#071329]">Questions</h2><p className="mt-2">Contact Tessaris AI Ltd through the support or account-contact channel supplied with the Tessaris service. We may update these terms and will publish the current version here.</p></section>
        </div>
      </article>
    </main>
  </>;
}
