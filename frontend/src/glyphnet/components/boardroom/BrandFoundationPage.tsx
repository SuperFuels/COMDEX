"use client";

import { useMemo, useState } from "react";

type FoundationSectionKey =
  | "overview"
  | "brand_core"
  | "audience"
  | "offers"
  | "funnel_goals"
  | "messaging"
  | "tone_of_voice"
  | "visual_identity"
  | "assets"
  | "seo_keywords"
  | "hashtags"
  | "compliance"
  | "content_rules"
  | "approval_rules"
  | "strategy_summary";

type BrandFoundationModel = {
  status: "draft" | "active" | "archived";
  updatedAt: string;
  missionStatement: string;
  uniqueValueProp: string;
  businessGoals: string[];
  audienceFunnel: string;
  targetAudience: string;
  personas: Array<{
    id: string;
    name: string;
    summary: string;
    painPoints: string[];
    desiredOutcomes: string[];
    channels: string[];
  }>;
  offers: Array<{
    id: string;
    name: string;
    description: string;
    price?: string;
    audience: string;
    funnelStage: string;
  }>;
  funnelGoals: {
    awareness: string;
    traffic: string;
    leads: string;
    conversions: string;
    retention: string;
  };
  messaging: {
    primaryMessage: string;
    supportingPoints: string[];
    ctas: string[];
    proofPoints: string[];
  };
  tone: {
    brandVoice: string;
    doSay: string[];
    dontSay: string[];
    writingStyle: string[];
  };
  visualIdentity: {
    brandLook: string;
    primaryColor: string;
    accentColor: string;
    fontPrimary: string;
    fontSecondary: string;
    visualRules: string[];
  };
  assets: Array<{
    id: string;
    name: string;
    type: string;
    status: "ready" | "missing" | "needs_refresh";
  }>;
  seo: {
    primaryKeywords: string[];
    secondaryKeywords: string[];
    localKeywords: string[];
  };
  hashtags: string[];
  compliance: {
    mustInclude: string[];
    avoid: string[];
    approvalTriggers: string[];
  };
  contentRules: string[];
  approvalRules: string[];
  strategySummary: {
    currentFocus: string;
    monthlyObjective: string;
    kpis: string[];
    publishingRhythm: string;
  };
};

const NAV_ITEMS: Array<{ key: FoundationSectionKey; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "brand_core", label: "Brand Core" },
  { key: "audience", label: "Audience" },
  { key: "offers", label: "Offers" },
  { key: "funnel_goals", label: "Funnel Goals" },
  { key: "messaging", label: "Messaging" },
  { key: "tone_of_voice", label: "Tone of Voice" },
  { key: "visual_identity", label: "Visual Identity" },
  { key: "assets", label: "Assets" },
  { key: "seo_keywords", label: "SEO / Keywords" },
  { key: "hashtags", label: "Hashtags" },
  { key: "compliance", label: "Compliance / Guardrails" },
  { key: "content_rules", label: "Content Rules" },
  { key: "approval_rules", label: "Approval Rules" },
  { key: "strategy_summary", label: "Strategy Summary" },
];

