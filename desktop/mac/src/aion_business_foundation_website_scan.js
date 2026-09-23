'use strict';

/*
 * AION O25AX — Foundation Website Discovery Runtime
 * -------------------------------------------------
 * Captures a website supplied during Business Foundation discovery,
 * calls the existing read-only website scanner, and enriches the
 * Business Foundation and Business Map with evidenced public facts.
 *
 * User-provided answers remain authoritative. Website extraction only
 * fills missing values and does not overwrite confirmed founder answers.
 *
 * Safety:
 * - Public website reading only.
 * - No publishing.
 * - No external messaging.
 * - No booking, payment, workflow execution or live chain write.
 * - No business-specific or industry-specific defaults.
 */

(function installAionBusinessFoundationWebsiteScan(globalObject) {
  const VERSION =
    "aion.o25ax.business_foundation_website_scan.v0.1";

  const DEFAULT_API_BASE =
    "http://127.0.0.1:8080";

  const SCAN_PATH =
    "/api/local-node/aion/small-business/website-scan";

  function clean(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function isMeaningful(value) {
    const text = clean(value);
    const lower = text.toLowerCase();

    return Boolean(text) &&
      lower !== "unknown" &&
      lower !== "not known" &&
      lower !== "n/a" &&
      lower !== "{}" &&
      lower !== "[]";
  }

  function isNoWebsiteAnswer(value) {
    const lower = clean(value).toLowerCase();

    return [
      "no",
      "none",
      "no website",
      "not yet",
      "i do not have a website",
      "i don't have a website",
      "we do not have a website",
      "we don't have a website",
      "no site",
      "skip",
      "skip that",
    ].includes(lower);
  }

  function normaliseWebsiteUrl(value = "") {
    let website = clean(value);

    if (!website) return "";

    if (isNoWebsiteAnswer(website)) {
      return "";
    }

    if (/^www\./i.test(website)) {
      website = `https://${website}`;
    }

    if (!/^https?:\/\//i.test(website)) {
      website = `https://${website}`;
    }

    return website;
  }

  function normaliseBusinessModel(value = "") {
    const lower = clean(value).toLowerCase();

    if (lower === "services" || lower === "service") {
      return "service";
    }

    if (lower === "products" || lower === "product") {
      return "product";
    }

    if (
      lower === "both" ||
      lower === "mixed" ||
      lower === "mixture"
    ) {
      return "mixed";
    }

    return clean(value);
  }

  function resolveApiBase(options = {}) {
    const candidate =
      options.apiBase ||
      globalObject.__AION_API_BASE__ ||
      globalObject.AION_API_BASE ||
      DEFAULT_API_BASE;

    return clean(candidate || DEFAULT_API_BASE)
      .replace(/\/+$/, "");
  }

  function clonePacket(packetInput = {}) {
    const packet =
      packetInput &&
      typeof packetInput === "object"
        ? packetInput
        : {};

    const businessMap =
      packet.business_map &&
      typeof packet.business_map === "object"
        ? packet.business_map
        : {};

    return {
      ...packet,

      foundation_draft: {
        ...(
          packet.foundation_draft &&
          typeof packet.foundation_draft === "object"
            ? packet.foundation_draft
            : {}
        ),
      },

      business_map: {
        ...businessMap,

        facts: Array.isArray(businessMap.facts)
          ? [...businessMap.facts]
          : [],

        assumptions:
          Array.isArray(businessMap.assumptions)
            ? [...businessMap.assumptions]
            : [],

        unanswered_fields:
          Array.isArray(businessMap.unanswered_fields)
            ? [...businessMap.unanswered_fields]
            : [],
      },
    };
  }

  function resolveExtractedFields(payload = {}) {
    const result =
      payload &&
      typeof payload === "object"
        ? payload
        : {};

    return (
      result.extracted_fields ||
      result.foundation ||
      result.result?.extracted_fields ||
      result.result?.foundation ||
      result.result ||
      result.data ||
      {}
    );
  }

  function compactEvidence(evidenceInput = {}) {
    const evidence =
      evidenceInput && typeof evidenceInput === "object"
        ? evidenceInput
        : {};

    const boundedList = (value, count, itemLimit = 500) =>
      (Array.isArray(value) ? value : [])
        .slice(0, count)
        .map((item) => clean(item).slice(0, itemLimit))
        .filter(Boolean);

    return {
      url: clean(evidence.url).slice(0, 2048),
      domain: clean(evidence.domain).slice(0, 255),
      title: clean(evidence.title).slice(0, 1000),
      headings: boundedList(evidence.headings, 24),
      emails: boundedList(evidence.emails, 20, 320),
      phones: boundedList(evidence.phones, 20, 100),
      social_links: boundedList(evidence.social_links, 24, 2048),
      logo_candidates: boundedList(evidence.logo_candidates, 16, 2048),
      icon_candidates: boundedList(evidence.icon_candidates, 16, 2048),
      social_image_candidates: boundedList(evidence.social_image_candidates, 16, 2048),
      colour_candidates: boundedList(evidence.colour_candidates, 24, 100),
      font_candidates: boundedList(evidence.font_candidates, 24, 320),
      stylesheet_urls: boundedList(evidence.stylesheet_urls, 24, 2048),
      visible_text_length:
        Number.isFinite(Number(evidence.visible_text_length))
          ? Math.max(0, Number(evidence.visible_text_length))
          : 0,
      live_external_side_effect: false,
    };
  }

  function buildFieldCandidates(extracted = {}) {
    const operatingBase = [
      clean(extracted.service_area),
      clean(extracted.business_address),
    ].filter(Boolean).join(" · ");

    const toolsAndEvidence = [
      clean(extracted.current_tools),
      clean(extracted.reviews_or_proof),
      clean(extracted.social_accounts),
    ].filter(Boolean).join(" · ");

    return [
      {
        target: "business_name",
        value: extracted.business_name,
      },
      {
        target: "business_model",
        value: normaliseBusinessModel(
          extracted.business_type
        ),
      },
      {
        target: "offer_summary",
        value: extracted.products_services,
      },
      {
        target: "customer_type",
        value: extracted.target_customers,
      },
      {
        target: "revenue_streams",
        value: extracted.revenue_streams,
      },
      {
        target: "operating_base",
        value: operatingBase,
      },
      {
        target: "current_tools_and_evidence",
        value: toolsAndEvidence,
      },
      {
        target: "current_challenges",
        value: extracted.current_pain_points,
      },
      {
        target: "near_term_priorities",
        value: extracted.growth_goals,
      },
    ];
  }

  function addBusinessMapFact(
    packet,
    field,
    value,
    receipt,
  ) {
    const facts =
      packet.business_map.facts;

    const duplicate = facts.some((fact) => {
      return (
        clean(fact?.field) === clean(field) &&
        clean(fact?.value) === clean(value) &&
        clean(fact?.source) ===
          "public_website_scan"
      );
    });

    if (duplicate) return;

    facts.push({
      field,
      value: clean(value),
      confidence: 0.72,
      source: "public_website_scan",
      source_url: receipt.url,
      receipt_id: receipt.receipt_id,
      provider: receipt.provider,
      model: receipt.model,
      created_at: receipt.completed_at,
      evidence_only: true,
      user_answer_overwritten: false,
    });
  }

  function rebuildPacket(
    packet,
    receipt,
    options = {},
  ) {
    const buildPacket =
      options.buildPacket ||
      globalObject
        .buildAionO25BBusinessFoundationDiscoveryPacket;

    let rebuilt = packet;

    if (typeof buildPacket === "function") {
      rebuilt = buildPacket(packet);
    }

    rebuilt =
      rebuilt &&
      typeof rebuilt === "object"
        ? rebuilt
        : packet;

    rebuilt.website_scan_receipt = receipt;

    rebuilt.business_map = {
      ...(rebuilt.business_map || {}),
      website_scan: receipt,
      facts:
        Array.isArray(packet.business_map?.facts)
          ? [...packet.business_map.facts]
          : [],
    };

    rebuilt.foundation_draft = {
      ...(rebuilt.foundation_draft || {}),
      ...(packet.foundation_draft || {}),
    };

    return rebuilt;
  }

  async function scanAndMerge(
    packetInput = {},
    options = {},
  ) {
    const packet = clonePacket(packetInput);
    const draft = packet.foundation_draft;

    const suppliedWebsite =
      clean(
        options.website ||
        draft.website_url ||
        draft.website ||
        ""
      );

    const startedAt =
      new Date().toISOString();

    if (isNoWebsiteAnswer(suppliedWebsite)) {
      draft.website_url = "No website";
      draft.website = "No website";

      const receipt = {
        version: VERSION,
        receipt_id:
          `website_scan_skipped_${Date.now()}`,
        status: "skipped",
        reason: "user_has_no_website",
        url: "",
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        extracted_fields: [],
        source_facts: [],
        warnings: [],
        public_read_only: true,
        live_external_side_effect: false,
        user_answers_overwritten: false,
      };

      return rebuildPacket(
        packet,
        receipt,
        options,
      );
    }

    const website =
      normaliseWebsiteUrl(suppliedWebsite);

    if (!website) {
      const receipt = {
        version: VERSION,
        receipt_id:
          `website_scan_missing_${Date.now()}`,
        status: "skipped",
        reason: "website_not_supplied",
        url: "",
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        extracted_fields: [],
        source_facts: [],
        warnings: [],
        public_read_only: true,
        live_external_side_effect: false,
        user_answers_overwritten: false,
      };

      return rebuildPacket(
        packet,
        receipt,
        options,
      );
    }

    draft.website_url = website;

    if (!isMeaningful(draft.website)) {
      draft.website = website;
    }

    const apiBase =
      resolveApiBase(options);

    const endpoint =
      `${apiBase}${SCAN_PATH}`;

    const fetchImpl =
      options.fetchImpl ||
      globalObject.fetch;

    if (typeof fetchImpl !== "function") {
      const receipt = {
        version: VERSION,
        receipt_id:
          `website_scan_failed_${Date.now()}`,
        status: "failed",
        reason: "fetch_unavailable",
        url: website,
        endpoint,
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        extracted_fields: [],
        source_facts: [],
        warnings: ["Website scanner fetch is unavailable."],
        public_read_only: true,
        live_external_side_effect: false,
        user_answers_overwritten: false,
      };

      return rebuildPacket(
        packet,
        receipt,
        options,
      );
    }

    let response;
    let payload = {};

    try {
      response = await fetchImpl(endpoint, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          website,
          business_id:
            clean(
              draft.business_id ||
              packet.business_id ||
              ""
            ),

          source:
            "business_foundation_voice_discovery",

          mode:
            "business_twin_foundation_scan",

          preview_only: true,
        }),
      });

      try {
        payload =
          await response.json();
      } catch {
        payload = {};
      }
    } catch (error) {
      const receipt = {
        version: VERSION,
        receipt_id:
          `website_scan_failed_${Date.now()}`,
        status: "failed",
        reason: "website_scan_request_failed",
        url: website,
        endpoint,
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        extracted_fields: [],
        source_facts: [],
        warnings: [
          clean(
            error?.message ||
            error ||
            "Website scan request failed"
          ),
        ],
        public_read_only: true,
        live_external_side_effect: false,
        user_answers_overwritten: false,
      };

      return rebuildPacket(
        packet,
        receipt,
        options,
      );
    }

    if (
      !response?.ok ||
      payload?.ok === false ||
      payload?.error
    ) {
      const warnings =
        Array.isArray(payload?.warnings)
          ? payload.warnings
          : [
              clean(
                payload?.detail ||
                payload?.error ||
                `Website scan failed with HTTP ${
                  response?.status || "unknown"
                }`
              ),
            ].filter(Boolean);

      const receipt = {
        version: VERSION,
        receipt_id:
          `website_scan_failed_${Date.now()}`,
        status: "failed",
        reason:
          payload?.error ||
          "website_scan_backend_rejected",
        url: website,
        endpoint,
        provider:
          clean(payload?.provider),
        model:
          clean(payload?.model),
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        extracted_fields: [],
        source_facts:
          payload?.source_facts || [],
        warnings,
        public_read_only: true,
        live_external_side_effect: false,
        user_answers_overwritten: false,
      };

      return rebuildPacket(
        packet,
        receipt,
        options,
      );
    }

    const extracted =
      resolveExtractedFields(payload);

    const safeEvidence =
      compactEvidence(payload?.evidence);

    const completedAt =
      new Date().toISOString();

    const receipt = {
      version: VERSION,
      receipt_id:
        `website_scan_${Date.now()}`,
      status: "success",
      reason:
        "public_website_evidence_collected",
      url: website,
      endpoint,
      provider:
        clean(payload?.provider || "openai"),
      model:
        clean(payload?.model),
      started_at: startedAt,
      completed_at: completedAt,
      extracted_fields: [],
      source_facts:
        payload?.source_facts ||
        extracted?.source_facts ||
        [],
      warnings:
        payload?.warnings ||
        extracted?.missing_information ||
        [],
      evidence:
        safeEvidence,
      public_read_only: true,
      live_external_side_effect: false,
      user_answers_overwritten: false,
    };

    const candidates =
      buildFieldCandidates(extracted);

    for (const candidate of candidates) {
      const target =
        clean(candidate.target);

      const value =
        clean(candidate.value);

      if (
        !target ||
        !isMeaningful(value)
      ) {
        continue;
      }

      if (
        isMeaningful(
          draft[target]
        )
      ) {
        continue;
      }

      draft[target] = value;

      receipt.extracted_fields.push(
        target
      );

      addBusinessMapFact(
        packet,
        target,
        value,
        receipt,
      );
    }

    const extendedWebsiteEvidence = {
      url: website,
      domain:
        clean(payload?.evidence?.domain),
      industry:
        clean(extracted?.industry),
      service_area:
        clean(extracted?.service_area),
      contact_email:
        clean(extracted?.contact_email),
      phone_number:
        clean(extracted?.phone_number),
      business_address:
        clean(extracted?.business_address),
      opening_hours:
        clean(extracted?.opening_hours),
      pricing_notes:
        clean(extracted?.pricing_notes),
      brand_notes:
        clean(extracted?.brand_notes),
      tone_of_voice:
        clean(extracted?.tone_of_voice),
      social_accounts:
        clean(extracted?.social_accounts),
      reviews_or_proof:
        clean(extracted?.reviews_or_proof),
      calls_to_action:
        clean(extracted?.calls_to_action),
      source_facts:
        receipt.source_facts,
      evidence:
        safeEvidence,
    };

    packet.business_map.website_evidence =
      extendedWebsiteEvidence;

    const detectedBrandEvidence = {
      source: "public_website_scan",
      authority: "detected_evidence_requires_confirmation",
      website,
      domain: safeEvidence.domain,
      logoCandidates: safeEvidence.logo_candidates,
      iconCandidates: safeEvidence.icon_candidates,
      socialImageCandidates: safeEvidence.social_image_candidates,
      colourCandidates: safeEvidence.colour_candidates,
      fontCandidates: safeEvidence.font_candidates,
      stylesheetUrls: safeEvidence.stylesheet_urls,
      scannedAt: completedAt,
    };

    packet.business_map.brand_design_evidence =
      detectedBrandEvidence;

    try {
      globalObject.desktopStore?.setBrandFoundationNestedValue?.(
        "brandMap.visualIdentity.designSystem.detectedEvidence",
        detectedBrandEvidence,
      );
    } catch (_error) {
      // The scan receipt remains canonical evidence even when the desktop
      // Brand Foundation store has not mounted yet.
    }

    packet.business_map.website_scan =
      receipt;

    return rebuildPacket(
      packet,
      receipt,
      options,
    );
  }

  const api = Object.freeze({
    VERSION,
    SCAN_PATH,
    clean,
    isNoWebsiteAnswer,
    normaliseWebsiteUrl,
    normaliseBusinessModel,
    scanAndMerge,
  });

  globalObject
    .AionBusinessFoundationWebsiteScan =
      api;

  globalObject
    .__aionBusinessFoundationWebsiteScanInstalled =
      true;

  if (
    typeof module !== "undefined" &&
    module.exports
  ) {
    module.exports = api;
  }
})(
  typeof window !== "undefined"
    ? window
    : globalThis
);
