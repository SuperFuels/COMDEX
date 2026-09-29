"use client";

import Head from "next/head";
import Link from "next/link";
import { Check, CreditCard, Gift, ShieldCheck, Users } from "lucide-react";
import { useState } from "react";
import Shell from "@/components/Shell";
import styles from "@/styles/Pricing.module.css";

type CreditOption = {
  credits: number;
  price: number;
  saving?: number;
};

const proCredits: CreditOption[] = [
  { credits: 100, price: 25 },
  { credits: 200, price: 50 },
  { credits: 400, price: 100 },
  { credits: 800, price: 200 },
  { credits: 1200, price: 294, saving: 2 },
  { credits: 2000, price: 480, saving: 4 },
  { credits: 3000, price: 705, saving: 6 },
  { credits: 4000, price: 920, saving: 8 },
  { credits: 5000, price: 1125, saving: 10 },
  { credits: 7500, price: 1688, saving: 10 },
  { credits: 10000, price: 2250, saving: 10 },
];

const businessCredits: CreditOption[] = [
  { credits: 100, price: 50 },
  { credits: 200, price: 100 },
  { credits: 400, price: 200 },
  { credits: 800, price: 400 },
  { credits: 1200, price: 588, saving: 2 },
  { credits: 2000, price: 960, saving: 4 },
  { credits: 3000, price: 1410, saving: 6 },
  { credits: 4000, price: 1840, saving: 8 },
  { credits: 5000, price: 2250, saving: 10 },
  { credits: 7500, price: 3300, saving: 12 },
  { credits: 10000, price: 4300, saving: 14 },
];

const freeFeatures = [
  "Private Tessaris workspace",
  "Core AION experience",
  "Connected model preview",
  "Community support",
];

const proFeatures = [
  "Everything in Free",
  "100 Pro credits included",
  "Credit rollovers",
  "On-demand credit top-ups",
  "Unlimited collaborators",
  "Business connections",
  "Email support",
];

const businessFeatures = [
  "Everything in Pro",
  "100 Business credits included",
  "Unlimited users",
  "Team workspace",
  "Role-based access",
  "Governed departments",
  "Priority support",
];

const enterpriseFeatures = [
  "Everything in Business",
  "Volume-based pricing",
  "Unlimited users",
  "Directory sync (SCIM)",
  "Audit and governance controls",
  "Private deployment options",
  "Named onboarding and support",
];

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-GB").format(value);
}