const INITIAL_FOUNDATION: BrandFoundationModel = {
  status: "active",
  updatedAt: "11 Apr 2026, 15:12",
  missionStatement:
    "Help local small businesses get more customers through clear, trusted, conversion-focused marketing.",
  uniqueValueProp:
    "A done-for-you local marketing engine that combines brand clarity, conversion strategy, and operational content production.",
  businessGoals: [
    "Increase brand awareness in core service towns",
    "Drive more traffic to the website and profile pages",
    "Capture more inbound leads and email signups",
    "Improve conversion from content views to enquiries",
  ],
  audienceFunnel:
    "Turn cold local viewers into warm prospects, then into enquiries, booked calls, and paying customers.",
  targetAudience:
    "Local small business owners and service buyers across key towns who value trust, clarity, and visible proof.",
  personas: [
    {
      id: "persona_1",
      name: "Local Service Buyer",
      summary:
        "Needs a trusted provider quickly and responds to clear offers, proof, and locality.",
      painPoints: [
        "Does not know who to trust",
        "Wants quick response",
        "Worries about poor workmanship",
      ],
      desiredOutcomes: [
        "Find a reliable provider",
        "Get reassurance through reviews and visuals",
        "Book quickly",
      ],
      channels: ["Facebook", "Google", "WhatsApp"],
    },
    {
      id: "persona_2",
      name: "Owner-Operator Business",
      summary:
        "Wants more local leads without needing to become a full-time marketer.",
      painPoints: [
        "Inconsistent lead flow",
        "No real content strategy",
        "Limited time to create content",
      ],
      desiredOutcomes: [
        "Steady enquiries",
        "Clear monthly plan",
        "Simple approval flow",
      ],
      channels: ["Facebook", "Instagram", "Email"],
    },
  ],
  offers: [
    {
      id: "offer_1",
      name: "Spring Upgrade Campaign",
      description: "Seasonal campaign designed to generate direct local enquiries.",
      price: "From £299",
      audience: "Warm local homeowners and businesses",
      funnelStage: "consideration",
    },
    {
      id: "offer_2",
      name: "Free Quote Lead Magnet",
      description: "Low-friction CTA designed to capture enquiries and email leads.",
      audience: "Cold and warm traffic",
      funnelStage: "lead_capture",
    },
  ],
  funnelGoals: {
    awareness: "Increase reach and recognition in local towns",
    traffic: "Drive visitors to landing pages and business profiles",
    leads: "Capture quote requests and email signups",
    conversions: "Turn enquiries into booked work",
    retention: "Build repeat demand through useful follow-up content",
  },
  messaging: {
    primaryMessage:
      "Trusted local service, clear communication, and simple next steps.",
    supportingPoints: [
      "Use proof, examples, and before/after visuals",
      "Focus on locality and trust",
      "Keep calls to action simple and direct",
    ],
    ctas: [
      "Book a free quote",
      "Send us a message",
      "View local services",
      "Get pricing today",
    ],
    proofPoints: [
      "Local jobs completed",
      "Customer testimonials",
      "Before and after visuals",
      "Fast response times",
    ],
  },
  tone: {
    brandVoice: "Confident, clean, practical, helpful, locally trusted.",
    doSay: [
      "Clear local-language offers",
      "Helpful and grounded explanations",
      "Simple confidence-building proof",
    ],
    dontSay: [
      "Overhyped claims",
      "Aggressive sales language",
      "Corporate jargon",
    ],
    writingStyle: [
      "Short paragraphs",
      "Simple calls to action",
      "Strong hooks and practical value",
    ],
  },
  visualIdentity: {
    brandLook: "Modern local-business marketing with clean cards and simple proof-led visuals.",
    primaryColor: "#1a8aff",
    accentColor: "#f41aff",
    fontPrimary: "Inter",
    fontSecondary: "Manrope",
    visualRules: [
      "Use clear hierarchy",
      "Prefer clean cards over clutter",
      "Show proof visually where possible",
      "Use consistent CTA styling",
    ],
  },
  assets: [
    { id: "asset_1", name: "Primary Logo", type: "logo", status: "ready" },
    { id: "asset_2", name: "Brand Icons", type: "icons", status: "ready" },
    { id: "asset_3", name: "Service Photos", type: "images", status: "needs_refresh" },
    { id: "asset_4", name: "Testimonial Cards", type: "social_proof", status: "missing" },
  ],
  seo: {
    primaryKeywords: ["local marketing", "small business marketing", "lead generation"],
    secondaryKeywords: ["content strategy", "facebook content", "local SEO"],
    localKeywords: ["Almería services", "Arboleas businesses", "Albox local services"],
  },
  hashtags: [
    "#LocalBusiness",
    "#TrustedServices",
    "#SmallBusinessGrowth",
    "#AlmeriaBusiness",
    "#LeadGeneration",
  ],
  compliance: {
    mustInclude: [
      "No autonomous publishing by default",
      "Use approval for key outbound content",
      "Keep claims truthful and grounded",
    ],
    avoid: [
      "Medical/legal sounding guarantees",
      "Misleading urgency",
      "Excessive posting frequency",
    ],
    approvalTriggers: [
      "Any ad spend launch",
      "Any publish-ready campaign asset",
      "Any sensitive offer or pricing change",
    ],
  },
  contentRules: [
    "Do not publish automatically.",
    "Do not exceed one main post per day unless explicitly planned.",
    "Each piece of content must map to a funnel goal.",
    "Use a clear CTA on action-oriented posts.",
  ],
  approvalRules: [
    "Draft mode by default",
    "High-risk offers require approval",
    "Paid campaign changes require approval",
    "Tone/brand deviations require approval",
  ],
  strategySummary: {
    currentFocus: "Spring upgrade offer with strong local trust positioning.",
    monthlyObjective: "Increase qualified inbound enquiries by 20%.",
    kpis: [
      "Website clicks",
      "Quote requests",
      "Email signups",
      "CTR",
      "Lead-to-enquiry conversion",
    ],
    publishingRhythm: "3 core posts per week, 2 supporting posts, 1 review cycle.",
  },
};

