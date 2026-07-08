'use strict';

/*
 * AION O25B — Business Foundation Voice Discovery Controller
 * ----------------------------------------------------------
 * Purpose:
 * - Convert voice/onboarding transcript turns into a structured Business Foundation draft.
 * - Preserve a Business Map packet that can feed Boardroom, Pilot and Department Intelligence.
 * - Keep the question flow generic and schema-driven.
 * - Do not hard-code business examples, verticals, services, answers or demo business defaults.
 * - Do not execute, publish, send, book, pay, or mutate external systems.
 */

const AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION =
  "aion.o25b.business_foundation_voice_discovery_controller.v0.1";

const AION_FOUNDATION_DISCOVERY_STARTERS = Object.freeze([
  {
    id: "welcome",
    role: "aion",
    purpose: "intro",
    text:
      "Welcome to AION. AION is a business operating system, not a normal chatbot. It helps map your business, build a Business Twin, support your Boardroom, and route work to the right business functions under approval controls.",
  },
  {
    id: "entry_mode",
    role: "aion",
    purpose: "starting_question",
    field: "entry_mode",
    text:
      "Are we working with an existing business, a new business idea, or a limited-context task?",
  },
  {
    id: "desired_outcome",
    role: "aion",
    purpose: "starting_question",
    field: "desired_outcome",
    text:
      "What are you looking to achieve first: map the business, improve decisions, automate internal work, build sales or marketing processes, or something else?",
  },
]);

const AION_FOUNDATION_SCHEMA = Object.freeze([
  {
    field: "entry_mode",
    label: "Entry mode",
    required: true,
    category: "foundation",
    prompt: "Are we working with an existing business, a new idea, or limited context?",
  },
  {
    field: "desired_outcome",
    label: "Desired outcome",
    required: true,
    category: "foundation",
    prompt: "What do you want AION to help you achieve first?",
  },
  {
    field: "business_name",
    label: "Business name",
    required: false,
    category: "identity",
    prompt: "What is the business called?",
  },
  {
    field: "business_model",
    label: "Business model",
    required: true,
    category: "model",
    prompt: "Does the business mainly sell products, services, both, subscriptions, digital products, marketplace access, or experiences?",
  },
  {
    field: "offer_summary",
    label: "Offer summary",
    required: true,
    category: "model",
    prompt: "What does the business sell or deliver in plain language?",
  },
  {
    field: "customer_type",
    label: "Customer type",
    required: true,
    category: "market",
    prompt: "Who buys from the business or who is the intended customer?",
  },
  {
    field: "revenue_streams",
    label: "Revenue streams",
    required: true,
    category: "finance",
    prompt: "How does the business make money?",
  },
  {
    field: "delivery_model",
    label: "Delivery model",
    required: true,
    category: "operations",
    prompt: "How is the product, service, access, or experience delivered to the customer?",
  },
  {
    field: "operating_base",
    label: "Operating base",
    required: false,
    category: "operations",
    prompt: "What people, premises, tools, suppliers, assets, or systems are involved?",
  },
  {
    field: "current_tools_and_evidence",
    label: "Current tools and evidence",
    required: false,
    category: "evidence",
    prompt: "Where does the real business data live, such as finance, sales, marketing, operations, support, website, inboxes, calendars, files, or spreadsheets?",
  },
  {
    field: "department_priorities",
    label: "Department priorities",
    required: false,
    category: "department_routing",
    prompt: "Which area should AION discover in more detail first: marketing, sales, finance, operations, support, or overall Boardroom planning?",
  },
]);

const AION_DEPARTMENT_DISCOVERY_KEYS = Object.freeze([
  "marketing",
  "sales",
  "finance",
  "operations",
  "support",
]);

function cleanAionO25BText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function normaliseAionO25BFieldValue(value) {
  return cleanAionO25BText(value);
}

function createAionBusinessFoundationVoiceDiscoveryState(seed = {}) {
  const now = new Date().toISOString();
  return {
    schema_version: AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION,
    status: "discovering",
    created_at: seed.created_at || now,
    updated_at: now,
    entry_mode: seed.entry_mode || "",
    transcript: Array.isArray(seed.transcript) ? [...seed.transcript] : [],
    foundation_draft: {
      ...(seed.foundation_draft && typeof seed.foundation_draft === "object"
        ? seed.foundation_draft
        : {}),
    },
    business_map: {
      schema_version: "aion.business_map.voice_foundation.v0.1",
      source: "voice_discovery",
      facts: [],
      assumptions: [],
      unanswered_fields: [],
      department_discovery_gaps: [...AION_DEPARTMENT_DISCOVERY_KEYS],
      ...(seed.business_map && typeof seed.business_map === "object"
        ? seed.business_map
        : {}),
    },
    safety: {
      preview_only: true,
      human_review_required: true,
      external_actions_allowed: false,
      live_execution_allowed: false,
      publish_allowed: false,
      send_message_allowed: false,
      booking_allowed: false,
      payment_allowed: false,
      mutates_business_context_only_after_review: true,
    },
  };
}

