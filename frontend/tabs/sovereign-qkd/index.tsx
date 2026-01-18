"use client";

import QKDSecurityDemo from "./QKDSecurityDemo";

export default function SovereignQKDTab() {
  return (
    // FIX: remove pb-24 + mt-32 patterns that can interact badly with a parent scroll container,
    // and keep this tab as "content-only" (like GlyphTab). Content is unchanged.
    <section className="space-y-16">
      {/* 1. HERO HEADER */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          Sovereign QKD
        </h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Privacy enforced by{" "}
          <span className="text-black font-medium">physical collapse.</span>
        </p>
        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
          A secure channel where the act of interception becomes the alarm — and
          the data can’t be copied without being destroyed.
        </p>
      </div>

      {/* 2. LIVE INTERACTIVE DEMO */}
      <QKDSecurityDemo />

      {/* 3. THE PITCH DECK (UNDERNEATH) */}
      <div className="grid md:grid-cols-2 gap-12 border-t border-gray-100 pt-24">
        {/* The Strategy */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold italic tracking-tight">
              The Observer Advantage
            </h2>
            <p className="text-gray-600 leading-relaxed">
              In classical networks, “security” is a math problem layered on top
              of a copyable medium. In GlyphNet, the medium itself is part of the
              security model: a coherent transmission behaves like a state that
              can be verified at the destination.
              <br />
              <br />
              The key idea is simple: if an unauthorized observer touches the
              channel, they introduce interference. That disturbance becomes
              detectable immediately — and the session can be invalidated before
              meaningful content is recovered.
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-[#0071e3] mb-4">
              What we are testing
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              The demo shows a secure handshake progressing from IDLE → SECURE,
              then simulates a tap attempt that triggers a collapse event. The
              log stream is the “flight recorder”: a human-readable trace of
              interference detection and session termination.
            </p>
          </div>
        </div>

        {/* The Impact */}
        <div className="space-y-12">
          <div className="grid grid-cols-1 gap-8">
            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">
                Decoherence Fingerprinting
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                The SRK-14 ledger concept is that stability is measurable. A tap
                introduces phase noise — a “fingerprint” that can be detected
                and used to revoke the session key before any payload is safely
                interpreted.
              </p>
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">
                Deployment & Use Cases
              </h3>
              <ul className="space-y-3 text-sm text-gray-500">
                <li className="flex items-start gap-3">
                  <span className="text-[#0071e3] font-bold">01.</span>
                  <span>
                    <strong>Sovereign agents:</strong> high-level intent exchange
                    over public infrastructure with immediate tamper evidence.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#0071e3] font-bold">02.</span>
                  <span>
                    <strong>Critical links:</strong> detect line taps in
                    real-time and rotate keys automatically.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#0071e3] font-bold">03.</span>
                  <span>
                    <strong>Auditability:</strong> the channel produces a
                    verifiable trace of “no-interference” delivery conditions.
                  </span>
                </li>
              </ul>
            </div>
          </div>

          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500 mb-2">
              The Result
            </h4>
            <p className="text-xl font-medium italic leading-snug">
              “If the wave arrives coherent, we have evidence no one looked.
              If someone looks, the system knows — and the session dies.”
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}