function shellCardStyle(): React.CSSProperties {
  return {
    borderRadius: 18,
    border: "1px solid rgba(203,213,225,0.9)",
    background: "rgba(255,255,255,0.88)",
    boxShadow: "0 10px 30px rgba(15,23,42,0.04)",
  };
}

function sectionTitleStyle(): React.CSSProperties {
  return {
    fontSize: 14,
    fontWeight: 800,
    color: "#334155",
    letterSpacing: 0.2,
  };
}

function panelBlockStyle(): React.CSSProperties {
  return {
    ...shellCardStyle(),
    padding: 16,
    display: "grid",
    gap: 12,
  };
}

function metricTile(label: string, value: string | number) {
  return (
    <div
      key={label}
      style={{
        borderRadius: 14,
        border: "1px solid rgba(226,232,240,1)",
        background: "#ffffff",
        padding: "12px 14px",
      }}
    >
      <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700 }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: 28, fontWeight: 800, color: "#0f172a" }}>
        {value}
      </div>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "8px 12px",
        borderRadius: 999,
        border: "1px solid rgba(203,213,225,1)",
        background: "#f8fafc",
        fontSize: 13,
        color: "#334155",
        fontWeight: 600,
      }}
    >
      {children}
    </span>
  );
}

function StatusPill({ status }: { status: BrandFoundationModel["status"] }) {
  const map = {
    draft: {
      bg: "rgba(148,163,184,0.16)",
      border: "rgba(148,163,184,0.35)",
      color: "#475569",
      label: "Draft",
    },
    active: {
      bg: "rgba(34,197,94,0.14)",
      border: "rgba(34,197,94,0.3)",
      color: "#15803d",
      label: "Active",
    },
    archived: {
      bg: "rgba(239,68,68,0.12)",
      border: "rgba(239,68,68,0.28)",
      color: "#b91c1c",
      label: "Archived",
    },
  } as const;

  const current = map[status];

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 14px",
        borderRadius: 999,
        border: `1px solid ${current.border}`,
        background: current.bg,
        color: current.color,
        fontSize: 14,
        fontWeight: 800,
      }}
    >
      {current.label}
    </div>
  );
}