function getAionBusinessFoundationVoiceSchemaO25B() {
  return {
    schema_version: AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION,
    starters: AION_FOUNDATION_DISCOVERY_STARTERS.map((item) => ({ ...item })),
    fields: AION_FOUNDATION_SCHEMA.map((item) => ({ ...item })),
    departments: [...AION_DEPARTMENT_DISCOVERY_KEYS],
    policy: {
      schema_driven_questions: true,
      hardcoded_business_answers: false,
      hardcoded_vertical: false,
      hardcoded_demo_business: false,
      provider_generated_followups_allowed_later: true,
      deterministic_fallback_allowed: true,
      approval_required_before_business_context_commit: true,
    },
  };
}

function inferAionO25BEntryMode(text) {
  const lower = cleanAionO25BText(text).toLowerCase();
  if (!lower) return "";

  if (
    /\b(existing|already|current|trading|operating|running)\b/.test(lower) ||
    lower.includes("i have a business")
  ) {
    return "existing_business";
  }

  if (
    /\b(idea|new business|startup|start up|starting|launch)\b/.test(lower) ||
    lower.includes("i have an idea")
  ) {
    return "new_business_idea";
  }

  if (
    lower.includes("limited") ||
    lower.includes("just help") ||
    lower.includes("only need") ||
    lower.includes("one area")
  ) {
    return "limited_context";
  }

  return "";
}

function inferAionO25BBusinessModel(text) {
  const lower = cleanAionO25BText(text).toLowerCase();
  if (!lower) return "";

  const hasProduct = /\b(product|products|stock|sku|goods|items|catalogue|inventory)\b/.test(lower);
  const hasService = /\b(service|services|appointments|jobs|projects|consulting|labour|labor|client work)\b/.test(lower);
  const hasSubscription = /\b(subscription|membership|monthly|recurring|retainer|saas)\b/.test(lower);
  const hasDigital = /\b(digital|download|course|software|template|content)\b/.test(lower);
  const hasMarketplace = /\b(marketplace|buyers and sellers|vendors|platform)\b/.test(lower);
  const hasExperience = /\b(experience|venue|visits|hospitality|event|booking based)\b/.test(lower);

  if (hasProduct && hasService) return "product_service";
  if (hasSubscription) return "subscription";
  if (hasDigital) return "digital_product";
  if (hasMarketplace) return "marketplace";
  if (hasExperience) return "experience_hospitality";
  if (hasProduct) return "product";
  if (hasService) return "service";
  return "";
}

function extractAionO25BBusinessName(text) {
  const clean = cleanAionO25BText(text);
  const patterns = [
    /\b(?:business|company|brand)\s+(?:is called|is named|is)\s+(.+)$/i,
    /\b(?:we are called|we're called|it is called|it's called)\s+(.+)$/i,
    /\b(?:called)\s+(.+)$/i,
  ];

  for (const pattern of patterns) {
    const match = clean.match(pattern);
    if (match && match[1]) {
      return cleanAionO25BText(match[1]).replace(/[.!?]+$/g, "");
    }
  }

  return "";
}

function inferAionO25BDesiredOutcome(text) {
  const clean = cleanAionO25BText(text);
  const lower = clean.toLowerCase();
  if (!clean) return "";

  if (
    lower.includes("i want") ||
    lower.includes("we want") ||
    lower.includes("looking to") ||
    lower.includes("need to") ||
    lower.includes("trying to") ||
    lower.includes("help me") ||
    lower.includes("achieve") ||
    lower.includes("automate") ||
    lower.includes("map") ||
    lower.includes("improve") ||
    lower.includes("grow")
  ) {
    return clean;
  }

  return "";
}

