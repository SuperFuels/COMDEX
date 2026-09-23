(function (global) {
  var DEFAULT_API_BASE = "http://127.0.0.1:8080";
  var DEFAULT_WEB_BASE = "http://127.0.0.1:3000";
  var DEFAULT_WORKSPACE_ID = "costa-conexion";
  var DEFAULT_NODE_ID = "node_mac_local_01";

  var LIVE_AGENTS_VIEWS = {
    stream: true,
    calendar: true,
    runs: true,
    approvals: true,
    settings: true
  };

  var MARKETING_CALENDAR_MODES = {
    done: true,
    review: true,
    planning: true
  };

  var CREATIVE_ASSET_TYPES = {
    product: true,
    brand: true,
    brand_logo: true,
    background: true,
    people: true,
    people_headshot: true,
    reference: true,
    reference_style: true
  };

  var AION_CHAT_MODES = {
    business_workspace: true,
    general_ai: true
  };

  var AION_CHAT_ENGINES = {
    gemma4: true,
    openai: true,
    claude: true
  };

  var STORAGE_KEYS = {
    apiBase: "aionDesktop.apiBase",
    webBase: "aionDesktop.webBase",
    workspaceId: "aionDesktop.workspaceId",
    nodeId: "aionDesktop.nodeId",
    activeTab: "aionDesktop.activeTab",
    boardroomViewMode: "aionDesktop.boardroomViewMode",
    operationsFlowViewMode: "aionDesktop.operationsFlowViewMode",
    activeZone: "aionDesktop.activeZone",
    selectedSeatId: "aionDesktop.selectedSeatId",
    selectedInspectorTarget: "aionDesktop.selectedInspectorTarget",
    selectedLiveAgentId: "aionDesktop.selectedLiveAgentId",
    selectedLiveRunId: "aionDesktop.selectedLiveRunId",
    liveAgentsReplayOpen: "aionDesktop.liveAgentsReplayOpen",
    liveAgentsView: "aionDesktop.liveAgentsView",
    marketingCalendarMode: "aionDesktop.marketingCalendarMode",

    aionChatMode: "aionDesktop.aionChatMode",
    aionChatEngine: "aionDesktop.aionChatEngine",
    aionChatPrompt: "aionDesktop.aionChatPrompt",
    aionChatOutput: "aionDesktop.aionChatOutput"
  };

  var CACHE_KEYS = {
    status: "aionDesktop.cache.status",
    runs: "aionDesktop.cache.runs",
    approvals: "aionDesktop.cache.approvals",
    audit: "aionDesktop.cache.audit",
    scheduler: "aionDesktop.cache.scheduler",
    dashboardSummary: "aionDesktop.cache.dashboardSummary",
    marketingSummary: "aionDesktop.cache.marketingSummary",
    boardroomSnapshot: "aionDesktop.cache.boardroomSnapshot",
    liveAgentsSnapshot: "aionDesktop.cache.liveAgentsSnapshot",
    operationsFlowSnapshot: "aionDesktop.cache.operationsFlowSnapshot",
    recoveryPayload: "aionDesktop.cache.recoveryPayload",
    brandFoundationState: "aionDesktop.cache.brandFoundationState",
    containerBindings: "aionDesktop.cache.containerBindings",
    syncBoundary: "aionDesktop.cache.syncBoundary",
    marketingForm: "aionDesktop.cache.marketingForm",
    lastRefreshAt: "aionDesktop.cache.lastRefreshAt",
    liveAgentsView: "aionDesktop.cache.liveAgentsView",
    marketingCalendarMode: "aionDesktop.cache.marketingCalendarMode",

    aionChatMode: "aionDesktop.cache.aionChatMode",
    aionChatEngine: "aionDesktop.cache.aionChatEngine",
    aionChatPrompt: "aionDesktop.cache.aionChatPrompt",
    aionChatOutput: "aionDesktop.cache.aionChatOutput"
  };

  var DEFAULTS = {
    apiBase: DEFAULT_API_BASE,
    webBase: DEFAULT_WEB_BASE,
    workspaceId: DEFAULT_WORKSPACE_ID,
    nodeId: DEFAULT_NODE_ID,
    activeTab: "dashboard",
    boardroomViewMode: "dashboard",
    operationsFlowViewMode: "flat",
    activeZone: "coo",
    selectedSeatId: "seat_coo",
    selectedInspectorTarget: { kind: "seat", seatId: "seat_coo" },
    selectedLiveAgentId: null,
    selectedLiveRunId: null,
    liveAgentsReplayOpen: false,
    liveAgentsView: "stream",
    marketingCalendarMode: "done",

    aionChatMode: "business_workspace",
    aionChatEngine: "gemma4",
    aionChatPrompt: "",
    aionChatOutput: ""
  };

  var SURFACE_READ_CONTRACT = {
    local_node: {
      reads: [
        "status",
        "runs",
        "approvals",
        "audit",
        "scheduler",
        "syncBoundary",
        "recoveryPayload"
      ],
      writable: [],
      truth: "local_node_runtime"
    },

    dashboard: {
      reads: [
        "dashboardSummary",
        "status",
        "scheduler",
        "runs",
        "approvals",
        "audit"
      ],
      writable: [],
      truth: "container_projection"
    },

    operations_agents: {
      reads: [
        "dashboardSummary",
        "status",
        "scheduler",
        "runs",
        "approvals",
        "audit"
      ],
      writable: [],
      truth: "local_node_runtime"
    },

    marketing_stream: {
      reads: [
        "marketingSummary",
        "marketingForm",
        "brandFoundationState",
        "approvals",
        "runs",
        "marketingCalendarMode"
      ],
      writable: ["marketingForm", "marketingCalendarMode"],
      truth: "container_projection"
    },

    brand_foundation: {
      reads: ["brandFoundationState", "marketingForm"],
      writable: ["brandFoundationState"],
      truth: "brand_foundation_container"
    },

    boardroom: {
      reads: ["boardroomSnapshot", "containerBindings", "dashboardSummary"],
      writable: [
        "boardroomViewMode",
        "activeZone",
        "selectedSeatId",
        "selectedInspectorTarget"
      ],
      truth: "boardroom_projection_container"
    },

    live_agents: {
      reads: [
        "liveAgentsSnapshot",
        "runs",
        "approvals",
        "status",
        "boardroomSnapshot",
        "dashboardSummary",
        "lastRefreshAt",
        "liveAgentsView",
        "selectedLiveAgentId",
        "selectedLiveRunId",
        "liveAgentsReplayOpen",
        "marketingCalendarMode"
      ],
      writable: [
        "selectedLiveAgentId",
        "selectedLiveRunId",
        "liveAgentsReplayOpen",
        "liveAgentsView",
        "marketingCalendarMode"
      ],
      truth: "local_node_runtime"
    },

    aion_chat: {
      reads: [
        "aionChatMode",
        "aionChatEngine",
        "aionChatPrompt",
        "aionChatOutput",
        "workspaceId",
        "nodeId",
        "dashboardSummary",
        "boardroomSnapshot",
        "brandFoundationState",
        "marketingSummary",
        "marketingForm",
        "operationsFlowSnapshot",
        "liveAgentsSnapshot",
        "scheduler",
        "status",
        "runs",
        "approvals",
        "audit",
        "lastRefreshAt"
      ],
      writable: [
        "aionChatMode",
        "aionChatEngine",
        "aionChatPrompt",
        "aionChatOutput"
      ],
      truth: "aion_context_orchestration"
    },

    operations_flow: {
      reads: [
        "operationsFlowSnapshot",
        "boardroomSnapshot",
        "dashboardSummary",
        "containerBindings"
      ],
      writable: [
        "operationsFlowViewMode",
        "activeZone",
        "selectedSeatId",
        "selectedInspectorTarget"
      ],
      truth: "boardroom_projection_container"
    }
  };

  function splitLines(value) {
    return String(value || "")
      .split(/\n|,|•|·|\|/)
      .map(function (part) {
        return part.trim();
      })
      .filter(Boolean);
  }

  function clone(value) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return value;
    }
  }

  function asObject(value) {
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : {};
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function firstDefined() {
    for (var i = 0; i < arguments.length; i += 1) {
      if (arguments[i] !== undefined) return arguments[i];
    }
    return undefined;
  }

  function normalizeString(value, fallback) {
    if (value == null || value === "") return fallback == null ? null : String(fallback);
    return String(value);
  }

  function normalizePlainString(value, fallback) {
    if (value == null) return fallback == null ? "" : String(fallback);
    return String(value);
  }

  function normalizeNumber(value, fallback) {
    if (typeof value === "number" && isFinite(value)) return value;
    return fallback;
  }

  function normalizeRecord(value, fallback) {
    if (value && typeof value === "object" && !Array.isArray(value)) return clone(value);
    return clone(fallback || {});
  }

  function normalizeList(value, fallback) {
    if (Array.isArray(value)) {
      return value
        .map(function (item) {
          return String(item || "").trim();
        })
        .filter(Boolean);
    }

    if (typeof value === "string") return splitLines(value);
    if (Array.isArray(fallback)) return clone(fallback);
    return [];
  }

  function normalizeCreativeAssetType(value) {
    var raw = String(value || "").trim().toLowerCase();

    var aliases = {
      brand: "brand_logo",
      logo: "brand_logo",
      brand_logo: "brand_logo",
      people: "people_headshot",
      headshot: "people_headshot",
      people_headshot: "people_headshot",
      reference: "reference_style",
      reference_style: "reference_style"
    };

    var normalized = aliases[raw] || raw;
    return CREATIVE_ASSET_TYPES[normalized] ? normalized : "product";
  }

  function normalizeAionChatMode(value) {
    return AION_CHAT_MODES[value] ? value : DEFAULTS.aionChatMode;
  }

  function normalizeAionChatEngine(value) {
    return AION_CHAT_ENGINES[value] ? value : DEFAULTS.aionChatEngine;
  }

  function normalizeCreativeUploadedAsset(value, index) {
    var next = asObject(value);
    var fallbackId = "asset_" + String(index || 0).padStart(3, "0");

    return {
      id: normalizePlainString(firstDefined(next.id, next.asset_id, fallbackId), fallbackId),
      type: normalizeCreativeAssetType(firstDefined(next.type, next.asset_type, next.intent, "product")),
      label: normalizePlainString(firstDefined(next.label, next.name, next.title, ""), ""),
      url: normalizePlainString(firstDefined(next.url, next.asset_url, next.public_url, ""), ""),
      file_path: normalizePlainString(firstDefined(next.file_path, next.filePath, next.path, ""), ""),
      notes: normalizePlainString(firstDefined(next.notes, next.usage_notes, next.description, ""), "")
    };
  }

  function normalizeCreativeUploadedAssets(value) {
    if (!Array.isArray(value)) return [];

    return value
      .map(function (item, index) {
        return normalizeCreativeUploadedAsset(item, index);
      })
      .filter(function (item) {
        return !!(item.id || item.label || item.url || item.file_path || item.notes);
      });
  }

  function buildDefaultMarketingForm() {
    return {
      brief: "Draft a Facebook post and simple carousel for spring telecom upgrade offer.",
      objective: "Drive local enquiries",
      funnelGoal: "Lead capture",
      targetAudience: "Local homeowners and small business owners in core service towns.",
      persona: "Local service buyer",
      offer: "Spring telecom upgrade offer",

      assetIntent: "product",
      productName: "",
      offerPrice: "",
      offerDetails: "",
      imageUsageNotes: "",
      styleDirection: "",
      creativeDirection: "",
      creativeAssets: [],

      creativeAssetType: "product",
      creativeAssetLabel: "",
      creativeProductName: "",
      creativeOfferPrice: "",
      creativeOfferDetails: "",
      creativeUsageNotes: "",
      creativeUploadedAssets: [],

      channels: "Facebook\nInstagram",
      hashtags: "#LocalBusiness\n#TrustedServices\n#LeadGeneration",
      keywords: "local telecom upgrade\nsmall business connectivity\ntrusted local installer",
      hardRules:
        "Do not publish automatically.\nDo not exceed one main post per day.\nAvoid shouting sales language.",
      guidanceNotes:
        "Keep the tone clean, useful, and confident.\nLean into trusted local-business language.\nPrefer simple visuals and clear calls to action.",
      campaignNotes:
        "Current focus: spring telecom upgrade offer.\nPush reliability, clarity, and local service trust.\nAvoid weekend publishing for now."
    };
  }

  function normalizeMarketingForm(value) {
    var base = buildDefaultMarketingForm();
    var next = asObject(value);

    var creativeAssets = normalizeCreativeUploadedAssets(
      firstDefined(
        next.creativeAssets,
        next.creative_assets,
        next.creativeUploadedAssets,
        next.creative_uploaded_assets,
        base.creativeAssets
      )
    );

    var assetIntent = normalizeCreativeAssetType(
      firstDefined(
        next.assetIntent,
        next.asset_intent,
        next.creativeAssetType,
        next.creative_asset_type,
        base.assetIntent
      )
    );

    var productName = normalizePlainString(
      firstDefined(
        next.productName,
        next.product_name,
        next.creativeProductName,
        next.creative_product_name,
        base.productName
      ),
      base.productName
    );

    var offerPrice = normalizePlainString(
      firstDefined(
        next.offerPrice,
        next.offer_price,
        next.creativeOfferPrice,
        next.creative_offer_price,
        base.offerPrice
      ),
      base.offerPrice
    );

    var offerDetails = normalizePlainString(
      firstDefined(
        next.offerDetails,
        next.offer_details,
        next.creativeOfferDetails,
        next.creative_offer_details,
        base.offerDetails
      ),
      base.offerDetails
    );

    var imageUsageNotes = normalizePlainString(
      firstDefined(
        next.imageUsageNotes,
        next.image_usage_notes,
        next.creativeUsageNotes,
        next.creative_usage_notes,
        next.usage_notes,
        base.imageUsageNotes
      ),
      base.imageUsageNotes
    );

    var styleDirection = normalizePlainString(
      firstDefined(
        next.styleDirection,
        next.style_direction,
        base.styleDirection
      ),
      base.styleDirection
    );

    var creativeDirection = normalizePlainString(
      firstDefined(
        next.creativeDirection,
        next.creative_direction,
        base.creativeDirection
      ),
      base.creativeDirection
    );

    return {
      brief: normalizePlainString(firstDefined(next.brief, base.brief), base.brief),
      objective: normalizePlainString(firstDefined(next.objective, base.objective), base.objective),
      funnelGoal: normalizePlainString(firstDefined(next.funnelGoal, next.funnel_goal, base.funnelGoal), base.funnelGoal),
      targetAudience: normalizePlainString(firstDefined(next.targetAudience, next.target_audience, base.targetAudience), base.targetAudience),
      persona: normalizePlainString(firstDefined(next.persona, base.persona), base.persona),
      offer: normalizePlainString(firstDefined(next.offer, base.offer), base.offer),

      assetIntent: assetIntent,
      productName: productName,
      offerPrice: offerPrice,
      offerDetails: offerDetails,
      imageUsageNotes: imageUsageNotes,
      styleDirection: styleDirection,
      creativeDirection: creativeDirection,
      creativeAssets: creativeAssets,

      creativeAssetType: assetIntent,
      creativeAssetLabel: normalizePlainString(firstDefined(next.creativeAssetLabel, next.creative_asset_label, ""), ""),
      creativeProductName: productName,
      creativeOfferPrice: offerPrice,
      creativeOfferDetails: offerDetails,
      creativeUsageNotes: imageUsageNotes,
      creativeUploadedAssets: creativeAssets,

      channels: normalizePlainString(firstDefined(next.channels, base.channels), base.channels),
      hashtags: normalizePlainString(firstDefined(next.hashtags, base.hashtags), base.hashtags),
      keywords: normalizePlainString(firstDefined(next.keywords, base.keywords), base.keywords),
      hardRules: normalizePlainString(firstDefined(next.hardRules, next.hard_rules, base.hardRules), base.hardRules),
      guidanceNotes: normalizePlainString(firstDefined(next.guidanceNotes, next.guidance_notes, base.guidanceNotes), base.guidanceNotes),
      campaignNotes: normalizePlainString(firstDefined(next.campaignNotes, next.campaign_notes, base.campaignNotes), base.campaignNotes)
    };
  }

  function buildDefaultBrandIntelligenceMap(marketingForm) {
    var form = normalizeMarketingForm(marketingForm || buildDefaultMarketingForm());

    return {
      version: "brand_intelligence_map.v2",
      layout: {
        style: "single_column_layer_cake",
        sectionMode: "one_container_per_section",
        preferredColumns: 1
      },

      brandOverview: {
        brandName: "Costa Conexion",
        whatYouDo: "Provide trusted local telecom, connectivity, installation, and support services for homeowners and small businesses.",
        uniqueValueProposition: "Reliable local service, clear communication, and practical support without technical confusion.",
        shortDescription: "A trusted local service provider helping homes and businesses stay connected.",
        businessType: "service_business",
        serviceArea: "Local service towns and surrounding areas",
        category: "Telecoms and local connectivity support"
      },

      brandGoals: {
        objective: form.objective || "Drive local enquiries",
        primaryGoal: form.objective || "Drive local enquiries",
        funnelGoal: form.funnelGoal || "Lead capture",
        marketGoal: "Establish ourselves as a trusted local service provider.",
        commercialGoal: "Generate qualified enquiries that become calls, quotes, bookings, installs, or retained customers.",
        awarenessGoal: "Make the brand feel visible, reliable, local, and easy to contact.",
        leadGoal: "Move interested local buyers into enquiry, WhatsApp, call, form, or message action.",
        campaignNotes: splitLines(form.campaignNotes),
        kpis: [
          "qualified enquiries",
          "message clicks",
          "calls",
          "form submissions",
          "booked quotes",
          "cost per lead"
        ]
      },

      brandPurpose: {
        statement: "Provide practical, professional local service that helps customers solve telecom and connectivity problems with confidence.",
        customerPromise: "Clear advice, reliable service, and a simple next step.",
        whyItMatters: "Customers need someone local they can trust when service issues, upgrades, or technical decisions feel confusing."
      },

      brandVision: {
        statement: "Become a leading local service provider within the target service radius.",
        localAmbition: "Be the first brand local customers think of when they need telecom, connectivity, installation, or service support.",
        longTermDirection: "Build a recognised local reputation through useful content, reliable work, and consistent communication."
      },

      brandMission: {
        statement: "Help every customer understand their options, choose the right service, and get reliable support from a trusted local provider.",
        deliveryPrinciples: [
          "respond clearly",
          "explain simply",
          "recommend honestly",
          "complete work professionally",
          "make the next step easy"
        ]
      },

      brandValues: {
        values: [
          "Trust",
          "Reliability",
          "Clarity",
          "Local service",
          "Professionalism"
        ],
        valueCards: [
          {
            label: "Trust",
            meaning: "Be clear, honest, and useful before trying to sell."
          },
          {
            label: "Reliability",
            meaning: "Show up, communicate properly, and focus on solving the real problem."
          },
          {
            label: "Clarity",
            meaning: "Avoid jargon and help customers understand what they need."
          },
          {
            label: "Local service",
            meaning: "Position the brand as accessible, nearby, and easy to contact."
          },
          {
            label: "Professionalism",
            meaning: "Keep the customer experience clean, respectful, and organised."
          }
        ]
      },

      brandPositioning: {
        positioning: "A trusted local connectivity and telecom support provider for homeowners and small businesses who want reliable help without confusion.",
        positioningStatement: "A trusted local connectivity and telecom support provider for homeowners and small businesses who want reliable help without confusion.",
        categoryPosition: "Local service provider",
        differentiation: [
          "local presence",
          "clear communication",
          "trusted installer positioning",
          "simple next steps",
          "professional support"
        ],
        trustSignals: [
          "local service presence",
          "trusted installer positioning",
          "simple communication",
          "practical support"
        ],
        proofPoints: [
          "local service presence",
          "trusted installer positioning",
          "simple communication",
          "practical support"
        ],
        competitors: {
          competitorUrls: [],
          notes: "",
          comparisonAngles: [
            "trust",
            "speed",
            "clarity",
            "local knowledge",
            "service quality",
            "price confidence"
          ]
        }
      },

      brandPersonality: {
        traits: [
          "sophisticated",
          "knowledgeable",
          "practical",
          "cost-effective",
          "clear",
          "professional",
          "local",
          "trusted"
        ],
        notTraits: [
          "pushy",
          "shouty",
          "overly technical",
          "vague",
          "generic"
        ],
        avoidTraits: [
          "pushy",
          "shouty",
          "overly technical",
          "vague",
          "generic"
        ]
      },

      brandVoice: {
        voice: "Sophisticated, knowledgeable, practical, cost-effective, and easy to understand.",
        toneOfVoice: [
          "clean",
          "useful",
          "confident",
          "local",
          "trusted"
        ],
        communicationStyle: "Explain the problem simply, show the benefit clearly, and give the customer one obvious next step.",
        doRules: [
          "Use simple language",
          "Lead with the customer problem",
          "Make the benefit obvious",
          "Use a clear CTA",
          "Sound local and trustworthy",
          "Respect brand approval rules"
        ],
        doNotRules: [
          "Do not use shouting sales language",
          "Do not overuse jargon",
          "Do not make guarantees",
          "Do not imply automatic publishing",
          "Do not create pressure-heavy content"
        ],
        dos: [
          "Use simple language",
          "Lead with the customer problem",
          "Make the benefit obvious",
          "Use a clear CTA",
          "Sound local and trustworthy",
          "Respect brand approval rules"
        ],
        donts: [
          "Do not use shouting sales language",
          "Do not overuse jargon",
          "Do not make guarantees",
          "Do not imply automatic publishing",
          "Do not create pressure-heavy content"
        ],
        phraseBank: [
          "Need help choosing the right option?",
          "Message us and we’ll point you in the right direction.",
          "Local support, clear advice, simple next steps.",
          "Reliable help without the technical confusion."
        ]
      },

      brandStory: {
        howStarted: "",
        originStory: "",
        journey: "",
        founderNotes: "",
        keyStoryPoints: [],
        keyMoments: [],
        customerFacingStory: "Built around local trust, clear advice, and practical service support.",
        storyAngles: [
          "local reliability",
          "clear service",
          "customer confidence",
          "professional support",
          "simple practical help"
        ]
      },

      tagline: {
        value: "Reliable local support without the confusion.",
        primary: "Reliable local support without the confusion.",
        alternatives: [
          "Clear advice. Reliable service. Local support.",
          "Helping local homes and businesses stay connected.",
          "Trusted local service made simple."
        ]
      },

      audience: {
        primaryAudience: form.targetAudience || "",
        customerType: "B2C and B2B",
        b2c: true,
        b2b: true,
        targetLocations: [],
        demographicNotes: "",
        segments: [
          "Local homeowners",
          "Small business owners"
        ],
        audienceSegments: [
          {
            id: "audience_homeowners",
            label: "Local homeowners",
            customerType: "B2C",
            description: "People who need reliable home telecom, connectivity, TV, internet, installation, repair, or upgrade support.",
            needs: [
              "reliable service",
              "clear pricing",
              "local trust",
              "fast response",
              "simple explanation"
            ],
            objections: [
              "not sure who to trust",
              "concerned about cost",
              "unclear what service they need",
              "bad past provider experience"
            ],
            desiredAction: "Send a message, call, or request help."
          },
          {
            id: "audience_small_business",
            label: "Small business owners",
            customerType: "B2B",
            description: "Local businesses that need dependable connectivity and practical support.",
            needs: [
              "stable connectivity",
              "minimal downtime",
              "professional support",
              "clear communication"
            ],
            objections: [
              "downtime risk",
              "unclear technical options",
              "too busy to compare providers"
            ],
            desiredAction: "Ask for a quote or practical recommendation."
          }
        ],
        whereToReachThem: [
          "Facebook",
          "Instagram",
          "Google search",
          "Local groups",
          "Website"
        ]
      },

      customerPersonas: {
        primaryPersona: form.persona || "Local service buyer",
        personaCards: [
          {
            id: "persona_local_homeowner",
            name: "Local Homeowner",
            ageRange: "35-65",
            gender: "Any",
            location: "Local service area",
            occupation: "Homeowner / household decision maker",
            customerType: "B2C",
            interests: [
              "home improvement",
              "reliable services",
              "local recommendations",
              "value for money"
            ],
            values: [
              "trust",
              "clarity",
              "fair pricing",
              "reliability"
            ],
            cultureNotes: "",
            hobbies: [],
            painPoints: [
              "does not know who to trust",
              "does not understand technical options",
              "wants a quick reliable fix",
              "worries about cost"
            ],
            messagingAngle: "Friendly local expert who makes the right next step simple.",
            preferredPlatforms: ["Facebook"],
            preferredCta: "Message us to check availability.",
            headshotUrl: ""
          },
          {
            id: "persona_small_business_owner",
            name: "Small Business Owner",
            ageRange: "30-60",
            gender: "Any",
            location: "Local service area",
            occupation: "Business owner / manager",
            customerType: "B2B",
            interests: [
              "business continuity",
              "productivity",
              "customer service",
              "reliable suppliers"
            ],
            values: [
              "speed",
              "professionalism",
              "minimal downtime",
              "clear communication"
            ],
            cultureNotes: "",
            hobbies: [],
            painPoints: [
              "downtime costs money",
              "technical options are confusing",
              "needs quick practical recommendations",
              "does not have time to compare providers"
            ],
            messagingAngle: "Professional local support that protects time, service, and productivity.",
            preferredPlatforms: ["Facebook", "LinkedIn"],
            preferredCta: "Ask for a quote or quick recommendation.",
            headshotUrl: ""
          }
        ]
      },

      customerJourney: {
        steps: [
          "Awareness",
          "Interest",
          "Consideration",
          "Conversion",
          "Follow-up"
        ],
        conversionPoints: [
          "WhatsApp",
          "Phone call",
          "Website form",
          "Facebook message"
        ],
        defaultJourney: [
          {
            step: 1,
            label: "Awareness",
            example: "Customer scrolls on social media and sees a relevant local service post.",
            channel: "Facebook / Instagram",
            messageGoal: "Make the problem feel familiar and solvable."
          },
          {
            step: 2,
            label: "Interest",
            example: "Customer recognises the service need and checks the post, comments, page, or website.",
            channel: "Social / Website",
            messageGoal: "Build trust quickly."
          },
          {
            step: 3,
            label: "Consideration",
            example: "Customer compares whether this provider feels reliable, local, and clear.",
            channel: "Website / Reviews / Social proof",
            messageGoal: "Reduce risk and answer objections."
          },
          {
            step: 4,
            label: "Conversion",
            example: "Customer messages, calls, submits a form, or requests a quote.",
            channel: "WhatsApp / Phone / Form / Messenger",
            messageGoal: "Give one low-friction action."
          },
          {
            step: 5,
            label: "Follow-up",
            example: "Customer receives clear guidance and is moved toward a booking or quote.",
            channel: "Phone / WhatsApp / Email",
            messageGoal: "Confirm trust and progress the lead."
          }
        ]
      },

      painPoints: {
        items: [
          "I do not know who to trust locally.",
          "I do not understand the technical options.",
          "I am worried about cost.",
          "I need the problem solved quickly.",
          "I have had a bad experience with providers before.",
          "I need someone to explain it simply."
        ],
        solutions: [
          "clear advice",
          "reliable local support",
          "simple next step",
          "professional service",
          "confidence before purchase"
        ],
        messageFormula: "Problem → simple explanation → trust proof → clear benefit → easy CTA"
      },

      customerPainPoints: {
        painPoints: [
          "I do not know who to trust locally.",
          "I do not understand the technical options.",
          "I am worried about cost.",
          "I need the problem solved quickly.",
          "I have had a bad experience with providers before.",
          "I need someone to explain it simply."
        ],
        problemsSolved: [
          "clear advice",
          "reliable local support",
          "simple next step",
          "professional service",
          "confidence before purchase"
        ],
        messageFormula: "Problem → simple explanation → trust proof → clear benefit → easy CTA"
      },

      productsServices: {
        primaryProductOrService: "Telecom upgrade / local connectivity support",
        serviceCategories: [
          "telecom upgrades",
          "connectivity support",
          "small business connectivity",
          "local installation",
          "service advice"
        ],
        activeProductOrServiceId: "service_spring_telecom_upgrade",
        items: [
          {
            id: "service_spring_telecom_upgrade",
            label: "Spring telecom upgrade offer",
            type: "service",
            description: form.offer || "Spring telecom upgrade offer",
            targetAudienceIds: ["audience_homeowners", "audience_small_business"],
            personaIds: ["persona_local_homeowner", "persona_small_business_owner"],
            keyBenefits: [
              "reliable connectivity",
              "local installer support",
              "clear guidance",
              "simple next step"
            ],
            objectionsHandled: [
              "confusing options",
              "trust concerns",
              "unclear price",
              "provider frustration"
            ]
          }
        ],
        keyBenefits: [
          "reliable connectivity",
          "local installer support",
          "clear guidance",
          "simple next step"
        ]
      },

      offers: {
        primaryOffer: form.offer || "",
        activeOfferId: "offer_spring_telecom_upgrade",
        offers: [
          {
            id: "offer_spring_telecom_upgrade",
            label: "Spring telecom upgrade offer",
            productOrServiceId: "service_spring_telecom_upgrade",
            price: "",
            details: "Current campaign focus. Emphasise reliability, clarity, and local trust.",
            funnelStage: "lead_capture",
            cta: "Message us to check your options.",
            urgency: "Spring campaign",
            terms: ""
          }
        ]
      },

      messaging: {
        coreMessage: "Reliable local telecom support without the confusion.",
        messagePillars: [
          {
            id: "pillar_trust",
            label: "Trust",
            message: "A local service people can contact and understand."
          },
          {
            id: "pillar_clarity",
            label: "Clarity",
            message: "Simple explanations and clear next steps."
          },
          {
            id: "pillar_reliability",
            label: "Reliability",
            message: "Support focused on keeping homes and businesses connected."
          }
        ],
        ctaLibrary: [
          "Message us to check availability.",
          "Ask for a quick recommendation.",
          "Send us your postcode and we’ll advise.",
          "Book a local upgrade check."
        ],
        prohibitedLanguage: [
          "guaranteed results",
          "shouting sales language",
          "too much jargon",
          "pushy pressure"
        ]
      },

      platformStrategy: {
        activeChannels: splitLines(form.channels),
        facebook: "Use Facebook for local trust, service visibility, simple explainers, offer posts, and lead capture.",
        retargetingNotes: "Retarget people who engage with local service posts, visit key pages, or show intent around telecom/connectivity support.",
        defaultPlatform: "facebook",
        platforms: {
          facebook: {
            enabled: true,
            objective: "local trust, lead capture, service visibility",
            targetAudience: "Local homeowners and small business owners",
            persona: "Local service buyer",
            tone: "friendly, local, clear, confidence-building",
            contentTypes: ["single_post", "carousel", "local_offer", "proof_post"],
            postingRhythm: "maximum one main post per day",
            preferredCtas: ["Message us", "Call for advice", "Ask for availability"],
            targetingNotes: "Target local homeowners and small business owners in the service radius. Use interest and behaviour signals related to electrical, telecom, connectivity, home improvement, and local services where available.",
            creativeRules: {
              fonts: ["Inter", "Arial", "system-ui"],
              colours: {
                primary: "#1a8aff",
                accent: "#f41aff",
                dark: "#0f172a",
                light: "#f3f6fb",
                background: "#ffffff"
              },
              layout: "clear headline, simple benefit, obvious CTA",
              imageStyle: "clean local-service visual with minimal clutter"
            }
          },
          instagram: {
            enabled: true,
            objective: "brand awareness and trust building",
            targetAudience: "Local homeowners and service buyers",
            persona: "Local service buyer",
            tone: "clean, visual, simple, confident",
            contentTypes: ["carousel", "story", "service_tip", "before_after"],
            postingRhythm: "supporting posts around active campaigns",
            preferredCtas: ["DM us", "Save this", "Message for help"],
            targetingNotes: "Use simple visual education, service examples, and local trust-building.",
            creativeRules: {
              fonts: ["Inter", "Arial", "system-ui"],
              colours: {
                primary: "#1a8aff",
                accent: "#f41aff",
                background: "#ffffff"
              },
              layout: "visual-first carousel with short copy",
              imageStyle: "clean, premium, simple, local"
            }
          }
        }
      },

      competitorAnalysis: {
        urls: [],
        competitorUrls: [],
        websites: [],
        uploadedResearchAssets: [],
        notes: "",
        analysis: "",
        analysisSummary: "",
        opportunities: [],
        differentiation: "Stand apart through clearer communication, stronger local trust, simpler CTAs, better service explanation, and a more professional brand presence.",
        differentiationAngles: [
          "clearer communication",
          "stronger local trust",
          "simpler CTA",
          "better service explanation",
          "more professional brand presence"
        ]
      },

      creativeDirection: {
        assetIntent: form.assetIntent || "product",
        productName: form.productName || "",
        offerPrice: form.offerPrice || "",
        offerDetails: form.offerDetails || "",
        direction: form.creativeDirection || "",
        creativeDirection: form.creativeDirection || "",
        usageNotes: form.imageUsageNotes || "",
        styleDirection: form.styleDirection || "Premium, clean, practical, local, trustworthy.",
        doRules: [
          "make the offer immediately understandable",
          "use simple visual hierarchy",
          "avoid clutter",
          "keep CTA visible",
          "respect uploaded product/brand assets"
        ],
        doNotRules: [
          "do not use childish graphics",
          "do not clutter the artwork",
          "do not make unsafe or unsupported claims"
        ],
        imagePrinciples: [
          "make the offer immediately understandable",
          "use simple visual hierarchy",
          "avoid clutter",
          "keep CTA visible",
          "respect uploaded product/brand assets"
        ],
        creativeAssets: normalizeCreativeUploadedAssets(form.creativeAssets)
      },

      visualIdentity: {
        defaultFonts: ["Inter", "Arial", "system-ui"],
        fontRules: {
          headline: "Use clean bold sans-serif fonts.",
          body: "Use readable sans-serif body copy.",
          avoid: ["script fonts", "overly decorative fonts", "hard-to-read compressed fonts"]
        },
        colourPalette: {
          primary: "#1a8aff",
          accent: "#f41aff",
          dark: "#0f172a",
          muted: "#64748b",
          border: "#dbe3ef",
          background: "#f3f6fb",
          card: "#ffffff"
        },
        platformOverrides: {
          facebook: {
            fonts: ["Inter", "Arial", "system-ui"],
            colours: {
              primary: "#1a8aff",
              accent: "#f41aff",
              background: "#ffffff"
            }
          },
          instagram: {
            fonts: ["Inter", "Arial", "system-ui"],
            colours: {
              primary: "#1a8aff",
              accent: "#f41aff",
              background: "#ffffff"
            }
          }
        }
      },

      contentRules: {
        hardRules: splitLines(form.hardRules),
        guidanceNotes: splitLines(form.guidanceNotes),
        campaignNotes: splitLines(form.campaignNotes),
        approvalRules: [
          "Do not publish automatically.",
          "Public-facing content must stop for approval.",
          "Escalate unclear, risky, or off-brand outputs."
        ],
        publishingRules: [
          "Do not exceed one main post per day.",
          "Avoid weekend publishing for now."
        ]
      },

      campaignPlanning: {
        currentCampaign: "Spring telecom upgrade offer",
        funnelStage: form.funnelGoal || "Lead capture",
        channels: splitLines(form.channels),
        keywords: splitLines(form.keywords),
        hashtags: splitLines(form.hashtags),
        activeAudiences: ["audience_homeowners", "audience_small_business"],
        activePersonas: ["persona_local_homeowner", "persona_small_business_owner"],
        activeProductsServices: ["service_spring_telecom_upgrade"],
        activeOffers: ["offer_spring_telecom_upgrade"]
      },

      aiUsageRules: {
        summary:
          "Aion is the business context and orchestration layer. The selected LLM is only the reasoning engine. Every generated output should use this map first when Business Workspace mode is active.",
        promptOrder: [
          "brandOverview",
          "brandGoals",
          "brandPurpose",
          "brandVision",
          "brandMission",
          "brandValues",
          "brandPositioning",
          "brandPersonality",
          "brandVoice",
          "audience",
          "customerPersonas",
          "customerJourney",
          "painPoints",
          "productsServices",
          "offers",
          "platformStrategy",
          "contentRules"
        ],
        outputInstruction:
          "Create the right message, in the right tone, for the right customer, on the right platform, with one clear CTA."
      },

      governance: {
        owner: "Marketing",
        approvalMode: "draft_and_approval",
        publishAutonomously: false,
        reviewCadence: "before_publication",
        lastReviewedAt: null,
        updatedBy: "desktop",
        hardRules: splitLines(form.hardRules),
        approvalRules: [
          "Do not publish automatically.",
          "Public-facing content must stop for approval.",
          "Escalate unclear, risky, or off-brand outputs."
        ],
        complianceNotes: []
      }
    };
  }

  function normalizePlatformStrategy(value, fallback) {
    var base = fallback || buildDefaultBrandIntelligenceMap().platformStrategy;
    var next = asObject(value);
    var platforms = asObject(firstDefined(next.platforms, base.platforms));
    var normalizedPlatforms = {};

    Object.keys(platforms).forEach(function (key) {
      var platform = asObject(platforms[key]);
      var basePlatform = asObject(base.platforms && base.platforms[key]);

      normalizedPlatforms[key] = {
        enabled: platform.enabled !== undefined ? platform.enabled === true : basePlatform.enabled === true,
        objective: normalizePlainString(firstDefined(platform.objective, basePlatform.objective, ""), ""),
        targetAudience: normalizePlainString(firstDefined(platform.targetAudience, platform.target_audience, basePlatform.targetAudience, ""), ""),
        persona: normalizePlainString(firstDefined(platform.persona, basePlatform.persona, ""), ""),
        tone: normalizePlainString(firstDefined(platform.tone, basePlatform.tone, ""), ""),
        contentTypes: normalizeList(firstDefined(platform.contentTypes, platform.content_types, basePlatform.contentTypes), []),
        postingRhythm: normalizePlainString(firstDefined(platform.postingRhythm, platform.posting_rhythm, basePlatform.postingRhythm, ""), ""),
        preferredCtas: normalizeList(firstDefined(platform.preferredCtas, platform.preferred_ctas, basePlatform.preferredCtas), []),
        targetingNotes: normalizePlainString(firstDefined(platform.targetingNotes, platform.targeting_notes, basePlatform.targetingNotes, ""), ""),
        creativeRules: normalizeRecord(firstDefined(platform.creativeRules, platform.creative_rules, basePlatform.creativeRules), {})
      };
    });

    return {
      activeChannels: normalizeList(firstDefined(next.activeChannels, next.active_channels, base.activeChannels), []),
      facebook: normalizePlainString(firstDefined(next.facebook, base.facebook, ""), ""),
      retargetingNotes: normalizePlainString(firstDefined(next.retargetingNotes, next.retargeting_notes, base.retargetingNotes, ""), ""),
      defaultPlatform: normalizePlainString(firstDefined(next.defaultPlatform, next.default_platform, base.defaultPlatform, "facebook"), "facebook"),
      platforms: normalizedPlatforms
    };
  }

  function normalizeBrandIntelligenceMap(value, marketingForm) {
    var fallback = buildDefaultBrandIntelligenceMap(marketingForm);
    var next = asObject(value);

    var painPointsValue = firstDefined(
      next.painPoints,
      next.pain_points,
      next.customerPainPoints,
      next.customer_pain_points,
      fallback.painPoints
    );

    var customerPainPointsValue = firstDefined(
      next.customerPainPoints,
      next.customer_pain_points,
      next.painPoints,
      next.pain_points,
      fallback.customerPainPoints
    );

    return {
      version: normalizePlainString(firstDefined(next.version, fallback.version), fallback.version),
      layout: normalizeRecord(firstDefined(next.layout, fallback.layout), fallback.layout),

      brandOverview: normalizeRecord(firstDefined(next.brandOverview, next.brand_overview, next.brandCore, next.brand_core, fallback.brandOverview), fallback.brandOverview),
      brandGoals: normalizeRecord(firstDefined(next.brandGoals, next.brand_goals, next.strategy, fallback.brandGoals), fallback.brandGoals),
      brandPurpose: normalizeRecord(firstDefined(next.brandPurpose, next.brand_purpose, fallback.brandPurpose), fallback.brandPurpose),
      brandVision: normalizeRecord(firstDefined(next.brandVision, next.brand_vision, fallback.brandVision), fallback.brandVision),
      brandMission: normalizeRecord(firstDefined(next.brandMission, next.brand_mission, fallback.brandMission), fallback.brandMission),
      brandValues: normalizeRecord(firstDefined(next.brandValues, next.brand_values, fallback.brandValues), fallback.brandValues),
      brandPositioning: normalizeRecord(firstDefined(next.brandPositioning, next.brand_positioning, fallback.brandPositioning), fallback.brandPositioning),
      brandPersonality: normalizeRecord(firstDefined(next.brandPersonality, next.brand_personality, fallback.brandPersonality), fallback.brandPersonality),
      brandVoice: normalizeRecord(firstDefined(next.brandVoice, next.brand_voice, next.voice, next.messaging, fallback.brandVoice), fallback.brandVoice),
      brandStory: normalizeRecord(firstDefined(next.brandStory, next.brand_story, fallback.brandStory), fallback.brandStory),
      tagline: normalizeRecord(firstDefined(next.tagline, fallback.tagline), fallback.tagline),

      audience: normalizeRecord(firstDefined(next.audience, next.audiences, fallback.audience), fallback.audience),
      customerPersonas: normalizeRecord(firstDefined(next.customerPersonas, next.customer_personas, next.personas, fallback.customerPersonas), fallback.customerPersonas),
      customerJourney: normalizeRecord(firstDefined(next.customerJourney, next.customer_journey, fallback.customerJourney), fallback.customerJourney),

      painPoints: normalizeRecord(painPointsValue, fallback.painPoints),
      customerPainPoints: normalizeRecord(customerPainPointsValue, fallback.customerPainPoints),

      productsServices: normalizeRecord(
        firstDefined(next.productsServices, next.products_services, next.productsAndServices, next.products_and_services, fallback.productsServices),
        fallback.productsServices
      ),

      offers: normalizeRecord(firstDefined(next.offers, fallback.offers), fallback.offers),
      messaging: normalizeRecord(firstDefined(next.messaging, fallback.messaging), fallback.messaging),
      platformStrategy: normalizePlatformStrategy(firstDefined(next.platformStrategy, next.platform_strategy, fallback.platformStrategy), fallback.platformStrategy),
      competitorAnalysis: normalizeRecord(firstDefined(next.competitorAnalysis, next.competitor_analysis, fallback.competitorAnalysis), fallback.competitorAnalysis),
      creativeDirection: normalizeRecord(firstDefined(next.creativeDirection, next.creative_direction, fallback.creativeDirection), fallback.creativeDirection),
      visualIdentity: normalizeRecord(firstDefined(next.visualIdentity, next.visual_identity, fallback.visualIdentity), fallback.visualIdentity),
      contentRules: normalizeRecord(firstDefined(next.contentRules, next.content_rules, fallback.contentRules), fallback.contentRules),
      campaignPlanning: normalizeRecord(firstDefined(next.campaignPlanning, next.campaign_planning, fallback.campaignPlanning), fallback.campaignPlanning),
      aiUsageRules: normalizeRecord(firstDefined(next.aiUsageRules, next.ai_usage_rules, fallback.aiUsageRules), fallback.aiUsageRules),
      governance: normalizeRecord(firstDefined(next.governance, fallback.governance), fallback.governance)
    };
  }

  function buildDefaultBrandFoundationState(marketingForm) {
    var form = normalizeMarketingForm(marketingForm || buildDefaultMarketingForm());
    var intelligenceMap = buildDefaultBrandIntelligenceMap(form);

    return {
      objective: form.objective || "",
      funnelGoal: form.funnelGoal || "",
      targetAudience: form.targetAudience || "",
      persona: form.persona || "",
      offer: form.offer || "",
      channels: splitLines(form.channels),
      hashtags: splitLines(form.hashtags),
      keywords: splitLines(form.keywords),
      hardRules: splitLines(form.hardRules),
      guidanceNotes: splitLines(form.guidanceNotes),
      campaignNotes: splitLines(form.campaignNotes),

      brandIntelligenceMap: intelligenceMap,
      brand_intelligence_map: intelligenceMap,
      brandMap: intelligenceMap,
      brand_map: intelligenceMap,

      updatedAt: null,
      updated_at: null
    };
  }

  function normalizeBrandFoundationState(value, marketingForm) {
    var form = normalizeMarketingForm(marketingForm || buildDefaultMarketingForm());
    var base = buildDefaultBrandFoundationState(form);
    var next = asObject(value);

    var nested = firstDefined(
      next.brandIntelligenceMap,
      next.brand_intelligence_map,
      next.brandMap,
      next.brand_map,
      next.intelligenceMap,
      next.intelligence_map,
      next.map,
      {}
    );

    var mergedNested = normalizeBrandIntelligenceMap(nested, form);

    mergedNested.brandGoals.primaryGoal = normalizePlainString(
      firstDefined(
        mergedNested.brandGoals.primaryGoal,
        mergedNested.brandGoals.objective,
        next.objective,
        next.marketing_objective,
        base.objective
      ),
      base.objective
    );

    mergedNested.brandGoals.objective = normalizePlainString(
      firstDefined(
        mergedNested.brandGoals.objective,
        mergedNested.brandGoals.primaryGoal,
        next.objective,
        base.objective
      ),
      base.objective
    );

    mergedNested.brandGoals.funnelGoal = normalizePlainString(
      firstDefined(
        mergedNested.brandGoals.funnelGoal,
        mergedNested.brandGoals.funnel_goal,
        next.funnelGoal,
        next.funnel_goal,
        base.funnelGoal
      ),
      base.funnelGoal
    );

    mergedNested.audience.primaryAudience = normalizePlainString(
      firstDefined(
        mergedNested.audience.primaryAudience,
        mergedNested.audience.primary_audience,
        next.targetAudience,
        next.target_audience,
        base.targetAudience
      ),
      base.targetAudience
    );

    mergedNested.customerPersonas.primaryPersona = normalizePlainString(
      firstDefined(
        mergedNested.customerPersonas.primaryPersona,
        mergedNested.customerPersonas.primary_persona,
        next.persona,
        base.persona
      ),
      base.persona
    );

    mergedNested.offers.primaryOffer = normalizePlainString(
      firstDefined(
        mergedNested.offers.primaryOffer,
        mergedNested.offers.primary_offer,
        next.offer,
        base.offer
      ),
      base.offer
    );

    return {
      objective: normalizePlainString(firstDefined(next.objective, mergedNested.brandGoals.primaryGoal, base.objective), base.objective),
      funnelGoal: normalizePlainString(firstDefined(next.funnelGoal, next.funnel_goal, mergedNested.brandGoals.funnelGoal, base.funnelGoal), base.funnelGoal),
      funnel_goal: normalizePlainString(firstDefined(next.funnelGoal, next.funnel_goal, mergedNested.brandGoals.funnelGoal, base.funnelGoal), base.funnelGoal),

      targetAudience: normalizePlainString(firstDefined(next.targetAudience, next.target_audience, mergedNested.audience.primaryAudience, base.targetAudience), base.targetAudience),
      target_audience: normalizePlainString(firstDefined(next.targetAudience, next.target_audience, mergedNested.audience.primaryAudience, base.targetAudience), base.targetAudience),

      persona: normalizePlainString(firstDefined(next.persona, mergedNested.customerPersonas.primaryPersona, base.persona), base.persona),
      offer: normalizePlainString(firstDefined(next.offer, mergedNested.offers.primaryOffer, base.offer), base.offer),

      channels: normalizeList(firstDefined(next.channels, mergedNested.campaignPlanning.channels, base.channels), base.channels),
      hashtags: normalizeList(firstDefined(next.hashtags, mergedNested.campaignPlanning.hashtags, base.hashtags), base.hashtags),
      keywords: normalizeList(firstDefined(next.keywords, mergedNested.campaignPlanning.keywords, base.keywords), base.keywords),
      hardRules: normalizeList(firstDefined(next.hardRules, next.hard_rules, mergedNested.contentRules.hardRules, base.hardRules), base.hardRules),
      hard_rules: normalizeList(firstDefined(next.hardRules, next.hard_rules, mergedNested.contentRules.hardRules, base.hardRules), base.hardRules),
      guidanceNotes: normalizeList(firstDefined(next.guidanceNotes, next.guidance_notes, mergedNested.contentRules.guidanceNotes, base.guidanceNotes), base.guidanceNotes),
      guidance_notes: normalizeList(firstDefined(next.guidanceNotes, next.guidance_notes, mergedNested.contentRules.guidanceNotes, base.guidanceNotes), base.guidanceNotes),
      campaignNotes: normalizeList(firstDefined(next.campaignNotes, next.campaign_notes, mergedNested.contentRules.campaignNotes, base.campaignNotes), base.campaignNotes),
      campaign_notes: normalizeList(firstDefined(next.campaignNotes, next.campaign_notes, mergedNested.contentRules.campaignNotes, base.campaignNotes), base.campaignNotes),

      brandIntelligenceMap: mergedNested,
      brand_intelligence_map: mergedNested,
      brandMap: mergedNested,
      brand_map: mergedNested,

      updatedAt: firstDefined(next.updatedAt, next.updated_at, base.updatedAt),
      updated_at: firstDefined(next.updatedAt, next.updated_at, base.updatedAt)
    };
  }

  function buildDefaultSyncBoundary() {
    return {
      mode: "local_first",
      updatedAt: null,
      layers: {
        localEditableBusinessState: true,
        containerBoundRuntimeState: true,
        kgSemanticJournalState: true
      },
      cloud: {
        summaries: "optional",
        snapshots: "optional",
        commands: "optional",
        approvals: "optional",
        semanticExport: "optional"
      }
    };
  }

  function buildDefaultBoardroomPulse() {
    return {
      sales: { orders: 24, conversionRate: 18, sellThroughRate: 82, revenue: 12450 },
      ops: { backlog: 17, blockedJobs: 3, avgTurnaroundDays: 3, fulfilmentRate: 92 },
      cash: { onHand: 18450, incoming30d: 9600, outgoing30d: 7200, runwayDays: 76 },
      finance: { debtorDays: 21, creditorDays: 32, grossMarginPct: 48 },
      stock: { value: 22800, daysCover: 41 },
      risk: { demand: "medium", cash: "low", operations: "medium" }
    };
  }

  function buildDefaultBoardroomCenter() {
    return {
      revenue: "£12,450",
      cash: "£18,450",
      pipeline: "24 active",
      profit: "£4,220",
      health: "stable"
    };
  }

  function buildDefaultBoardroomRuntime() {
    return {
      node: { status: "offline", mode: "local_first", lastHeartbeatAt: null },
      approvals: [],
      runs: []
    };
  }

  function buildDefaultBoardroomFloors() {
    return {
      sales: null,
      finance: null,
      operations: null,
      support: null,
      hr: null,
      marketing: null
    };
  }

  function buildDefaultBoardroomTopology() {
    return { nodes: [], edges: [] };
  }

  function buildDefaultBoardroomWorkspace(workspaceId) {
    var resolvedWorkspaceId = workspaceId || DEFAULT_WORKSPACE_ID;
    return {
      id: resolvedWorkspaceId,
      slug: resolvedWorkspaceId,
      name: "Costa Conexion",
      business_type: "service_business"
    };
  }

  function buildDefaultDashboardSummary(workspaceId, nodeId) {
    var resolvedWorkspaceId = workspaceId || DEFAULT_WORKSPACE_ID;
    var resolvedNodeId = nodeId || DEFAULT_NODE_ID;

    return {
      workspace: {
        workspace_id: resolvedWorkspaceId,
        node_id: resolvedNodeId,
        deployment_mode: "local_first",
        sync_mode: "local_primary"
      },
      node: { status: "offline" },
      scheduler: { is_running: false, last_tick_at: null },
      queue: {
        queued: 0,
        running: 0,
        waiting_approval: 0,
        completed: 0,
        cancelled: 0,
        failed: 0
      },
      approvals: { pending: 0, approved: 0, rejected: 0 },
      health: { lifecycle_state: "starting", last_heartbeat_at: null },
      departments: [],
      alerts: [],
      recent_audit: [],
      audit_event_count: 0,
      updatedAt: null
    };
  }

  function buildDefaultLiveAgentsSnapshot() {
    return {
      runs: [],
      approvals: [],
      selectedLiveAgentId: null,
      selectedLiveRunId: null,
      liveAgentsReplayOpen: false,
      liveAgentsView: DEFAULTS.liveAgentsView,
      activeZone: DEFAULTS.activeZone,
      updatedAt: null
    };
  }

  function buildDefaultOperationsFlowSnapshot() {
    return {
      viewMode: DEFAULTS.operationsFlowViewMode,
      activeZone: "operations",
      selectedSeatId: null,
      selectedInspectorTarget: null,
      boardroomSnapshot: null,
      containerBindings: [],
      workspace: buildDefaultBoardroomWorkspace(DEFAULTS.workspaceId),
      pulse: buildDefaultBoardroomPulse(),
      runtime: buildDefaultBoardroomRuntime(),
      topology: buildDefaultBoardroomTopology(),
      updatedAt: null
    };
  }

  function buildDefaultBoardroomSnapshot(workspaceId) {
    var resolvedWorkspaceId = workspaceId || DEFAULT_WORKSPACE_ID;

    return {
      workspaceId: resolvedWorkspaceId,
      viewMode: "dashboard",
      activeZone: DEFAULTS.activeZone,
      selectedSeatId: DEFAULTS.selectedSeatId,
      selectedInspectorTarget: clone(DEFAULTS.selectedInspectorTarget),
      summary: null,
      workspace: buildDefaultBoardroomWorkspace(resolvedWorkspaceId),
      center: buildDefaultBoardroomCenter(),
      pulse: buildDefaultBoardroomPulse(),
      seats: [],
      departments: [],
      floors: buildDefaultBoardroomFloors(),
      runtime: buildDefaultBoardroomRuntime(),
      topology: buildDefaultBoardroomTopology(),
      bindingsByCategory: {},
      updatedAt: null
    };
  }

  function buildDefaultRecoveryState() {
    return {
      workspaceId: DEFAULTS.workspaceId,
      nodeId: DEFAULTS.nodeId,
      activeTab: DEFAULTS.activeTab,
      boardroomViewMode: DEFAULTS.boardroomViewMode,
      operationsFlowViewMode: DEFAULTS.operationsFlowViewMode,
      activeZone: DEFAULTS.activeZone,
      selectedSeatId: DEFAULTS.selectedSeatId,
      selectedInspectorTarget: clone(DEFAULTS.selectedInspectorTarget),
      selectedLiveAgentId: DEFAULTS.selectedLiveAgentId,
      selectedLiveRunId: DEFAULTS.selectedLiveRunId,
      liveAgentsReplayOpen: DEFAULTS.liveAgentsReplayOpen,
      liveAgentsView: DEFAULTS.liveAgentsView,
      marketingCalendarMode: DEFAULTS.marketingCalendarMode,

      aionChatMode: DEFAULTS.aionChatMode,
      aionChatEngine: DEFAULTS.aionChatEngine,
      aionChatPrompt: DEFAULTS.aionChatPrompt,
      aionChatOutput: DEFAULTS.aionChatOutput,

      dashboardSummary: buildDefaultDashboardSummary(DEFAULTS.workspaceId, DEFAULTS.nodeId),
      marketingSummary: null,
      boardroomSnapshot: buildDefaultBoardroomSnapshot(DEFAULTS.workspaceId),
      liveAgentsSnapshot: buildDefaultLiveAgentsSnapshot(),
      operationsFlowSnapshot: buildDefaultOperationsFlowSnapshot(),
      recoveryPayload: null,
      brandFoundationState: buildDefaultBrandFoundationState(),
      containerBindings: [],
      lastRefreshAt: null
    };
  }

  function normalizeOperationsFlowViewMode(value) {
    return value === "spatial" ? "spatial" : "flat";
  }

  function normalizeBoardroomViewMode(value) {
    return value === "spatial" ? "spatial" : "dashboard";
  }

  function normalizeActiveTab(value) {
    const allowed = {
      boardroom: true,
      dashboard: true,
      marketing_stream: true,
      brand_foundation: true,
      live_agents: true,
      aion_chat: true,
      operations_flow: true,
      operations_agents: true,
      vault: true,
      local_node: true,
    };

    return allowed[value] ? value : DEFAULTS.activeTab;
  }

  function normalizeActiveZone(value) {
    var allowed = {
      coo: true,
      marketing: true,
      sales: true,
      operations: true,
      hr: true,
      support: true,
      finance: true,
      ceo: true,
      aion: true,
      openai: true
    };
    return allowed[value] ? value : DEFAULTS.activeZone;
  }

  function normalizeSelectedSeatId(value) {
    if (value == null || value === "") return null;
    return String(value);
  }

  function normalizeSelectedLiveAgentId(value) {
    if (value == null || value === "") return null;
    return String(value);
  }

  function normalizeSelectedLiveRunId(value) {
    if (value == null || value === "") return null;
    return String(value);
  }

  function normalizeLiveAgentsReplayOpen(value) {
    return value === true;
  }

  function normalizeLiveAgentsView(value) {
    return LIVE_AGENTS_VIEWS[value] ? value : DEFAULTS.liveAgentsView;
  }

  function normalizeMarketingCalendarMode(value) {
    return MARKETING_CALENDAR_MODES[value] ? value : DEFAULTS.marketingCalendarMode;
  }

  function normalizeSelectedInspectorTarget(value) {
    if (value == null) return null;
    if (!value || typeof value !== "object") return clone(DEFAULTS.selectedInspectorTarget);
    return clone(value);
  }

  function normalizeContainerBindings(value) {
    return Array.isArray(value) ? clone(value) : [];
  }

  function normalizeBoardroomWorkspace(value, workspaceId) {
    var base = buildDefaultBoardroomWorkspace(workspaceId);
    var next = asObject(value);

    return {
      id: normalizeString(firstDefined(next.id, next.workspace_id, base.id), base.id),
      slug: normalizeString(firstDefined(next.slug, next.workspace_slug, base.slug), base.slug),
      name: normalizeString(firstDefined(next.name, next.title, base.name), base.name),
      business_type: normalizeString(firstDefined(next.business_type, next.industry, next.category, base.business_type), base.business_type)
    };
  }

  function normalizeBoardroomCenter(value) {
    var base = buildDefaultBoardroomCenter();
    var next = asObject(value);

    return {
      revenue: normalizeString(firstDefined(next.revenue, base.revenue), base.revenue),
      cash: normalizeString(firstDefined(next.cash, base.cash), base.cash),
      pipeline: normalizeString(firstDefined(next.pipeline, base.pipeline), base.pipeline),
      profit: normalizeString(firstDefined(next.profit, base.profit), base.profit),
      health: normalizeString(firstDefined(next.health, base.health), base.health)
    };
  }

  function normalizeBoardroomPulse(value) {
    var base = buildDefaultBoardroomPulse();
    var next = asObject(value);

    return {
      sales: {
        orders: normalizeNumber(firstDefined(next.sales && next.sales.orders), base.sales.orders),
        conversionRate: normalizeNumber(firstDefined(next.sales && next.sales.conversionRate, next.sales && next.sales.conversion_rate), base.sales.conversionRate),
        sellThroughRate: normalizeNumber(firstDefined(next.sales && next.sales.sellThroughRate, next.sales && next.sales.sell_through_rate), base.sales.sellThroughRate),
        revenue: normalizeNumber(firstDefined(next.sales && next.sales.revenue), base.sales.revenue)
      },
      ops: {
        backlog: normalizeNumber(firstDefined(next.ops && next.ops.backlog), base.ops.backlog),
        blockedJobs: normalizeNumber(firstDefined(next.ops && next.ops.blockedJobs, next.ops && next.ops.blocked_jobs), base.ops.blockedJobs),
        avgTurnaroundDays: normalizeNumber(firstDefined(next.ops && next.ops.avgTurnaroundDays, next.ops && next.ops.avg_turnaround_days), base.ops.avgTurnaroundDays),
        fulfilmentRate: normalizeNumber(firstDefined(next.ops && next.ops.fulfilmentRate, next.ops && next.ops.fulfilment_rate), base.ops.fulfilmentRate)
      },
      cash: {
        onHand: normalizeNumber(firstDefined(next.cash && next.cash.onHand, next.cash && next.cash.on_hand), base.cash.onHand),
        incoming30d: normalizeNumber(firstDefined(next.cash && next.cash.incoming30d, next.cash && next.cash.incoming_30d), base.cash.incoming30d),
        outgoing30d: normalizeNumber(firstDefined(next.cash && next.cash.outgoing30d, next.cash && next.cash.outgoing_30d), base.cash.outgoing30d),
        runwayDays: normalizeNumber(firstDefined(next.cash && next.cash.runwayDays, next.cash && next.cash.runway_days), base.cash.runwayDays)
      },
      finance: {
        debtorDays: normalizeNumber(firstDefined(next.finance && next.finance.debtorDays, next.finance && next.finance.debtor_days), base.finance.debtorDays),
        creditorDays: normalizeNumber(firstDefined(next.finance && next.finance.creditorDays, next.finance && next.finance.creditor_days), base.finance.creditorDays),
        grossMarginPct: normalizeNumber(firstDefined(next.finance && next.finance.grossMarginPct, next.finance && next.finance.gross_margin_pct), base.finance.grossMarginPct)
      },
      stock: {
        value: normalizeNumber(firstDefined(next.stock && next.stock.value), base.stock.value),
        daysCover: normalizeNumber(firstDefined(next.stock && next.stock.daysCover, next.stock && next.stock.days_cover), base.stock.daysCover)
      },
      risk: {
        demand: normalizeString(firstDefined(next.risk && next.risk.demand), base.risk.demand),
        cash: normalizeString(firstDefined(next.risk && next.risk.cash), base.risk.cash),
        operations: normalizeString(firstDefined(next.risk && next.risk.operations), base.risk.operations)
      }
    };
  }

  function normalizeBoardroomRuntime(value) {
    var base = buildDefaultBoardroomRuntime();
    var next = asObject(value);
    var node = asObject(next.node);

    return {
      node: {
        status: normalizeString(firstDefined(node.status, base.node.status), base.node.status),
        mode: normalizeString(firstDefined(node.mode, base.node.mode), base.node.mode),
        lastHeartbeatAt: firstDefined(node.lastHeartbeatAt, node.last_heartbeat_at, base.node.lastHeartbeatAt) || null
      },
      approvals: asArray(firstDefined(next.approvals, base.approvals)),
      runs: asArray(firstDefined(next.runs, base.runs))
    };
  }

  function normalizeBoardroomFloors(value) {
    var base = buildDefaultBoardroomFloors();
    var next = asObject(value);

    return {
      sales: firstDefined(next.sales, base.sales, null),
      finance: firstDefined(next.finance, base.finance, null),
      operations: firstDefined(next.operations, base.operations, null),
      support: firstDefined(next.support, base.support, null),
      hr: firstDefined(next.hr, base.hr, null),
      marketing: firstDefined(next.marketing, base.marketing, null)
    };
  }

  function normalizeBoardroomTopology(value) {
    var base = buildDefaultBoardroomTopology();
    var next = asObject(value);

    return {
      nodes: asArray(firstDefined(next.nodes, base.nodes)),
      edges: asArray(firstDefined(next.edges, base.edges))
    };
  }

  function normalizeDashboardSummary(value, workspaceId, nodeId) {
    var base = buildDefaultDashboardSummary(workspaceId, nodeId);
    var next = asObject(value);

    return {
      workspace: clone(asObject(firstDefined(next.workspace, base.workspace))),
      node: clone(asObject(firstDefined(next.node, base.node))),
      scheduler: clone(asObject(firstDefined(next.scheduler, base.scheduler))),
      queue: clone(asObject(firstDefined(next.queue, base.queue))),
      approvals: clone(asObject(firstDefined(next.approvals, base.approvals))),
      health: clone(asObject(firstDefined(next.health, base.health))),
      departments: asArray(next.departments),
      alerts: asArray(next.alerts),
      recent_audit: asArray(next.recent_audit),
      audit_event_count: next.audit_event_count != null ? next.audit_event_count : asArray(next.recent_audit).length,
      updatedAt: firstDefined(next.updatedAt, next.updated_at, null)
    };
  }

  function normalizeBoardroomSnapshot(value, workspaceId) {
    var base = buildDefaultBoardroomSnapshot(workspaceId);
    var next = asObject(value);
    var resolvedWorkspaceId = workspaceId || next.workspaceId || next.workspace_id || base.workspaceId;

    return {
      workspaceId: resolvedWorkspaceId,
      viewMode: normalizeBoardroomViewMode(firstDefined(next.viewMode, next.view_mode, base.viewMode)),
      activeZone: normalizeActiveZone(firstDefined(next.activeZone, next.active_zone, base.activeZone)),
      selectedSeatId: normalizeSelectedSeatId(firstDefined(next.selectedSeatId, next.selected_seat_id, base.selectedSeatId)),
      selectedInspectorTarget: normalizeSelectedInspectorTarget(firstDefined(next.selectedInspectorTarget, next.selected_inspector_target, base.selectedInspectorTarget)),
      summary: next.summary || null,
      workspace: normalizeBoardroomWorkspace(firstDefined(next.workspace, base.workspace), resolvedWorkspaceId),
      center: normalizeBoardroomCenter(firstDefined(next.center, base.center)),
      pulse: normalizeBoardroomPulse(firstDefined(next.pulse, base.pulse)),
      seats: asArray(next.seats),
      departments: asArray(next.departments),
      floors: normalizeBoardroomFloors(firstDefined(next.floors, base.floors)),
      runtime: normalizeBoardroomRuntime(firstDefined(next.runtime, base.runtime)),
      topology: normalizeBoardroomTopology(firstDefined(next.topology, base.topology)),
      bindingsByCategory:
        next.bindingsByCategory && typeof next.bindingsByCategory === "object"
          ? clone(next.bindingsByCategory)
          : next.bindings_by_category && typeof next.bindings_by_category === "object"
            ? clone(next.bindings_by_category)
            : {},
      updatedAt: firstDefined(next.updatedAt, next.updated_at, null)
    };
  }

  function buildLiveAgentsSnapshot(seed) {
    seed = seed || {};
    return normalizeLiveAgentsSnapshot(seed);
  }

  function normalizeLiveAgentsSnapshot(value) {
    var base = buildDefaultLiveAgentsSnapshot();
    var next = asObject(value);

    return {
      runs: asArray(firstDefined(next.runs, base.runs)),
      approvals: asArray(firstDefined(next.approvals, base.approvals)),
      selectedLiveAgentId: normalizeSelectedLiveAgentId(firstDefined(next.selectedLiveAgentId, next.selected_live_agent_id, base.selectedLiveAgentId)),
      selectedLiveRunId: normalizeSelectedLiveRunId(firstDefined(next.selectedLiveRunId, next.selected_live_run_id, base.selectedLiveRunId)),
      liveAgentsReplayOpen: normalizeLiveAgentsReplayOpen(firstDefined(next.liveAgentsReplayOpen, next.live_agents_replay_open, base.liveAgentsReplayOpen)),
      liveAgentsView: normalizeLiveAgentsView(firstDefined(next.liveAgentsView, next.live_agents_view, base.liveAgentsView)),
      activeZone: normalizeActiveZone(firstDefined(next.activeZone, next.active_zone, base.activeZone)),
      updatedAt: firstDefined(next.updatedAt, next.updated_at, null)
    };
  }

  function buildOperationsFlowSnapshot(seed) {
    seed = seed || {};
    return normalizeOperationsFlowSnapshot(seed);
  }

  function normalizeOperationsFlowSnapshot(value) {
    var base = buildDefaultOperationsFlowSnapshot();
    var next = asObject(value);
    var workspaceId = firstDefined(next.workspaceId, next.workspace_id, next.boardroomSnapshot && next.boardroomSnapshot.workspaceId, DEFAULTS.workspaceId);

    var normalizedBoardroom =
      next.boardroomSnapshot || next.boardroom_snapshot
        ? normalizeBoardroomSnapshot(firstDefined(next.boardroomSnapshot, next.boardroom_snapshot), workspaceId)
        : null;

    return {
      viewMode: normalizeOperationsFlowViewMode(firstDefined(next.viewMode, next.view_mode, base.viewMode)),
      activeZone: normalizeActiveZone(firstDefined(next.activeZone, next.active_zone, base.activeZone)),
      selectedSeatId: normalizeSelectedSeatId(firstDefined(next.selectedSeatId, next.selected_seat_id, base.selectedSeatId)),
      selectedInspectorTarget: normalizeSelectedInspectorTarget(firstDefined(next.selectedInspectorTarget, next.selected_inspector_target, base.selectedInspectorTarget)),
      boardroomSnapshot: normalizedBoardroom,
      containerBindings: normalizeContainerBindings(firstDefined(next.containerBindings, next.container_bindings, base.containerBindings)),
      workspace: normalizeBoardroomWorkspace(firstDefined(next.workspace, normalizedBoardroom && normalizedBoardroom.workspace, base.workspace), workspaceId),
      pulse: normalizeBoardroomPulse(firstDefined(next.pulse, normalizedBoardroom && normalizedBoardroom.pulse, base.pulse)),
      runtime: normalizeBoardroomRuntime(firstDefined(next.runtime, normalizedBoardroom && normalizedBoardroom.runtime, base.runtime)),
      topology: normalizeBoardroomTopology(firstDefined(next.topology, normalizedBoardroom && normalizedBoardroom.topology, base.topology)),
      updatedAt: firstDefined(next.updatedAt, next.updated_at, null)
    };
  }

  function normalizeRecoveryPayload(value) {
    if (value == null || typeof value !== "object") return null;

    var next = asObject(value);
    // The old implementation cloned `next` wholesale, including its previous
    // `raw` member. Each normalization embedded the complete prior payload
    // inside the next one, growing the local cache recursively until the
    // renderer exhausted memory. Preserve useful non-recursive source fields
    // while explicitly excluding recovery wrappers.
    var rawSource = {};
    Object.keys(next).forEach(function (key) {
      if (key === "raw" || key === "recoveryPayload" || key === "recovery_payload") return;
      rawSource[key] = next[key];
    });
    var resolvedWorkspaceId = firstDefined(next.workspaceId, next.workspace_id, next.active_workspace_id, DEFAULTS.workspaceId);
    var resolvedNodeId = firstDefined(next.nodeId, next.node_id, DEFAULTS.nodeId);

    var normalizedBrandFoundation = normalizeBrandFoundationState(
      firstDefined(next.brandFoundationState, next.brand_foundation_state, next.brand_foundation, buildDefaultBrandFoundationState())
    );

    return {
      workspaceId: resolvedWorkspaceId,
      nodeId: resolvedNodeId,
      activeTab: normalizeActiveTab(firstDefined(next.activeTab, next.active_tab, DEFAULTS.activeTab)),
      boardroomViewMode: normalizeBoardroomViewMode(firstDefined(next.boardroomViewMode, next.boardroom_view_mode, DEFAULTS.boardroomViewMode)),
      operationsFlowViewMode: normalizeOperationsFlowViewMode(firstDefined(next.operationsFlowViewMode, next.operations_flow_view_mode, DEFAULTS.operationsFlowViewMode)),
      activeZone: normalizeActiveZone(firstDefined(next.activeZone, next.active_zone, DEFAULTS.activeZone)),
      selectedSeatId: normalizeSelectedSeatId(firstDefined(next.selectedSeatId, next.selected_seat_id, DEFAULTS.selectedSeatId)),
      selectedInspectorTarget: normalizeSelectedInspectorTarget(firstDefined(next.selectedInspectorTarget, next.selected_inspector_target, DEFAULTS.selectedInspectorTarget)),
      selectedLiveAgentId: normalizeSelectedLiveAgentId(firstDefined(next.selectedLiveAgentId, next.selected_live_agent_id, DEFAULTS.selectedLiveAgentId)),
      selectedLiveRunId: normalizeSelectedLiveRunId(firstDefined(next.selectedLiveRunId, next.selected_live_run_id, DEFAULTS.selectedLiveRunId)),
      liveAgentsReplayOpen: normalizeLiveAgentsReplayOpen(firstDefined(next.liveAgentsReplayOpen, next.live_agents_replay_open, DEFAULTS.liveAgentsReplayOpen)),
      liveAgentsView: normalizeLiveAgentsView(firstDefined(next.liveAgentsView, next.live_agents_view, DEFAULTS.liveAgentsView)),
      marketingCalendarMode: normalizeMarketingCalendarMode(firstDefined(next.marketingCalendarMode, next.marketing_calendar_mode, DEFAULTS.marketingCalendarMode)),

      aionChatMode: normalizeAionChatMode(firstDefined(next.aionChatMode, next.aion_chat_mode, DEFAULTS.aionChatMode)),
      aionChatEngine: normalizeAionChatEngine(firstDefined(next.aionChatEngine, next.aion_chat_engine, DEFAULTS.aionChatEngine)),
      aionChatPrompt: normalizePlainString(firstDefined(next.aionChatPrompt, next.aion_chat_prompt, DEFAULTS.aionChatPrompt), DEFAULTS.aionChatPrompt),
      aionChatOutput: normalizePlainString(firstDefined(next.aionChatOutput, next.aion_chat_output, DEFAULTS.aionChatOutput), DEFAULTS.aionChatOutput),

      dashboardSummary: normalizeDashboardSummary(firstDefined(next.dashboardSummary, next.dashboard_summary, null), resolvedWorkspaceId, resolvedNodeId),
      marketingSummary: firstDefined(next.marketingSummary, next.marketing_summary, null),
      boardroomSnapshot: normalizeBoardroomSnapshot(firstDefined(next.boardroomSnapshot, next.boardroom_snapshot, next.boardroom, null), resolvedWorkspaceId),
      liveAgentsSnapshot: normalizeLiveAgentsSnapshot(firstDefined(next.liveAgentsSnapshot, next.live_agents_snapshot, null)),
      operationsFlowSnapshot: normalizeOperationsFlowSnapshot(firstDefined(next.operationsFlowSnapshot, next.operations_flow_snapshot, null)),
      brandFoundationState: normalizedBrandFoundation,
      containerBindings: normalizeContainerBindings(firstDefined(next.containerBindings, next.container_bindings, [])),
      status: firstDefined(next.status, null),
      runs: asArray(firstDefined(next.runs, [])),
      approvals: asArray(firstDefined(next.approvals, [])),
      audit: asArray(firstDefined(next.audit, [])),
      scheduler: firstDefined(next.scheduler, null),
      syncBoundary: firstDefined(next.syncBoundary, next.sync_boundary, buildDefaultSyncBoundary()),
      lastRefreshAt: firstDefined(next.lastRefreshAt, next.last_refresh_at, next.at, null),
      raw: clone(rawSource)
    };
  }

  function buildDefaultState(seed) {
    seed = seed || {};

    var workspaceId = seed.workspaceId || DEFAULTS.workspaceId;
    var nodeId = seed.nodeId || DEFAULTS.nodeId;
    var marketingForm = normalizeMarketingForm(seed.marketingForm || buildDefaultMarketingForm());
    var boardroomSnapshot = normalizeBoardroomSnapshot(seed.boardroomSnapshot, workspaceId);

    return {
      apiBase: seed.apiBase || DEFAULTS.apiBase,
      webBase: seed.webBase || DEFAULTS.webBase,
      workspaceId: workspaceId,
      nodeId: nodeId,
      activeTab: normalizeActiveTab(seed.activeTab || DEFAULTS.activeTab),

      boardroomViewMode: normalizeBoardroomViewMode(seed.boardroomViewMode || boardroomSnapshot.viewMode || DEFAULTS.boardroomViewMode),
      operationsFlowViewMode: normalizeOperationsFlowViewMode(seed.operationsFlowViewMode || DEFAULTS.operationsFlowViewMode),
      activeZone: normalizeActiveZone(seed.activeZone || boardroomSnapshot.activeZone || DEFAULTS.activeZone),

      selectedSeatId: normalizeSelectedSeatId(seed.selectedSeatId !== undefined ? seed.selectedSeatId : boardroomSnapshot.selectedSeatId),
      selectedInspectorTarget: normalizeSelectedInspectorTarget(seed.selectedInspectorTarget !== undefined ? seed.selectedInspectorTarget : boardroomSnapshot.selectedInspectorTarget),
      selectedLiveAgentId: normalizeSelectedLiveAgentId(seed.selectedLiveAgentId !== undefined ? seed.selectedLiveAgentId : DEFAULTS.selectedLiveAgentId),
      selectedLiveRunId: normalizeSelectedLiveRunId(seed.selectedLiveRunId !== undefined ? seed.selectedLiveRunId : DEFAULTS.selectedLiveRunId),
      liveAgentsReplayOpen: normalizeLiveAgentsReplayOpen(seed.liveAgentsReplayOpen !== undefined ? seed.liveAgentsReplayOpen : DEFAULTS.liveAgentsReplayOpen),
      liveAgentsView: normalizeLiveAgentsView(seed.liveAgentsView !== undefined ? seed.liveAgentsView : DEFAULTS.liveAgentsView),
      marketingCalendarMode: normalizeMarketingCalendarMode(seed.marketingCalendarMode !== undefined ? seed.marketingCalendarMode : DEFAULTS.marketingCalendarMode),

      aionChatMode: normalizeAionChatMode(seed.aionChatMode !== undefined ? seed.aionChatMode : DEFAULTS.aionChatMode),
      aionChatEngine: normalizeAionChatEngine(seed.aionChatEngine !== undefined ? seed.aionChatEngine : DEFAULTS.aionChatEngine),
      aionChatPrompt: normalizePlainString(seed.aionChatPrompt !== undefined ? seed.aionChatPrompt : DEFAULTS.aionChatPrompt, DEFAULTS.aionChatPrompt),
      aionChatOutput: normalizePlainString(seed.aionChatOutput !== undefined ? seed.aionChatOutput : DEFAULTS.aionChatOutput, DEFAULTS.aionChatOutput),

      bound: false,
      loading: false,
      message: "",
      messageTone: "neutral",
      backendReady: false,
      backendStatus: "starting",

      status: seed.status || null,
      runs: asArray(seed.runs),
      approvals: asArray(seed.approvals),
      audit: asArray(seed.audit),
      scheduler: seed.scheduler || null,
      dashboardSummary: normalizeDashboardSummary(seed.dashboardSummary, workspaceId, nodeId),
      marketingSummary: seed.marketingSummary || null,
      boardroomSnapshot: boardroomSnapshot,
      liveAgentsSnapshot: normalizeLiveAgentsSnapshot(seed.liveAgentsSnapshot || {
        runs: seed.runs,
        approvals: seed.approvals,
        selectedLiveAgentId: seed.selectedLiveAgentId,
        selectedLiveRunId: seed.selectedLiveRunId,
        liveAgentsReplayOpen: seed.liveAgentsReplayOpen,
        liveAgentsView: seed.liveAgentsView,
        activeZone: seed.activeZone
      }),
      operationsFlowSnapshot: normalizeOperationsFlowSnapshot(seed.operationsFlowSnapshot || {
        viewMode: seed.operationsFlowViewMode,
        activeZone: seed.activeZone,
        selectedSeatId: seed.selectedSeatId,
        selectedInspectorTarget: seed.selectedInspectorTarget,
        boardroomSnapshot: boardroomSnapshot,
        containerBindings: seed.containerBindings,
        workspace: boardroomSnapshot.workspace,
        pulse: boardroomSnapshot.pulse,
        runtime: boardroomSnapshot.runtime,
        topology: boardroomSnapshot.topology
      }),
      recoveryPayload: normalizeRecoveryPayload(seed.recoveryPayload),
      brandFoundationState: normalizeBrandFoundationState(seed.brandFoundationState || buildDefaultBrandFoundationState(marketingForm), marketingForm),
      containerBindings: normalizeContainerBindings(seed.containerBindings),
      syncBoundary: seed.syncBoundary || buildDefaultSyncBoundary(),
      marketingForm: marketingForm,
      operationsAgentsWizardOpen: seed.operationsAgentsWizardOpen === true,
      operationsAgentsWizardStep: normalizeNumber(seed.operationsAgentsWizardStep, 1),
      operationsAgentsWizardSaving: seed.operationsAgentsWizardSaving === true,
      operationsAgentsWizardError: normalizePlainString(seed.operationsAgentsWizardError, ""),
      operationsAgentsWizardResult:
        seed.operationsAgentsWizardResult && typeof seed.operationsAgentsWizardResult === "object"
          ? clone(seed.operationsAgentsWizardResult)
          : null,

      operationsAgentsWizardDraft:
        seed.operationsAgentsWizardDraft && typeof seed.operationsAgentsWizardDraft === "object"
          ? clone(seed.operationsAgentsWizardDraft)
          : {
              name: "Gmail lead to HubSpot and welcome draft",
              department_key: "operations",
              operator_id: "operator_customer_onboarding_custom_v1",

              trigger: {
                trigger_type: "gmail_message_match",
                account_id: "default",
                query: "is:unread",
                dedupe: true,
                max_results: 10,
              },

              extraction: {
                step_type: "extract_customer_details",
                fields: [
                  {
                    key: "name",
                    label: "Customer name",
                    required: false,
                    description: "Name of the customer or lead.",
                  },
                  {
                    key: "email",
                    label: "Email",
                    required: true,
                    description: "Customer email address.",
                  },
                  {
                    key: "phone",
                    label: "Phone",
                    required: false,
                    description: "Customer phone number if present.",
                  },
                  {
                    key: "company",
                    label: "Company",
                    required: false,
                    description: "Company name if present.",
                  },
                  {
                    key: "enquiry_type",
                    label: "Enquiry type",
                    required: false,
                    description: "What the customer appears to be asking about.",
                  },
                ],
              },

              hubspot: {
                step_type: "hubspot_create_or_update_contact",
                account_id: "default",
                match_field: "email",
                dry_run: true,
                field_mapping: {
                  email: "email",
                  name: "firstname",
                  phone: "phone",
                  company: "company",
                  enquiry_type: "message",
                },
              },

              email_draft: {
                step_type: "gmail_draft_welcome_email",
                account_id: "default",
                to_field: "email",
                subject_template: "Welcome — thanks for your enquiry",
                body_template:
                  "Hi {{name}},\n\nThanks for getting in touch. We’ve received your enquiry about {{enquiry_type}} and will come back to you shortly.\n\nBest,\n{{business_name}}",
              },

              approval: {
                step_type: "approval_checkpoint",
                approval_mode: "ask_before_external_action",
                title: "Review new customer automation",
                require_human: true,
              },
            },

      lastRefreshAt: seed.lastRefreshAt || null
    };
  }

  global.TessarisDesktopContracts = {
    STORAGE_KEYS: STORAGE_KEYS,
    CACHE_KEYS: CACHE_KEYS,
    DEFAULTS: DEFAULTS,
    SURFACE_READ_CONTRACT: SURFACE_READ_CONTRACT,
    LIVE_AGENTS_VIEWS: LIVE_AGENTS_VIEWS,
    MARKETING_CALENDAR_MODES: MARKETING_CALENDAR_MODES,
    CREATIVE_ASSET_TYPES: CREATIVE_ASSET_TYPES,
    AION_CHAT_MODES: AION_CHAT_MODES,
    AION_CHAT_ENGINES: AION_CHAT_ENGINES,

    splitLines: splitLines,
    clone: clone,

    buildDefaultMarketingForm: buildDefaultMarketingForm,
    normalizeMarketingForm: normalizeMarketingForm,
    normalizeCreativeAssetType: normalizeCreativeAssetType,
    normalizeCreativeUploadedAsset: normalizeCreativeUploadedAsset,
    normalizeCreativeUploadedAssets: normalizeCreativeUploadedAssets,

    buildDefaultBrandIntelligenceMap: buildDefaultBrandIntelligenceMap,
    normalizeBrandIntelligenceMap: normalizeBrandIntelligenceMap,
    normalizePlatformStrategy: normalizePlatformStrategy,
    buildDefaultBrandFoundationState: buildDefaultBrandFoundationState,
    normalizeBrandFoundationState: normalizeBrandFoundationState,

    buildDefaultSyncBoundary: buildDefaultSyncBoundary,
    buildDefaultBoardroomPulse: buildDefaultBoardroomPulse,
    buildDefaultBoardroomCenter: buildDefaultBoardroomCenter,
    buildDefaultBoardroomRuntime: buildDefaultBoardroomRuntime,
    buildDefaultBoardroomFloors: buildDefaultBoardroomFloors,
    buildDefaultBoardroomTopology: buildDefaultBoardroomTopology,
    buildDefaultDashboardSummary: buildDefaultDashboardSummary,
    buildDefaultBoardroomSnapshot: buildDefaultBoardroomSnapshot,
    buildDefaultLiveAgentsSnapshot: buildDefaultLiveAgentsSnapshot,
    buildLiveAgentsSnapshot: buildLiveAgentsSnapshot,
    buildDefaultOperationsFlowSnapshot: buildDefaultOperationsFlowSnapshot,
    buildOperationsFlowSnapshot: buildOperationsFlowSnapshot,
    buildDefaultRecoveryState: buildDefaultRecoveryState,

    normalizeBoardroomViewMode: normalizeBoardroomViewMode,
    normalizeOperationsFlowViewMode: normalizeOperationsFlowViewMode,
    normalizeActiveTab: normalizeActiveTab,
    normalizeActiveZone: normalizeActiveZone,
    normalizeSelectedSeatId: normalizeSelectedSeatId,
    normalizeSelectedInspectorTarget: normalizeSelectedInspectorTarget,
    normalizeDashboardSummary: normalizeDashboardSummary,
    normalizeBoardroomWorkspace: normalizeBoardroomWorkspace,
    normalizeBoardroomCenter: normalizeBoardroomCenter,
    normalizeBoardroomPulse: normalizeBoardroomPulse,
    normalizeBoardroomRuntime: normalizeBoardroomRuntime,
    normalizeBoardroomFloors: normalizeBoardroomFloors,
    normalizeBoardroomTopology: normalizeBoardroomTopology,
    normalizeBoardroomSnapshot: normalizeBoardroomSnapshot,
    normalizeContainerBindings: normalizeContainerBindings,
    normalizeSelectedLiveAgentId: normalizeSelectedLiveAgentId,
    normalizeSelectedLiveRunId: normalizeSelectedLiveRunId,
    normalizeLiveAgentsReplayOpen: normalizeLiveAgentsReplayOpen,
    normalizeLiveAgentsView: normalizeLiveAgentsView,
    normalizeMarketingCalendarMode: normalizeMarketingCalendarMode,
    normalizeAionChatMode: normalizeAionChatMode,
    normalizeAionChatEngine: normalizeAionChatEngine,
    normalizeLiveAgentsSnapshot: normalizeLiveAgentsSnapshot,
    normalizeOperationsFlowSnapshot: normalizeOperationsFlowSnapshot,
    normalizeRecoveryPayload: normalizeRecoveryPayload,

    buildDefaultState: buildDefaultState
  };
})(window);
