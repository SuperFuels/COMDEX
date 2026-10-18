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
    id: "contact_name",
    role: "aion",
    purpose: "starting_question",
    field: "contact_name",
    text: "Before we start, what should I call you?",
  },
  {
    id: "business_structure",
    role: "aion",
    purpose: "starting_question",
    field: "business_structure",
    text: "Which best describes the business: just you, you with occasional help, or a team with employees or regular contractors?",
  },
  {
    id: "owner_role",
    role: "aion",
    purpose: "starting_question",
    field: "owner_role",
    text: "Thanks. What is your role in the business?",
  },
]);

const AION_FOUNDATION_SCHEMA = Object.freeze([
  {
    field: "contact_name",
    label: "Contact name",
    required: true,
    guided: true,
    category: "identity",
    prompt: "Before we start, what should I call you?",
  },
  {
    field: "business_structure",
    label: "Business structure",
    required: true,
    guided: true,
    category: "identity",
    prompt:
      "Which best describes the business: just you, you with occasional help, or a team with employees or regular contractors?",
  },
  {
    field: "owner_role",
    label: "Owner role",
    required: true,
    guided: true,
    category: "identity",
    prompt: "What is your role in the business?",
  },
  {
    field: "business_name",
    label: "Business name",
    required: true,
    guided: true,
    category: "identity",
    prompt: "What is the business called?",
  },
  {
    field: "website_url",
    label: "Website",
    required: false,
    guided: true,
    category: "evidence",
    prompt:
      "Do you have a website? If so, please provide it starting with www. You can say no or skip.",
  },
  {
    field: "entry_mode",
    label: "Entry mode",
    required: true,
    guided: false,
    category: "foundation",
    prompt:
      "Are we working with an existing business, a new business idea, or generated business exploration?",
  },
  {
    field: "business_stage",
    label: "Business stage",
    required: true,
    guided: true,
    category: "foundation",
    prompt:
      "What stage is the business at: pre-launch, recently started, established, growing, or restructuring?",
  },
  {
    field: "revenue_status",
    label: "Revenue status",
    required: true,
    guided: true,
    category: "finance",
    prompt:
      "Is the business pre-revenue, earning occasional revenue, or generating regular revenue?",
  },
  {
    field: "annual_turnover_band",
    label: "Approximate annual turnover",
    required: false,
    guided: true,
    category: "finance",
    prompt:
      "What is the approximate annual turnover? A range is fine, and you can skip this or say that you prefer not to answer.",
  },
  {
    field: "desired_outcome",
    label: "Desired outcome",
    required: false,
    guided: false,
    category: "foundation",
    prompt: "",
  },
  {
    field: "business_model",
    label: "Business model",
    required: true,
    guided: true,
    category: "model",
    prompt:
      "Does the business mainly sell products, services, subscriptions, digital products, marketplace access, experiences, or a mixture?",
  },
  {
    field: "offer_summary",
    label: "Offer summary",
    required: true,
    guided: true,
    category: "model",
    prompt:
      "What does the business sell or deliver in plain language?",
  },
  {
    field: "customer_type",
    label: "Customer type",
    required: true,
    guided: true,
    category: "market",
    prompt:
      "Who are the main customers, and does the business mainly sell to individuals, businesses, or both?",
  },
  {
    field: "revenue_streams",
    label: "Revenue streams",
    required: true,
    guided: true,
    category: "finance",
    prompt: "How does the business make money?",
  },
  {
    field: "delivery_model",
    label: "Delivery model",
    required: true,
    guided: true,
    category: "operations",
    prompt:
      "How is the product, service, access, or experience delivered to the customer?",
  },
  {
    field: "operating_base",
    label: "Operating base",
    required: true,
    guided: true,
    category: "operations",
    prompt:
      "Where is the business based, and where does it serve customers?",
  },
  {
    field: "team_structure",
    label: "Team structure",
    required: false,
    guided: true,
    category: "operations",
    prompt:
      "Who is involved in running the business, and what are their main responsibilities?",
  },
  {
    field: "current_tools_and_evidence",
    label: "Current tools and evidence",
    required: false,
    guided: true,
    category: "evidence",
    prompt:
      "What systems or records does the business currently use, such as accounting software, email, CRM, website, calendars, files, or spreadsheets?",
  },
  {
    field: "current_challenges",
    label: "Current challenges",
    required: true,
    guided: true,
    category: "strategy",
    prompt:
      "What are the biggest problems, bottlenecks, or risks affecting the business right now?",
  },
  {
    field: "near_term_priorities",
    label: "Near-term priorities",
    required: false,
    guided: true,
    category: "strategy",
    prompt:
      "What are the most important things the business needs to achieve over the next three to twelve months?",
  },
  {
    field: "success_measure",
    label: "Success measure",
    required: false,
    guided: false,
    category: "measurement",
    prompt: "",
  },
  {
    field: "department_priorities",
    label: "Department priority",
    required: false,
    guided: false,
    category: "department_routing",
    prompt: "",
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
      entry_mode:
        cleanAionO25BText(
          seed.foundation_draft?.entry_mode ||
          seed.entry_mode ||
          ""
        ),
      ...(seed.foundation_draft && typeof seed.foundation_draft === "object"
        ? seed.foundation_draft
        : {}),
    },
    next_question: seed.next_question && typeof seed.next_question === "object" ? { ...seed.next_question } : null,
    last_turn: seed.last_turn && typeof seed.last_turn === "object" ? { ...seed.last_turn } : null,
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
  if (
    stateInput &&
    typeof stateInput === "object" &&
    !Object.keys(turnInput || {}).length &&
    (stateInput.text || stateInput.speaker || stateInput.source)
  ) {
    turnInput = stateInput;
    stateInput = {};
  }

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

  const currentQuestionField = cleanAionO25BText(
    turnInput.target_field ||
    turnInput.field ||
    state.next_question?.target_field ||
    state.next_question?.field ||
    ""
  );

  const patches = Array.isArray(turnInput.patches)
    ? [...turnInput.patches]
    : inferAionO25BFieldPatches(turn.text, state);

  const currentQuestionSchema = AION_FOUNDATION_SCHEMA.find(
    (item) => item.field === currentQuestionField
  );

  const userDeferredCurrentQuestion =
    turn.text &&
    currentQuestionSchema &&
    currentQuestionSchema.required === false &&
    /^(skip|skip that|not sure|i am not sure|i'm not sure|prefer not to say|rather not say|do not know|don't know)$/i.test(
      cleanAionO25BText(turn.text)
    );

  if (userDeferredCurrentQuestion) {
    patches.unshift({
      field: currentQuestionField,
      value: "deferred_by_user",
      confidence: 1,
      source: "user_deferred_optional_question",
    });
  }

  if (
    turn.text &&
    currentQuestionField &&
    AION_FOUNDATION_SCHEMA.some((item) => item.field === currentQuestionField) &&
    !state.foundation_draft[currentQuestionField] &&
    !userDeferredCurrentQuestion
  ) {
    patches.unshift({
      field: currentQuestionField,
      value: turn.text,
      confidence: 0.88,
      source: "current_question_answer",
    });
  }

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
  state.last_turn = {
    ...turn,
    mapped_field: patches.find((patch) => state.foundation_draft[patch.field])?.field || "",
  };
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
      text: unansweredStarter.text,
      target_field: unansweredStarter.field,
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
      text: next.prompt,
      target_field: next.field,
      reason: "required_foundation_field_missing",
      provider_generated: false,
      schema_driven: true,
    };
  }

  const nextOptionalGuidedField = AION_FOUNDATION_SCHEMA.find((item) => {
    return (
      item.required === false &&
      item.guided === true &&
      !cleanAionO25BText(draft[item.field] || "")
    );
  });

  if (nextOptionalGuidedField) {
    return {
      source: "optional_foundation_schema",
      field: nextOptionalGuidedField.field,
      question: nextOptionalGuidedField.prompt,
      text: nextOptionalGuidedField.prompt,
      target_field: nextOptionalGuidedField.field,
      reason: "optional_guided_foundation_field_unanswered",
      optional: true,
      skippable: true,
      provider_generated: false,
      schema_driven: true,
    };
  }

  return {
    source: "finance_handoff",
    field: "",
    question:
      "I now have a clear starting picture of what your business does, how it earns revenue, who it serves, and how it operates. We will now move into Finance and begin building your Finance Pilot. This is where AION will develop a deeper understanding of your pricing, revenue, costs, fixed and variable overheads, cash flow, margins, and connected accounting data. Your Finance Pilot will become a specialist agent for financial tasks, analysis, reporting, and controlled execution. Once the financial model is established, that understanding can be carried into the other business functions and your AI Boardroom. I am opening the Finance Live Agent now.",
    text:
      "I now have a clear starting picture of what your business does, how it earns revenue, who it serves, and how it operates. We will now move into Finance and begin building your Finance Pilot. This is where AION will develop a deeper understanding of your pricing, revenue, costs, fixed and variable overheads, cash flow, margins, and connected accounting data. Your Finance Pilot will become a specialist agent for financial tasks, analysis, reporting, and controlled execution. Once the financial model is established, that understanding can be carried into the other business functions and your AI Boardroom. I am opening the Finance Live Agent now.",
    target_field: "",
    reason: "finance_handoff_ready",
    action: "route_finance_live_agent",
    completion: true,
    next_department: "finance",
    next_pilot: "finance_pilot",
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
    status:
      missing.length
        ? "foundation_discovery_in_progress"
        : "foundation_ready_for_finance_handoff",
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
    transcript: Array.isArray(state.transcript) ? [...state.transcript] : [],
    transcript_count: Array.isArray(state.transcript) ? state.transcript.length : 0,
    last_turn: state.last_turn || null,
    next_question: buildAionO25BNextBestFoundationQuestion(state),
    business_map: {
      ...(state.business_map || {}),
      unanswered_fields: missing.map((field) => field.field),
    },
    department_handoff_preview: {
      enabled: missing.length === 0,
      department: "finance",
      pilot: "finance_pilot",
      route: "live_agents",
      sequence_position: 1,
      departments: [...AION_DEPARTMENT_DISCOVERY_KEYS],
      writes_department_ledger_now: false,
      requires_founder_review: false,
      automatic_route_allowed: missing.length === 0,
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