function inferAionO25BFieldPatches(text, state = createAionBusinessFoundationVoiceDiscoveryState()) {
  const clean = cleanAionO25BText(text);
  const lower = clean.toLowerCase();
  const patches = [];

  if (!clean) return patches;

  const draft = state.foundation_draft || {};

  const entryMode = inferAionO25BEntryMode(clean);
  if (entryMode && !draft.entry_mode) {
    patches.push({ field: "entry_mode", value: entryMode, confidence: 0.78, source: "entry_mode_signal" });
  }

  const desiredOutcome = inferAionO25BDesiredOutcome(clean);
  if (desiredOutcome && !draft.desired_outcome) {
    patches.push({ field: "desired_outcome", value: desiredOutcome, confidence: 0.68, source: "outcome_signal" });
  }

  const businessName = extractAionO25BBusinessName(clean);
  if (businessName && !draft.business_name) {
    patches.push({ field: "business_name", value: businessName, confidence: 0.72, source: "name_phrase" });
  }

  const businessModel = inferAionO25BBusinessModel(clean);
  if (businessModel && !draft.business_model) {
    patches.push({ field: "business_model", value: businessModel, confidence: 0.66, source: "business_model_signal" });
  }

  if (
    !draft.customer_type &&
    /\b(customers|clients|members|users|buyers|audience|patients|guests|tenants|businesses|consumers)\b/.test(lower)
  ) {
    patches.push({ field: "customer_type", value: clean, confidence: 0.52, source: "customer_signal" });
  }

  if (
    !draft.revenue_streams &&
    /\b(make money|revenue|charge|pricing|price|paid|subscription|fee|margin|profit|sales)\b/.test(lower)
  ) {
    patches.push({ field: "revenue_streams", value: clean, confidence: 0.52, source: "revenue_signal" });
  }

  if (
    !draft.delivery_model &&
    /\b(deliver|delivered|fulfil|fulfill|appointment|online|in person|on site|remote|ship|booking|visit|project)\b/.test(lower)
  ) {
    patches.push({ field: "delivery_model", value: clean, confidence: 0.52, source: "delivery_signal" });
  }

  if (
    !draft.current_tools_and_evidence &&
    /\b(xero|quickbooks|sage|stripe|paypal|calendar|gmail|email|crm|website|spreadsheet|analytics|files|invoices|forms)\b/.test(lower)
  ) {
    patches.push({ field: "current_tools_and_evidence", value: clean, confidence: 0.52, source: "evidence_signal" });
  }

  if (
    !draft.offer_summary &&
    /\b(we sell|we provide|we offer|we deliver|business sells|business provides|business offers)\b/.test(lower)
  ) {
    patches.push({ field: "offer_summary", value: clean, confidence: 0.58, source: "offer_signal" });
  }

  return patches;
}

function applyAionO25BVoiceTurnToFoundationDraft(stateInput = {}, turnInput = {}) {
  const state = createAionBusinessFoundationVoiceDiscoveryState(stateInput);
  const now = new Date().toISOString();

  const turn = {
    id: turnInput.id || `voice_turn_${Date.now()}_${Math.random().toString(16).slice(2)}`,
    speaker: turnInput.speaker || "user",
    text: cleanAionO25BText(turnInput.text || ""),
    created_at: turnInput.created_at || now,
    source: turnInput.source || "voice_or_text_transcript",
  };

  if (turn.text) {
    state.transcript.push(turn);
  }

  const patches = Array.isArray(turnInput.patches)
    ? turnInput.patches
    : inferAionO25BFieldPatches(turn.text, state);

  for (const patch of patches) {
    const field = cleanAionO25BText(patch.field || "");
    const schemaField = AION_FOUNDATION_SCHEMA.find((item) => item.field === field);
    if (!schemaField) continue;

    const value = normaliseAionO25BFieldValue(patch.value);
    if (!value) continue;

    state.foundation_draft[field] = value;

    state.business_map.facts.push({
      field,
      category: schemaField.category,
      value,
      confidence: typeof patch.confidence === "number" ? patch.confidence : 0.5,
      source: patch.source || "transcript",
      transcript_turn_id: turn.id,
      created_at: now,
    });
  }

  state.entry_mode = state.foundation_draft.entry_mode || state.entry_mode || "";
  state.updated_at = now;
  state.business_map.unanswered_fields = getAionO25BMissingFoundationFields(state.foundation_draft).map((item) => item.field);
  state.next_question = buildAionO25BNextBestFoundationQuestion(state);

  return state;
}

function getAionO25BMissingFoundationFields(draft = {}) {
  return AION_FOUNDATION_SCHEMA.filter((field) => {
    if (!field.required) return false;
    return !cleanAionO25BText(draft[field.field] || "");
  }).map((field) => ({ ...field }));
}