function CreditPicker({
  name,
  options,
  selected,
  onSelect,
}: {
  name: string;
  options: CreditOption[];
  selected: CreditOption;
  onSelect: (option: CreditOption) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.creditPicker}>
      <button
        type="button"
        className={styles.creditTrigger}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((value) => !value)}
      >
        <span>{formatNumber(selected.credits)} monthly credits</span>
        <span className={styles.chevron}>{open ? "⌃" : "⌄"}</span>
      </button>
      {open && (
        <div className={styles.creditMenu} role="listbox" aria-label={`${name} monthly credits`}>
          {options.map((option) => (
            <button
              type="button"
              role="option"
              aria-selected={option.credits === selected.credits}
              className={`${styles.creditOption} ${option.credits === selected.credits ? styles.selectedOption : ""}`}
              key={option.credits}
              onClick={() => {
                onSelect(option);
                setOpen(false);
              }}
            >
              <strong>{formatNumber(option.credits)} credits</strong>
              <span>{option.saving ? <em>Save {option.saving}%</em> : null}<b>€{formatNumber(option.price)} /mo</b></span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className={styles.featureList}>
      {items.map((item) => <li key={item}><Check size={16} strokeWidth={2.2} /><span>{item}</span></li>)}
    </ul>
  );
}

export default function PricingPage() {
  const [pro, setPro] = useState(proCredits[0]);
  const [business, setBusiness] = useState(businessCredits[0]);

  return (
    <>
      <Head>
        <title>Pricing — Tessaris</title>
        <meta name="description" content="Choose a Tessaris plan for individuals, teams and governed enterprise intelligence." />
      </Head>
      <Shell activeKey="pricing" maxWidth="max-w-none" className="!bg-white !text-[#111315]">
        <section className={styles.page}>
          <header className={styles.hero}>
            <div className={styles.eyebrow}><span /> Tessaris plans</div>
            <h1>Intelligence that grows with your business.</h1>
            <p>Start with the core platform, then add the monthly intelligence capacity and governance your team needs.</p>
          </header>

          <div className={styles.planGrid}>
            <article className={styles.planCard}>
              <div className={styles.planTop}>
                <div><span className={styles.planNumber}>01</span><h2>Free</h2><p>Explore Tessaris and build your first governed workspace.</p></div>
                <div className={styles.price}><strong>€0</strong><span>/ month</span></div>
                <div className={styles.fixedSpace} />
                <Link className={styles.secondaryCta} href="/register?plan=free">Get started</Link>
              </div>
              <div className={styles.planMeta}><span><CreditCard size={15} />No credit card needed</span><span><Gift size={15} />Free access</span></div>
              <FeatureList items={freeFeatures} />
            </article>

            <article className={`${styles.planCard} ${styles.featuredCard}`}>
              <div className={styles.recommended}>Most popular</div>
              <div className={styles.planTop}>
                <div><span className={styles.planNumber}>02</span><h2>Pro</h2><p>For founders and fast-moving teams building with AION.</p></div>
                <div className={styles.price}><strong>€{formatNumber(pro.price)}</strong><span>/ month incl. VAT</span></div>
                <CreditPicker name="Pro" options={proCredits} selected={pro} onSelect={setPro} />
                <Link className={styles.primaryCta} href={`/register?plan=pro&credits=${pro.credits}`}>Get started</Link>
              </div>
              <div className={styles.planMeta}><span><Users size={15} />Unlimited collaborators</span><span><Gift size={15} />Flexible credits</span></div>
              <FeatureList items={proFeatures} />
            </article>

            <article className={styles.planCard}>
              <div className={styles.planTop}>
                <div><span className={styles.planNumber}>03</span><h2>Business</h2><p>Advanced controls and operating intelligence for growing teams.</p></div>
                <div className={styles.price}><strong>€{formatNumber(business.price)}</strong><span>/ month incl. VAT</span></div>
                <CreditPicker name="Business" options={businessCredits} selected={business} onSelect={setBusiness} />
                <Link className={styles.secondaryCta} href={`/register?plan=business&credits=${business.credits}`}>Get started</Link>
              </div>
              <div className={styles.planMeta}><span><Users size={15} />Unlimited users</span><span><ShieldCheck size={15} />Governed workspace</span></div>
              <FeatureList items={businessFeatures} />
            </article>

            <article className={styles.planCard}>
              <div className={styles.planTop}>
                <div><span className={styles.planNumber}>04</span><h2>Enterprise</h2><p>Flexibility, scale and governance for complex organisations.</p></div>
                <div className={`${styles.price} ${styles.enterprisePrice}`}><strong>Platform fee</strong><span>Volume-based pricing</span></div>
                <div className={styles.fixedSpace} />
                <Link className={styles.secondaryCta} href="/register?plan=enterprise">Book a demo</Link>
              </div>
              <div className={styles.planMeta}><span><CreditCard size={15} />Volume pricing</span><span><Users size={15} />Unlimited users</span></div>
              <FeatureList items={enterpriseFeatures} />
            </article>
          </div>

          <footer className={styles.pricingFooter}>
            <div><span className={styles.footerDot} /><strong>Governed by design</strong><p>Plans, allowances and package wording can be refined without changing the pricing structure.</p></div>
            <Link href="/register">Talk to Tessaris <span aria-hidden="true">→</span></Link>
          </footer>
        </section>
      </Shell>
    </>
  );
}