function FoundationTextarea(props: {
  label: string;
  value: string;
  minHeight?: number;
}) {
  const { label, value, minHeight = 110 } = props;
  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div style={sectionTitleStyle()}>{label}</div>
      <textarea
        defaultValue={value}
        style={{
          width: "100%",
          minHeight,
          resize: "vertical",
          borderRadius: 14,
          border: "1px solid rgba(203,213,225,1)",
          background: "#ffffff",
          padding: "14px 16px",
          outline: "none",
          fontSize: 15,
          lineHeight: 1.5,
          color: "#0f172a",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}

function FoundationListCard(props: {
  title: string;
  items: string[];
}) {
  return (
    <div style={panelBlockStyle()}>
      <div style={sectionTitleStyle()}>{props.title}</div>
      <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 8, color: "#334155" }}>
        {props.items.map((item) => (
          <li key={item} style={{ lineHeight: 1.45 }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

type BrandFoundationPageProps = {
  workspaceId?: string;
  onBackToMarketingStream?: () => void;
  onBackToBoardroom?: () => void;
  onBackToDashboard?: () => void;
};

export default function BrandFoundationPage({
  workspaceId = "costa-conexion",
  onBackToMarketingStream,
  onBackToBoardroom,
  onBackToDashboard,
}: BrandFoundationPageProps) {
  const [activeSection, setActiveSection] =
    useState<FoundationSectionKey>("overview");
  const [foundation] = useState<BrandFoundationModel>(INITIAL_FOUNDATION);

  const summaryMetrics = useMemo(() => {
    return {
      personas: foundation.personas.length,
      offers: foundation.offers.length,
      assets: foundation.assets.length,
      keywords:
        foundation.seo.primaryKeywords.length +
        foundation.seo.secondaryKeywords.length +
        foundation.seo.localKeywords.length,
    };
  }, [foundation]);

  return (
    <div
      style={{
        width: "100%",
        minHeight: "100%",
        background:
          "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%)," +
          "radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%)," +
          "linear-gradient(180deg, #f7f9fc, #edf2f8)",
        padding: "20px 24px 28px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "grid",
          gap: 18,
        }}
      >
        <div
          style={{
            ...shellCardStyle(),
            padding: "18px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>
              Marketing &nbsp;›&nbsp; Brand Foundation
            </div>
            <div
              style={{
                marginTop: 8,
                fontSize: 52,
                lineHeight: 1,
                fontWeight: 900,
                color: "#0f172a",
                letterSpacing: -1.4,
              }}
            >
              Brand Foundation
            </div>
            <div
              style={{
                marginTop: 10,
                fontSize: 18,
                color: "#475569",
                maxWidth: 920,
                lineHeight: 1.45,
              }}
            >
              Define brand voice, audience, offers, funnel goals, assets, guardrails,
              and campaign rules that the marketing operator will execute against for {workspaceId}.            

            </div>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: 12,
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
                justifyContent: "flex-end",
              }}
            >
              {onBackToMarketingStream ? (
                <button
                  type="button"
                  onClick={onBackToMarketingStream}
                  style={{
                    borderRadius: 14,
                    border: "1px solid rgba(191,206,224,0.9)",
                    background: "rgba(255,255,255,0.9)",
                    color: "#1f2937",
                    padding: "12px 16px",
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Back to marketing stream
                </button>
              ) : null}

              {onBackToBoardroom ? (
                <button
                  type="button"
                  onClick={onBackToBoardroom}
                  style={{
                    borderRadius: 14,
                    border: "1px solid rgba(191,206,224,0.9)",
                    background: "rgba(255,255,255,0.9)",
                    color: "#1f2937",
                    padding: "12px 16px",
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Back to boardroom
                </button>
              ) : null}

              {onBackToDashboard ? (
                <button
                  type="button"
                  onClick={onBackToDashboard}
                  style={{
                    borderRadius: 14,
                    border: "1px solid rgba(191,206,224,0.9)",
                    background: "rgba(255,255,255,0.9)",
                    color: "#1f2937",
                    padding: "12px 16px",
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Back to dashboard
                </button>
              ) : null}

              {["Save draft", "Publish foundation", "Duplicate"].map((label) => (
                <button
                  key={label}
                  type="button"
                  style={{
                    borderRadius: 14,
                    border: "1px solid rgba(191,206,224,0.9)",
                    background: "rgba(255,255,255,0.9)",
                    color: "#1f2937",
                    padding: "12px 16px",
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {label}
                </button>
              ))}

              <button
                type="button"
                style={{
                  borderRadius: 14,
                  border: "1px solid rgba(26,138,255,0.55)",
                  background: "linear-gradient(180deg, #3394ff, #1a8aff)",
                  color: "#ffffff",
                  padding: "12px 18px",
                  fontSize: 14,
                  fontWeight: 800,
                  cursor: "pointer",
                  boxShadow: "0 8px 18px rgba(26,138,255,0.22)",
                }}
              >
                Activate for workspace
              </button>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <div style={{ fontSize: 13, color: "#64748b" }}>
                Last updated {foundation.updatedAt}
              </div>
              <StatusPill status={foundation.status} />
            </div>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "260px minmax(0, 1fr) 360px",
            gap: 18,
            alignItems: "start",
          }}
        >
          <aside
            style={{
              ...shellCardStyle(),
              padding: 16,
              position: "sticky",
              top: 20,
              display: "grid",
              gap: 8,
            }}
          >
            {NAV_ITEMS.map((item) => {
              const active = activeSection === item.key;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setActiveSection(item.key)}
                  style={{
                    textAlign: "left",
                    borderRadius: 14,
                    border: active
                      ? "1px solid rgba(26,138,255,0.55)"
                      : "1px solid transparent",
                    background: active
                      ? "linear-gradient(180deg, #4b9fff, #2f84e2)"
                      : "transparent",
                    color: active ? "#ffffff" : "#334155",
                    padding: "12px 14px",
                    fontSize: 15,
                    fontWeight: active ? 800 : 600,
                    cursor: "pointer",
                  }}
                >
                  {item.label}
                </button>
              );
            })}
          </aside>

          <main style={{ display: "grid", gap: 18 }}>
            <section style={panelBlockStyle()}>
              <div style={{ fontSize: 16, fontWeight: 900, color: "#334155" }}>Overview</div>

              <FoundationTextarea
                label="Mission Statement"
                value={foundation.missionStatement}
                minHeight={88}
              />

              <FoundationTextarea
                label="Unique Value Proposition"
                value={foundation.uniqueValueProp}
                minHeight={88}
              />

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, minmax(0,1fr))",
                  gap: 12,
                }}
              >
                {metricTile("Personas", summaryMetrics.personas)}
                {metricTile("Offers", summaryMetrics.offers)}
                {metricTile("Assets", summaryMetrics.assets)}
                {metricTile("Keywords", `${summaryMetrics.keywords}+`)}
              </div>
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "1.2fr 1fr",
                gap: 18,
              }}
            >
              <div style={panelBlockStyle()}>
                <div style={sectionTitleStyle()}>Business Goals</div>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 18,
                    display: "grid",
                    gap: 10,
                    color: "#334155",
                  }}
                >
                  {foundation.businessGoals.map((goal) => (
                    <li key={goal}>{goal}</li>
                  ))}
                </ul>

                <div style={sectionTitleStyle()}>Audience Funnel</div>
                <div
                  style={{
                    borderRadius: 14,
                    border: "1px solid rgba(226,232,240,1)",
                    background: "#ffffff",
                    padding: "14px 16px",
                    fontSize: 15,
                    lineHeight: 1.5,
                    color: "#334155",
                  }}
                >
                  {foundation.audienceFunnel}
                </div>
              </div>

              <div style={panelBlockStyle()}>
                <div style={sectionTitleStyle()}>Content Strategy</div>
                <div style={{ display: "grid", gap: 10 }}>
                  <div style={{ color: "#334155", fontSize: 15 }}>
                    <strong>Target Audience:</strong> {foundation.targetAudience}
                  </div>
                  <div style={{ color: "#334155", fontSize: 15 }}>
                    <strong>Monthly Objective:</strong>{" "}
                    {foundation.strategySummary.monthlyObjective}
                  </div>
                  <div style={{ color: "#334155", fontSize: 15 }}>
                    <strong>Publishing Rhythm:</strong>{" "}
                    {foundation.strategySummary.publishingRhythm}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {foundation.strategySummary.kpis.map((kpi) => (
                    <Tag key={kpi}>{kpi}</Tag>
                  ))}
                </div>
              </div>
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 18,
              }}
            >
              <div style={panelBlockStyle()}>
                <div style={sectionTitleStyle()}>Audience Personas</div>
                <div style={{ display: "grid", gap: 12 }}>
                  {foundation.personas.map((persona) => (
                    <div
                      key={persona.id}
                      style={{
                        borderRadius: 16,
                        border: "1px solid rgba(226,232,240,1)",
                        background: "#ffffff",
                        padding: 14,
                        display: "grid",
                        gap: 10,
                      }}
                    >
                      <div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: "#0f172a" }}>
                          {persona.name}
                        </div>
                        <div style={{ marginTop: 6, color: "#475569", lineHeight: 1.45 }}>
                          {persona.summary}
                        </div>
                      </div>

                      <div>
                        <div style={{ ...sectionTitleStyle(), marginBottom: 8 }}>
                          Pain Points
                        </div>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          {persona.painPoints.map((item) => (
                            <Tag key={item}>{item}</Tag>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div style={{ ...sectionTitleStyle(), marginBottom: 8 }}>
                          Desired Outcomes
                        </div>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          {persona.desiredOutcomes.map((item) => (
                            <Tag key={item}>{item}</Tag>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div style={{ ...sectionTitleStyle(), marginBottom: 8 }}>
                          Channels
                        </div>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          {persona.channels.map((item) => (
                            <Tag key={item}>{item}</Tag>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={panelBlockStyle()}>
                <div style={sectionTitleStyle()}>Offers and Funnel Positioning</div>
                <div style={{ display: "grid", gap: 12 }}>
                  {foundation.offers.map((offer) => (
                    <div
                      key={offer.id}
                      style={{
                        borderRadius: 16,
                        border: "1px solid rgba(226,232,240,1)",
                        background: "#ffffff",
                        padding: 14,
                        display: "grid",
                        gap: 8,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 12,
                          alignItems: "center",
                        }}
                      >
                        <div style={{ fontSize: 16, fontWeight: 800, color: "#0f172a" }}>
                          {offer.name}
                        </div>
                        {offer.price ? <Tag>{offer.price}</Tag> : null}
                      </div>
                      <div style={{ color: "#475569", lineHeight: 1.45 }}>
                        {offer.description}
                      </div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <Tag>{offer.audience}</Tag>
                        <Tag>{offer.funnelStage}</Tag>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 18,
              }}
            >
              <FoundationListCard
                title="Messaging Framework"
                items={[
                  `Primary: ${foundation.messaging.primaryMessage}`,
                  ...foundation.messaging.supportingPoints,
                  ...foundation.messaging.ctas.map((cta) => `CTA: ${cta}`),
                  ...foundation.messaging.proofPoints.map((proof) => `Proof: ${proof}`),
                ]}
              />

              <FoundationListCard
                title="Tone and Voice"
                items={[
                  `Voice: ${foundation.tone.brandVoice}`,
                  ...foundation.tone.doSay.map((item) => `Do say: ${item}`),
                  ...foundation.tone.dontSay.map((item) => `Do not say: ${item}`),
                  ...foundation.tone.writingStyle.map((item) => `Style: ${item}`),
                ]}
              />
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 18,
              }}
            >
              <div style={panelBlockStyle()}>
                <div style={sectionTitleStyle()}>Visual Identity</div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div
                    style={{
                      borderRadius: 16,
                      border: "1px solid rgba(226,232,240,1)",
                      background: "#ffffff",
                      padding: 14,
                    }}
                  >
                    <div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>
                      Primary Color
                    </div>
                    <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 12,
                          background: foundation.visualIdentity.primaryColor,
                        }}
                      />
                      <div style={{ fontWeight: 800, color: "#0f172a" }}>
                        {foundation.visualIdentity.primaryColor}
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      borderRadius: 16,
                      border: "1px solid rgba(226,232,240,1)",
                      background: "#ffffff",
                      padding: 14,
                    }}
                  >
                    <div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>
                      Accent Color
                    </div>
                    <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 12,
                          background: foundation.visualIdentity.accentColor,
                        }}
                      />
                      <div style={{ fontWeight: 800, color: "#0f172a" }}>
                        {foundation.visualIdentity.accentColor}
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div
                    style={{
                      borderRadius: 16,
                      border: "1px solid rgba(226,232,240,1)",
                      background: "#ffffff",
                      padding: 14,
                    }}
                  >
                    <div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>
                      Primary Font
                    </div>
                    <div style={{ marginTop: 8, fontSize: 18, fontWeight: 800, color: "#0f172a" }}>
                      {foundation.visualIdentity.fontPrimary}
                    </div>
                  </div>

                  <div
                    style={{
                      borderRadius: 16,
                      border: "1px solid rgba(226,232,240,1)",
                      background: "#ffffff",
                      padding: 14,
                    }}
                  >
                    <div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>
                      Secondary Font
                    </div>
                    <div style={{ marginTop: 8, fontSize: 18, fontWeight: 800, color: "#0f172a" }}>
                      {foundation.visualIdentity.fontSecondary}
                    </div>
                  </div>
                </div>

                <FoundationListCard
                  title="Visual Rules"
                  items={[
                    foundation.visualIdentity.brandLook,
                    ...foundation.visualIdentity.visualRules,
                  ]}
                />
              </div>

              <div style={panelBlockStyle()}>
                <div style={sectionTitleStyle()}>Assets</div>
                <div style={{ display: "grid", gap: 10 }}>
                  {foundation.assets.map((asset) => {
                    const statusMap = {
                      ready: { bg: "rgba(34,197,94,0.12)", color: "#15803d", label: "Ready" },
                      missing: { bg: "rgba(239,68,68,0.12)", color: "#b91c1c", label: "Missing" },
                      needs_refresh: {
                        bg: "rgba(245,158,11,0.12)",
                        color: "#b45309",
                        label: "Needs refresh",
                      },
                    } as const;

                    const status = statusMap[asset.status];

                    return (
                      <div
                        key={asset.id}
                        style={{
                          borderRadius: 14,
                          border: "1px solid rgba(226,232,240,1)",
                          background: "#ffffff",
                          padding: "12px 14px",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 12,
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 800, color: "#0f172a" }}>{asset.name}</div>
                          <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
                            {asset.type}
                          </div>
                        </div>

                        <div
                          style={{
                            padding: "8px 10px",
                            borderRadius: 999,
                            background: status.bg,
                            color: status.color,
                            fontWeight: 800,
                            fontSize: 12,
                          }}
                        >
                          {status.label}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>
          </main>

          <aside
            style={{
              display: "grid",
              gap: 18,
              position: "sticky",
              top: 20,
            }}
          >
            <div style={panelBlockStyle()}>
              <div style={{ fontSize: 16, fontWeight: 900, color: "#334155" }}>
                Strategic Output
              </div>

              <div
                style={{
                  borderRadius: 16,
                  border: "1px solid rgba(226,232,240,1)",
                  background: "#ffffff",
                  padding: 14,
                  display: "grid",
                  gap: 14,
                }}
              >
                <div style={{ fontSize: 18, fontWeight: 800, color: "#0f172a" }}>
                  Brand at a Glance
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0,1fr))",
                    gap: 10,
                  }}
                >
                  {metricTile("Reach", "400k")}
                  {metricTile("Audience", "36.7k")}
                  {metricTile("Active Content", "24")}
                </div>
              </div>

              <FoundationListCard
                title="Immediate Focus"
                items={[
                  `Current focus: ${foundation.strategySummary.currentFocus}`,
                  `Objective: ${foundation.strategySummary.monthlyObjective}`,
                  `Target audience: ${foundation.targetAudience}`,
                ]}
              />

              <FoundationListCard
                title="SEO / Keywords"
                items={[
                  ...foundation.seo.primaryKeywords.map((k) => `Primary: ${k}`),
                  ...foundation.seo.secondaryKeywords.map((k) => `Secondary: ${k}`),
                  ...foundation.seo.localKeywords.map((k) => `Local: ${k}`),
                ]}
              />

              <div style={panelBlockStyle()}>
                <div style={sectionTitleStyle()}>Hashtags</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {foundation.hashtags.map((tag) => (
                    <Tag key={tag}>{tag}</Tag>
                  ))}
                </div>
              </div>

              <FoundationListCard
                title="Compliance / Guardrails"
                items={[
                  ...foundation.compliance.mustInclude.map((v) => `Must include: ${v}`),
                  ...foundation.compliance.avoid.map((v) => `Avoid: ${v}`),
                  ...foundation.compliance.approvalTriggers.map(
                    (v) => `Approval trigger: ${v}`,
                  ),
                ]}
              />

              <FoundationListCard
                title="Content Rules"
                items={foundation.contentRules}
              />

              <FoundationListCard
                title="Approval Rules"
                items={foundation.approvalRules}
              />

              <button
                type="button"
                style={{
                  borderRadius: 16,
                  border: "1px solid rgba(26,138,255,0.55)",
                  background: "linear-gradient(180deg, #3394ff, #1a8aff)",
                  color: "#ffffff",
                  padding: "14px 18px",
                  fontSize: 15,
                  fontWeight: 800,
                  cursor: "pointer",
                  boxShadow: "0 8px 18px rgba(26,138,255,0.22)",
                }}
              >
                Generate marketing report
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}