function buildAionO25BNextBestFoundationQuestion(stateInput = {}) {
  const state = createAionBusinessFoundationVoiceDiscoveryState(stateInput);
  const draft = state.foundation_draft || {};
  const missing = getAionO25BMissingFoundationFields(draft);

  const unansweredStarter = AION_FOUNDATION_DISCOVERY_STARTERS.find((starter) => {
    return starter.field && !cleanAionO25BText(draft[starter.field] || "");
  });

  if (unansweredStarter) {
    return {
      source: "starter",
      field: unansweredStarter.field,
      question: unansweredStarter.text,
      reason: "starting_context_required",
      provider_generated: false,
      schema_driven: true,
    };
  }

  if (missing.length > 0) {
    const next = missing[0];
    return {
      source: "foundation_schema",
      field: next.field,
      question: next.prompt,
      reason: "required_foundation_field_missing",
      provider_generated: false,
      schema_driven: true,
    };
  }

  const departmentGaps = Array.isArray(state.business_map?.department_discovery_gaps)
    ? state.business_map.department_discovery_gaps.filter(Boolean)
    : [];

  if (departmentGaps.length > 0) {
    return {
      source: "department_discovery_gap",
      field: "department_priorities",
      question:
        "The foundation is ready enough to choose a deeper discovery area. Which function should AION explore next: marketing, sales, finance, operations, support, or overall Boardroom planning?",
      reason: "department_discovery_required",
      department_gaps: departmentGaps,
      provider_generated: false,
      schema_driven: true,
    };
  }

  return {
    source: "readiness",
    field: "",
    question:
      "AION has enough starting context to prepare a Business Foundation review. Do you want to review, correct, or continue deeper discovery?",
    reason: "foundation_review_ready",
    provider_generated: false,
    schema_driven: true,
  };
}

function buildAionO25BBusinessFoundationDiscoveryPacket(stateInput = {}) {
  const state = createAionBusinessFoundationVoiceDiscoveryState(stateInput);
  const draft = state.foundation_draft || {};
  const missing = getAionO25BMissingFoundationFields(draft);
  const requiredCount = AION_FOUNDATION_SCHEMA.filter((field) => field.required).length;
  const completeRequired = requiredCount - missing.length;
  const readinessScore = requiredCount > 0 ? Math.round((completeRequired / requiredCount) * 100) : 0;

  return {
    schema_version: "aion.business_foundation_discovery_packet.o25b.v0.1",
    controller_version: AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION,
    status: missing.length ? "foundation_discovery_in_progress" : "foundation_review_ready",
    readiness: {
      required_fields: requiredCount,
      complete_required_fields: completeRequired,
      missing_required_fields: missing.map((field) => field.field),
      readiness_score: readinessScore,
      readiness_label:
        readinessScore >= 90 ? "review_ready" :
        readinessScore >= 60 ? "partial" :
        readinessScore > 0 ? "early" :
        "not_started",
    },
    foundation_draft: { ...draft },
    business_map: {
      ...(state.business_map || {}),
      unanswered_fields: missing.map((field) => field.field),
    },
    next_question: buildAionO25BNextBestFoundationQuestion(state),
    department_handoff_preview: {
      enabled: missing.length === 0,
      departments: [...AION_DEPARTMENT_DISCOVERY_KEYS],
      writes_department_ledger_now: false,
      requires_founder_review: true,
    },
    boardroom_activation_preview: {
      advisory_mode_available: missing.length === 0,
      planning_mode_requires_review: true,
      execution_preview_requires_approval: true,
    },
    safety: { ...(state.safety || {}) },
  };
}

const exported = {
  AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION,
  AION_FOUNDATION_DISCOVERY_STARTERS,
  AION_FOUNDATION_SCHEMA,
  AION_DEPARTMENT_DISCOVERY_KEYS,
  createAionBusinessFoundationVoiceDiscoveryState,
  getAionBusinessFoundationVoiceSchemaO25B,
  inferAionO25BEntryMode,
  inferAionO25BBusinessModel,
  inferAionO25BDesiredOutcome,
  inferAionO25BFieldPatches,
  applyAionO25BVoiceTurnToFoundationDraft,
  getAionO25BMissingFoundationFields,
  buildAionO25BNextBestFoundationQuestion,
  buildAionO25BBusinessFoundationDiscoveryPacket,
};

if (typeof window !== "undefined") {
  window.AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION =
    AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION;
  window.AION_FOUNDATION_DISCOVERY_STARTERS = AION_FOUNDATION_DISCOVERY_STARTERS;
  window.AION_FOUNDATION_SCHEMA = AION_FOUNDATION_SCHEMA;
  window.createAionBusinessFoundationVoiceDiscoveryState =
    createAionBusinessFoundationVoiceDiscoveryState;
  window.getAionBusinessFoundationVoiceSchemaO25B =
    getAionBusinessFoundationVoiceSchemaO25B;
  window.applyAionO25BVoiceTurnToFoundationDraft =
    applyAionO25BVoiceTurnToFoundationDraft;
  window.buildAionO25BNextBestFoundationQuestion =
    buildAionO25BNextBestFoundationQuestion;
  window.buildAionO25BBusinessFoundationDiscoveryPacket =
    buildAionO25BBusinessFoundationDiscoveryPacket;
  window.__debugAionO25BBusinessFoundationVoiceController = function () {
    return getAionBusinessFoundationVoiceSchemaO25B();
  };
}

if (typeof module !== "undefined") {
  module.exports = exported;
}
