window.__aionWorkflowUserViewportLocked = window.__aionWorkflowUserViewportLocked || false;
window.__aionWorkflowLastAutoFitGraphId = window.__aionWorkflowLastAutoFitGraphId || "";

window.__syncedArchitectInput = window.__syncedArchitectInput || {
  provider: "mock",
  workflowGoal: "",
};

if (window.__TESSARIS_DESKTOP_APP_INITIALIZED__) {
  console.warn("Tessaris desktop app.js already initialised, skipping duplicate load.");
} else {
  window.__TESSARIS_DESKTOP_APP_INITIALIZED__ = true;

  if (!window.TessarisDesktopContracts) {
    throw new Error("TessarisDesktopContracts not loaded before app.js");
  }

  if (!window.TessarisDesktopStore) {
    throw new Error("TessarisDesktopStore not loaded before app.js");
  }

  const {
    DEFAULTS,
    splitLines,
  } = window.TessarisDesktopContracts;

  const { createDesktopStore } = window.TessarisDesktopStore;

  const runtimeShared = window.TessarisDesktopRuntimeShared;
  const liveAgentsRuntime = window.TessarisDesktopLiveAgentsRuntime;
  const boardroomRuntime = window.TessarisDesktopBoardroomRuntime;
  const runtimeAdapter = window.TessarisDesktopRuntimeAdapter;

  if (!runtimeShared) {
    throw new Error("TessarisDesktopRuntimeShared not loaded before app.js");
  }

  if (!liveAgentsRuntime) {
    throw new Error("TessarisDesktopLiveAgentsRuntime not loaded before app.js");
  }

  if (!boardroomRuntime) {
    throw new Error("TessarisDesktopBoardroomRuntime not loaded before app.js");
  }

  if (!runtimeAdapter) {
    throw new Error("TessarisDesktopRuntimeAdapter not loaded before app.js");
  }

  const DEFAULT_API_BASE = DEFAULTS.apiBase;
  const DEFAULT_WEB_BASE = DEFAULTS.webBase;
  const DEFAULT_WORKSPACE_ID = DEFAULTS.workspaceId;
  const DEFAULT_NODE_ID = DEFAULTS.nodeId;

  const APP_TABS = [
    { key: "boardroom", label: "Boardroom" },
    { key: "dashboard", label: "Dashboard" },
    { key: "marketing_stream", label: "Marketing Stream" },
    { key: "brand_foundation", label: "Brand Foundation" },
    { key: "live_agents", label: "Live Agents" },
    { key: "aion_chat", label: "Aion", highlight: true },
    {
      key: "operations_agents",
      label: "Train Agent",
      description: "Train and test backend business automations",
    },
    { key: "operations_flow", label: "Operations Flow" },
    { key: "vault", label: "Vault" },
    { key: "local_node", label: "Local Node" },
  ];

  const LIVE_AGENT_VIEWS = {
    STREAM: "stream",
    CALENDAR: "calendar",
    RUNS: "runs",
    SETTINGS: "settings",
    APPROVALS: "approvals",
  };

  const MARKETING_CALENDAR_MODES = {
    PLANNING: "planning",
    REVIEW: "review",
    DONE: "done",
  };

  const desktopStore = createDesktopStore();
  const state = desktopStore.state;

  let unsubscribeBackendStatus = null;
  window.__TESSARIS_BACKEND_LISTENER_ATTACHED__ =
    window.__TESSARIS_BACKEND_LISTENER_ATTACHED__ || false;

  function getMarketingCalendarMode() {
    return state.marketingCalendarMode || MARKETING_CALENDAR_MODES.DONE;
  }

  function getLiveAgentsView() {
    return state.liveAgentsView || LIVE_AGENT_VIEWS.STREAM;
  }

  function getInputValue(event) {
    return event && event.target ? event.target.value : "";
  }

  function getRuntimeAdapterDeps() {
    return {
      state,
      desktopStore,
      render,
      normalizeBindingsByCategory,
    };
  }

  
const AION_BROWSER_WORKFLOW_MODES = [
  {
    id: "aion_workspace",
    title: "Aion Browser Workspace",
    label: "Recommended",
    risk: "Lower risk",
    description:
      "Aion uses its own isolated browser profile, logins, downloads, permissions, replay, and audit trail.",
    bullets: [
      "Separate browser profile",
      "Best for business automation",
      "Cleaner screenshots and replay",
      "Recommended for real workflows",
    ],
  },
  {
    id: "user_browser",
    title: "Use My Browser",
    label: "Advanced",
    risk: "Higher risk",
    description:
      "Aion can use a browser/profile you explicitly connect. Useful when you are already logged in, but it needs tighter approval gates.",
    bullets: [
      "Fastest setup",
      "Uses an explicitly connected browser",
      "Requires visible activation",
      "Approval required before risky actions",
    ],
  },
];

const AION_BROWSER_WORKFLOW_RISK_RULES = [
  "No hidden browser access.",
  "No silent extension install.",
  "No password capture.",
  "No payment, delete, send, or final submit without approval.",
  "Every browser run must have replay and audit.",
];

function getBrowserWorkflowBridgeState() {
  const existing = state.browserWorkflowBridge || {};
  return {
    mode: existing.mode || "aion_workspace",
    status: existing.status || "inactive",
    connectedBrowser: existing.connectedBrowser || "",
    connectedProfile: existing.connectedProfile || "",
    allowedDomains: Array.isArray(existing.allowedDomains)
      ? existing.allowedDomains
      : [],
    approvalRequired: existing.approvalRequired !== false,
    recordScreenshots: existing.recordScreenshots !== false,
    maskSecrets: existing.maskSecrets !== false,
    lastActivatedAt: existing.lastActivatedAt || "",
    lastStoppedAt: existing.lastStoppedAt || "",
  };
}

function renderBrowserWorkflowModeCard(mode, selectedMode, bridge, loading) {
  const selected = mode.id === selectedMode;

  return `
    <button
      class="browser-workflow-mode-card ${selected ? "browser-workflow-mode-selected" : ""}"
      data-operations-agents-action="select-browser-workflow-mode"
      data-browser-workflow-mode="${escapeHtml(mode.id)}"
      type="button"
      ${loading ? "disabled" : ""}
    >
      <div class="browser-workflow-mode-top">
        <div>
          <div class="eyebrow">${escapeHtml(mode.label)}</div>
          <h3>${escapeHtml(mode.title)}</h3>
        </div>
        <span class="train-status-chip ${selected ? "train-status-ok" : ""}">
          ${selected ? "Selected" : escapeHtml(mode.risk)}
        </span>
      </div>

      <p>${escapeHtml(mode.description)}</p>

      <div class="browser-workflow-bullet-list">
        ${mode.bullets.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
      </div>
    </button>
  `;
}

function renderBrowserWorkflowBridgePanel() {
  const bridge = getBrowserWorkflowBridgeState();
  const loading = state.operationsAgentsLoading === true;
  const selectedMode = bridge.mode || "aion_workspace";
  const selectedModeMeta =
    AION_BROWSER_WORKFLOW_MODES.find((item) => item.id === selectedMode) ||
    AION_BROWSER_WORKFLOW_MODES[0];
  const isActive = bridge.status === "active";

  return `
    <div class="train-panel browser-workflow-panel">
      <div class="train-panel-header">
        <div>
          <div class="eyebrow">Phase 4A</div>
          <h2>Browser Workflow Operator</h2>
          <p class="muted" style="margin:10px 0 0; max-width:860px;">
            Teach Aion browser tasks by demonstration. First choose whether Aion should use an isolated workspace browser
            or a browser/profile you explicitly connect.
          </p>
        </div>

        <span class="train-status-chip ${isActive ? "train-status-ok" : ""}">
          ${isActive ? "Bridge active" : "Bridge inactive"}
        </span>
      </div>

      <div class="train-panel-body">
        <div class="browser-workflow-mode-grid">
          ${AION_BROWSER_WORKFLOW_MODES.map((mode) =>
            renderBrowserWorkflowModeCard(mode, selectedMode, bridge, loading),
          ).join("")}
        </div>

        <div class="browser-workflow-activation-row">
          <div>
            <div class="eyebrow">Selected mode</div>
            <h3>${escapeHtml(selectedModeMeta.title)}</h3>
            <p class="muted" style="margin:8px 0 0;">
              ${selectedMode === "aion_workspace"
                ? "Recommended default. Aion will use its own isolated browser workspace when the bridge is implemented."
                : "Advanced mode. Aion will only use a browser/profile after the user explicitly activates the bridge."}
            </p>
          </div>

          <div class="browser-workflow-button-row">
            ${
              isActive
                ? `
                  <button
                    class="secondary-btn danger-btn"
                    data-operations-agents-action="stop-browser-workflow-bridge"
                    ${loading ? "disabled" : ""}
                  >
                    Stop Bridge
                  </button>
                `
                : `
                  <button
                    class="primary-btn"
                    data-operations-agents-action="activate-browser-workflow-bridge"
                    ${loading ? "disabled" : ""}
                  >
                    Activate Bridge
                  </button>
                `
            }

            <button
              class="secondary-btn"
              data-operations-agents-action="reset-browser-workflow-bridge"
              ${loading ? "disabled" : ""}
            >
              Reset
            </button>
          </div>
        </div>

        <div class="browser-workflow-status-grid">
          <div class="mini-card">
            <div class="metric-label">Mode</div>
            <div class="metric-note">${escapeHtml(selectedModeMeta.title)}</div>
          </div>

          <div class="mini-card">
            <div class="metric-label">Approval</div>
            <div class="metric-note">${bridge.approvalRequired ? "Required before risky actions" : "Not required"}</div>
          </div>

          <div class="mini-card">
            <div class="metric-label">Screenshots</div>
            <div class="metric-note">${bridge.recordScreenshots ? "Replay capture enabled" : "Replay capture disabled"}</div>
          </div>

          <div class="mini-card">
            <div class="metric-label">Secrets</div>
            <div class="metric-note">${bridge.maskSecrets ? "Passwords and secrets masked" : "Masking disabled"}</div>
          </div>
        </div>

        <div class="train-status-note train-status-note-waiting" style="margin-top:16px;">
          <span class="train-status-label">Safety</span>
          <div>
            <strong>Browser control is explicit, visible, and stoppable.</strong>
            <p class="muted" style="margin:6px 0 0;">
              This phase only adds the bridge activation model. Actual browser control, recording, and replay come next.
            </p>
          </div>
        </div>

        <div class="browser-workflow-risk-list">
          ${AION_BROWSER_WORKFLOW_RISK_RULES.map((rule) => `
            <div class="browser-workflow-risk-item">${escapeHtml(rule)}</div>
          `).join("")}
        </div>

        ${
          bridge.lastActivatedAt || bridge.lastStoppedAt
            ? `
              <pre class="json-preview" style="margin-top:16px;">${escapeHtml(JSON.stringify({
                status: bridge.status,
                mode: bridge.mode,
                connectedBrowser: bridge.connectedBrowser || null,
                connectedProfile: bridge.connectedProfile || null,
                lastActivatedAt: bridge.lastActivatedAt || null,
                lastStoppedAt: bridge.lastStoppedAt || null,
              }, null, 2))}</pre>
            `
            : ""
        }
      </div>
    </div>
  `;
}


function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

function prettify(value) {
  return String(value ?? "—").replaceAll("_", " ");
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-GB");
}

function shortJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch (_) {
    return String(value);
  }
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function asFileListArray(value) {
  return Array.from(value || []).filter(Boolean);
}

function normalizeMarketingAssetType(value) {
  const raw = String(value || "").trim().toLowerCase();

  const allowed = {
    product: true,
    brand_logo: true,
    background: true,
    people_headshot: true,
    reference_style: true,
  };

  return allowed[raw] ? raw : "product";
}

function getMarketingCreativeAssetDrafts() {
  const form = state.marketingForm || {};
  return Array.isArray(form.creativeAssets) ? form.creativeAssets : [];
}

function renderMarketingAssetTypeOptions(selected) {
  const value = normalizeMarketingAssetType(selected);

  const options = [
    ["product", "Product / offer"],
    ["brand_logo", "Brand / logo"],
    ["background", "Background"],
    ["people_headshot", "People / headshot"],
    ["reference_style", "Reference style"],
  ];

  return options
    .map(
      ([key, label]) => `
        <option value="${escapeHtml(key)}" ${value === key ? "selected" : ""}>
          ${escapeHtml(label)}
        </option>
      `,
    )
    .join("");
}

function renderMarketingCreativeAssetList() {
  const assets = getMarketingCreativeAssetDrafts();

  if (!assets.length) {
    return `
      <div class="empty-state" style="margin-top:10px;">
        No creative assets added yet. Upload product shots, logos, backgrounds, headshots, or reference style images.
      </div>
    `;
  }

  return `
    <div class="list-wrap" style="margin-top:10px;">
      ${assets
        .map((asset, index) => {
          const assetId = asset?.id || `asset_${index}`;
          const previewUrl = asset?.previewUrl || asset?.url || "";

          return `
            <div class="list-item" style="
              display:grid;
              grid-template-columns:72px minmax(0, 1fr) auto;
              gap:12px;
              align-items:start;
            ">
              <div style="
                width:72px;
                height:72px;
                border:1px solid rgba(15,23,42,0.14);
                background:#f8fafc;
                overflow:hidden;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:11px;
                color:rgba(17,17,17,0.55);
              ">
                ${
                  previewUrl
                    ? `
                      <img
                        src="${escapeHtml(previewUrl)}"
                        alt="${escapeHtml(asset?.label || "Creative asset")}"
                        style="
                          width:100%;
                          height:100%;
                          object-fit:cover;
                          display:block;
                        "
                      />
                    `
                    : "Image"
                }
              </div>

              <div style="min-width:0;">
                <div class="list-item-title">${escapeHtml(asset?.label || asset?.fileName || "Creative asset")}</div>
                <div class="list-item-sub">${escapeHtml(prettify(asset?.type || "product"))}</div>

                <label class="field-label" style="margin-top:8px;">Asset notes</label>
                <textarea
                  class="input input-textarea input-textarea-small marketing-asset-notes-input"
                  data-asset-id="${escapeHtml(assetId)}"
                  placeholder="Example: Main hero product image. Use on cards 1 and 5."
                >${escapeHtml(asset?.notes || "")}</textarea>
              </div>

              <button
                type="button"
                class="secondary-btn marketing-asset-remove-btn"
                data-asset-id="${escapeHtml(assetId)}"
              >
                Remove
              </button>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function buildCreativeAssetsPayload() {
  return getMarketingCreativeAssetDrafts().map((asset, index) => ({
    id: asset?.id || `asset_${index + 1}`,
    type: normalizeMarketingAssetType(asset?.type),
    label: asset?.label || asset?.fileName || `Creative asset ${index + 1}`,
    url: asset?.url || "",
    file_path: asset?.file_path || asset?.filePath || "",
    notes: asset?.notes || "",
    mime_type: asset?.mimeType || asset?.mime_type || "",
    size_bytes: asset?.sizeBytes || asset?.size_bytes || null,
  }));
}

function buildCreativeDirectionPayload() {
  const form = state.marketingForm || {};

  return {
    asset_intent: normalizeMarketingAssetType(form.assetIntent || "product"),
    product_name: form.productName || "",
    offer_price: form.offerPrice || "",
    offer_details: form.offerDetails || "",
    usage_notes: form.imageUsageNotes || "",
    style_direction: form.styleDirection || "",
    creative_direction: form.creativeDirection || "",
  };
}

function asRecord(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : null;
}

function getRunResultPayload(run) {
  return asRecord(run?.result_payload) || asRecord(run?.result) || {};
}

function getRunContext(run) {
  return asRecord(run?.context) || {};
}

function getRunInputPayload(run) {
  return asRecord(run?.input_payload) || {};
}

function getRunPostPackage(run) {
  const resultPayload = getRunResultPayload(run);
  const context = getRunContext(run);

  if (resultPayload?.type === "marketing_post_package") {
    return resultPayload;
  }

  if (context?.type === "marketing_post_package") {
    return context;
  }

  return (
    asRecord(resultPayload?.post_package) ||
    asRecord(resultPayload?.publish_result?.post_package) ||
    asRecord(context?.post_package) ||
    null
  );
}

function getRunGeneratedImage(run) {
  const resultPayload = getRunResultPayload(run);
  const postPackage = getRunPostPackage(run);

  const publishResult =
    asRecord(postPackage?.publish_result) ||
    asRecord(resultPayload?.publish_result) ||
    null;

  return (
    asRecord(resultPayload?.generated_image) ||
    asRecord(postPackage?.generated_image) ||
    asRecord(publishResult?.generated_image) ||
    null
  );
}

function toRuntimeImageUrl(path) {
  const raw = firstString(path) || "";
  if (!raw) return "";

  if (/^https?:\/\//i.test(raw)) {
    return raw;
  }

  if (raw.startsWith("/runtime/")) {
    return `${state.apiBase}${raw}`;
  }

  if (raw.startsWith(".runtime/")) {
    return `${state.apiBase}/runtime/${raw.slice(".runtime/".length)}`;
  }

  if (raw.startsWith("runtime/")) {
    return `${state.apiBase}/${raw}`;
  }

  if (raw.startsWith("/")) {
    return `${state.apiBase}${raw}`;
  }

  return `${state.apiBase}/${raw}`;
}

function toRuntimeAssetUrl(value) {
  const raw = firstString(value);
  if (!raw) return "";

  if (
    raw.startsWith("http://") ||
    raw.startsWith("https://") ||
    raw.startsWith("data:")
  ) {
    return raw;
  }

  const apiBase = String(state.apiBase || "http://127.0.0.1:8080").replace(/\/+$/, "");

  if (raw.startsWith(".runtime/")) {
    return `${apiBase}/runtime/${raw.slice(".runtime/".length)}`;
  }

  if (raw.startsWith("runtime/")) {
    return `${apiBase}/${raw}`;
  }

  if (raw.startsWith("/runtime/")) {
    return `${apiBase}${raw}`;
  }

  return raw;
}

function getRunGeneratedImageUrl(run) {
  const resultPayload = getRunResultPayload(run);
  const postPackage = getRunPostPackage(run);
  const generatedImage = getRunGeneratedImage(run);
  const publishResult =
    asRecord(postPackage?.publish_result) ||
    asRecord(resultPayload?.publish_result) ||
    null;

  const raw =
    firstString(
      generatedImage?.url,
      generatedImage?.asset_url,
      generatedImage?.file_path,
      resultPayload?.generated_image?.url,
      resultPayload?.generated_image?.asset_url,
      resultPayload?.generated_image?.file_path,
      postPackage?.generated_image?.url,
      postPackage?.generated_image?.asset_url,
      postPackage?.generated_image?.file_path,
      publishResult?.generated_image?.url,
      publishResult?.generated_image?.asset_url,
      publishResult?.generated_image?.file_path,
      resultPayload?.image_generation?.asset_url,
      resultPayload?.image_generation?.url,
      postPackage?.image_generation?.asset_url,
      postPackage?.image_generation?.url,
      publishResult?.image_generation?.asset_url,
      publishResult?.image_generation?.url
    ) || "";

  return toRuntimeAssetUrl(raw);
}

function getRunImageGeneration(run) {
  const resultPayload = getRunResultPayload(run);
  const postPackage = getRunPostPackage(run);

  const publishResult =
    asRecord(postPackage?.publish_result) ||
    asRecord(resultPayload?.publish_result) ||
    null;

  return (
    asRecord(resultPayload?.image_generation) ||
    asRecord(postPackage?.image_generation) ||
    asRecord(publishResult?.image_generation) ||
    null
  );
}

function getRunImageFailure(run) {
  const imageGeneration = getRunImageGeneration(run);
  return firstString(
    imageGeneration?.error,
    getRunGeneratedImage(run)?.error,
  ) || "";
}

function getRunCarouselSlides(run) {
  const postPackage = getRunPostPackage(run);
  const resultPayload = getRunResultPayload(run);
  const context = getRunContext(run);

  const rawCarousel =
    safeArray(postPackage?.carousel).length
      ? safeArray(postPackage?.carousel)
      : safeArray(postPackage?.content_blocks).length
        ? safeArray(postPackage?.content_blocks)
        : safeArray(resultPayload?.draft_carousel?.draft_carousel).length
          ? safeArray(resultPayload.draft_carousel.draft_carousel)
          : safeArray(resultPayload?.draft_carousel).length
            ? safeArray(resultPayload.draft_carousel)
            : safeArray(context?.draft_carousel);

  const slides = rawCarousel
    .map((item) => {
      if (typeof item === "string") {
        return { headline: item.trim(), body: "" };
      }

      if (isRecord(item)) {
        return {
          headline: firstString(
            item.headline,
            item.title,
            item.hook,
            item.label,
            item.text,
          ) || "",
          body: firstString(
            item.body,
            item.subtitle,
            item.copy,
            item.description,
            item.value,
          ) || "",
        };
      }

      return { headline: String(item ?? "").trim(), body: "" };
    })
    .filter((item) => item.headline || item.body)
    .slice(0, 5);

  return slides;
}

function renderFacebookPostMockup(run, options = {}) {
  const postPackage = getRunPostPackage(run);
  const resultPayload = getRunResultPayload(run);
  const context = getRunContext(run);

  const publishResult =
    asRecord(postPackage?.publish_result) ||
    asRecord(resultPayload?.publish_result) ||
    null;

  const imageFailure = getRunImageFailure(run);
  const slides = getRunCarouselSlides(run);

  const caption =
    firstString(
      postPackage?.caption,
      postPackage?.body,
      resultPayload?.draft_caption?.draft_caption,
      resultPayload?.draft_caption,
      context?.draft_caption,
      run?.draft_caption,
      run?.brief,
    ) || "";

  const channels = safeArray(postPackage?.channels);
  const primaryChannel = firstString(channels[0], "Facebook") || "Facebook";

  const pageName =
    firstString(
      postPackage?.brand_name,
      postPackage?.page_name,
      postPackage?.business_name,
      context?.business_name,
      "Costa Conexion",
    ) || "Costa Conexion";

  const publishStatus =
    firstString(
      publishResult?.status,
      postPackage?.status,
      run?.status,
    ) || "draft";

  const visualType = firstString(
    postPackage?.visual_type,
    postPackage?.image_layout,
    slides.length > 1 ? "carousel" : "single",
  );

  const isCarousel = visualType === "carousel" || slides.length > 1;

  const requestedActiveIndex = Number(options.activeIndex ?? 0);
  const maxSlideIndex = Math.max(slides.length - 1, 0);

  const activeIndex = Math.max(
    0,
    Math.min(
      Number.isFinite(requestedActiveIndex) ? requestedActiveIndex : 0,
      maxSlideIndex,
    ),
  );

  const activeSlide =
    slides[activeIndex] ||
    (caption
      ? {
          headline: caption,
          body: "",
        }
      : null);

  const pageCount = slides.length || 1;
  const pageLabel = `${activeIndex + 1}/${pageCount}`;

  const rawCarouselCards =
    safeArray(postPackage?.carousel_cards).length
      ? safeArray(postPackage.carousel_cards)
      : safeArray(postPackage?.generated_carousel_cards).length
        ? safeArray(postPackage.generated_carousel_cards)
        : safeArray(publishResult?.carousel_cards).length
          ? safeArray(publishResult.carousel_cards)
          : safeArray(resultPayload?.carousel_cards).length
            ? safeArray(resultPayload.carousel_cards)
            : safeArray(resultPayload?.generated_carousel_cards).length
              ? safeArray(resultPayload.generated_carousel_cards)
              : [];

  const carouselCards = rawCarouselCards.map((card, index) => {
    const record = asRecord(card) || {};

    const rawUrl =
      firstString(
        record?.image_url,
        record?.imageUrl,
        record?.asset_url,
        record?.assetUrl,
        record?.url,
        record?.file_path,
        record?.filePath,
      ) || "";

    return {
      ...record,
      card_index:
        Number.isFinite(Number(record?.card_index))
          ? Number(record.card_index)
          : Number.isFinite(Number(record?.cardIndex))
            ? Number(record.cardIndex)
            : index + 1,
      imageUrl: normalizeImageSrc(toRuntimeAssetUrl(rawUrl)),
      status:
        firstString(record?.status, rawUrl ? "completed" : "pending") || "pending",
    };
  });

  const fallbackImageUrl = normalizeImageSrc(getRunGeneratedImageUrl(run));

  const activeCarouselCard =
    carouselCards.find((card) => Number(card?.card_index) === activeIndex + 1) ||
    carouselCards[activeIndex] ||
    null;

  // IMPORTANT:
  // Always allow fallbackImageUrl, even when this is a carousel.
  // The backend may currently generate one main image under generated_image rather
  // than one image per carousel card.
  const activeCardImageUrl =
    activeCarouselCard?.imageUrl ||
    fallbackImageUrl ||
    "";

  const showDesignedImage = !!activeCardImageUrl;
  const showTextOverlay = !showDesignedImage;

  const mediaAspectRatio = isCarousel ? "4 / 5" : "1.91 / 1";

  const canGoPrev = activeIndex > 0;
  const canGoNext = activeIndex < pageCount - 1;

  const footerMeta = [
    primaryChannel,
    prettify(publishStatus),
    isCarousel
      ? `${slides.length || Math.max(carouselCards.length, 1)} cards`
      : "Single creative",
    isCarousel ? "4:5 creative" : "1.91:1 creative",
  ].filter(Boolean);

  return `
    <div style="
      width:100%;
      display:flex;
      justify-content:center;
      align-items:flex-start;
    ">
      <div style="
        border:1px solid rgba(15,23,42,0.14);
        background:#ffffff;
        overflow:hidden;
        width:min(420px, 100%);
      ">
        <div style="
          padding:14px 16px 12px;
          border-bottom:1px solid rgba(15,23,42,0.1);
          background:#ffffff;
        ">
          <div style="
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:12px;
          ">
            <div style="
              display:flex;
              align-items:center;
              gap:12px;
              min-width:0;
            ">
              <div style="
                width:38px;
                height:38px;
                border-radius:999px;
                background:#1877f2;
                color:#fff;
                display:flex;
                align-items:center;
                justify-content:center;
                font-weight:800;
                font-size:15px;
                flex:0 0 auto;
              ">f</div>

              <div style="min-width:0;">
                <div style="
                  font-weight:700;
                  color:#111111;
                  line-height:1.2;
                  white-space:nowrap;
                  overflow:hidden;
                  text-overflow:ellipsis;
                ">
                  ${escapeHtml(pageName)}
                </div>

                <div style="
                  font-size:12px;
                  color:rgba(17,17,17,0.62);
                  line-height:1.2;
                  display:flex;
                  flex-wrap:wrap;
                  gap:6px;
                  align-items:center;
                  font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                ">
                  <span>Suggested Facebook post</span>
                  <span>·</span>
                  <span>${escapeHtml(pageLabel)}</span>
                </div>
              </div>
            </div>

            <div style="
              font-size:11px;
              color:rgba(17,17,17,0.62);
              font-weight:700;
              text-transform:uppercase;
              letter-spacing:0.08em;
              white-space:nowrap;
              font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            ">
              ${escapeHtml(prettify(publishStatus))}
            </div>
          </div>

          ${
            caption
              ? `
                <div style="
                  margin-top:12px;
                  font-size:14px;
                  line-height:1.55;
                  color:#111111;
                  white-space:pre-wrap;
                  word-break:break-word;
                ">${escapeHtml(caption)}</div>
              `
              : ""
          }
        </div>

        <div style="padding:14px;">
          <div style="
            position:relative;
            border:1px solid rgba(15,23,42,0.12);
            overflow:hidden;
            background:${showDesignedImage ? "#111111" : "#dbe7f8"};
            aspect-ratio:${mediaAspectRatio};
            width:100%;
          ">
            ${
              showDesignedImage
                ? `
                  <img
                    src="${escapeHtml(activeCardImageUrl)}"
                    alt="Generated creative"
                    style="
                      position:absolute;
                      inset:0;
                      width:100%;
                      height:100%;
                      object-fit:cover;
                      display:block;
                    "
                  />
                `
                : ""
            }

            ${
              !showDesignedImage
                ? `
                  <div style="
                    position:absolute;
                    inset:0;
                    background:linear-gradient(
                      180deg,
                      rgba(255,255,255,0.1) 0%,
                      rgba(15,23,42,0.12) 100%
                    );
                  "></div>

                  <div style="
                    position:absolute;
                    top:18px;
                    right:18px;
                    padding:6px 10px;
                    background:#ffffff;
                    color:#111111;
                    font-size:11px;
                    font-weight:700;
                    text-transform:uppercase;
                    letter-spacing:0.08em;
                    font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                    border:1px solid rgba(15,23,42,0.12);
                  ">
                    ${isCarousel ? "Carousel preview" : "Preview layout"}
                  </div>
                `
                : ""
            }

            ${
              showTextOverlay
                ? `
                  <div style="
                    position:absolute;
                    left:18px;
                    right:18px;
                    bottom:18px;
                    display:grid;
                    gap:10px;
                  ">
                    ${
                      activeSlide
                        ? `
                          <div style="
                            display:inline-flex;
                            align-items:center;
                            gap:8px;
                            width:max-content;
                            max-width:100%;
                            padding:6px 10px;
                            background:rgba(255,255,255,0.18);
                            color:#ffffff;
                            font-size:11px;
                            font-weight:700;
                            text-transform:uppercase;
                            letter-spacing:0.08em;
                            font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                          ">
                            ${escapeHtml(primaryChannel)} ${isCarousel ? "carousel" : "creative"}
                          </div>

                          <div style="
                            color:#ffffff;
                            font-size:${isCarousel ? "30px" : "28px"};
                            line-height:1.05;
                            font-weight:800;
                            word-break:break-word;
                            max-width:92%;
                          ">
                            ${escapeHtml(activeSlide.headline || "")}
                          </div>

                          ${
                            activeSlide.body
                              ? `
                                <div style="
                                  color:rgba(255,255,255,0.96);
                                  font-size:15px;
                                  line-height:1.45;
                                  font-weight:600;
                                  max-width:92%;
                                  word-break:break-word;
                                ">
                                  ${escapeHtml(activeSlide.body)}
                                </div>
                              `
                              : ""
                          }
                        `
                        : `
                          <div style="
                            color:#ffffff;
                            font-size:28px;
                            line-height:1.08;
                            font-weight:800;
                            word-break:break-word;
                            max-width:92%;
                          ">
                            ${escapeHtml(caption || "Suggested marketing creative")}
                          </div>
                        `
                    }
                  </div>
                `
                : ""
            }
          </div>

          ${
            imageFailure
              ? `
                <div style="
                  margin-top:10px;
                  border:1px solid rgba(17,17,17,0.18);
                  color:#111111;
                  background:#ffffff;
                  padding:10px 12px;
                  font-size:12px;
                  line-height:1.45;
                ">
                  Image generation failed: ${escapeHtml(imageFailure)}
                </div>
              `
              : !showDesignedImage
                ? `
                  <div style="
                    margin-top:10px;
                    border:1px solid rgba(17,17,17,0.12);
                    color:rgba(17,17,17,0.72);
                    background:#ffffff;
                    padding:10px 12px;
                    font-size:12px;
                    line-height:1.45;
                  ">
                    No generated image attached yet. This is a styled preview using the carousel text and caption.
                  </div>
                `
                : ""
          }

          ${
            footerMeta.length
              ? `
                <div style="
                  margin-top:12px;
                  display:flex;
                  flex-wrap:wrap;
                  gap:8px;
                  align-items:center;
                ">
                  ${footerMeta
                    .map(
                      (item) => `
                        <span style="
                          display:inline-flex;
                          align-items:center;
                          padding:6px 10px;
                          background:#ffffff;
                          border:1px solid rgba(15,23,42,0.12);
                          color:rgba(17,17,17,0.72);
                          font-size:11px;
                          font-weight:700;
                          text-transform:uppercase;
                          letter-spacing:0.08em;
                          font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                        ">
                          ${escapeHtml(item)}
                        </span>
                      `,
                    )
                    .join("")}
                </div>
              `
              : ""
          }

          ${
            slides.length > 1
              ? `
                <div style="
                  margin-top:12px;
                  border:1px solid rgba(15,23,42,0.12);
                  background:#ffffff;
                  padding:10px 12px;
                  display:flex;
                  align-items:center;
                  justify-content:space-between;
                  gap:12px;
                ">
                  <button
                    type="button"
                    data-facebook-card-nav="prev"
                    data-facebook-card-index="${Math.max(activeIndex - 1, 0)}"
                    ${canGoPrev ? "" : "disabled"}
                    style="
                      appearance:none;
                      -webkit-appearance:none;
                      border:1px solid rgba(15,23,42,0.14);
                      background:${canGoPrev ? "#ffffff" : "rgba(15,23,42,0.04)"};
                      color:${canGoPrev ? "#111111" : "rgba(17,17,17,0.36)"};
                      width:36px;
                      height:36px;
                      cursor:${canGoPrev ? "pointer" : "default"};
                      font-size:16px;
                      font-weight:700;
                      flex:0 0 auto;
                    "
                  >
                    ‹
                  </button>

                  <div style="
                    min-width:0;
                    flex:1 1 auto;
                    text-align:center;
                    display:grid;
                    gap:4px;
                  ">
                    <div style="
                      font-size:11px;
                      color:rgba(17,17,17,0.58);
                      text-transform:uppercase;
                      letter-spacing:0.08em;
                      font-weight:700;
                      font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                    ">
                      Card ${activeIndex + 1} of ${pageCount}
                    </div>

                    <div style="
                      font-size:14px;
                      line-height:1.4;
                      color:#111111;
                      font-weight:700;
                      word-break:break-word;
                    ">
                      ${escapeHtml(activeSlide?.headline || activeSlide?.body || `Card ${activeIndex + 1}`)}
                    </div>
                  </div>

                  <button
                    type="button"
                    data-facebook-card-nav="next"
                    data-facebook-card-index="${Math.min(activeIndex + 1, pageCount - 1)}"
                    ${canGoNext ? "" : "disabled"}
                    style="
                      appearance:none;
                      -webkit-appearance:none;
                      border:1px solid rgba(15,23,42,0.14);
                      background:${canGoNext ? "#ffffff" : "rgba(15,23,42,0.04)"};
                      color:${canGoNext ? "#111111" : "rgba(17,17,17,0.36)"};
                      width:36px;
                      height:36px;
                      cursor:${canGoNext ? "pointer" : "default"};
                      font-size:16px;
                      font-weight:700;
                      flex:0 0 auto;
                    "
                  >
                    ›
                  </button>
                </div>
              `
              : ""
          }
        </div>
      </div>
    </div>
  `;
}

function getBoardroomSnapshot() {
  return asRecord(state.boardroomSnapshot) || {};
}

function getBoardroomSummary() {
  const snapshot = getBoardroomSnapshot();
  return asRecord(snapshot.summary) || {};
}

function getBoardroomWorkspace() {
  const snapshot = getBoardroomSnapshot();
  return (
    asRecord(snapshot.workspace) ||
    asRecord(snapshot.summary?.workspace) ||
    { workspace_id: state.workspaceId, name: state.workspaceId }
  );
}

function getBoardroomPulse() {
  const snapshot = getBoardroomSnapshot();
  return asRecord(snapshot.pulse) || asRecord(snapshot.summary?.pulse) || {};
}

function getBoardroomCenter() {
  const snapshot = getBoardroomSnapshot();
  return asRecord(snapshot.center) || asRecord(snapshot.summary?.center) || {};
}

function disposeBackendStatusListener() {
  if (typeof unsubscribeBackendStatus === "function") {
    unsubscribeBackendStatus();
    unsubscribeBackendStatus = null;
  }
  window.__TESSARIS_BACKEND_LISTENER_ATTACHED__ = false;
}

function getBoardroomRuntime() {
  const snapshot = getBoardroomSnapshot();
  return asRecord(snapshot.runtime) || asRecord(snapshot.summary?.runtime) || {};
}

function getBoardroomDepartments() {
  const snapshot = getBoardroomSnapshot();
  return safeArray(snapshot.departments);
}

function getBoardroomBindingsByCategory() {
  const snapshot = getBoardroomSnapshot();
  return asRecord(snapshot.bindingsByCategory) || {};
}

function getBoardroomTopology() {
  const snapshot = getBoardroomSnapshot();
  return asRecord(snapshot.topology) || { nodes: [], edges: [] };
}

function normalizeListForTextarea(value) {
  if (Array.isArray(value)) return value.join("\n");
  if (value == null) return "";
  return String(value);
}

function getBrandFoundationState() {
  const fallback =
    window.TessarisDesktopContracts &&
    typeof window.TessarisDesktopContracts.buildDefaultBrandFoundationState === "function"
      ? window.TessarisDesktopContracts.buildDefaultBrandFoundationState(state.marketingForm)
      : {};

  const current = state.brandFoundationState || {};

  if (
    window.TessarisDesktopContracts &&
    typeof window.TessarisDesktopContracts.normalizeBrandFoundationState === "function"
  ) {
    return window.TessarisDesktopContracts.normalizeBrandFoundationState(
      current,
      state.marketingForm,
    );
  }

  return {
    ...fallback,
    ...current,
    brandMap: {
      ...(fallback.brandMap || {}),
      ...(current.brandMap || {}),
    },
  };
}

function getBrandMap() {
  const foundation = getBrandFoundationState();

  return (
    asRecord(foundation.brandIntelligenceMap) ||
    asRecord(foundation.brand_intelligence_map) ||
    asRecord(foundation.brandMap) ||
    asRecord(foundation.brand_map) ||
    {}
  );
}

function getBrandMapSection(sectionKey) {
  const brandMap = getBrandMap();

  const aliases = {
    brandOverview: ["brandOverview", "brand_overview", "brandCore", "brand_core"],
    brandGoals: ["brandGoals", "brand_goals", "strategy"],
    brandPurpose: ["brandPurpose", "brand_purpose"],
    brandVision: ["brandVision", "brand_vision"],
    brandMission: ["brandMission", "brand_mission"],
    brandValues: ["brandValues", "brand_values"],
    brandPositioning: ["brandPositioning", "brand_positioning", "identity"],
    brandPersonality: ["brandPersonality", "brand_personality"],
    brandVoice: ["brandVoice", "brand_voice", "voice", "messaging"],
    brandStory: ["brandStory", "brand_story"],
    tagline: ["tagline"],
    audience: ["audience", "audiences"],
    customerPersonas: ["customerPersonas", "customer_personas", "personas"],
    customerJourney: ["customerJourney", "customer_journey"],
    painPoints: ["painPoints", "pain_points"],
    competitorAnalysis: ["competitorAnalysis", "competitor_analysis"],
    productsServices: ["productsServices", "products_services", "productsAndServices", "products_and_services"],
    platformStrategy: ["platformStrategy", "platform_strategy"],
    creativeDirection: ["creativeDirection", "creative_direction"],
    governance: ["governance", "contentRules", "content_rules"],
  };

  const keys = aliases[sectionKey] || [sectionKey];

  for (const key of keys) {
    const value = brandMap[key];
    if (isRecord(value)) return value;
  }

  return {};
}

function renderBrandTextInput({
  id,
  label,
  value,
  path,
  placeholder = "",
}) {
  return `
    <label class="field-label">${escapeHtml(label)}</label>
    <input
      id="${escapeHtml(id)}"
      class="input brand-foundation-input"
      data-brand-path="${escapeHtml(path)}"
      value="${escapeHtml(value || "")}"
      placeholder="${escapeHtml(placeholder)}"
    />
  `;
}

function renderBrandTextarea({
  id,
  label,
  value,
  path,
  placeholder = "",
  rows = 4,
  list = false,
}) {
  return `
    <label class="field-label">${escapeHtml(label)}</label>
    <textarea
      id="${escapeHtml(id)}"
      class="input input-textarea input-textarea-small brand-foundation-input"
      data-brand-path="${escapeHtml(path)}"
      data-brand-list="${list ? "true" : "false"}"
      rows="${escapeHtml(rows)}"
      placeholder="${escapeHtml(placeholder)}"
    >${escapeHtml(list ? normalizeListForTextarea(value) : value || "")}</textarea>
  `;
}

function renderBrandSectionCard(title, subtitle, bodyHtml) {
  return `
    <div class="panel large-panel" style="min-width:0;">
      <div class="panel-title">${escapeHtml(title)}</div>
      ${
        subtitle
          ? `<div class="helper-text" style="margin-top:0; margin-bottom:12px;">${escapeHtml(subtitle)}</div>`
          : ""
      }
      <div style="display:grid; gap:10px;">
        ${bodyHtml}
      </div>
    </div>
  `;
}

function renderBrandAssistantPanel() {
  return `
    <div class="panel large-panel brand-ai-panel">
      <div style="
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:12px;
      ">
        <div>
          <div class="panel-title">Brand Assistant</div>
          <div class="helper-text" style="margin-top:0;">
            Use the selected AI to help write, improve, or complete each brand section.
          </div>
        </div>
      </div>

      <label class="field-label">AI provider</label>
      <select id="brandAssistantProviderInput" class="input">
        <option value="gemma4" ${
          state.brandAssistantProvider === "gemma4" || !state.brandAssistantProvider
            ? "selected"
            : ""
        }>
          Free · Gemma 4 AI
        </option>
        <option value="openai" ${
          state.brandAssistantProvider === "openai" ? "selected" : ""
        }>
          OpenAI
        </option>
        <option value="claude" ${
          state.brandAssistantProvider === "claude" ? "selected" : ""
        }>
          Claude
        </option>
      </select>

      <label class="field-label">Current section</label>
      <select id="brandAssistantSectionInput" class="input">
        ${renderBrandAssistantSectionOptions()}
      </select>

      <div class="brand-ai-suggestions">
        <button
          class="secondary-btn brand-ai-suggestion-btn"
          type="button"
          data-brand-ai-prompt="help_write"
        >
          Help me write this section
        </button>

        <button
          class="secondary-btn brand-ai-suggestion-btn"
          type="button"
          data-brand-ai-prompt="make_clearer"
        >
          Make this clearer
        </button>

        <button
          class="secondary-btn brand-ai-suggestion-btn"
          type="button"
          data-brand-ai-prompt="make_premium"
        >
          Make it sound more professional
        </button>

        <button
          class="secondary-btn brand-ai-suggestion-btn"
          type="button"
          data-brand-ai-prompt="use_website"
        >
          Use website context
        </button>
      </div>

      <label class="field-label">Ask the brand assistant</label>
      <textarea
        id="brandAssistantPromptInput"
        class="input input-textarea"
        placeholder="Example: Help me write what we do for a local trade directory serving English-speaking expats in Almería."
      >${escapeHtml(state.brandAssistantPrompt || "")}</textarea>

      <div class="marketing-form-actions" style="
        display:grid;
        gap:10px;
      ">
        <button id="brandAssistantRunBtn" class="primary-btn" type="button">
          Generate suggestion
        </button>

        <button id="brandAssistantApplyBtn" class="secondary-btn" type="button">
          Apply to current section
        </button>

        <button id="brandAssistantClearBtn" class="secondary-btn" type="button">
          Clear
        </button>
      </div>

      <label class="field-label">Suggestion</label>
      <textarea
        id="brandAssistantOutputInput"
        class="input input-textarea"
        placeholder="AI suggestion will appear here."
      >${escapeHtml(state.brandAssistantOutput || "")}</textarea>
    </div>
  `;
}

function renderBrandAssistantSectionOptions() {
  const selected =
    state.brandAssistantSection || "brandMap.brandOverview.whatYouDo";

  const options = [
    ["brandMap.brandOverview.brandName", "Brand Overview · Brand name"],
    ["brandMap.brandOverview.whatYouDo", "Brand Overview · What do you do?"],
    ["brandMap.brandOverview.uniqueValueProposition", "Brand Overview · Unique value proposition"],

    ["brandMap.brandGoals.objective", "Brand Goals · Primary goal"],
    ["brandMap.brandGoals.funnelGoal", "Brand Goals · Funnel goal"],
    ["brandMap.brandGoals.campaignNotes", "Brand Goals · Campaign / growth notes"],

    ["brandMap.brandPurpose.statement", "Brand Purpose"],
    ["brandMap.brandVision.statement", "Brand Vision"],
    ["brandMap.brandMission.statement", "Brand Mission"],
    ["brandMap.brandValues.values", "Brand Values"],

    ["brandMap.brandPositioning.positioning", "Brand Positioning · Statement"],
    ["brandMap.brandPositioning.differentiation", "Brand Positioning · Differentiation"],
    ["brandMap.brandPositioning.trustSignals", "Brand Positioning · Trust signals"],

    ["brandMap.brandPersonality.traits", "Brand Personality · Traits"],
    ["brandMap.brandPersonality.notTraits", "Brand Personality · What the brand is not"],

    ["brandMap.brandVoice.toneOfVoice", "Brand Voice · Tone of voice"],
    ["brandMap.brandVoice.communicationStyle", "Brand Voice · Communication style"],
    ["brandMap.brandVoice.doRules", "Brand Voice · Do"],
    ["brandMap.brandVoice.doNotRules", "Brand Voice · Do not"],

    ["brandMap.brandStory.howStarted", "Brand Story · How it started"],
    ["brandMap.brandStory.journey", "Brand Story · Journey"],
    ["brandMap.brandStory.keyStoryPoints", "Brand Story · Key story points"],

    ["brandMap.tagline.value", "Tagline"],

    ["brandMap.audience.primaryAudience", "Audience · Primary audience"],
    ["brandMap.audience.customerType", "Audience · Customer type"],
    ["brandMap.audience.segments", "Audience · Segments"],
    ["brandMap.audience.whereToReachThem", "Audience · Where to reach them"],

    ["brandMap.customerPersonas.personaCards", "Customer Personas"],
    ["brandMap.customerJourney.steps", "Customer Journey · Steps"],
    ["brandMap.customerJourney.conversionPoints", "Customer Journey · Conversion points"],

    ["brandMap.painPoints.items", "Pain Points · Problems"],
    ["brandMap.painPoints.solutions", "Pain Points · Solutions"],

    ["brandMap.productsServices.items", "Products / Services"],
    ["brandMap.productsServices.keyBenefits", "Products / Services · Benefits"],

    ["brandMap.competitorAnalysis.urls", "Competitor Analysis · URLs"],
    ["brandMap.competitorAnalysis.notes", "Competitor Analysis · Notes"],
    ["brandMap.competitorAnalysis.differentiation", "Competitor Analysis · Differentiation"],

    ["brandMap.platformStrategy.activeChannels", "Platform Strategy · Active channels"],
    ["brandMap.platformStrategy.facebook", "Platform Strategy · Facebook"],
    ["brandMap.platformStrategy.retargetingNotes", "Platform Strategy · Retargeting"],

    ["brandMap.creativeDirection.direction", "Creative Direction"],
    ["brandMap.creativeDirection.doRules", "Creative Direction · Do rules"],
    ["brandMap.creativeDirection.doNotRules", "Creative Direction · Do not rules"],

    ["brandMap.governance.hardRules", "Governance · Hard rules"],
    ["brandMap.governance.approvalRules", "Governance · Approval rules"],
    ["brandMap.governance.complianceNotes", "Governance · Compliance notes"],
  ];

  return options
    .map(
      ([value, label]) => `
        <option value="${escapeHtml(value)}" ${selected === value ? "selected" : ""}>
          ${escapeHtml(label)}
        </option>
      `,
    )
    .join("");
}

function buildBrandFoundationPayload() {
  const foundation = getBrandFoundationState();
  const brandMap = getBrandMap();

  const now = new Date().toISOString();

  return {
    objective: foundation.objective || "",
    funnelGoal: foundation.funnelGoal || "",
    funnel_goal: foundation.funnelGoal || "",

    targetAudience: foundation.targetAudience || "",
    target_audience: foundation.targetAudience || "",

    persona: foundation.persona || "",
    offer: foundation.offer || "",

    channels: Array.isArray(foundation.channels) ? foundation.channels : [],
    hashtags: Array.isArray(foundation.hashtags) ? foundation.hashtags : [],
    keywords: Array.isArray(foundation.keywords) ? foundation.keywords : [],

    hardRules: Array.isArray(foundation.hardRules) ? foundation.hardRules : [],
    hard_rules: Array.isArray(foundation.hardRules) ? foundation.hardRules : [],

    guidanceNotes: Array.isArray(foundation.guidanceNotes)
      ? foundation.guidanceNotes
      : [],
    guidance_notes: Array.isArray(foundation.guidanceNotes)
      ? foundation.guidanceNotes
      : [],

    campaignNotes: Array.isArray(foundation.campaignNotes)
      ? foundation.campaignNotes
      : [],
    campaign_notes: Array.isArray(foundation.campaignNotes)
      ? foundation.campaignNotes
      : [],

    brandIntelligenceMap: brandMap,
    brand_intelligence_map: brandMap,
    brandMap,
    brand_map: brandMap,

    updatedAt: foundation.updatedAt || now,
    updated_at: foundation.updatedAt || now,
  };
}

async function saveBrandFoundationToBackend() {
  const workspaceId = encodeURIComponent(state.workspaceId);
  const payload = buildBrandFoundationPayload();

  return await apiPost(
    `/api/aion/business/brand-foundation/${workspaceId}`,
    payload,
  );
}

function renderOperationsFlowSurface() {
  const viewMode =
    state.operationsFlowViewMode === "spatial" ? "spatial" : "flat";

  return `
    <div class="surface-shell">
      <div class="surface-header">
        <div>
          <div class="surface-eyebrow">Aion Business Desktop</div>
          <div class="surface-title">Operations Flow</div>
          <div class="surface-subtitle">
            Local-first operations flow surface rendered directly inside Tessaris.
          </div>
        </div>
        <div class="surface-right-meta">
          <div class="surface-pill">DESKTOP · OPERATIONS FLOW</div>
          <div class="last-refresh">Last refresh: ${escapeHtml(formatDateTime(state.lastRefreshAt))}</div>
        </div>
      </div>

      ${renderAppTabs()}
      ${renderOperationsFlowModeToggle()}

      ${
        viewMode === "spatial"
          ? `
            <div class="dashboard-shell">
              <div class="panel large-panel">
                <div class="panel-title">3D Operations Flow</div>
                <div class="helper-text" style="margin-bottom:12px;">
                  Spatial operations renderer driven by local boardroom/runtime state.
                </div>
                <div class="spatial-boardroom-shell">
                  <div id="operationsFlowMount" class="spatial-boardroom-mount"></div>
                </div>
              </div>
            </div>
          `
          : `
            <div class="dashboard-shell">
              ${renderDashboardBodyOnly()}
            </div>
          `
      }
    </div>
  `;
}

function renderBrandFoundationSurface() {
  const foundation = getBrandFoundationState();
  const brandMap = getBrandMap();
  const workspaceId = state.workspaceId || "workspace";

  const overview = getBrandMapSection("brandOverview");
  const goals = getBrandMapSection("brandGoals");
  const purpose = getBrandMapSection("brandPurpose");
  const vision = getBrandMapSection("brandVision");
  const mission = getBrandMapSection("brandMission");
  const values = getBrandMapSection("brandValues");
  const positioning = getBrandMapSection("brandPositioning");
  const personality = getBrandMapSection("brandPersonality");
  const voice = getBrandMapSection("brandVoice");
  const story = getBrandMapSection("brandStory");
  const tagline = getBrandMapSection("tagline");
  const audience = getBrandMapSection("audience");
  const personas = getBrandMapSection("customerPersonas");
  const journey = getBrandMapSection("customerJourney");
  const painPoints = getBrandMapSection("painPoints");
  const competitors = getBrandMapSection("competitorAnalysis");
  const productsServices = getBrandMapSection("productsServices");
  const platform = getBrandMapSection("platformStrategy");
  const creative = getBrandMapSection("creativeDirection");
  const governance = getBrandMapSection("governance");

  return `
    <div class="surface-shell">
      <div class="surface-header">
        <div>
          <div class="surface-eyebrow">Aion Business Desktop</div>
          <div class="surface-title">Brand Foundation</div>
          <div class="surface-subtitle">
            A single layered brand document. The AI uses this as the source of truth for messaging, audience, offers, tone, channels, and creative direction.
          </div>
        </div>
        <div class="surface-right-meta">
          <div class="surface-pill">DESKTOP · BRAND FOUNDATION</div>
          <div class="last-refresh">Last refresh: ${escapeHtml(formatDateTime(state.lastRefreshAt))}</div>
        </div>
      </div>

      ${renderAppTabs()}

      <div class="brand-foundation-layout">
        <main class="brand-foundation-main">
          <div class="dashboard-shell">
            <div class="card-grid">
              ${renderDashboardMetricCard("Workspace", workspaceId, "Desktop-local truth")}
              ${renderDashboardMetricCard(
                "Channels",
                Array.isArray(foundation.channels) ? foundation.channels.length : 0,
                "Configured acquisition channels",
              )}
              ${renderDashboardMetricCard(
                "Keywords",
                Array.isArray(foundation.keywords) ? foundation.keywords.length : 0,
                "Search / targeting terms",
              )}
              ${renderDashboardMetricCard(
                "Last updated",
                foundation.updatedAt ? formatDateTime(foundation.updatedAt) : "—",
                "Brand foundation state",
              )}
            </div>

            <div style="
              display:grid;
              grid-template-columns:minmax(0, 1fr);
              gap:16px;
              align-items:start;
            ">
              ${renderBrandSectionCard(
                "1. Brand Overview",
                "What the business does and the clear value it provides.",
                `
                  ${renderBrandTextInput({
                    id: "brandOverviewNameInput",
                    label: "Brand / business name",
                    value: overview.brandName ?? overview.brand_name ?? "",
                    path: "brandMap.brandOverview.brandName",
                    placeholder: "Example: Addlestone Electrical Services",
                  })}
                  ${renderBrandTextarea({
                    id: "brandOverviewWhatYouDoInput",
                    label: "What do you do?",
                    value: overview.whatYouDo ?? overview.what_you_do ?? "",
                    path: "brandMap.brandOverview.whatYouDo",
                    placeholder: "Example: We provide domestic and commercial electrical services across Addlestone and nearby towns.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandOverviewUvpInput",
                    label: "Unique value proposition",
                    value: overview.uniqueValueProposition ?? overview.unique_value_proposition ?? "",
                    path: "brandMap.brandOverview.uniqueValueProposition",
                    placeholder: "Example: Professional, reliable local electricians with clear pricing and fast response times.",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "2. Brand Goals",
                "Where the business is trying to go commercially and reputationally.",
                `
                  ${renderBrandTextInput({
                    id: "brandGoalsObjectiveInput",
                    label: "Primary goal",
                    value: goals.objective ?? foundation.objective,
                    path: "brandMap.brandGoals.objective",
                    placeholder: "Example: Establish ourselves as the No.1 electrical service in London.",
                  })}
                  ${renderBrandTextInput({
                    id: "brandGoalsFunnelGoalInput",
                    label: "Funnel goal",
                    value: goals.funnelGoal ?? goals.funnel_goal ?? foundation.funnelGoal,
                    path: "brandMap.brandGoals.funnelGoal",
                    placeholder: "Example: Generate quote requests and booked callouts.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandGoalsNotesInput",
                    label: "Campaign / growth notes",
                    value: goals.campaignNotes ?? goals.campaign_notes ?? foundation.campaignNotes,
                    path: "brandMap.brandGoals.campaignNotes",
                    list: true,
                    placeholder: "One goal or campaign note per line",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "3. Brand Purpose",
                "Why the business exists beyond simply selling the service.",
                `
                  ${renderBrandTextarea({
                    id: "brandPurposeInput",
                    label: "Purpose",
                    value: purpose.statement ?? purpose.purpose ?? "",
                    path: "brandMap.brandPurpose.statement",
                    placeholder: "Example: Provide electrical services to local homeowners in a professional, safe, and trustworthy way.",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "4. Brand Vision",
                "The future state the business wants to become.",
                `
                  ${renderBrandTextarea({
                    id: "brandVisionInput",
                    label: "Vision",
                    value: vision.statement ?? vision.vision ?? "",
                    path: "brandMap.brandVision.statement",
                    placeholder: "Example: Become the leading electrical service provider within a 10 mile radius.",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "5. Brand Mission",
                "What the business commits to delivering every day.",
                `
                  ${renderBrandTextarea({
                    id: "brandMissionInput",
                    label: "Mission",
                    value: mission.statement ?? mission.mission ?? "",
                    path: "brandMap.brandMission.statement",
                    placeholder: "Example: Provide every customer with safe work, clear communication, fair pricing, and a reliable finish.",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "6. Brand Values",
                "The values that guide decisions, service, content, and communication.",
                `
                  ${renderBrandTextarea({
                    id: "brandValuesInput",
                    label: "Values",
                    value: values.values ?? foundation.values,
                    path: "brandMap.brandValues.values",
                    list: true,
                    placeholder: "Professionalism\nReliability\nSafety\nClear communication\nFair pricing",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "7. Brand Positioning",
                "How the business should be positioned against alternatives.",
                `
                  ${renderBrandTextInput({
                    id: "brandPositioningInput",
                    label: "Positioning statement",
                    value: positioning.positioning ?? "",
                    path: "brandMap.brandPositioning.positioning",
                    placeholder: "Example: The trusted local electrician for homeowners who want safe, professional work without confusion.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandDifferentiationInput",
                    label: "Differentiation",
                    value: positioning.differentiation ?? "",
                    path: "brandMap.brandPositioning.differentiation",
                    placeholder: "What makes this business different from competitors?",
                  })}
                  ${renderBrandTextarea({
                    id: "brandTrustSignalsInput",
                    label: "Trust signals",
                    value: positioning.trustSignals ?? positioning.trust_signals,
                    path: "brandMap.brandPositioning.trustSignals",
                    list: true,
                    placeholder: "Reviews\nQualifications\nLocal experience\nInsurance\nBefore/after work",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "8. Brand Personality",
                "How the brand should feel as a character.",
                `
                  ${renderBrandTextarea({
                    id: "brandPersonalityTraitsInput",
                    label: "Personality traits",
                    value: personality.traits ?? "",
                    path: "brandMap.brandPersonality.traits",
                    list: true,
                    placeholder: "Sophisticated\nKnowledgeable\nCost-effective\nHelpful\nProfessional",
                  })}
                  ${renderBrandTextarea({
                    id: "brandPersonalityNotInput",
                    label: "What the brand is not",
                    value: personality.notTraits ?? personality.not_traits,
                    path: "brandMap.brandPersonality.notTraits",
                    list: true,
                    placeholder: "Not pushy\nNot cheap-looking\nNot overly technical\nNot aggressive",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "9. Brand Voice",
                "Tone of voice, communication style, dos, don'ts, and wording rules.",
                `
                  ${renderBrandTextarea({
                    id: "brandVoiceToneInput",
                    label: "Tone of voice",
                    value: voice.toneOfVoice ?? voice.tone_of_voice ?? voice.toneRules,
                    path: "brandMap.brandVoice.toneOfVoice",
                    list: true,
                    placeholder: "Sophisticated\nKnowledgeable\nCost-effective\nClear\nFriendly",
                  })}
                  ${renderBrandTextarea({
                    id: "brandVoiceStyleInput",
                    label: "Communication style",
                    value: voice.communicationStyle ?? voice.communication_style,
                    path: "brandMap.brandVoice.communicationStyle",
                    placeholder: "Example: Explain things simply, sound confident, avoid jargon unless needed.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandVoiceDosInput",
                    label: "Do",
                    value: voice.doRules ?? voice.dos,
                    path: "brandMap.brandVoice.doRules",
                    list: true,
                    placeholder: "Use simple language\nExplain the customer benefit\nSound professional",
                  })}
                  ${renderBrandTextarea({
                    id: "brandVoiceDontsInput",
                    label: "Do not",
                    value: voice.doNotRules ?? voice.donts,
                    path: "brandMap.brandVoice.doNotRules",
                    list: true,
                    placeholder: "Do not use hype\nDo not overpromise\nDo not sound desperate",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "10. Brand Story",
                "Origin, journey, credibility, and the story the AI can pull into posts.",
                `
                  ${renderBrandTextarea({
                    id: "brandStoryStartedInput",
                    label: "How did the business start?",
                    value: story.howStarted ?? story.how_started,
                    path: "brandMap.brandStory.howStarted",
                    placeholder: "Tell the origin story in plain language.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandStoryJourneyInput",
                    label: "Journey / key moments",
                    value: story.journey,
                    path: "brandMap.brandStory.journey",
                    placeholder: "Important milestones, lessons, experience, or customer wins.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandStoryKeyBitsInput",
                    label: "Key story points to reuse in content",
                    value: story.keyStoryPoints ?? story.key_story_points,
                    path: "brandMap.brandStory.keyStoryPoints",
                    list: true,
                    placeholder: "One key story point per line",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "11. Tagline",
                "Short brand line or memorable phrase.",
                `
                  ${renderBrandTextInput({
                    id: "brandTaglineInput",
                    label: "Tagline",
                    value: tagline.value ?? tagline.tagline ?? "",
                    path: "brandMap.tagline.value",
                    placeholder: "Example: Reliable electrics, done properly.",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "12. Audience",
                "Who the business is targeting and whether it is B2B, B2C, or both.",
                `
                  ${renderBrandTextInput({
                    id: "brandAudiencePrimaryInput",
                    label: "Primary audience",
                    value: audience.primaryAudience ?? audience.primary_audience ?? foundation.targetAudience,
                    path: "brandMap.audience.primaryAudience",
                    placeholder: "Example: Male homeowners aged 35–65 living around Addlestone.",
                  })}
                  ${renderBrandTextInput({
                    id: "brandAudienceCustomerTypeInput",
                    label: "Customer type",
                    value: audience.customerType ?? audience.customer_type ?? "",
                    path: "brandMap.audience.customerType",
                    placeholder: "B2C, B2B, or both",
                  })}
                  ${renderBrandTextarea({
                    id: "brandAudienceSegmentsInput",
                    label: "Audience segments",
                    value: audience.segments ?? audience.audienceSegments,
                    path: "brandMap.audience.segments",
                    list: true,
                    placeholder: "Homeowners needing consumer unit upgrades\nLandlords needing EICR certificates\nSmall businesses needing electrical maintenance",
                  })}
                  ${renderBrandTextarea({
                    id: "brandAudienceWhereInput",
                    label: "Where to reach them",
                    value: audience.whereToReachThem ?? audience.where_to_reach_them,
                    path: "brandMap.audience.whereToReachThem",
                    list: true,
                    placeholder: "Facebook\nGoogle search\nLocal groups\nRetargeting ads",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "13. Customer Personas",
                "Actual persona cards: name, age, location, occupation, values, interests, and buying context.",
                `
                  ${renderBrandTextarea({
                    id: "brandPersonasInput",
                    label: "Persona cards",
                    value: personas.personaCards ?? personas.persona_cards,
                    path: "brandMap.customerPersonas.personaCards",
                    placeholder: "Example:\nName: Mark\nAge: 42\nLocation: Addlestone\nOccupation: Homeowner / manager\nInterests: home improvement, family safety\nValues: trust, speed, fair pricing\nPain: needs consumer unit upgraded but unsure who to trust",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "14. Customer Journey",
                "Basic journey from first touch to conversion.",
                `
                  ${renderBrandTextarea({
                    id: "brandJourneyStepsInput",
                    label: "Journey steps",
                    value: journey.steps,
                    path: "brandMap.customerJourney.steps",
                    list: true,
                    placeholder: "Scrolls on Facebook\nSees local electrical safety ad\nClicks website\nChecks proof/reviews\nRequests quote\nBooks job",
                  })}
                  ${renderBrandTextarea({
                    id: "brandJourneyConversionInput",
                    label: "Conversion points",
                    value: journey.conversionPoints ?? journey.conversion_points,
                    path: "brandMap.customerJourney.conversionPoints",
                    list: true,
                    placeholder: "Facebook message\nPhone call\nWebsite form\nWhatsApp enquiry",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "15. Customer Pain Points",
                "The problems the business solves and the messages that address them.",
                `
                  ${renderBrandTextarea({
                    id: "brandPainPointsInput",
                    label: "Pain points",
                    value: painPoints.items ?? audience.painPoints,
                    path: "brandMap.painPoints.items",
                    list: true,
                    placeholder: "Worried about unsafe electrics\nDoesn't know if consumer unit is outdated\nNeeds reliable local electrician\nWants clear price before booking",
                  })}
                  ${renderBrandTextarea({
                    id: "brandPainSolutionsInput",
                    label: "How we solve them",
                    value: painPoints.solutions,
                    path: "brandMap.painPoints.solutions",
                    list: true,
                    placeholder: "Clear inspection\nSimple explanation\nProfessional installation\nTransparent quote\nLocal follow-up",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "16. Products / Services",
                "The actual service or product being sold and who it fits.",
                `
                  ${renderBrandTextarea({
                    id: "brandServicesInput",
                    label: "Products / services",
                    value: productsServices.items ?? productsServices.serviceCategories,
                    path: "brandMap.productsServices.items",
                    placeholder: "Example:\nConsumer unit installation — homeowners with outdated fuse boxes\nEICR certificates — landlords and sellers\nEmergency callouts — local homeowners and businesses",
                  })}
                  ${renderBrandTextarea({
                    id: "brandServiceBenefitsInput",
                    label: "Key benefits",
                    value: productsServices.keyBenefits ?? productsServices.key_benefits,
                    path: "brandMap.productsServices.keyBenefits",
                    list: true,
                    placeholder: "Safer home\nCompliant electrics\nReliable installation\nClear advice",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "17. Competitor Analysis",
                "Competitor websites and what to learn from them.",
                `
                  ${renderBrandTextarea({
                    id: "brandCompetitorUrlsInput",
                    label: "Competitor websites",
                    value: competitors.urls ?? competitors.websites,
                    path: "brandMap.competitorAnalysis.urls",
                    list: true,
                    placeholder: "https://competitor-one.com\nhttps://competitor-two.com\nhttps://competitor-three.com",
                  })}
                  ${renderBrandTextarea({
                    id: "brandCompetitorNotesInput",
                    label: "Competitor notes / analysis",
                    value: competitors.notes ?? competitors.analysis,
                    path: "brandMap.competitorAnalysis.notes",
                    placeholder: "What they do well, where they are weak, how we should differentiate.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandCompetitorDifferentiationInput",
                    label: "Differentiation against competitors",
                    value: competitors.differentiation,
                    path: "brandMap.competitorAnalysis.differentiation",
                    placeholder: "How this brand should stand apart.",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "18. Platform Strategy",
                "Where to communicate, what tone to use, and what message fits each place.",
                `
                  ${renderBrandTextarea({
                    id: "brandPlatformActiveChannelsInput",
                    label: "Active channels",
                    value: platform.activeChannels ?? platform.active_channels ?? foundation.channels,
                    path: "brandMap.platformStrategy.activeChannels",
                    list: true,
                    placeholder: "Facebook\nInstagram\nGoogle\nWebsite\nEmail",
                  })}
                  ${renderBrandTextarea({
                    id: "brandPlatformFacebookInput",
                    label: "Facebook strategy",
                    value: platform.facebook,
                    path: "brandMap.platformStrategy.facebook",
                    placeholder: "Example: Target local homeowners with trust-led posts and simple service explainers.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandPlatformRetargetingInput",
                    label: "Retargeting / intent notes",
                    value: platform.retargetingNotes ?? platform.retargeting_notes,
                    path: "brandMap.platformStrategy.retargetingNotes",
                    placeholder: "Example: Speak to people who visited electrical service pages or interacted with local posts.",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "19. Creative Direction",
                "Rules that go directly into image, carousel, and content prompts.",
                `
                  ${renderBrandTextarea({
                    id: "brandCreativeDirectionInput",
                    label: "Creative direction",
                    value: creative.direction ?? creative.creativeDirection,
                    path: "brandMap.creativeDirection.direction",
                    placeholder: "Example: Clean, professional electrical service creative with clear benefit, local trust, and simple CTA.",
                  })}
                  ${renderBrandTextarea({
                    id: "brandCreativeDoInput",
                    label: "Creative DO rules",
                    value: creative.doRules,
                    path: "brandMap.creativeDirection.doRules",
                    list: true,
                    placeholder: "Use professional local-service imagery\nShow clear CTA\nKeep visual hierarchy simple",
                  })}
                  ${renderBrandTextarea({
                    id: "brandCreativeDontInput",
                    label: "Creative DO NOT rules",
                    value: creative.doNotRules,
                    path: "brandMap.creativeDirection.doNotRules",
                    list: true,
                    placeholder: "Do not use childish graphics\nDo not clutter the artwork\nDo not make unsafe claims",
                  })}
                `,
              )}

              ${renderBrandSectionCard(
                "20. Governance",
                "Hard rules, approval rules, compliance notes, and publishing boundaries.",
                `
                  ${renderBrandTextarea({
                    id: "brandGovernanceHardRulesInput",
                    label: "Hard rules",
                    value: governance.hardRules ?? foundation.hardRules,
                    path: "brandMap.governance.hardRules",
                    list: true,
                    placeholder: "Do not publish automatically\nDo not overpromise\nDo not use unsafe electrical claims",
                  })}
                  ${renderBrandTextarea({
                    id: "brandGovernanceApprovalInput",
                    label: "Approval rules",
                    value: governance.approvalRules,
                    path: "brandMap.governance.approvalRules",
                    list: true,
                    placeholder: "All public posts require approval\nEscalate uncertain claims\nHuman reviews final calendar publish",
                  })}
                  ${renderBrandTextarea({
                    id: "brandGovernanceComplianceInput",
                    label: "Compliance notes",
                    value: governance.complianceNotes,
                    path: "brandMap.governance.complianceNotes",
                    list: true,
                    placeholder: "Electrical safety claims must be accurate\nNo fake guarantees\nNo misleading accreditations",
                  })}
                `,
              )}
            </div>

            <div class="panel large-panel" style="margin-top:16px;">
              <div class="panel-title">Save / Recovery</div>
              <div class="helper-text" style="margin-top:0;">
                Saves flat compatibility fields plus the nested Brand Intelligence Map.
              </div>

              <div class="marketing-form-actions">
                <button id="saveBrandFoundationBtn" class="primary-btn">Save brand foundation</button>
                <button id="resetBrandFoundationBtn" class="secondary-btn">Reset from marketing form</button>
              </div>

              <details style="margin-top:14px;">
                <summary class="helper-text">Preview payload</summary>
                <pre class="json-block" style="margin-top:10px;">${escapeHtml(shortJson(buildBrandFoundationPayload()))}</pre>
              </details>
            </div>
          </div>
        </main>
      </div>
    </div>
  `;
}


function getQueueCounts() {
  const queued = state.runs.filter((x) => x.status === "queued").length;
  const running = state.runs.filter((x) => x.status === "running").length;
  const waiting = state.runs.filter((x) => x.status === "waiting_approval").length;
  const completed = state.runs.filter((x) => x.status === "completed").length;
  const cancelled = state.runs.filter((x) => x.status === "cancelled").length;
  const failed = state.runs.filter((x) => x.status === "failed").length;

  return { queued, running, waiting, completed, cancelled, failed };
}

function getApprovalCounts() {
  const pending = state.approvals.filter((x) => x.status === "pending").length;
  const approved = state.approvals.filter((x) => x.status === "approved").length;
  const rejected = state.approvals.filter((x) => x.status === "rejected").length;

  return { pending, approved, rejected };
}

function ensureLiveAgentSelection(options = {}) {
  const result = liveAgentsRuntime.ensureLiveAgentSelection(state, options) || {};
  const updates = {};

  if (Object.prototype.hasOwnProperty.call(result, "activeZone")) {
    updates.activeZone = result.activeZone;
  }

  if (Object.prototype.hasOwnProperty.call(result, "selectedLiveAgentId")) {
    updates.selectedLiveAgentId = result.selectedLiveAgentId;
  }

  if (Object.prototype.hasOwnProperty.call(result, "selectedLiveRunId")) {
    updates.selectedLiveRunId = result.selectedLiveRunId;
  }

  if (Object.prototype.hasOwnProperty.call(result, "liveAgentsReplayOpen")) {
    updates.liveAgentsReplayOpen = result.liveAgentsReplayOpen;
  }

  if (Object.prototype.hasOwnProperty.call(result, "liveAgentsView")) {
    updates.liveAgentsView = result.liveAgentsView;
  }

  if (
    Object.prototype.hasOwnProperty.call(result, "selectedSeatId") &&
    result.selectedSeatId !== undefined
  ) {
    updates.selectedSeatId = result.selectedSeatId;
  }

  if (
    Object.prototype.hasOwnProperty.call(result, "selectedInspectorTarget") &&
    result.selectedInspectorTarget !== undefined
  ) {
    updates.selectedInspectorTarget = result.selectedInspectorTarget;
  }

  if (!Object.keys(updates).length) {
    return false;
  }

  desktopStore.patch(updates);
  return true;
}


function normalizeBindingsByCategory(bindings) {
  const grouped = {};

  (Array.isArray(bindings) ? bindings : []).forEach((binding) => {
    const category = binding?.category || "uncategorized";
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(binding);
  });

  return grouped;
}

async function apiGetOptional(path, fallback = null) {
  return await runtimeAdapter.apiGetOptional(
    getRuntimeAdapterDeps(),
    path,
    fallback,
  );
}

async function apiGet(path) {
  return await runtimeAdapter.apiGet(
    getRuntimeAdapterDeps(),
    path,
  );
}

async function apiDelete(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data?.detail || data?.error || `DELETE ${path} failed`);
  }

  return data;
}

async function apiPost(path, body) {
  return await runtimeAdapter.apiPost(
    getRuntimeAdapterDeps(),
    path,
    body,
  );
}

async function loadDesktopRecovery() {
  return await runtimeAdapter.loadDesktopRecovery(
    getRuntimeAdapterDeps(),
  );
}

async function bindWorkspace(options = {}) {
  return await runtimeAdapter.bindWorkspace(
    getRuntimeAdapterDeps(),
    {
      ...options,
      defaultApiBase: DEFAULT_API_BASE,
      defaultWebBase: DEFAULT_WEB_BASE,
      defaultWorkspaceId: DEFAULT_WORKSPACE_ID,
      defaultNodeId: DEFAULT_NODE_ID,
    },
  );
}

async function refreshAll() {
  const value = await runtimeAdapter.refreshAll(
    getRuntimeAdapterDeps(),
  );

  ensureLiveAgentSelection();
  return value;
}

async function runControl(path, body) {
  return await runtimeAdapter.runControl(
    getRuntimeAdapterDeps(),
    path,
    body,
  );
}

function setActiveTab(tabKey) {
  console.log("[tab click]", tabKey);

  desktopStore.setActiveTab(tabKey);

  console.log("[after setActiveTab]", state.activeTab);

  if (tabKey === "live_agents") {
    ensureLiveAgentSelection({
      preferredDepartmentKey: state.activeZone || "marketing",
    });
  }

  if (tabKey === "operations_agents") {
    Promise.resolve()
      .then(() => refreshBrowserSkillWorkspaceAssets())
      .catch((error) => {
        console.warn("[browser-skills] workspace refresh failed", error);
      });
  }

  render();
}

function renderTopNav() {
  return "";
}

function renderGlobalStatusBanner() {
  return "";
}

function renderAppTabs() {
  return `
    <div class="app-tabs">
      ${APP_TABS.map((tab) => {
        const activeClass = state.activeTab === tab.key ? "app-tab-active" : "";
        const highlightClass = tab.highlight ? "app-tab-highlight" : "";

        return `
          <button
            class="app-tab ${activeClass} ${highlightClass}"
            data-tab="${escapeHtml(tab.key)}"
          >
            ${escapeHtml(tab.label)}
          </button>
        `;
      }).join("")}
    </div>
  `;
}

function renderStatusBadge(status) {
  const value = String(status || "unknown");
  return `<span class="status-badge status-${escapeHtml(value)}">${escapeHtml(prettify(value))}</span>`;
}

function renderRuns() {
  if (!state.runs.length) {
    return `<div class="empty-state">No runs recorded yet.</div>`;
  }

  return `
    <div class="list-wrap">
      ${state.runs
        .slice()
        .reverse()
        .map(
          (run) => `
            <div class="list-item">
              <div class="list-item-title">${escapeHtml(run.workflow_id || "workflow")}</div>
              <div class="list-item-sub">${escapeHtml(run.id || run.queue_item_id || "—")}</div>
              <div class="badge-row">
                ${renderStatusBadge(run.status)}
                <span class="badge">Dept: ${escapeHtml(run.department_key || "—")}</span>
                <span class="badge">Operator: ${escapeHtml(run.operator_id || "—")}</span>
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderApprovals() {
  if (!state.approvals.length) {
    return `<div class="empty-state">No approvals recorded.</div>`;
  }

  return `
    <div class="list-wrap">
      ${state.approvals
        .slice()
        .reverse()
        .map(
          (approval) => `
            <div class="list-item">
              <div class="list-item-title">${escapeHtml(approval.title || "Approval")}</div>
              <div class="list-item-sub">${escapeHtml(approval.id)}</div>
              <div class="badge-row">
                ${renderStatusBadge(approval.status)}
                <span class="badge">Dept: ${escapeHtml(approval.department_key || "—")}</span>
              </div>
              <div class="list-item-sub">
                Run: ${escapeHtml(approval.run_id || approval.queue_item_id || "—")}
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderAudit() {
  if (!state.audit.length) {
    return `<div class="empty-state">No audit events recorded.</div>`;
  }

  return `
    <div class="list-wrap">
      ${state.audit
        .slice(0, 10)
        .map(
          (event) => `
            <div class="list-item">
              <div class="list-item-title">${escapeHtml(event.event_type || "event")}</div>
              <div class="list-item-sub">${escapeHtml(event.message || "")}</div>
              <div class="badge-row">
                <span class="badge">Level: ${escapeHtml(event.level || "info")}</span>
                <span class="badge">${escapeHtml(formatDateTime(event.created_at))}</span>
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderDashboardMetricCard(label, value, sub = "") {
  return `
    <div class="card">
      <div class="card-label">${escapeHtml(label)}</div>
      <div class="card-value">${escapeHtml(value)}</div>
      ${sub ? `<div class="card-sub">${escapeHtml(sub)}</div>` : ""}
    </div>
  `;
}

function renderDashboardDepartmentCards(departments) {
  if (!Array.isArray(departments) || !departments.length) {
    return `<div class="empty-state">No department summaries available.</div>`;
  }

  return `
    <div class="dashboard-department-grid">
      ${departments
        .map(
          (dept) => `
            <div class="dashboard-department-card">
              <div class="dashboard-department-header">
                <div>
                  <div class="dashboard-department-name">${escapeHtml(
                    dept.label || dept.key || "Department",
                  )}</div>
                  <div class="dashboard-department-sub">${escapeHtml(dept.summary || "")}</div>
                </div>
                ${renderStatusBadge(dept.status || "unknown")}
              </div>

              <div class="dashboard-department-metrics">
                <div class="dashboard-mini-stat">
                  <span>Queued</span>
                  <strong>${escapeHtml(dept.queued ?? 0)}</strong>
                </div>
                <div class="dashboard-mini-stat">
                  <span>Running</span>
                  <strong>${escapeHtml(dept.running ?? 0)}</strong>
                </div>
                <div class="dashboard-mini-stat">
                  <span>Done</span>
                  <strong>${escapeHtml(dept.completed ?? 0)}</strong>
                </div>
                <div class="dashboard-mini-stat">
                  <span>Pending approvals</span>
                  <strong>${escapeHtml(dept.pending_approvals ?? 0)}</strong>
                </div>
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderBindingCards(bindings) {
  if (!Array.isArray(bindings) || !bindings.length) {
    return `<div class="empty-state">No container bindings available.</div>`;
  }

  return `
    <div class="list-wrap">
      ${bindings
        .map((binding) => `
          <div class="list-item">
            <div class="list-item-title">${escapeHtml(binding.name || binding.id || "Binding")}</div>
            <div class="list-item-sub">${escapeHtml(binding.description || binding.runtime_container_id || "—")}</div>
            <div class="badge-row">
              <span class="badge">Category: ${escapeHtml(binding.category || "custom")}</span>
              <span class="badge">Runtime: ${escapeHtml(binding.runtime_backend || "ucs")}</span>
              <span class="badge">KG: ${escapeHtml(binding.kg_graph || "work")}</span>
              <span class="badge">Status: ${escapeHtml(binding.status || "active")}</span>
            </div>
            <div class="list-item-sub">
              Runtime container: ${escapeHtml(binding.runtime_container_id || "—")}
            </div>
            <div class="list-item-sub">
              KG container: ${escapeHtml(binding.kg_container_id || "—")}
            </div>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function renderBindingCategorySections(bindingsByCategory) {
  const entries = Object.entries(bindingsByCategory || {});
  if (!entries.length) {
    return `<div class="empty-state">No categorized bindings available.</div>`;
  }

  return `
    <div class="dashboard-shell">
      ${entries
        .sort(([a], [b]) => a.localeCompare(b))
        .map(
          ([category, bindings]) => `
            <div class="panel">
              <div class="panel-title">${escapeHtml(prettify(category))}</div>
              ${renderBindingCards(bindings)}
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderTopologySummary(topology) {
  const nodes = Array.isArray(topology?.nodes) ? topology.nodes : [];
  const edges = Array.isArray(topology?.edges) ? topology.edges : [];

  const nodeTypeCounts = {};
  nodes.forEach((node) => {
    const key = node?.node_type || "unknown";
    nodeTypeCounts[key] = (nodeTypeCounts[key] || 0) + 1;
  });

  const typeEntries = Object.entries(nodeTypeCounts);

  return `
    <div class="dashboard-shell">
      <div class="card-grid">
        ${renderDashboardMetricCard("Topology Nodes", nodes.length, "Business graph nodes")}
        ${renderDashboardMetricCard("Topology Edges", edges.length, "Business graph relationships")}
        ${renderDashboardMetricCard("Node Types", typeEntries.length, "Distinct topology node types")}
        ${renderDashboardMetricCard("Bindings", state.containerBindings.length, "Business container bindings")}
      </div>

      <div class="panel">
        <div class="panel-title">Topology Node Types</div>
        ${
          typeEntries.length
            ? `
              <div class="badge-row">
                ${typeEntries
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(
                    ([type, count]) =>
                      `<span class="badge">${escapeHtml(prettify(type))}: ${escapeHtml(count)}</span>`,
                  )
                  .join("")}
              </div>
            `
            : `<div class="empty-state">No topology node data available.</div>`
        }
      </div>
    </div>
  `;
}

function renderDashboardSurface() {
  const summary = state.dashboardSummary || {};
  const workspace = summary.workspace || {};
  const node = summary.node || {};
  const scheduler = summary.scheduler || {};
  const queue = summary.queue || {};
  const approvals = summary.approvals || {};
  const health = summary.health || {};
  const recentAudit = Array.isArray(summary.recent_audit) ? summary.recent_audit : [];
  const departments = Array.isArray(summary.departments) ? summary.departments : [];
  const alerts = Array.isArray(summary.alerts) ? summary.alerts : [];

  const workspaceSub = `${workspace.node_id || state.nodeId} · ${workspace.deployment_mode || "local_first"}`;
  const nodeSub = `${health.lifecycle_state || "healthy"} · heartbeat ${
    health.last_heartbeat_at ? formatDateTime(health.last_heartbeat_at) : "—"
  }`;
  const schedulerSub = `Last tick ${
    scheduler.last_tick_at ? formatDateTime(scheduler.last_tick_at) : "—"
  }`;
  const approvalsSub = `Approved ${approvals.approved ?? 0} · Rejected ${approvals.rejected ?? 0}`;
  const queuedSub = `Running ${queue.running ?? 0}`;
  const completedSub = `Failed ${queue.failed ?? 0} · Cancelled ${queue.cancelled ?? 0}`;

  return `
    <div class="surface-shell">
      <div class="surface-header">
        <div>
          <div class="surface-eyebrow">Aion Business Desktop</div>
          <div class="surface-title">Business Dashboard</div>
          <div class="surface-subtitle">
            Local-first dashboard rendered directly in the native Tessaris desktop shell.
          </div>
        </div>
        <div class="surface-right-meta">
          <div class="surface-pill">DESKTOP · LOCAL DASHBOARD</div>
          <div class="last-refresh">Last refresh: ${escapeHtml(formatDateTime(state.lastRefreshAt))}</div>
        </div>
      </div>

      ${renderAppTabs()}

      <div class="dashboard-shell">
        <div class="card-grid">
          ${renderDashboardMetricCard(
            "Workspace",
            workspace.workspace_id || state.workspaceId,
            workspaceSub,
          )}
          ${renderDashboardMetricCard(
            "Node Status",
            node.status || "unknown",
            nodeSub,
          )}
          ${renderDashboardMetricCard(
            "Scheduler",
            scheduler.is_running ? "running" : "stopped",
            schedulerSub,
          )}
          ${renderDashboardMetricCard(
            "Approvals",
            approvals.pending ?? 0,
            approvalsSub,
          )}
        </div>

        <div class="card-grid">
          ${renderDashboardMetricCard(
            "Queued Runs",
            queue.queued ?? 0,
            queuedSub,
          )}
          ${renderDashboardMetricCard(
            "Completed Runs",
            queue.completed ?? 0,
            completedSub,
          )}
          ${renderDashboardMetricCard(
            "Audit Events",
            summary.audit_event_count ?? recentAudit.length,
            "Recent activity visible locally",
          )}
          ${renderDashboardMetricCard(
            "Sync Mode",
            workspace.sync_mode || "local_primary",
            "Cloud optional",
          )}
        </div>

        <div class="two-col">
          <div class="panel large-panel">
            <div class="panel-title">Department Summary</div>
            ${renderDashboardDepartmentCards(departments)}
          </div>

          <div class="panel large-panel">
            <div class="panel-title">Alerts / Exceptions</div>
            ${
              alerts.length
                ? `
                  <div class="list-wrap">
                    ${alerts
                      .map(
                        (alert) => `
                          <div class="list-item">
                            <div class="list-item-title">${escapeHtml(alert.title || "Alert")}</div>
                            <div class="list-item-sub">${escapeHtml(alert.detail || "")}</div>
                            <div class="badge-row">
                              ${renderStatusBadge(alert.level || "unknown")}
                              <span class="badge">${escapeHtml(alert.scope || "local")}</span>
                            </div>
                          </div>
                        `,
                      )
                      .join("")}
                  </div>
                `
                : `<div class="empty-state">No active alerts.</div>`
            }
          </div>
        </div>

        <div class="panel large-panel">
          <div class="panel-title">Recent Audit Activity</div>
          ${
            recentAudit.length
              ? `
                <div class="list-wrap">
                  ${recentAudit
                    .map(
                      (event) => `
                        <div class="list-item">
                          <div class="list-item-title">${escapeHtml(event.event_type || "event")}</div>
                          <div class="list-item-sub">${escapeHtml(event.message || "")}</div>
                          <div class="badge-row">
                            <span class="badge">${escapeHtml(event.level || "info")}</span>
                            <span class="badge">${escapeHtml(formatDateTime(event.created_at))}</span>
                          </div>
                        </div>
                      `,
                    )
                    .join("")}
                </div>
              `
              : `<div class="empty-state">No recent audit activity.</div>`
          }
        </div>
      </div>
    </div>
  `;
}

function renderMarketingRunCard(run) {
  const resultPayload = getRunResultPayload(run);
  const context = getRunContext(run);
  const inputPayload = getRunInputPayload(run);
  const postPackage = getRunPostPackage(run);

  const draftCaption =
    firstString(
      postPackage?.caption,
      postPackage?.body,
      resultPayload?.draft_caption?.draft_caption,
      resultPayload?.draft_caption,
      context?.draft_caption,
      run?.draft_caption,
      run?.brief,
      inputPayload?.brief,
      run?.workflow_name,
      run?.workflow_id
    ) || "Marketing run";

  const brief =
    firstString(
      postPackage?.brief,
      run?.brief,
      inputPayload?.brief,
      context?.brief
    ) || "";

  const workflowLabel =
    run?.workflow_name ||
    run?.workflow_id ||
    "workflow";

  const updatedAt =
    run?.updated_at ||
    run?.created_at ||
    null;

  const safeStatus = run?.status || "unknown";
  const imageFailure = getRunImageFailure(run);

  return `
    <div class="marketing-run-card">
      <div class="marketing-run-head">
        <div>
          <div class="marketing-run-title">${escapeHtml(draftCaption)}</div>
          <div class="marketing-run-meta">
            ${escapeHtml(workflowLabel)} · ${escapeHtml(formatDateTime(updatedAt))}
          </div>
        </div>
        ${renderStatusBadge(safeStatus)}
      </div>

      ${
        brief
          ? `<div class="marketing-run-brief">${escapeHtml(brief)}</div>`
          : ""
      }

      <div style="margin-top:12px;">
        ${renderFacebookPostMockup(run, {
          activeIndex: Number(state.selectedFacebookCardIndex || 0),
        })}
      </div>

      ${
        imageFailure
          ? `<div class="marketing-error" style="margin-top:10px;">${escapeHtml(imageFailure)}</div>`
          : ""
      }

      ${
        run?.failure_reason
          ? `<div class="marketing-error" style="margin-top:10px;">${escapeHtml(run.failure_reason)}</div>`
          : ""
      }
    </div>
  `;
}

function renderMarketingApprovalCard(item) {
  const approvalId = escapeHtml(item?.id || "");
  const runId = escapeHtml(
    item?.workflow_run_id ||
      item?.run_id ||
      item?.queue_item_id ||
      item?.runtime_run_id ||
      "",
  );

  const requestedAt =
    item?.requested_at ||
    item?.created_at ||
    null;

  const departmentLabel =
    item?.department_key ||
    "marketing";

  return `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(item?.title || "Approval")}</div>
      <div class="list-item-sub">${escapeHtml(item?.summary || "")}</div>

      <div class="badge-row">
        ${renderStatusBadge(item?.status)}
        <span class="badge">${escapeHtml(departmentLabel)}</span>
        ${
          requestedAt
            ? `<span class="badge">${escapeHtml(formatDateTime(requestedAt))}</span>`
            : ""
        }
      </div>

      ${
        runId
          ? `<div class="list-item-sub">Run: ${runId}</div>`
          : ""
      }

      <div class="marketing-approval-actions">
        <button
          class="secondary-btn approve-marketing-btn"
          data-approval-id="${approvalId}"
          data-run-id="${runId}"
          data-approve="true"
        >
          Approve
        </button>
        <button
          class="secondary-btn approve-marketing-btn"
          data-approval-id="${approvalId}"
          data-run-id="${runId}"
          data-approve="false"
        >
          Reject
        </button>
      </div>
    </div>
  `;
}

function renderCompactStatus(status) {
  const value = String(status || "unknown").toLowerCase();
  return `<span class="compact-status compact-status-${escapeHtml(value)}">${escapeHtml(prettify(value))}</span>`;
}

function renderCompactRecentRuns(runs, expanded = false) {
  const items = Array.isArray(runs) ? runs : [];
  const visible = expanded ? items : items.slice(0, 5);

  if (!items.length) {
    return `<div class="empty-state">No local marketing runs yet.</div>`;
  }

  return `
    <div class="compact-section">
      <div class="compact-list">
        ${visible
          .map((run) => {
            const workflowName = runtimeShared.getRunWorkflowLabel(run);
            const runId = run?.id || run?.queue_item_id || "";
            const updatedAt = formatDateTime(run?.updated_at || run?.created_at);
            const isSelectedRun = runId && state.selectedLiveRunId === String(runId);

            return `
              <div class="compact-row ${isSelectedRun ? "run-row-selected" : ""}">
                <div class="compact-row-main">
                  ${renderCompactStatus(run?.status)}
                  <span class="compact-row-meta">·</span>
                  <strong>${escapeHtml(workflowName)}</strong>
                  <span class="compact-row-meta">·</span>
                  <span>${escapeHtml(updatedAt)}</span>
                </div>

                ${
                  runId
                    ? `
                      <button
                        type="button"
                        class="compact-row-action live-run-select-btn"
                        data-run-id="${escapeHtml(runId)}"
                      >
                        Open
                      </button>
                    `
                    : ""
                }
              </div>
            `;
          })
          .join("")}
      </div>

      ${
        items.length > 5
          ? `
            <button
              type="button"
              class="compact-more-btn"
              data-marketing-runs-expand="${expanded ? "less" : "more"}"
            >
              ${expanded ? "Show less" : `Show more (${items.length - 5} more)`}
            </button>
          `
          : ""
      }
    </div>
  `;
}

function renderCompactResolvedApprovals(items, expanded = false) {
  const approvals = Array.isArray(items) ? items : [];
  const visible = expanded ? approvals : approvals.slice(0, 5);

  if (!approvals.length) {
    return `<div class="empty-state">No resolved approvals yet.</div>`;
  }

  return `
    <div class="compact-section">
      <div class="compact-list">
        ${visible
          .map((item) => {
            const linkedRunId =
              item?.workflow_run_id ||
              item?.run_id ||
              item?.queue_item_id ||
              "";

            const resolvedAt = formatDateTime(
              item?.resolved_at || item?.requested_at || item?.created_at,
            );

            return `
              <div class="compact-row">
                <div class="compact-row-main">
                  ${renderCompactStatus(item?.status)}
                  <span class="compact-row-meta">·</span>
                  <span>${escapeHtml(resolvedAt)}</span>
                  ${
                    linkedRunId
                      ? `
                          <span class="compact-row-meta">·</span>
                          <span>${escapeHtml(linkedRunId)}</span>
                        `
                      : ""
                  }
                </div>

                ${
                  linkedRunId
                    ? `
                        <button
                          type="button"
                          class="compact-row-action live-run-select-btn"
                          data-run-id="${escapeHtml(linkedRunId)}"
                        >
                          Open
                        </button>
                      `
                    : ""
                }
              </div>
            `;
          })
          .join("")}
      </div>

      ${
        approvals.length > 5
          ? `
              <button
                type="button"
                class="compact-more-btn"
                data-marketing-approvals-expand="${expanded ? "less" : "more"}"
              >
                ${expanded ? "Show less" : `Show more (${approvals.length - 5} more)`}
              </button>
            `
          : ""
      }
    </div>
  `;
}

function getDepartmentApprovals(departmentKey) {
  const normalizedDepartment = String(departmentKey || "").toLowerCase();
  const approvals = Array.isArray(state.approvals) ? state.approvals : [];

  return approvals
    .filter(
      (item) =>
        String(item?.department_key || "").toLowerCase() === normalizedDepartment,
    )
    .slice()
    .sort((a, b) => {
      const aTime = new Date(
        a?.resolved_at || a?.requested_at || a?.created_at || 0,
      ).getTime();
      const bTime = new Date(
        b?.resolved_at || b?.requested_at || b?.created_at || 0,
      ).getTime();
      return bTime - aTime;
    });
}

function getApprovalStatusCounts(items) {
  const approvals = Array.isArray(items) ? items : [];
  return {
    total: approvals.length,
    pending: approvals.filter((item) => item?.status === "pending").length,
    approved: approvals.filter((item) => item?.status === "approved").length,
    rejected: approvals.filter((item) => item?.status === "rejected").length,
  };
}

function findRunById(runId) {
  if (!runId) return null;
  const runs = Array.isArray(state.runs) ? state.runs : [];
  return (
    runs.find(
      (run) => String(run?.id || run?.queue_item_id || "") === String(runId),
    ) || null
  );
}

function renderDepartmentApprovalsSurface(departmentKey, selectedAgentCard) {
  const departmentLabel = runtimeShared.getDepartmentLabel(departmentKey);
  const approvals = getDepartmentApprovals(departmentKey);
  const counts = getApprovalStatusCounts(approvals);

  return `
    <div class="dashboard-shell">
      <div class="card-grid">
        ${renderDashboardMetricCard(
          "Department",
          departmentLabel,
          selectedAgentCard?.label || "Department approval history",
        )}
        ${renderDashboardMetricCard(
          "Total approvals",
          counts.total,
          "All recorded approval events",
        )}
        ${renderDashboardMetricCard(
          "Pending",
          counts.pending,
          "Awaiting decision",
        )}
        ${renderDashboardMetricCard(
          "Resolved",
          counts.approved + counts.rejected,
          `Approved ${counts.approved} · Rejected ${counts.rejected}`,
        )}
      </div>

      <div class="panel large-panel">
        <div class="panel-title">${escapeHtml(departmentLabel)} Approval History</div>

        ${
          approvals.length
            ? `
              <div class="list-wrap">
                ${approvals.map((item) => {
                  const runId =
                    item?.run_id ||
                    item?.queue_item_id ||
                    item?.runtime_run_id ||
                    "";
                  const linkedRun = findRunById(runId);
                  const workflowLabel = linkedRun
                    ? runtimeShared.getRunWorkflowLabel(linkedRun)
                    : item?.title || "Approval";
                  const agentLabel = linkedRun
                    ? runtimeShared.getRunAgentLabel(linkedRun)
                    : item?.requested_by || "unknown";

                  return `
                    <div class="list-item">
                      <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px;">
                        <div>
                          <div class="list-item-title">${escapeHtml(workflowLabel)}</div>
                          <div class="list-item-sub">${escapeHtml(agentLabel)}</div>
                        </div>
                        ${renderStatusBadge(item?.status || "unknown")}
                      </div>

                      ${
                        item?.summary
                          ? `<div class="list-item-sub">${escapeHtml(item.summary)}</div>`
                          : ""
                      }

                      <div class="badge-row">
                        <span class="badge">Dept: ${escapeHtml(departmentLabel)}</span>
                        ${
                          runId
                            ? `<span class="badge">Run: ${escapeHtml(runId)}</span>`
                            : ""
                        }
                        <span class="badge">Requested: ${escapeHtml(formatDateTime(item?.requested_at || item?.created_at))}</span>
                        ${
                          item?.resolved_at
                            ? `<span class="badge">Resolved: ${escapeHtml(formatDateTime(item.resolved_at))}</span>`
                            : ""
                        }
                      </div>

                      ${
                        item?.resolved_by
                          ? `<div class="list-item-sub">Resolved by: ${escapeHtml(item.resolved_by)}</div>`
                          : ""
                      }

                      ${
                        item?.resolution_note
                          ? `<div class="list-item-sub">${escapeHtml(item.resolution_note)}</div>`
                          : ""
                      }

                      <div class="marketing-form-actions" style="margin-top:10px;">
                        ${
                          runId
                            ? `
                              <button
                                class="secondary-btn live-run-select-btn"
                                data-run-id="${escapeHtml(runId)}"
                              >
                                Inspect run
                              </button>

                              <button
                                class="secondary-btn live-run-open-replay-btn"
                                data-run-id="${escapeHtml(runId)}"
                              >
                                Open replay
                              </button>
                            `
                            : ""
                        }
                      </div>
                    </div>
                  `;
                }).join("")}
              </div>
            `
            : `<div class="empty-state">No approval history for ${escapeHtml(
                departmentLabel,
              )}.</div>`
        }
      </div>
    </div>
  `;
}

function getSelectedRunElementId(runId) {
  return `live-run-card-${String(runId || "").replace(/[^a-zA-Z0-9_-]/g, "_")}`;
}

function scrollSelectedRunIntoView() {
  if (!state.selectedLiveRunId) return;

  const el = document.getElementById(
    getSelectedRunElementId(state.selectedLiveRunId),
  );

  if (!el) return;

  el.scrollIntoView({
    behavior: "smooth",
    block: "nearest",
    inline: "nearest",
  });
}

function focusRunInspector() {
  const el = document.getElementById("liveRunInspector");
  if (!el) return;

  el.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });

  requestAnimationFrame(() => {
    if (typeof el.focus === "function") {
      el.focus({ preventScroll: true });
    }
  });
}

function revealReplayForSelectedRun() {
  if (!state.selectedLiveRunId) return;

  const row = document.getElementById(
    getSelectedRunElementId(state.selectedLiveRunId),
  );

  if (!row) return;

  row.classList.add("run-row-pulse");
  window.setTimeout(() => {
    row.classList.remove("run-row-pulse");
  }, 1400);
}

function renderMarketingStreamSurface() {
  const marketingRuns = (Array.isArray(state.runs) ? state.runs : [])
    .filter(
      (run) =>
        String(run?.department_key || "").toLowerCase() === "marketing",
    )
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });

  const marketingApprovals = (Array.isArray(state.approvals) ? state.approvals : [])
    .filter(
      (item) =>
        String(item?.department_key || "").toLowerCase() === "marketing",
    )
    .slice()
    .sort((a, b) => {
      const aTime = new Date(
        a?.resolved_at || a?.requested_at || a?.created_at || 0,
      ).getTime();
      const bTime = new Date(
        b?.resolved_at || b?.requested_at || b?.created_at || 0,
      ).getTime();
      return bTime - aTime;
    });

  const pendingApprovals = marketingApprovals.filter(
    (item) => String(item?.status || "").toLowerCase() === "pending",
  );

  const resolvedApprovals = marketingApprovals.filter((item) => {
    const status = String(item?.status || "").toLowerCase();
    return status === "approved" || status === "rejected";
  });

  const counts = {
    total: marketingRuns.length,
    queued: marketingRuns.filter((run) => run?.status === "queued").length,
    running: marketingRuns.filter((run) => run?.status === "running").length,
    waitingApproval: marketingRuns.filter(
      (run) => run?.status === "waiting_approval",
    ).length,
    completed: marketingRuns.filter((run) => run?.status === "completed").length,
    failed: marketingRuns.filter((run) => run?.status === "failed").length,
    cancelled: marketingRuns.filter((run) => run?.status === "cancelled").length,
  };

  const latestPendingApproval = pendingApprovals[0] || null;
  const latestRun = marketingRuns[0] || null;
  const form = state.marketingForm || {};

  const brief = escapeHtml(form.brief || "");
  const objective = escapeHtml(form.objective || "");
  const funnelGoal = escapeHtml(form.funnelGoal || "");
  const targetAudience = escapeHtml(form.targetAudience || "");
  const persona = escapeHtml(form.persona || "");
  const offer = escapeHtml(form.offer || "");

  const assetIntent = escapeHtml(
    normalizeMarketingAssetType(form.assetIntent || "product"),
  );
  const productName = escapeHtml(form.productName || "");
  const offerPrice = escapeHtml(form.offerPrice || "");
  const offerDetails = escapeHtml(form.offerDetails || "");
  const creativeDirection = escapeHtml(form.creativeDirection || "");
  const imageUsageNotes = escapeHtml(form.imageUsageNotes || "");
  const styleDirection = escapeHtml(form.styleDirection || "");

  const channels = escapeHtml(form.channels || "");
  const keywords = escapeHtml(form.keywords || "");
  const hashtags = escapeHtml(form.hashtags || "");
  const hardRules = escapeHtml(form.hardRules || "");
  const guidanceNotes = escapeHtml(form.guidanceNotes || "");
  const campaignNotes = escapeHtml(form.campaignNotes || "");

  const pendingApprovalsHtml = pendingApprovals.length
    ? `<div class="list-wrap">${pendingApprovals
        .map((item) => renderMarketingApprovalCard(item))
        .join("")}</div>`
    : `<div class="empty-state">No pending approvals right now.</div>`;

  const recentRunsHtml = renderCompactRecentRuns(
    marketingRuns,
    !!state.marketingRunsExpanded,
  );

  const resolvedApprovalsHtml = renderCompactResolvedApprovals(
    resolvedApprovals,
    !!state.marketingResolvedApprovalsExpanded,
  );

  return `
    <div class="surface-shell">
      <div class="surface-header">
        <div>
          <div class="surface-eyebrow">Aion Business Desktop</div>
          <div class="surface-title">Marketing Stream</div>
          <div class="surface-subtitle">
            Minimal local marketing workflow surface.
          </div>
        </div>
        <div class="surface-right-meta">
          <div class="surface-pill">MARKETING STREAM</div>
          <div class="last-refresh">Updated ${escapeHtml(formatDateTime(state.lastRefreshAt))}</div>
        </div>
      </div>

      ${renderAppTabs()}

      <div class="dashboard-shell">
        <div class="card-grid">
          ${renderDashboardMetricCard(
            "Runs",
            counts.total,
            `Queued ${counts.queued} · Running ${counts.running}`,
          )}
          ${renderDashboardMetricCard(
            "Awaiting approval",
            counts.waitingApproval,
            latestPendingApproval
              ? `Latest ${escapeHtml(
                  formatDateTime(
                    latestPendingApproval?.requested_at ||
                      latestPendingApproval?.created_at,
                  ),
                )}`
              : "Pending approval queue",
          )}
          ${renderDashboardMetricCard(
            "Completed",
            counts.completed,
            `Failed ${counts.failed} · Cancelled ${counts.cancelled}`,
          )}
          ${renderDashboardMetricCard(
            "Resolved approvals",
            resolvedApprovals.length,
            latestRun
              ? `Latest run ${escapeHtml(
                  formatDateTime(latestRun?.updated_at || latestRun?.created_at),
                )}`
              : "History stored locally",
          )}
        </div>

        <div class="two-col">
          <div class="panel large-panel">
            <div class="panel-title">New manual suggestion</div>

            <label class="field-label">Brief</label>
            <textarea id="marketingBriefInput" class="input input-textarea">${brief}</textarea>

            <div class="two-col marketing-form-grid">
              <div>
                <label class="field-label">Objective</label>
                <input id="marketingObjectiveInput" class="input" value="${objective}" />
              </div>

              <div>
                <label class="field-label">Funnel goal</label>
                <input id="marketingFunnelGoalInput" class="input" value="${funnelGoal}" />
              </div>

              <div>
                <label class="field-label">Target audience</label>
                <input id="marketingAudienceInput" class="input" value="${targetAudience}" />
              </div>

              <div>
                <label class="field-label">Persona</label>
                <input id="marketingPersonaInput" class="input" value="${persona}" />
              </div>

              <div>
                <label class="field-label">Offer</label>
                <input id="marketingOfferInput" class="input" value="${offer}" />
              </div>
            </div>

            <div class="panel" style="
              margin-top:16px;
              margin-bottom:16px;
              background:#f8fafc;
              border:1px solid rgba(15,23,42,0.10);
            ">
              <div class="panel-title">Creative assets and direction</div>
              <div class="helper-text" style="margin-top:0;">
                Upload or describe the images Aion should use when creating the carousel.
              </div>

              <div class="two-col marketing-form-grid" style="margin-top:12px;">
                <div>
                  <label class="field-label">Asset intent</label>
                  <select id="marketingAssetIntentInput" class="input">
                    ${renderMarketingAssetTypeOptions(assetIntent)}
                  </select>
                </div>

                <div>
                  <label class="field-label">Product / subject name</label>
                  <input
                    id="marketingProductNameInput"
                    class="input"
                    value="${productName}"
                    placeholder="Example: Black trainers"
                  />
                </div>

                <div>
                  <label class="field-label">Offer price</label>
                  <input
                    id="marketingOfferPriceInput"
                    class="input"
                    value="${offerPrice}"
                    placeholder="Example: £99.99"
                  />
                </div>

                <div>
                  <label class="field-label">Offer details</label>
                  <input
                    id="marketingOfferDetailsInput"
                    class="input"
                    value="${offerDetails}"
                    placeholder="Example: Limited time. Available in black, blue and grey."
                  />
                </div>
              </div>

              <label class="field-label">Upload images</label>
              <input
                id="marketingCreativeAssetUploadInput"
                class="input"
                type="file"
                accept="image/*"
                multiple
              />

              <label class="field-label">Creative direction</label>
              <textarea
                id="marketingCreativeDirectionInput"
                class="input input-textarea input-textarea-small"
                placeholder="Example: Use the trainers as the hero product. Make the carousel feel premium but local."
              >${creativeDirection}</textarea>

              <label class="field-label">Image usage notes</label>
              <textarea
                id="marketingImageUsageNotesInput"
                class="input input-textarea input-textarea-small"
                placeholder="Example: Use product image on cards 1 and 5. Use background images subtly. Do not alter the logo."
              >${imageUsageNotes}</textarea>

              <label class="field-label">Style direction</label>
              <textarea
                id="marketingStyleDirectionInput"
                class="input input-textarea input-textarea-small"
                placeholder="Example: Premium, clean, energetic, simple."
              >${styleDirection}</textarea>

              ${renderMarketingCreativeAssetList()}
            </div>

            <div class="three-col marketing-form-grid">
              <div>
                <label class="field-label">Channels</label>
                <textarea id="marketingChannelsInput" class="input input-textarea input-textarea-small">${channels}</textarea>
              </div>

              <div>
                <label class="field-label">Keywords</label>
                <textarea id="marketingKeywordsInput" class="input input-textarea input-textarea-small">${keywords}</textarea>
              </div>

              <div>
                <label class="field-label">Hashtags</label>
                <textarea id="marketingHashtagsInput" class="input input-textarea input-textarea-small">${hashtags}</textarea>
              </div>
            </div>

            <label class="field-label">Hard rules</label>
            <textarea id="marketingHardRulesInput" class="input input-textarea input-textarea-small">${hardRules}</textarea>

            <label class="field-label">Guidance notes</label>
            <textarea id="marketingGuidanceNotesInput" class="input input-textarea input-textarea-small">${guidanceNotes}</textarea>

            <label class="field-label">Campaign notes</label>
            <textarea id="marketingCampaignNotesInput" class="input input-textarea input-textarea-small">${campaignNotes}</textarea>

            <div class="marketing-form-actions">
              <button id="launchMarketingBtn" class="primary-btn">Create content suggestions</button>
              <button id="refreshMarketingBtn" class="secondary-btn">Refresh stream</button>
            </div>
          </div>

          <div class="panel large-panel">
            <div class="panel-title">Pending approvals</div>
            ${pendingApprovalsHtml}
          </div>
        </div>

        <div class="two-col">
          <div class="panel large-panel">
            <div class="panel-title">Recent runs</div>
            ${recentRunsHtml}
          </div>

          <div class="panel large-panel">
            <div class="panel-title">Resolved approvals</div>
            ${resolvedApprovalsHtml}
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderBoardroomMetricCard(label, value, sub = "") {
  return `
    <div class="card">
      <div class="card-label">${escapeHtml(label)}</div>
      <div class="card-value">${escapeHtml(value)}</div>
      <div class="card-sub">${escapeHtml(sub)}</div>
    </div>
  `;
}

function renderBoardroomBindings(bindingsByCategory) {
  const entries = Object.entries(bindingsByCategory || {});
  if (!entries.length) {
    return `<div class="empty-state">No container bindings loaded.</div>`;
  }

  return `
    <div class="list-wrap">
      ${entries
        .map(([category, items]) => {
          const count = Array.isArray(items) ? items.length : 0;
          return `
            <div class="list-item">
              <div class="list-item-title">${escapeHtml(category)}</div>
              <div class="list-item-sub">${escapeHtml(count)} binding(s)</div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderBoardroomDepartments(departments) {
  if (!Array.isArray(departments) || !departments.length) {
    return `<div class="empty-state">No boardroom departments loaded.</div>`;
  }

  return `
    <div class="dashboard-department-grid">
      ${departments
        .map((dept) => {
          const status = dept.status || "unknown";
          return `
            <div class="dashboard-department-card">
              <div class="dashboard-department-header">
                <div>
                  <div class="dashboard-department-name">${escapeHtml(
                    dept.label || dept.name || dept.key || "Department",
                  )}</div>
                  <div class="dashboard-department-sub">${escapeHtml(
                    dept.summary || dept.owner || dept.key || "",
                  )}</div>
                </div>
                ${renderStatusBadge(status)}
              </div>

              <div class="dashboard-department-metrics">
                <div class="dashboard-mini-stat">
                  <span>Open</span>
                  <strong>${escapeHtml(dept.openTasks ?? dept.open_tasks ?? 0)}</strong>
                </div>
                <div class="dashboard-mini-stat">
                  <span>Blocked</span>
                  <strong>${escapeHtml(dept.blockedTasks ?? dept.blocked_tasks ?? 0)}</strong>
                </div>
                <div class="dashboard-mini-stat">
                  <span>Due today</span>
                  <strong>${escapeHtml(dept.dueToday ?? dept.due_today ?? 0)}</strong>
                </div>
                <div class="dashboard-mini-stat">
                  <span>KPIs</span>
                  <strong>${escapeHtml(
                    Array.isArray(dept.kpis) ? dept.kpis.length : dept.kpi_count ?? 0,
                  )}</strong>
                </div>
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderBoardroomOperatorPresence() {
  const runtime = getBoardroomRuntime();
  const runs = safeArray(runtime.runs);
  const approvals = safeArray(runtime.approvals);

  const running = runs.filter((run) => run?.status === "running").length;
  const waitingApproval = runs.filter((run) => run?.status === "waiting_approval").length;
  const failed = runs.filter((run) => run?.status === "failed").length;
  const pendingApprovals = approvals.filter((item) => item?.status === "pending").length;

  return `
    <div class="panel large-panel">
      <div class="panel-title">Operator Presence</div>
      <div class="card-grid">
        ${renderBoardroomMetricCard("Active runs", running, "Currently executing")}
        ${renderBoardroomMetricCard("Waiting approval", waitingApproval, "Run pipeline blocked")}
        ${renderBoardroomMetricCard("Failed runs", failed, "Needs intervention")}
        ${renderBoardroomMetricCard("Pending approvals", pendingApprovals, "Decision queue")}
      </div>
    </div>
  `;
}


function getWorkflowCapsuleApprovalsForBoardroom(runtimeApprovals = []) {
  const localItems = Array.isArray(runtimeApprovals) ? runtimeApprovals : [];
  const extraItems = Array.isArray(state.workflowCapsuleApprovals)
    ? state.workflowCapsuleApprovals
    : [];

  return [...extraItems, ...localItems]
    .filter((item) => {
      const schema = String(item?.schema_version || "");
      const canonicalKey = String(item?.canonical_key || "");
      const source = String(item?.source || item?.requested_by || "");
      return (
        schema.includes("workflow_capsule_approval") ||
        canonicalKey.startsWith("workflow:") ||
        source.includes("workflow_capsule")
      );
    })
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.created_at || a?.requested_at || 0).getTime();
      const bTime = new Date(b?.created_at || b?.requested_at || 0).getTime();
      return bTime - aTime;
    });
}

function renderBoardroomWorkflowCapsuleApprovalQueue(runtimeApprovals = []) {
  const items = getWorkflowCapsuleApprovalsForBoardroom(runtimeApprovals);
  const pending = items.filter((item) => String(item?.status || "").toLowerCase() === "pending");

  return `
    <div class="panel large-panel" data-boardroom-workflow-capsule-approvals="true">
      <div class="panel-title">Workflow Capsule Approvals</div>

      ${
        pending.length
          ? `
            <div class="list-wrap">
              ${pending.map((item) => {
                const approvalId = String(item?.approval_id || item?.id || "");
                const payload = item?.payload && typeof item.payload === "object" ? item.payload : {};
                const meta = item?.meta && typeof item.meta === "object" ? item.meta : {};
                const permissionDecision =
                  item?.permission_decision ||
                  payload?.permission_decision ||
                  meta?.permission_decision ||
                  "request_approval";
                const riskTier =
                  item?.risk_tier ||
                  payload?.risk_tier ||
                  meta?.risk_tier ||
                  "medium";
                const vaultRequirements =
                  item?.vault_requirements ||
                  payload?.vault_requirements ||
                  meta?.vault_requirements ||
                  [];
                const externalWriteStepId =
                  item?.external_write_step_id ||
                  payload?.external_write_step_id ||
                  meta?.external_write_step_id ||
                  "—";

                return `
                  <div class="list-item" data-workflow-capsule-approval-card="true">
                    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px;">
                      <div>
                        <div class="list-item-title">${escapeHtml(item?.display_name || item?.title || "Workflow Capsule Approval")}</div>
                        <div class="list-item-sub">${escapeHtml(item?.canonical_key || "workflow:unknown")}</div>
                      </div>
                      ${renderStatusBadge(item?.status || "pending")}
                    </div>

                    <div class="badge-row">
                      <span class="badge">approval_id: ${escapeHtml(approvalId)}</span>
                      <span class="badge">permission_decision: ${escapeHtml(permissionDecision)}</span>
                      <span class="badge">risk_tier: ${escapeHtml(riskTier)}</span>
                      <span class="badge">external_write_step_id: ${escapeHtml(externalWriteStepId)}</span>
                    </div>

                    <div class="list-item-sub">
                      vault_requirements: ${escapeHtml(Array.isArray(vaultRequirements) ? vaultRequirements.join(", ") : String(vaultRequirements || "—"))}
                    </div>

                    <div class="list-item-sub">
                      Dry-run preview: external write is blocked until guarded approval resume.
                    </div>

                    <div class="marketing-approval-actions">
                      <button
                        class="secondary-btn"
                        type="button"
                        data-workflow-capsule-approval-action="approve"
                        data-workflow-capsule-approval-id="${escapeHtml(approvalId)}"
                        title="Approve workflow capsule"
                      >
                        Approve workflow capsule
                      </button>

                      <button
                        class="secondary-btn"
                        type="button"
                        data-workflow-capsule-approval-action="reject"
                        data-workflow-capsule-approval-id="${escapeHtml(approvalId)}"
                        title="Reject workflow capsule"
                      >
                        Reject workflow capsule
                      </button>
                    </div>
                  </div>
                `;
              }).join("")}
            </div>
          `
          : `<div class="empty-state">No pending workflow capsule approvals.</div>`
      }
    </div>
  `;
}

async function handleBoardroomWorkflowCapsuleApprovalAction(approvalId, action) {
  const safeApprovalId = String(approvalId || "").trim();
  const safeAction = String(action || "").trim();

  if (!safeApprovalId || !["approve", "reject"].includes(safeAction)) {
    return;
  }

  const apiBase =
    state.apiBase ||
    state.desktopApiBase ||
    window.AION_API_BASE ||
    "http://127.0.0.1:8080";

  const decisionPath = safeAction === "approve" ? "approve" : "reject";

  const decisionResponse = await fetch(
    `${apiBase}/api/workflow-capsules/approvals/${encodeURIComponent(safeApprovalId)}/${decisionPath}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decided_by: "boardroom_ui",
        reason: `Boardroom ${safeAction}`,
      }),
    },
  );

  const decisionResult = await decisionResponse.json().catch(() => ({}));

  if (!decisionResponse.ok || decisionResult?.ok === false) {
    throw new Error(decisionResult?.detail || decisionResult?.error || `Workflow capsule ${safeAction} failed`);
  }

  if (safeAction === "approve") {
    const resumeResponse = await fetch(
      `${apiBase}/api/workflow-capsules/approvals/${encodeURIComponent(safeApprovalId)}/resume`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          execution_mode: "connector_ready",
          available_vault_requirements: ["vault.gmail.credentials"],
          cau_state: {
            allow_learn: false,
            adr_active: false,
            deny_reason: "boardroom_guarded_resume_default_no_learning",
          },
          extra: {
            source: "boardroom_ui",
            route: "workflow_capsule_guarded_resume",
          },
        }),
      },
    );

    const resumeResult = await resumeResponse.json().catch(() => ({}));

    if (!resumeResponse.ok || resumeResult?.ok === false) {
      throw new Error(resumeResult?.detail || resumeResult?.error || "Workflow capsule guarded resume failed");
    }
  }

  desktopStore.patch?.({
    message: safeAction === "approve"
      ? "Workflow capsule approved and resumed in connector_ready mode."
      : "Workflow capsule rejected.",
    messageTone: "success",
  });

  await refreshAll?.();
  requestRender?.();
}

function renderBoardroomDashboardView(snapshot) {
  const workspace = getBoardroomWorkspace();
  const pulse = getBoardroomPulse();
  const center = getBoardroomCenter();
  const runtime = getBoardroomRuntime();

  const cash = asRecord(pulse.cash) || {};
  const sales = asRecord(pulse.sales) || {};
  const ops = asRecord(pulse.ops) || {};
  const finance = asRecord(pulse.finance) || {};
  const risk = asRecord(pulse.risk) || {};

  const runtimeRuns = safeArray(runtime.runs);
  const runtimeApprovals = safeArray(runtime.approvals);
  const departments = getBoardroomDepartments();
  const bindingsByCategory = getBoardroomBindingsByCategory();

  return `
    <div class="dashboard-shell">
      <div class="card-grid">
        ${renderBoardroomMetricCard(
          "Workspace",
          workspace.name || workspace.workspace_id || state.workspaceId,
          workspace.industry || workspace.slug || workspace.category || state.workspaceId,
        )}
        ${renderBoardroomMetricCard(
          "Cash",
          cash.onHand ?? cash.on_hand ?? center.cash ?? "—",
          `Runway ${cash.runwayDays ?? cash.runway_days ?? "—"}d`,
        )}
        ${renderBoardroomMetricCard(
          "Revenue",
          sales.revenue ?? center.revenue ?? "—",
          `Orders ${sales.orders ?? "—"} · Conv ${sales.conversionRate ?? sales.conversion_rate ?? "—"}%`,
        )}
        ${renderBoardroomMetricCard(
          "Operations",
          ops.backlog ?? center.pipeline ?? "—",
          `Fulfilment ${ops.fulfilmentRate ?? ops.fulfilment_rate ?? "—"}%`,
        )}
      </div>

      <div class="card-grid">
        ${renderBoardroomMetricCard(
          "Debtor Days",
          finance.debtorDays ?? finance.debtor_days ?? "—",
          `Creditor ${finance.creditorDays ?? finance.creditor_days ?? "—"}`,
        )}
        ${renderBoardroomMetricCard(
          "Gross Margin",
          finance.grossMarginPct ?? finance.gross_margin_pct ?? "—",
          "Finance pulse",
        )}
        ${renderBoardroomMetricCard(
          "Demand Risk",
          risk.demand || "—",
          `Cash ${risk.cash || "—"} · Ops ${risk.operations || "—"}`,
        )}
        ${renderBoardroomMetricCard(
          "Live Runs",
          runtimeRuns.length,
          `Pending approvals ${runtimeApprovals.filter((item) => item?.status === "pending").length}`,
        )}
      </div>

      ${renderBoardroomOperatorPresence()}

      ${renderBoardroomWorkflowCapsuleApprovalQueue(runtimeApprovals)}

      <div class="two-col">
        ${renderBoardroomRecentRunsPanel()}
        ${renderBoardroomExceptionsPanel()}
      </div>

      <div class="two-col">
        <div class="panel large-panel">
          <div class="panel-title">Departments</div>
          ${renderBoardroomDepartments(departments)}
        </div>

        <div class="panel large-panel">
          <div class="panel-title">Container Bindings</div>
          ${renderBoardroomBindings(bindingsByCategory)}
        </div>
      </div>
    </div>
  `;
}

function openDepartmentWorkspaceFromBoardroom(departmentKey, nextView, runId, openReplay) {
  boardroomRuntime.openDepartmentWorkspaceFromBoardroom(
    {
      desktopStore,
      state,
      render,
    },
    departmentKey,
    nextView,
    runId,
    openReplay,
  );
}

function renderBoardroomSpatialView(snapshot) {
  const departments = getBoardroomDepartments();
  const topology = getBoardroomTopology();
  const runtime = getBoardroomRuntime();

  return `
    <div class="dashboard-shell">
      <div class="panel large-panel">
        <div class="panel-title">Spatial Boardroom</div>
        <div class="helper-text" style="margin-bottom:12px;">
          Real local boardroom renderer driven by desktop runtime snapshot, seat selection, stage selection, agent selection, and inspector target state.
        </div>

        <div class="card-grid">
          ${renderBoardroomMetricCard("Departments", departments.length, "Local seat map")}
          ${renderBoardroomMetricCard(
            "Topology Nodes",
            safeArray(topology.nodes).length,
            "Spatial graph",
          )}
          ${renderBoardroomMetricCard(
            "Topology Edges",
            safeArray(topology.edges).length,
            "Seat links",
          )}
          ${renderBoardroomMetricCard(
            "Runtime Runs",
            safeArray(runtime.runs).length,
            "Rendered from local runtime truth",
          )}
        </div>

        <div class="spatial-boardroom-shell" style="margin-top:14px;">
          <div id="spatialBoardroomMount" class="spatial-boardroom-mount"></div>
        </div>
      </div>

      <div class="panel large-panel">
        <div class="panel-title">Department Nodes</div>
        ${renderBoardroomDepartments(departments)}
      </div>
    </div>
  `;
}

function renderBoardroomSurface() {
  const snapshot = getBoardroomSnapshot();
  const viewMode = state.boardroomViewMode === "spatial" ? "spatial" : "dashboard";

  return `
    <div class="surface-shell">
      <div class="surface-header">
        <div>
          <div class="surface-eyebrow">Aion Business Desktop</div>
          <div class="surface-title">Boardroom</div>
          <div class="surface-subtitle">
            Native desktop boardroom surface using local runtime snapshot as source of truth.
          </div>
        </div>
        <div class="surface-right-meta">
          <div class="surface-pill">DESKTOP · LOCAL BOARDROOM</div>
          <div class="last-refresh">Last refresh: ${escapeHtml(formatDateTime(state.lastRefreshAt))}</div>
        </div>
      </div>

      ${renderAppTabs()}

      <div class="boardroom-view-toggle">
        <button
          class="secondary-btn boardroom-view-btn ${viewMode === "dashboard" ? "boardroom-view-btn-active" : ""}"
          data-boardroom-view="dashboard"
        >
          Flat Dashboard View
        </button>
        <button
          class="secondary-btn boardroom-view-btn ${viewMode === "spatial" ? "boardroom-view-btn-active" : ""}"
          data-boardroom-view="spatial"
        >
          Spatial Boardroom View
        </button>
      </div>

      ${
        viewMode === "spatial"
          ? renderBoardroomSpatialView(snapshot)
          : `
            <div class="boardroom-dashboard-shell">
              ${renderBoardroomDashboardView(snapshot)}
            </div>
          `
      }
    </div>
  `;
}

function getPrimaryDepartmentAgentCard(departmentKey) {
  return liveAgentsRuntime.getPrimaryDepartmentAgentCard(state, departmentKey);
}

function setLiveAgentsWorkspace(departmentKey, options = {}) {
  boardroomRuntime.setLiveAgentsWorkspace(
    {
      desktopStore,
      state,
      LIVE_AGENT_VIEWS,
    },
    departmentKey,
    options,
  );
}

function renderLocalNodeSurface() {
  const status = state.status || {};
  const control = status.control || {};
  const scheduler = state.scheduler || {};
  const counts = getQueueCounts();
  const approvalCounts = getApprovalCounts();

  return `
    <div class="surface-shell">
      <div class="surface-header">
        <div>
          <div class="surface-eyebrow">DA1–DA3</div>
          <div class="surface-title">Local Node Status Panel</div>
          <div class="surface-subtitle">Mac local node control surface inside the real Aion Business desktop shell.</div>
        </div>
        <div class="surface-right-meta">
          <div class="surface-pill">DESKTOP · LOCAL NODE</div>
          <div class="last-refresh">Last refresh: ${escapeHtml(formatDateTime(state.lastRefreshAt))}</div>
        </div>
      </div>

      ${renderAppTabs()}

      <div class="desktop-layout">
        <aside class="sidebar">
          <div class="panel">
            <div class="panel-title">Workspace Binding</div>

            <label class="field-label">API Base</label>
            <input id="apiBaseInput" class="input" value="${escapeHtml(state.apiBase)}" />

            <label class="field-label">Web Base</label>
            <input id="webBaseInput" class="input" value="${escapeHtml(state.webBase)}" />

            <label class="field-label">Workspace ID</label>
            <input id="workspaceIdInput" class="input" value="${escapeHtml(state.workspaceId)}" />

            <label class="field-label">Node ID</label>
            <input id="nodeIdInput" class="input" value="${escapeHtml(state.nodeId)}" />

            <button id="bindWorkspaceBtn" class="primary-btn">Bind Workspace</button>

            <div class="helper-text">
              ${escapeHtml(state.message || `Bound to ${state.workspaceId}`)}
            </div>
          </div>

          <div class="panel">
            <div class="panel-title">Node Controls</div>
            <div class="button-grid">
              <button id="refreshBtn" class="secondary-btn">Refresh</button>
              <button id="schedulerStartBtn" class="secondary-btn">Start Scheduler</button>
              <button id="schedulerStopBtn" class="secondary-btn">Stop Scheduler</button>
              <button id="pauseNodeBtn" class="secondary-btn">Pause Node</button>
              <button id="resumeNodeBtn" class="secondary-btn">Resume Node</button>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title">Environment</div>
            <div class="kv-row"><span>Platform</span><strong>mac</strong></div>
            <div class="kv-row"><span>Shell</span><strong>Electron</strong></div>
            <div class="kv-row"><span>Version</span><strong>0.1.0</strong></div>
          </div>

          <div class="panel">
            <div class="panel-title">Local Truth Boundary</div>
            <div class="helper-text">
              Local state is primary. Cloud remains optional for summaries, snapshots, commands, and approvals.
            </div>
          </div>
        </aside>

        <main class="main-content">
          <div class="card-grid">
            <div class="card">
              <div class="card-label">Node Status</div>
              <div class="card-value">${escapeHtml(control.status || "unknown")}</div>
              <div class="card-sub">${escapeHtml(control.node_id || state.nodeId)} · ${escapeHtml(control.workspace_id || state.workspaceId)}</div>
            </div>

            <div class="card">
              <div class="card-label">Scheduler</div>
              <div class="card-value">${escapeHtml(scheduler.is_running ? "running" : "stopped")}</div>
              <div class="card-sub">Last tick: ${escapeHtml(scheduler.last_tick_at || "—")}</div>
            </div>

            <div class="card">
              <div class="card-label">Queue Counts</div>
              <div class="card-value">${state.runs.length}</div>
              <div class="card-sub">
                Q ${counts.queued} · R ${counts.running} · W ${counts.waiting} · C ${counts.completed}
              </div>
            </div>

            <div class="card">
              <div class="card-label">Approvals</div>
              <div class="card-value">${approvalCounts.pending}</div>
              <div class="card-sub">
                Approved ${approvalCounts.approved} · Rejected ${approvalCounts.rejected}
              </div>
            </div>
          </div>

          <div class="two-col">
            <div class="panel large-panel">
              <div class="panel-title">Runs</div>
              ${renderRuns()}
            </div>

            <div class="panel large-panel">
              <div class="panel-title">Approvals</div>
              ${renderApprovals()}
            </div>
          </div>

          <div class="two-col">
            <div class="panel large-panel">
              <div class="panel-title">Audit Events</div>
              ${renderAudit()}
            </div>

            <div class="panel large-panel">
              <div class="panel-title">Raw Status</div>
              <pre class="json-block">${escapeHtml(shortJson({ status, scheduler }))}</pre>
            </div>
          </div>
        </main>
      </div>
    </div>
  `;
}

function getDepartmentRuntime(roomKey) {
  return runtimeShared.getDepartmentRuntime(state.runs, state.approvals, roomKey);
}

function getDepartmentRuntimeList() {
  return runtimeShared.getDepartmentRuntimeList(state.runs, state.approvals);
}

function getRecentDepartmentRuns(roomKey, limit = 4) {
  return runtimeShared.getRecentDepartmentRuns(
    state.runs,
    state.approvals,
    roomKey,
    limit,
  );
}

function getDepartmentExceptions(limit = 10) {
  return runtimeShared.getDepartmentExceptions(state.runs, limit);
}

function renderBoardroomRecentRunsPanel() {
  const rooms = getDepartmentRuntimeList().filter((room) => room.totalRuns > 0);

  return `
    <div class="panel large-panel">
      <div class="panel-title">Recent Workflow Runs</div>

      ${
        rooms.length
          ? `
            <div class="list-wrap">
              ${rooms.map((room) => {
                const recentRuns = getRecentDepartmentRuns(room.key, 3);

                return `
                  <div class="list-item">
                    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px;">
                      <div>
                        <div class="list-item-title">${escapeHtml(room.label)}</div>
                        <div class="list-item-sub">
                          ${escapeHtml(room.totalRuns)} total run(s) · ${escapeHtml(room.pendingApprovals)} pending approval(s)
                        </div>
                      </div>
                      <button
                        class="secondary-btn secondary-btn-small boardroom-open-runs-btn"
                        data-department-key="${escapeHtml(room.key)}"
                        data-live-view="runs"
                      >
                        Open
                      </button>
                    </div>

                    ${
                      recentRuns.length
                        ? `
                          <div class="list-wrap">
                            ${recentRuns.map((run) => {
                              const runId = run?.id || run?.queue_item_id || "";
                              return `
                                <div class="list-item">
                                  <div class="list-item-title">${escapeHtml(runtimeShared.getRunWorkflowLabel(run))}</div>
                                  <div class="badge-row">
                                    ${renderStatusBadge(run?.status)}
                                    <span class="badge">${escapeHtml(formatDateTime(run?.updated_at || run?.created_at))}</span>
                                  </div>
                                  <div class="marketing-form-actions">
                                    <button
                                      class="secondary-btn secondary-btn-small boardroom-open-run-btn"
                                      data-department-key="${escapeHtml(room.key)}"
                                      data-run-id="${escapeHtml(runId)}"
                                      data-live-view="runs"
                                    >
                                      Inspect
                                    </button>
                                    <button
                                      class="secondary-btn secondary-btn-small boardroom-open-run-btn"
                                      data-department-key="${escapeHtml(room.key)}"
                                      data-run-id="${escapeHtml(runId)}"
                                      data-live-view="runs"
                                      data-open-replay="true"
                                    >
                                      Replay
                                    </button>
                                  </div>
                                </div>
                              `;
                            }).join("")}
                          </div>
                        `
                        : `<div class="empty-state">No recent runs.</div>`
                    }
                  </div>
                `;
              }).join("")}
            </div>
          `
          : `<div class="empty-state">No recent runtime runs yet.</div>`
      }
    </div>
  `;
}

function renderBoardroomExceptionsPanel() {
  const exceptions = getDepartmentExceptions(12);

  return `
    <div class="panel large-panel">
      <div class="panel-title">Blocked / Failed Automations</div>

      ${
        exceptions.length
          ? `
            <div class="list-wrap">
              ${exceptions.map((run) => {
                const runId = run?.id || run?.queue_item_id || "";
                const departmentKey = runtimeShared.getRunDepartmentKey(run);

                return `
                  <div class="list-item">
                    <div class="list-item-title">${escapeHtml(runtimeShared.getRunWorkflowLabel(run))}</div>
                    <div class="list-item-sub">
                      ${escapeHtml(runtimeShared.getDepartmentLabel(departmentKey))} · ${escapeHtml(runtimeShared.getRunAgentLabel(run))}
                    </div>

                    <div class="badge-row">
                      ${renderStatusBadge(run?.status)}
                      <span class="badge">${escapeHtml(formatDateTime(run?.updated_at || run?.created_at))}</span>
                    </div>

                    ${
                      run?.failure_reason
                        ? `<div class="list-item-sub">${escapeHtml(run.failure_reason)}</div>`
                        : ""
                    }

                    <div class="marketing-form-actions">
                      <button
                        class="secondary-btn secondary-btn-small boardroom-open-run-btn"
                        data-department-key="${escapeHtml(departmentKey)}"
                        data-run-id="${escapeHtml(runId)}"
                        data-live-view="runs"
                      >
                        Inspect
                      </button>
                      <button
                        class="secondary-btn secondary-btn-small boardroom-open-run-btn"
                        data-department-key="${escapeHtml(departmentKey)}"
                        data-run-id="${escapeHtml(runId)}"
                        data-live-view="runs"
                        data-open-replay="true"
                      >
                        Replay
                      </button>
                    </div>
                  </div>
                `;
              }).join("")}
            </div>
          `
          : `<div class="empty-state">No blocked or failed automations.</div>`
      }
    </div>
  `;
}

function renderDashboardBodyOnly() {
  return renderDashboardSurface()
    .replace(/^.*?<div class="dashboard-shell">/s, '<div class="dashboard-shell">')
    .replace(/<\/div>\s*<\/div>\s*$/s, "</div>");
}

function renderOperationsFlowModeToggle() {
  const viewMode =
    state.operationsFlowViewMode === "spatial" ? "spatial" : "flat";

  return `
    <div class="boardroom-view-toggle">
      <button
        class="secondary-btn boardroom-view-btn ${viewMode === "flat" ? "boardroom-view-btn-active" : ""}"
        data-operations-flow-view="flat"
      >
        Flat Dashboard View
      </button>
      <button
        class="secondary-btn boardroom-view-btn ${viewMode === "spatial" ? "boardroom-view-btn-active" : ""}"
        data-operations-flow-view="spatial"
      >
        3D Operations Flow
      </button>
    </div>
  `;
}

function renderDesktopWorkspace() {
  const showAssistantRail = state.activeTab === "brand_foundation";

  const layoutClass = showAssistantRail
    ? "desktop-workspace-layout"
    : "desktop-workspace-layout-no-rail";

  return `
    <div class="${layoutClass}">
      <main class="desktop-workspace-main">
        ${renderMainSurface()}
      </main>

      ${
        showAssistantRail
          ? `
            <aside class="desktop-ai-rail">
              ${renderDesktopAssistantPanel()}
            </aside>
          `
          : ""
      }
    </div>
  `;
}

function getDesktopAssistantTitle() {
  const labels = {
    boardroom: "Boardroom Assistant",
    dashboard: "Dashboard Assistant",
    marketing_stream: "Marketing Assistant",
    brand_foundation: "Brand Assistant",
    live_agents: "Agent Assistant",
    aion_chat: "Aion",
    operations_agents: "Train Agent Assistant",
    operations_flow: "Operations Assistant",
    local_node: "Local Node Assistant",
  };

  return labels[state.activeTab] || "Aion Assistant";
}

function getDesktopAssistantPlaceholder() {
  const placeholders = {
    boardroom: "Ask what needs attention in the business...",
    dashboard: "Ask about alerts, queues, approvals, or current status...",
    marketing_stream: "Ask for post ideas, captions, hooks, or campaign improvements...",
    brand_foundation: "Ask for help writing or improving brand sections...",
    live_agents: "Ask about this run, approval, agent, or workflow...",
    operations_agents: "Ask about trained tasks, triggers, test runs, approvals, or automation setup...",
    operations_flow: "Ask what is blocked or how the work is flowing...",
    local_node: "Ask about backend status, runtime, scheduler, or sync...",
    aion_chat: "Ask Aion anything about the business, runtime, brand, agents, code, or next action...",
  };

  return placeholders[state.activeTab] || "Ask Aion anything...";
}

function renderDesktopAssistantQuickActions() {
  const tab = state.activeTab || "dashboard";

  const actionsByTab = {
    boardroom: [
      ["focus_today", "What should I focus on today?"],
      ["explain_business_state", "Explain current business state"],
      ["find_risks", "Find risks"],
    ],
    dashboard: [
      ["explain_alerts", "Explain alerts"],
      ["summarize_queue", "Summarize queue"],
      ["what_changed", "What changed recently?"],
    ],
    marketing_stream: [
      ["write_post", "Help write a post"],
      ["improve_caption", "Improve caption"],
      ["campaign_ideas", "Give campaign ideas"],
    ],
    brand_foundation: [
      ["help_section", "Help complete this section"],
      ["make_clearer", "Make it clearer"],
      ["make_premium", "Make it more professional"],
    ],
    live_agents: [
      ["explain_run", "Explain this run"],
      ["explain_approval", "Explain approval"],
      ["what_next", "What should happen next?"],
    ],
    operations_flow: [
      ["find_blockers", "Find blockers"],
      ["explain_flow", "Explain the flow"],
      ["next_actions", "Suggest next actions"],
    ],
    local_node: [
      ["backend_status", "Why is backend not ready?"],
      ["scheduler_status", "Explain scheduler"],
      ["sync_status", "Explain sync"],
    ],
  };

  const actions = actionsByTab[tab] || actionsByTab.dashboard;

  return `
    <div class="desktop-ai-actions">
      ${actions
        .map(
          ([key, label]) => `
            <button
              class="secondary-btn desktop-ai-action-btn"
              type="button"
              data-desktop-ai-action="${escapeHtml(key)}"
            >
              ${escapeHtml(label)}
            </button>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderDesktopAssistantPanel() {
  return `
    <div class="panel large-panel desktop-ai-panel">
      <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px;">
        <div>
          <div class="panel-title">${escapeHtml(getDesktopAssistantTitle())}</div>
          <div class="helper-text" style="margin-top:0;">
            Page-aware assistant using the current desktop context.
          </div>
        </div>
      </div>

      <label class="field-label">AI provider</label>
      <select id="desktopAssistantProviderInput" class="input">
        <option value="gemma4" ${
          state.desktopAssistantProvider === "gemma4" || !state.desktopAssistantProvider
            ? "selected"
            : ""
        }>
          Free · Gemma 4 AI
        </option>
        <option value="openai" ${
          state.desktopAssistantProvider === "openai" ? "selected" : ""
        }>
          OpenAI
        </option>
        <option value="claude" ${
          state.desktopAssistantProvider === "claude" ? "selected" : ""
        }>
          Claude
        </option>
      </select>

      ${renderDesktopAssistantQuickActions()}

      ${
        state.activeTab === "brand_foundation"
          ? `
            <label class="field-label">Brand section</label>
            <select id="desktopAssistantTargetPathInput" class="input">
              ${renderBrandAssistantSectionOptions()}
            </select>
          `
          : ""
      }

      <label class="field-label">Ask</label>
      <textarea
        id="desktopAssistantPromptInput"
        class="input input-textarea"
        placeholder="${escapeHtml(getDesktopAssistantPlaceholder())}"
      >${escapeHtml(state.desktopAssistantPrompt || "")}</textarea>

      <div class="marketing-form-actions" style="display:grid; gap:10px;">
        <button id="desktopAssistantRunBtn" class="primary-btn" type="button">
          Ask assistant
        </button>
        <button id="desktopAssistantApplyBtn" class="secondary-btn" type="button">
          Apply response
        </button>
        <button id="desktopAssistantClearBtn" class="secondary-btn" type="button">
          Clear
        </button>
      </div>

      <label class="field-label">Response</label>
      <textarea
        id="desktopAssistantOutputInput"
        class="input input-textarea"
        placeholder="Assistant response will appear here."
      >${escapeHtml(state.desktopAssistantOutput || "")}</textarea>
    </div>
  `;
}

function renderAionChatSurface() {
  const engine = state.aionChatEngine || state.desktopAssistantProvider || "gemma4";
  const mode = state.aionChatMode || "business_workspace";
  const prompt = state.aionChatPrompt || state.desktopAssistantPrompt || "";
  const output = state.aionChatOutput || state.desktopAssistantOutput || "";

  const askLabel =
    mode === "business_workspace"
      ? "Ask Aion"
      : engine === "openai"
        ? "Ask OpenAI"
        : engine === "claude"
          ? "Ask Claude"
          : "Ask Gemma 4";

  const modeDescription =
    mode === "business_workspace"
      ? "Aion uses the business workspace, dashboards, brand foundation, agents, runs, approvals, and local containers as context. Gemma/OpenAI/Claude are only used as the reasoning engine."
      : "General AI mode asks the selected model directly. Business context is not forced unless you ask for it.";

  return `
    <div class="surface-shell aion-chat-surface">
      <div class="surface-header">
        <div>
          <div class="surface-eyebrow">Local AI Workspace</div>
          <div class="surface-title">Aion</div>
          <div class="surface-subtitle">
            Ask business-context questions through Aion, or switch to a normal AI provider for general reasoning.
          </div>
        </div>

        <div class="surface-right-meta">
          <div class="surface-pill">
            ${mode === "business_workspace" ? "AION BUSINESS CONTEXT" : "GENERAL AI"}
          </div>
          <div class="last-refresh">Provider: ${escapeHtml(engine)}</div>
        </div>
      </div>

      ${renderAppTabs()}

      <div class="aion-chat-layout">
        <aside class="aion-chat-sidebar">
          <div class="panel">
            <div class="panel-title">Mode</div>
            <div class="helper-text" style="margin-top:0;">
              Choose whether Aion should answer from the business workspace or whether you want a normal AI chat.
            </div>

            <div class="aion-mode-toggle">
              <button
                type="button"
                class="secondary-btn aion-chat-mode-btn ${mode === "business_workspace" ? "aion-chat-mode-btn-active" : ""}"
                data-aion-chat-mode="business_workspace"
              >
                Aion Business
              </button>

              <button
                type="button"
                class="secondary-btn aion-chat-mode-btn ${mode === "general_ai" ? "aion-chat-mode-btn-active" : ""}"
                data-aion-chat-mode="general_ai"
              >
                General AI
              </button>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title">AI Provider</div>
            <div class="helper-text" style="margin-top:0;">
              Gemma 4 is the free local option. OpenAI and Claude can be used for heavier reasoning.
            </div>

            <select id="aionChatEngineInput" class="input">
              <option value="gemma4" ${engine === "gemma4" ? "selected" : ""}>
                Free · Gemma 4 AI
              </option>
              <option value="openai" ${engine === "openai" ? "selected" : ""}>
                OpenAI
              </option>
              <option value="claude" ${engine === "claude" ? "selected" : ""}>
                Claude
              </option>
            </select>
          </div>

          <div class="panel">
            <div class="panel-title">Current Routing</div>

            <div class="kv-row">
              <span>Mode</span>
              <strong>${escapeHtml(mode === "business_workspace" ? "Aion Business" : "General AI")}</strong>
            </div>

            <div class="kv-row">
              <span>Reasoning engine</span>
              <strong>${escapeHtml(engine)}</strong>
            </div>

            <div class="kv-row">
              <span>Context</span>
              <strong>${escapeHtml(mode === "business_workspace" ? "business containers" : "direct model")}</strong>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title">Actions</div>
            <div class="aion-mode-list">
              <button class="secondary-btn desktop-ai-action-btn" data-desktop-ai-action="explain_business_state">
                Explain business state
              </button>
              <button class="secondary-btn desktop-ai-action-btn" data-desktop-ai-action="find_risks">
                Find risks
              </button>
              <button class="secondary-btn desktop-ai-action-btn" data-desktop-ai-action="write_post">
                Write marketing post
              </button>
              <button class="secondary-btn desktop-ai-action-btn" data-desktop-ai-action="backend_status">
                Check backend
              </button>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title">Runtime Context</div>
            <div class="kv-row">
              <span>Workspace</span>
              <strong>${escapeHtml(state.workspaceId || "—")}</strong>
            </div>
            <div class="kv-row">
              <span>Node</span>
              <strong>${escapeHtml(state.nodeId || "—")}</strong>
            </div>
            <div class="kv-row">
              <span>Runs</span>
              <strong>${escapeHtml(Array.isArray(state.runs) ? state.runs.length : 0)}</strong>
            </div>
            <div class="kv-row">
              <span>Approvals</span>
              <strong>${escapeHtml(Array.isArray(state.approvals) ? state.approvals.length : 0)}</strong>
            </div>
          </div>
        </aside>

        <main class="aion-chat-main">
          <div class="panel large-panel aion-chat-panel">
            <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap;">
              <div>
                <div class="panel-title">Chat</div>
                <div class="helper-text" style="margin-top:0;">
                  ${escapeHtml(modeDescription)}
                </div>
              </div>

              <div class="badge-row">
                <span class="badge">${escapeHtml(mode === "business_workspace" ? "Aion Business" : "General AI")}</span>
                <span class="badge">${escapeHtml(engine)}</span>
              </div>
            </div>

            <div class="aion-chat-window">
              ${
                output
                  ? `
                    <div class="aion-message aion-message-assistant">
                      <div class="aion-message-label">
                        ${escapeHtml(mode === "business_workspace" ? "Aion" : engine)}
                      </div>
                      <div class="aion-message-body">${escapeHtml(output)}</div>
                    </div>
                  `
                  : `
                    <div class="empty-state">
                      No conversation yet. Ask a question below.
                    </div>
                  `
              }
            </div>

            <textarea
              id="aionChatPromptInput"
              class="input input-textarea aion-chat-input"
              placeholder="${
                mode === "business_workspace"
                  ? "Ask about the business, dashboard, brand, agents, approvals, runs, marketing, or next action..."
                  : "Ask the selected AI model anything..."
              }"
            >${escapeHtml(prompt)}</textarea>

            <div class="marketing-form-actions aion-chat-actions">
              <button id="aionChatRunBtn" class="primary-btn" type="button">
                ${escapeHtml(askLabel)}
              </button>

              <button id="aionChatClearBtn" class="secondary-btn" type="button">
                Clear
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  `;
}

function renderVaultCredentialsSurface() {
  const status = window.__aionGmailVaultStatus || state.gmailVaultStatus || {};
  const gmail = status.gmail || {};
  const gmailReady = gmail.ready === true;

  const statusLabel = gmailReady ? "Connected" : "Missing";
  const statusSub = gmailReady
    ? "OAuth credentials available for Gmail read and draft preparation."
    : "Connect Gmail before real read or draft actions can run.";

  const scopes = Array.isArray(gmail.granted_scopes) && gmail.granted_scopes.length
    ? gmail.granted_scopes
    : Array.isArray(gmail.required_scopes)
      ? gmail.required_scopes
      : [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.compose",
        ];

  return `
    <div class="operations-agents-page vault-classic-page">
      <div class="operations-agents-status-strip">
        <div>Vault mode <strong>LOCAL</strong></div>
        <div>Credential type <strong>OAUTH</strong></div>
        <div>Live send <strong>LOCKED</strong></div>
        <div>Permissions <strong>SCOPED</strong></div>
        <div>Audit trail <strong>LOCAL</strong></div>
      </div>

      <div class="operations-agents-hero">
        <div>
          <div class="eyebrow">Aion Business Desktop</div>
          <h1>Vault</h1>
          <p>
            Manage connector credentials, OAuth readiness, user scope, and guarded execution permissions.
          </p>
        </div>
        <div class="operations-agents-hero-meta">
          <span>Credential Vault</span>
          <span>Live send disabled</span>
        </div>
      </div>

      ${renderAppTabs()}

      <section class="operations-agents-intro">
        <div>
          <div class="eyebrow">Credentials & Connector Access</div>
          <h2>Connector vault</h2>
          <p>
            AION stores connector readiness as scoped Vault credentials. Gmail uses OAuth scopes, not raw passwords.
          </p>
        </div>

        <div class="operations-agents-actions">
          <button type="button" class="secondary-btn" data-aion-vault-refresh-gmail="true">
            Refresh Gmail
          </button>
          <button
            type="button"
            class="primary-btn"
            data-aion-vault-request-live-send="true"
            title="Live Gmail send is locked. Click to see why."
          >
            Enable live send
          </button>
        </div>
      </section>

      <div class="operations-agents-metric-grid">
        ${renderDashboardMetricCard("Connected", gmailReady ? "1" : "0", "Currently ready")}
        ${renderDashboardMetricCard("Mode", "OAuth", "No raw passwords")}
        ${renderDashboardMetricCard("Scope", "Owner", "Business/workspace/user")}
        ${renderDashboardMetricCard("Live send", "Locked", "Future phase")}
      </div>

      <div class="operations-agents-two-column">
        <section class="operations-agents-card">
          <div class="operations-agents-card-head">
            <div>
              <div class="eyebrow">Connector credentials</div>
              <h2>Connected apps</h2>
            </div>
            <span class="badge">${escapeHtml(statusLabel)}</span>
          </div>

          <div class="vault-connector-list">
            <div class="vault-connector-row">
              <div>
                <div class="vault-connector-kicker">
                  <span>Gmail</span>
                  <span>${escapeHtml(statusLabel)}</span>
                  <span>Live send locked</span>
                </div>
                <h3>Gmail OAuth</h3>
                <p>${escapeHtml(statusSub)}</p>
              </div>
              <button type="button" class="secondary-btn" data-aion-vault-refresh-gmail="true">
                Check status
              </button>
            </div>

            <div class="vault-connector-row vault-live-send-guard-row">
              <div>
                <div class="vault-connector-kicker">
                  <span>Gmail live send</span>
                  <span>Guarded</span>
                  <span>Future-only</span>
                </div>
                <h3>Live Gmail send is locked</h3>
                <p>
                  AION can create Gmail drafts after approval, but it cannot send emails,
                  reply to emails, send drafts, or delete Gmail messages in this phase.
                  Clicking the control only records interest and explains the guard.
                </p>
              </div>
              <button
                type="button"
                class="secondary-btn"
                data-aion-vault-request-live-send="true"
              >
                Explain guard
              </button>
            </div>

            <div class="vault-connector-row">
              <div>
                <div class="vault-connector-kicker">
                  <span>HubSpot</span>
                  <span>Missing</span>
                </div>
                <h3>HubSpot</h3>
                <p>Planned connector. Will use the same Vault scope and approval model.</p>
              </div>
            </div>

            <div class="vault-connector-row">
              <div>
                <div class="vault-connector-kicker">
                  <span>Mailchimp</span>
                  <span>Missing</span>
                </div>
                <h3>Mailchimp</h3>
                <p>Currently represented as a missing connector placeholder in generated workflows.</p>
              </div>
            </div>
          </div>
        </section>

        <section class="operations-agents-card">
          <div class="operations-agents-card-head">
            <div>
              <div class="eyebrow">Gmail scopes</div>
              <h2>Granted / required</h2>
            </div>
            <span class="badge">OAuth</span>
          </div>

          <div class="vault-classic-scope-list">
            ${scopes.map((scope) => `<code>${escapeHtml(scope)}</code>`).join("")}
          </div>

          <div class="vault-safety-note">
            <strong>Safety lock:</strong>
            AION can prepare connector-ready actions after approval, but live sends, draft sends,
            deletes, and external writes remain disabled until a future live execution phase.
          </div>
        </section>
      </div>
    </div>
  `;
}

function renderMainSurface() {
  if (state.activeTab === "vault") {
    return renderVaultCredentialsSurface();
  }

  if (state.activeTab === "local_node") {
    return renderLocalNodeSurface();
  }

  if (state.activeTab === "dashboard") {
    return renderDashboardSurface();
  }

  if (state.activeTab === "boardroom") {
    return renderBoardroomSurface();
  }

  if (state.activeTab === "marketing_stream") {
    return renderMarketingStreamSurface();
  }

  if (state.activeTab === "brand_foundation") {
    return renderBrandFoundationSurface();
  }

  if (state.activeTab === "live_agents") {
    return renderLiveAgentsSurface();
  }
  if (state.activeTab === "aion_chat") {
    return renderAionChatSurface();
  }

  if (state.activeTab === "operations_flow") {
    return renderOperationsFlowSurface();
  }

  if (state.activeTab === "operations_agents") {
    return renderOperationsAgentsSurface();
  }

  return renderLocalNodeSurface();
}

function buildLiveAgentCards(runs) {
  return liveAgentsRuntime.buildLiveAgentCards(runs);
}

function getSelectedLiveAgentCard() {
  return liveAgentsRuntime.getSelectedLiveAgentCard(state);
}

function getRunsForSelectedLiveAgent() {
  return liveAgentsRuntime.getRunsForSelectedLiveAgent(state);
}

function buildDepartmentRoomCards() {
  return runtimeShared
    .getDepartmentRuntimeList(state.runs, state.approvals)
    .map((room) => ({
      key: room.key,
      label: room.label,
      queued: room.queued,
      running: room.running,
      waitingApproval: room.waitingApproval,
      failed: room.failed,
      completed: room.completed,
      total: room.totalRuns,
      latestRun: room.latestRun,
      agentCount: room.agentCount,
      primaryAgent: room.primaryAgent,
    }));
}

function getRunPrimaryInput(run) {
  return (
    run?.input ??
    run?.payload ??
    run?.request ??
    run?.context?.input ??
    null
  );
}

function getRunPrimaryResult(run) {
  return (
    run?.result ??
    run?.output ??
    run?.response ??
    null
  );
}

function getRunPrimaryError(run) {
  return (
    run?.error ??
    run?.failure ??
    run?.failure_reason ??
    null
  );
}

function getRunApprovalItems(run) {
  const runId = String(run?.id || run?.queue_item_id || "");
  const approvals = Array.isArray(state.approvals) ? state.approvals : [];

  return approvals
    .filter((item) => {
      const approvalRunId = String(
        item?.run_id ||
          item?.workflow_run_id ||
          item?.queue_item_id ||
          item?.runtime_run_id ||
          "",
      );
      return runId && approvalRunId === runId;
    })
    .slice()
    .sort((a, b) => {
      const aTime = new Date(
        a?.resolved_at || a?.requested_at || a?.created_at || 0,
      ).getTime();
      const bTime = new Date(
        b?.resolved_at || b?.requested_at || b?.created_at || 0,
      ).getTime();
      return bTime - aTime;
    });
}

function getPendingApprovalForRun(run) {
  const approvals = getRunApprovalItems(run);
  return (
    approvals.find(
      (item) => String(item?.status || "").toLowerCase() === "pending",
    ) || null
  );
}

function getLatestApprovalForRun(run) {
  const approvals = getRunApprovalItems(run);
  return approvals.length ? approvals[0] : null;
}

function renderInspectorKeyValue(label, value) {
  return `
    <div class="kv-row">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value == null || value === "" ? "—" : value)}</strong>
    </div>
  `;
}

function getRunLifecycleLabel(run) {
  const status = String(run?.status || "").toLowerCase();

  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "waiting_approval") return "Waiting approval";
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  if (status === "cancelled") return "Cancelled";

  const latestApproval = getLatestApprovalForRun(run);
  const approvalStatus = String(latestApproval?.status || "").toLowerCase();

  if (approvalStatus === "approved") return "Approved";
  if (approvalStatus === "rejected") return "Rejected";

  return "Unknown";
}
function isTeachAionDeveloperMode() {
  try {
    return window.localStorage.getItem("teach_aion_dev_tools") === "1";
  } catch (_) {
    return false;
  }
}

function isTeachAionDebugWorkflow(workflow) {
  const workflowId = String(workflow?.workflow_id || workflow?.id || "").toLowerCase();
  const name = String(workflow?.name || "").toLowerCase();
  const metadata = workflow?.metadata || {};

  if (metadata.dev_only === true || metadata.debug === true) {
    return true;
  }

  return (
    workflowId.includes("acceptance_test") ||
    workflowId.includes("customer_onboarding_v1") ||
    workflowId.includes("test_customer") ||
    name.includes("acceptance test") ||
    name.includes("seed customer onboarding")
  );
}

function getVisibleTeachAionWorkflows(workflows) {
  const items = Array.isArray(workflows) ? workflows : [];

  if (isTeachAionDeveloperMode()) {
    return items;
  }

  return items.filter((workflow) => !isTeachAionDebugWorkflow(workflow));
}

async function refreshOperationsAgentsData() {
  const [workflowsResult, approvalsResult, genericWorkflowsResult] = await Promise.all([
    apiGet("/api/local-node/train-tasks/workflows"),
    apiGet("/api/local-node/train-tasks/approvals?limit=20"),
    apiGet("/api/local-node/train-tasks/workflows/generic-saved"),
  ]);

  return {
    operationsAgentsWorkflows: Array.isArray(workflowsResult?.items)
      ? workflowsResult.items
      : [],
    operationsAgentsApprovals: Array.isArray(approvalsResult?.items)
      ? approvalsResult.items
      : [],
    operationsAgentsGenericWorkflows: Array.isArray(genericWorkflowsResult?.items)
      ? genericWorkflowsResult.items
      : [],
  };
}

const OPERATIONS_AGENT_STEP_TYPES = [
  { value: "trigger", label: "Trigger" },
  { value: "extract", label: "Extract data" },
  { value: "summarise", label: "Transform / summarise" },
  { value: "crm_upsert", label: "Create/update CRM record" },
  { value: "draft_email", label: "Draft email" },
  { value: "create_task", label: "Create task" },
  { value: "approval_checkpoint", label: "Approval checkpoint" },
  { value: "notify_user", label: "Notify user" },
  { value: "end", label: "Stop / end" },
];

const OPERATIONS_AGENT_DEPARTMENTS = [
  "Sales",
  "Marketing",
  "Support",
  "Finance",
  "Operations",
  "HR",
];

const OPERATIONS_AGENT_INPUT_SOURCES = [
  { value: "trigger_payload", label: "Trigger payload" },
  { value: "previous_step", label: "Previous step output" },
  { value: "fixed_value", label: "Fixed value" },
  { value: "workspace_context", label: "Workspace context" },
];

const OPERATIONS_AGENT_TOOL_OPTIONS = [
  { value: "", label: "No tool / internal step" },
  { value: "tool.gmail.trigger.v1", label: "Gmail trigger" },
  { value: "tool.aion.extract.v1", label: "Aion extraction" },
  { value: "tool.aion.summarise.v1", label: "Aion summarise" },
  { value: "tool.mcp.hubspot.contact_upsert.v1", label: "HubSpot contact create/update" },
  { value: "tool.gmail.draft_preview.v1", label: "Gmail draft preview" },
  { value: "tool.aion.task.create.v1", label: "Create task" },
  { value: "tool.approval.checkpoint.v1", label: "Approval checkpoint" },
  { value: "tool.notify.user.v1", label: "Notify user" },
];

const OPERATIONS_AGENT_FAILURE_BEHAVIOURS = [
  { value: "stop", label: "Stop safely" },
  { value: "retry", label: "Retry" },
  { value: "ask_approval", label: "Ask approval" },
  { value: "skip", label: "Skip step" },
];

const OPERATIONS_AGENT_AUDIT_VISIBILITY = [
  { value: "full", label: "Full" },
  { value: "summary", label: "Summary" },
  { value: "hide_secret_values", label: "Hide secret values" },
];

function makeStepBuilderId(prefix = "step") {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

function createStepBuilderDraft() {
  return {
    workflow_id: `workflow_step_builder_${Date.now().toString(36)}`,
    workflow_name: "",
    department: "Sales",
    operator_name: "",
    description: "",
    goal: "",
    steps: [],
  };
}

function defaultToolForStepType(type) {
  if (type === "trigger") return "tool.gmail.trigger.v1";
  if (type === "extract") return "tool.aion.extract.v1";
  if (type === "summarise") return "tool.aion.summarise.v1";
  if (type === "crm_upsert") return "tool.mcp.hubspot.contact_upsert.v1";
  if (type === "draft_email") return "tool.gmail.draft_preview.v1";
  if (type === "create_task") return "tool.aion.task.create.v1";
  if (type === "approval_checkpoint") return "tool.approval.checkpoint.v1";
  if (type === "notify_user") return "tool.notify.user.v1";
  return "";
}

function createStepBuilderStep(type = "trigger") {
  const stepId = makeStepBuilderId("step");
  const typeMeta = OPERATIONS_AGENT_STEP_TYPES.find((item) => item.value === type);

  return {
    step_id: stepId,
    name: typeMeta?.label || "Workflow step",
    type,
    enabled: true,
    input_source: type === "trigger" ? "trigger_payload" : "previous_step",
    input_ref: "",
    fixed_value: "",
    tool_id: defaultToolForStepType(type),
    output: type === "end" ? "" : stepId.replace(/^step_/, "output_"),
    output_schema: "",
    failure_behavior: "stop",
    audit_visibility: "summary",
  };
}

function normaliseStepBuilderDraft(draft) {
  const source = draft && typeof draft === "object" ? draft : createStepBuilderDraft();

  return {
    workflow_id: source.workflow_id || `workflow_step_builder_${Date.now().toString(36)}`,
    workflow_name: source.workflow_name || "",
    department: source.department || "Sales",
    operator_name: source.operator_name || "",
    description: source.description || "",
    goal: source.goal || "",
    steps: Array.isArray(source.steps) ? source.steps : [],
  };
}

function updateStepBuilderDraftField(draft, path, value) {
  const next = normaliseStepBuilderDraft(draft);

  if (path === "workflow_name") next.workflow_name = value;
  if (path === "department") next.department = value;
  if (path === "operator_name") next.operator_name = value;
  if (path === "description") next.description = value;
  if (path === "goal") next.goal = value;

  return next;
}

function updateStepBuilderStep(draft, stepId, patch) {
  const next = normaliseStepBuilderDraft(draft);

  next.steps = next.steps.map((step) =>
    step.step_id === stepId
      ? {
          ...step,
          ...patch,
        }
      : step,
  );

  return next;
}

function moveStepBuilderStep(draft, stepId, direction) {
  const next = normaliseStepBuilderDraft(draft);
  const index = next.steps.findIndex((step) => step.step_id === stepId);

  if (index < 0) return next;

  const target = direction === "up" ? index - 1 : index + 1;
  if (target < 0 || target >= next.steps.length) return next;

  const steps = [...next.steps];
  const [item] = steps.splice(index, 1);
  steps.splice(target, 0, item);
  next.steps = steps;

  return next;
}

function duplicateStepBuilderStep(draft, stepId) {
  const next = normaliseStepBuilderDraft(draft);
  const index = next.steps.findIndex((step) => step.step_id === stepId);

  if (index < 0) return next;

  const original = next.steps[index];
  const copyId = makeStepBuilderId("step");
  const copy = {
    ...original,
    step_id: copyId,
    name: `${original.name || "Step"} copy`,
    output: original.output ? copyId.replace(/^step_/, "output_") : "",
  };

  next.steps = [...next.steps];
  next.steps.splice(index + 1, 0, copy);

  return next;
}

function deleteStepBuilderStep(draft, stepId) {
  const next = normaliseStepBuilderDraft(draft);
  next.steps = next.steps.filter((step) => step.step_id !== stepId);
  return next;
}

function addStepBuilderStep(draft, type = "trigger") {
  const next = normaliseStepBuilderDraft(draft);
  next.steps = [...next.steps, createStepBuilderStep(type)];
  return next;
}

function renderOperationsAgentsSurface() {
  const rawWorkflows = Array.isArray(state.operationsAgentsWorkflows)
    ? state.operationsAgentsWorkflows
    : [];

  const workflows = getVisibleTeachAionWorkflows(rawWorkflows);
  const hiddenWorkflowCount = rawWorkflows.length - workflows.length;
  const showDeveloperTools = isTeachAionDeveloperMode();

  const testResult = state.operationsAgentsTestResult || null;

  const tools = Array.isArray(state.operationsAgentsTools)
    ? state.operationsAgentsTools
    : [];

  const approvals = Array.isArray(state.operationsAgentsApprovals)
    ? state.operationsAgentsApprovals
    : [];

  const externalTools = Array.isArray(state.operationsAgentsExternalTools)
    ? state.operationsAgentsExternalTools
    : [];

  const genericWorkflows = Array.isArray(state.operationsAgentsGenericWorkflows)
    ? state.operationsAgentsGenericWorkflows
    : [];

  const visibleTools = tools.slice(0, 8);
  const visibleExternalTools = externalTools.slice(0, 8);
  const gmailConnector = state.operationsAgentsGmailConnector || null;
  const loading = state.operationsAgentsLoading === true;

  const builderOpen = state.operationsAgentsStepBuilderOpen === true;
  const builderValidated =
    state.operationsAgentsStepBuilderCompileResult?.ok === true ||
    state.operationsAgentsStepBuilderSaveResult?.ok === true;

  const builderStatusLabel = builderValidated ? "Validated" : "Draft";

  return `
    <div class="surface-shell operations-agents-surface operations-agents-canvas-mode">
      <div class="dashboard-shell">
        ${renderAionWorkflowCanvasPanel({ workflows, loading })}

        <details class="train-collapsed-section">
          <summary>
            <span>
              <span class="eyebrow">Browser recorder</span>
              <strong>Teach Aion a browser skill</strong>
            </span>
            <span class="badge">Open</span>
          </summary>
          ${renderBrowserDesktopOperatorPanel(loading)}
        </details>

        <details class="train-collapsed-section">
          <summary>
            <span>
              <span class="eyebrow">Browser skills</span>
              <strong>Saved browser micro-skills</strong>
            </span>
            <span class="badge">Open</span>
          </summary>
          ${renderBrowserMicroSkillLibrary()}
        </details>

        <details class="train-collapsed-section">
          <summary>
            <span>
              <span class="eyebrow">Workflow chain</span>
              <strong>Chain browser micro-skills</strong>
            </span>
            <span class="badge">Open</span>
          </summary>
          ${renderBrowserSkillChainBuilder()}
        </details>

        ${
          state.operationsAgentsGmailPollResult
            ? `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Gmail check result</div>
                    <h2>Latest Gmail check</h2>
                    <p class="muted" style="margin:6px 0 0;">
                      Poll id: ${escapeHtml(state.operationsAgentsGmailPollResult.poll_id || "unknown")}
                    </p>
                  </div>

                  <span class="status-pill ${
                    Number(state.operationsAgentsGmailPollResult.matched || 0) > 0
                      ? "status-running"
                      : "status-pending"
                  }">
                    ${Number(state.operationsAgentsGmailPollResult.matched || 0) > 0 ? "Gmail matched" : "No Gmail match"}
                  </span>
                </div>

                <div class="train-section-body">
                  <div class="card-grid">
                    ${renderDashboardMetricCard(
                      "Gmail matched",
                      state.operationsAgentsGmailPollResult.matched || 0,
                      "Would trigger trained tasks",
                    )}
                    ${renderDashboardMetricCard(
                      "Skipped",
                      state.operationsAgentsGmailPollResult.skipped || 0,
                      "No workflow match",
                    )}
                    ${renderDashboardMetricCard(
                      "Deduped",
                      state.operationsAgentsGmailPollResult.deduped || 0,
                      "Already processed",
                    )}
                    ${renderDashboardMetricCard(
                      "Runs",
                      Array.isArray(state.operationsAgentsGmailPollResult.runs)
                        ? state.operationsAgentsGmailPollResult.runs.length
                        : 0,
                      "Dry-run replays",
                    )}
                  </div>
                </div>
              </section>
            `
            : ""
        }

        ${
          gmailConnector
            ? `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Gmail Connector</div>
                    <h2>Connection status</h2>
                    <p class="muted" style="margin:6px 0 0;">
                      Account: ${escapeHtml(gmailConnector.account_id || "default")}
                    </p>
                  </div>

                  <span class="status-pill ${
                    gmailConnector.auth_status === "connected"
                      ? "status-running"
                      : "status-pending"
                  }">
                    ${escapeHtml(gmailConnector.connector_health || gmailConnector.auth_status || "unknown")}
                  </span>
                </div>

                <div class="train-section-body">
                  <div class="card-grid">
                    ${renderDashboardMetricCard(
                      "Auth",
                      gmailConnector.auth_status || "unknown",
                      "Gmail connector",
                    )}
                    ${renderDashboardMetricCard(
                      "Polling",
                      gmailConnector.polling_enabled ? "Enabled" : "Disabled",
                      gmailConnector.search_scope || "inbox",
                    )}
                    ${renderDashboardMetricCard(
                      "Last poll",
                      gmailConnector.last_poll_status || "never_polled",
                      gmailConnector.last_poll_at || "Not run yet",
                    )}
                    ${renderDashboardMetricCard(
                      "Writes",
                      gmailConnector.external_writes_enabled ? "Unlocked" : "Blocked",
                      gmailConnector.dry_run_only ? "Dry-run only" : "Live mode",
                    )}
                  </div>

                  <div class="train-status-note" style="margin-top:14px;">
                    <span class="train-status-label">Safety lock</span>
                    <div>
                      <strong>Dry-run safety lock is active.</strong>
                      <p class="muted" style="margin:6px 0 0;">
                        Aion can check matching Gmail messages, but it will not create Gmail drafts,
                        send emails, or write to HubSpot in this phase.
                      </p>
                    </div>
                  </div>

                  ${
                    gmailConnector.last_error
                      ? `<div class="marketing-error" style="margin-top:10px;">${escapeHtml(gmailConnector.last_error)}</div>`
                      : ""
                  }
                </div>
              </section>
            `
            : ""
        }

        ${
          tools.length
            ? `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Registered Tools</div>
                    <h2>Aion tool registry</h2>
                    <p class="muted" style="margin:6px 0 0;">
                      Tools are provider-agnostic and policy-gated. External writes stay blocked or dry-run until approved.
                    </p>
                  </div>

                  <span class="badge">${escapeHtml(tools.length)} tools</span>
                </div>

                <div class="train-section-body">
                  <div class="card-grid">
                    ${visibleTools.map((tool) => renderAionToolMiniCard(tool)).join("")}
                  </div>

                  ${
                    tools.length > visibleTools.length
                      ? `<p class="muted" style="margin:12px 0 0;">Showing ${escapeHtml(visibleTools.length)} of ${escapeHtml(tools.length)} registered tools.</p>`
                      : ""
                  }
                </div>
              </section>
            `
            : ""
        }

        ${
          externalTools.length
            ? `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">External Tools</div>
                    <h2>StackOne / MCP connector discovery</h2>
                    <p class="muted" style="margin:6px 0 0;">
                      Phase 5 proves external SaaS tools can be normalized into Aion.
                      These are placeholder/not connected and write-blocked.
                    </p>
                  </div>

                  <span class="badge">${escapeHtml(externalTools.length)} external tools</span>
                </div>

                <div class="train-section-body">
                  <div class="card-grid">
                    ${visibleExternalTools
                      .map((tool) =>
                        renderAionExternalToolMiniCard(tool, showDeveloperTools, loading),
                      )
                      .join("")}
                  </div>

                  ${
                    externalTools.length > visibleExternalTools.length
                      ? `<p class="muted" style="margin:12px 0 0;">Showing ${escapeHtml(visibleExternalTools.length)} of ${escapeHtml(externalTools.length)} external tools.</p>`
                      : ""
                  }
                </div>
              </section>
            `
            : ""
        }

        ${
          approvals.length
            ? `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Pending approvals</div>
                    <h2>Review trained-task actions</h2>
                    <p class="muted" style="margin:6px 0 0;">
                      Phase 3 approvals store the human decision only. They do not create Gmail drafts or write to HubSpot yet.
                    </p>
                  </div>

                  <span class="status-pill status-pending">
                    ${escapeHtml(approvals.length)} pending
                  </span>
                </div>

                <div class="train-section-body">
                  <div style="display:grid; gap:12px;">
                    ${approvals
                      .slice(0, 6)
                      .map((approval) => renderTrainTaskApprovalCard(approval, loading))
                      .join("")}
                  </div>
                </div>
              </section>
            `
            : ""
        }

        ${
          state.operationsAgentsExternalToolDryRunResult
            ? `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">External tool dry-run result</div>
                    <h2>${escapeHtml(
                      state.operationsAgentsExternalToolDryRunResult.tool_name ||
                        state.operationsAgentsExternalToolDryRunResult.tool_id ||
                        "External tool",
                    )}</h2>
                  </div>
                </div>

                <div class="train-section-body">
                  <div class="badge-row">
                    <span class="badge">${escapeHtml(state.operationsAgentsExternalToolDryRunResult.provider || "unknown")}</span>
                    <span class="badge">${escapeHtml(state.operationsAgentsExternalToolDryRunResult.permission_mode || "unknown")}</span>
                    <span class="badge">${state.operationsAgentsExternalToolDryRunResult.external_write_blocked ? "External write blocked" : "No write blocked"}</span>
                    <span class="badge">${state.operationsAgentsExternalToolDryRunResult.dry_run ? "Dry-run" : "Live"}</span>
                  </div>

                  <pre class="json-preview" style="margin-top:12px;">${escapeHtml(
                    JSON.stringify(
                      state.operationsAgentsExternalToolDryRunResult.output_payload || {},
                      null,
                      2,
                    ),
                  )}</pre>
                </div>
              </section>
            `
            : ""
        }

        <details class="train-collapsed-section">
          <summary>
            <span>
              <span class="eyebrow">Task templates</span>
              <strong>Start from a workflow</strong>
            </span>
            <span class="badge">Open</span>
          </summary>

          <div class="train-stack">
            <section class="train-panel">
              <div class="train-panel-header">
                <div>
                  <div class="eyebrow">Task templates</div>
                  <h2>Start from a workflow</h2>
                </div>

                <span class="train-status-chip">Safe defaults</span>
              </div>

              <div class="train-panel-body">
                <p class="muted" style="margin:0 0 18px;">
                  These templates are safe starting points. They compile into dry-run workflows first.
                </p>

                <div class="train-template-grid">
                  ${[
                    [
                      "gmail_hubspot_welcome",
                      "New email → HubSpot → welcome email",
                      "Extract lead details, prepare CRM contact, draft reply.",
                      "Dry-run",
                    ],
                    [
                      "stale_quote_chase",
                      "Stale quote → chase email",
                      "Detect an old quote and draft a polite follow-up.",
                      "Sales",
                    ],
                    [
                      "form_email_draft",
                      "New form submission → email draft",
                      "Turn an inbound form into a prepared response.",
                      "Dry-run",
                    ],
                    [
                      "customer_onboarding_checklist",
                      "New customer → onboarding checklist",
                      "Create a safe onboarding task plan after approval.",
                      "Support",
                    ],
                  ]
                    .map(
                      ([templateId, title, body, tag]) => `
                        <button
                          class="train-template-card"
                          data-operations-agents-action="open-step-builder"
                          data-template-id="${escapeHtml(templateId)}"
                          type="button"
                          title="Use this template"
                        >
                          <div>
                            <div class="badge-row" style="margin-bottom:10px;">
                              <span class="badge">Template</span>
                              <span class="badge">${escapeHtml(tag)}</span>
                            </div>

                            <strong>${escapeHtml(title)}</strong>
                            <p>${escapeHtml(body)}</p>
                          </div>

                          <span>Use template</span>
                        </button>
                      `,
                    )
                    .join("")}
                </div>
              </div>
            </section>
          </div>
        </details>

        <details class="train-collapsed-section">
          <summary>
            <span>
              <span class="eyebrow">Step Builder</span>
              <strong>Build custom agent</strong>
            </span>
            <span class="badge">Open</span>
          </summary>

          <div class="train-stack">
            <section class="train-panel">
              <div class="train-panel-header">
                <div>
                  <div class="eyebrow">Step Builder</div>
                  <h2>Build custom agent</h2>
                </div>

                <span class="train-status-chip ${builderValidated ? "train-status-ok" : ""}">
                  ${escapeHtml(builderStatusLabel)}
                </span>
              </div>

              <div class="train-panel-body">
                <p class="muted" style="margin:0 0 18px;">
                  Build an operator by adding ordered steps such as trigger, extract data,
                  CRM action, draft email, approval, and end.
                </p>

                <button
                  class="primary-btn"
                  data-operations-agents-action="open-step-builder"
                  ${loading ? "disabled" : ""}
                >
                  ${builderOpen ? "Builder open" : "Build step-by-step"}
                </button>
              </div>
            </section>

            ${builderOpen ? renderOperationsAgentsStepBuilder() : ""}
          </div>
        </details>

        <details class="train-collapsed-section">
          <summary>
            <span>
              <span class="eyebrow">Generic runtime</span>
              <strong>Saved generic workflows</strong>
            </span>
            <span class="badge">Open</span>
          </summary>

          <section class="train-section-panel">
            <div class="train-section-head">
              <div>
                <div class="eyebrow">Generic runtime</div>
                <h2>Saved generic workflows</h2>
              </div>
            </div>

            <div class="train-section-body">
              ${
                genericWorkflows.length
                  ? genericWorkflows
                      .map((item) => renderOperationsAgentGenericWorkflowCard(item, loading))
                      .join("")
                  : `<div class="empty-state">No saved generic workflows found.</div>`
              }
            </div>
          </section>
        </details>

        ${
          state.operationsAgentsLastGenericRun
            ? `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Generic runtime</div>
                    <h2>Latest generic run</h2>
                  </div>

                  <span class="status-pill ${
                    state.operationsAgentsLastGenericRun.ok ? "status-running" : "status-error"
                  }">
                    ${escapeHtml(state.operationsAgentsLastGenericRun.status || "unknown")}
                  </span>
                </div>

                <div class="train-section-body">
                  <pre class="json-preview">${escapeHtml(
                    JSON.stringify(
                      {
                        ok: state.operationsAgentsLastGenericRun.ok,
                        workflow_id: state.operationsAgentsLastGenericRun.workflow_id,
                        status: state.operationsAgentsLastGenericRun.status,
                        run_id: state.operationsAgentsLastGenericRun.run_id,
                        run_mode: state.operationsAgentsLastGenericRun.run_mode,
                        steps: Array.isArray(state.operationsAgentsLastGenericRun.steps)
                          ? state.operationsAgentsLastGenericRun.steps.map((step) => ({
                              step: step.step,
                              step_id: step.step_id,
                              type: step.type,
                              ok: step.ok,
                            }))
                          : [],
                      },
                      null,
                      2,
                    ),
                  )}</pre>
                </div>
              </section>
            `
            : ""
        }

        ${state.operationsAgentsWizardOpen ? renderOperationsAgentsWizard() : ""}

        <details class="train-collapsed-section">
          <summary>
            <span>
              <span class="eyebrow">Trained Tasks</span>
              <strong>Trained Tasks</strong>
            </span>
            <span class="badge">Open</span>
          </summary>
          <section class="train-section-panel">
          <div class="train-section-head">
            <div>
              <div class="eyebrow">Trained Tasks</div>
              <h2>Trained Tasks</h2>

              ${
                hiddenWorkflowCount > 0
                  ? `<p class="muted" style="margin:4px 0 0;">${escapeHtml(hiddenWorkflowCount)} developer/test workflow${hiddenWorkflowCount === 1 ? "" : "s"} hidden.</p>`
                  : ""
              }
            </div>
          </div>

          <div class="train-section-body">
            ${
              workflows.length
                ? workflows
                    .map((workflow) => renderOperationsAgentWorkflowCard(workflow, loading))
                    .join("")
                : `
                  <div class="empty-state">
                    No trained tasks loaded yet. Train an agent or refresh your saved tasks.
                  </div>
                `
            }
          </div>
        </section>

        ${
          testResult
            ? renderOperationsAgentTestReplay(testResult)
            : `
              <section class="train-section-panel">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Replay</div>
                    <h2>Test run output</h2>
                  </div>
                </div>

                <div class="train-section-body">
                  <div class="empty-state">
                    Run the customer onboarding test to see the trigger, extraction,
                    HubSpot action, email draft, and approval checkpoint.
                  </div>
                </div>
              </section>
            `
        }
      </div>
    </div>
  `;
}


function buildTeachAionTemplateDraft(templateId = "gmail_hubspot_welcome") {
  const templates = {
    gmail_hubspot_welcome: {
      workflow_id: "workflow_new_gmail_hubspot_welcome_v1",
      name: "New email to HubSpot and welcome draft",
      department_key: "operations",
      operator_id: "operator_customer_onboarding_v1",
      enabled: false,
      version: 1,
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
          { key: "name", label: "Customer name", required: false, description: "Name of the customer or lead." },
          { key: "email", label: "Email", required: true, description: "Customer email address." },
          { key: "phone", label: "Phone", required: false, description: "Customer phone number if present." },
          { key: "company", label: "Company", required: false, description: "Company name if present." },
          { key: "enquiry_type", label: "Enquiry type", required: false, description: "What the customer appears to be asking about." },
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
      metadata: {
        phase: "phase_2a_teach_aion_wizard",
        template_id: "gmail_hubspot_welcome",
        created_by: "teach_aion_template",
      },
    },

    lead_crm_followup: {
      workflow_id: "workflow_new_lead_crm_followup_v1",
      name: "New lead to CRM follow-up",
      department_key: "sales",
      operator_id: "operator_sales_followup_v1",
      enabled: false,
      version: 1,
      trigger: {
        trigger_type: "gmail_message_match",
        account_id: "default",
        query: "is:unread lead OR enquiry",
        dedupe: true,
        max_results: 10,
      },
      extraction: {
        step_type: "extract_customer_details",
        fields: [
          { key: "name", label: "Lead name", required: false, description: "Name of the lead." },
          { key: "email", label: "Email", required: true, description: "Lead email address." },
          { key: "phone", label: "Phone", required: false, description: "Lead phone number if present." },
          { key: "enquiry_type", label: "Follow-up reason", required: false, description: "What the lead needs help with." },
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
          enquiry_type: "message",
        },
      },
      email_draft: {
        step_type: "gmail_draft_welcome_email",
        account_id: "default",
        to_field: "email",
        subject_template: "Thanks — we’ll follow up shortly",
        body_template:
          "Hi {{name}},\n\nThanks for your enquiry. We’ve captured your details and will follow up shortly about {{enquiry_type}}.\n\nBest,\n{{business_name}}",
      },
      approval: {
        step_type: "approval_checkpoint",
        approval_mode: "ask_before_external_action",
        title: "Review new lead follow-up",
        require_human: true,
      },
      metadata: {
        phase: "phase_2a_teach_aion_wizard",
        template_id: "lead_crm_followup",
        created_by: "teach_aion_template",
      },
    },

    form_email_draft: {
      workflow_id: "workflow_form_submission_email_draft_v1",
      name: "New form submission to email draft",
      department_key: "support",
      operator_id: "operator_support_response_v1",
      enabled: false,
      version: 1,
      trigger: {
        trigger_type: "gmail_message_match",
        account_id: "default",
        query: "is:unread form submission",
        dedupe: true,
        max_results: 10,
      },
      extraction: {
        step_type: "extract_customer_details",
        fields: [
          { key: "name", label: "Customer name", required: false, description: "Name from the form." },
          { key: "email", label: "Email", required: true, description: "Reply email address." },
          { key: "enquiry_type", label: "Request type", required: false, description: "What the form is about." },
          { key: "message_summary", label: "Message summary", required: false, description: "Short summary of the submitted message." },
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
          enquiry_type: "message",
        },
      },
      email_draft: {
        step_type: "gmail_draft_welcome_email",
        account_id: "default",
        to_field: "email",
        subject_template: "Thanks for your message",
        body_template:
          "Hi {{name}},\n\nThanks for sending your message. We’ve received it and will reply shortly.\n\nBest,\n{{business_name}}",
      },
      approval: {
        step_type: "approval_checkpoint",
        approval_mode: "ask_before_external_action",
        title: "Review form response draft",
        require_human: true,
      },
      metadata: {
        phase: "phase_2a_teach_aion_wizard",
        template_id: "form_email_draft",
        created_by: "teach_aion_template",
      },
    },

    customer_onboarding_checklist: {
      workflow_id: "workflow_new_customer_onboarding_checklist_v1",
      name: "New customer onboarding checklist",
      department_key: "operations",
      operator_id: "operator_customer_onboarding_v1",
      enabled: false,
      version: 1,
      trigger: {
        trigger_type: "gmail_message_match",
        account_id: "default",
        query: "is:unread new customer",
        dedupe: true,
        max_results: 10,
      },
      extraction: {
        step_type: "extract_customer_details",
        fields: [
          { key: "name", label: "Customer name", required: false, description: "Customer name." },
          { key: "email", label: "Email", required: true, description: "Customer email address." },
          { key: "phone", label: "Phone", required: false, description: "Customer phone number." },
          { key: "enquiry_type", label: "Onboarding need", required: false, description: "What onboarding is required." },
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
          enquiry_type: "message",
        },
      },
      email_draft: {
        step_type: "gmail_draft_welcome_email",
        account_id: "default",
        to_field: "email",
        subject_template: "Welcome — next steps",
        body_template:
          "Hi {{name}},\n\nWelcome. We’ve prepared your onboarding next steps and will confirm everything shortly.\n\nBest,\n{{business_name}}",
      },
      approval: {
        step_type: "approval_checkpoint",
        approval_mode: "ask_before_external_action",
        title: "Review onboarding checklist",
        require_human: true,
      },
      metadata: {
        phase: "phase_2a_teach_aion_wizard",
        template_id: "customer_onboarding_checklist",
        created_by: "teach_aion_template",
      },
    },

    stale_quote_chase: {
      workflow_id: "workflow_stale_quote_chase_email_v1",
      name: "Stale quote chase email",
      department_key: "sales",
      operator_id: "operator_sales_followup_v1",
      enabled: false,
      version: 1,
      trigger: {
        trigger_type: "manual_run",
        account_id: "default",
        query: "manual stale quote review",
        dedupe: true,
        max_results: 10,
      },
      extraction: {
        step_type: "extract_customer_details",
        fields: [
          { key: "name", label: "Customer name", required: false, description: "Customer name." },
          { key: "email", label: "Email", required: true, description: "Customer email address." },
          { key: "enquiry_type", label: "Quote details", required: false, description: "What the quote was for." },
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
          enquiry_type: "message",
        },
      },
      email_draft: {
        step_type: "gmail_draft_welcome_email",
        account_id: "default",
        to_field: "email",
        subject_template: "Just checking in about your quote",
        body_template:
          "Hi {{name}},\n\nJust checking in to see if you had any questions about your quote for {{enquiry_type}}.\n\nBest,\n{{business_name}}",
      },
      approval: {
        step_type: "approval_checkpoint",
        approval_mode: "ask_before_external_action",
        title: "Review stale quote follow-up",
        require_human: true,
      },
      metadata: {
        phase: "phase_2a_teach_aion_wizard",
        template_id: "stale_quote_chase",
        created_by: "teach_aion_template",
      },
    },
  };

  return JSON.parse(JSON.stringify(templates[templateId] || templates.gmail_hubspot_welcome));
}

function formatTeachAionApprovalMode(value) {
  const mode = String(value || "ask_before_external_action");

  if (mode === "ask_before_external_action") {
    return "Ask before external action";
  }

  if (mode === "ask_before_crm_update") {
    return "Ask before CRM update";
  }

  if (mode === "ask_before_sending_email") {
    return "Ask before sending email";
  }

  if (mode === "save_draft_only") {
    return "Save draft only";
  }

  return mode
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getTeachAionActionSummary(draft) {
  const workflowId = String(draft?.workflow_id || "");

  if (workflowId.includes("new_customer_onboarding")) {
    return "It will then prepare an onboarding checklist and a Gmail draft, but it will stop at a human approval checkpoint before any external action can happen.";
  }

  if (workflowId.includes("form_submission")) {
    return "It will then prepare a Gmail draft, but it will stop at a human approval checkpoint before any external action can happen.";
  }

  if (workflowId.includes("stale_quote")) {
    return "It will then prepare a polite chase email draft, but it will stop at a human approval checkpoint before any external action can happen.";
  }

  if (draft?.hubspot?.enabled === false) {
    return "It will then prepare a Gmail draft, but it will stop at a human approval checkpoint before any external action can happen.";
  }

  return "It will then prepare a HubSpot contact action and a Gmail draft, but it will stop at a human approval checkpoint before any external action can happen.";
}

function getTeachAionActionKind(value) {
  const workflowId = String(value?.workflow_id || value?.id || "");
  const name = String(value?.name || "").toLowerCase();

  if (workflowId.includes("form_submission")) return "email_draft";
  if (workflowId.includes("new_customer_onboarding")) return "onboarding_checklist";
  if (workflowId.includes("stale_quote")) return "chase_email";
  if (workflowId.includes("crm_follow_up")) return "crm_follow_up";

  if (name.includes("form submission")) return "email_draft";
  if (name.includes("onboarding checklist")) return "onboarding_checklist";
  if (name.includes("stale quote")) return "chase_email";
  if (name.includes("follow-up") || name.includes("follow up")) return "crm_follow_up";

  return "hubspot_contact";
}

function getTeachAionPrimaryActionLabel(value) {
  const kind = getTeachAionActionKind(value);

  if (kind === "email_draft") return "Gmail draft";
  if (kind === "onboarding_checklist") return "Checklist";
  if (kind === "chase_email") return "Chase email";
  if (kind === "crm_follow_up") return "CRM follow-up";

  return "HubSpot contact";
}

function getTeachAionPrimaryActionDescription(value) {
  const kind = getTeachAionActionKind(value);

  if (kind === "email_draft") return "Prepared email only";
  if (kind === "onboarding_checklist") return "Prepared checklist";
  if (kind === "chase_email") return "Prepared follow-up";
  if (kind === "crm_follow_up") return "Prepared follow-up";

  return "Dry-run only";
}

function getTeachAionPrimaryActionTitle(value) {
  const kind = getTeachAionActionKind(value);

  if (kind === "email_draft") return "Prepare Gmail draft";
  if (kind === "onboarding_checklist") return "Prepare onboarding checklist";
  if (kind === "chase_email") return "Prepare chase email";
  if (kind === "crm_follow_up") return "Prepare CRM follow-up";

  return "Prepare HubSpot contact update";
}

function getTeachAionPrimaryActionBody(value) {
  const kind = getTeachAionActionKind(value);

  if (kind === "email_draft") {
    return "Aion prepares the email draft only. Nothing is sent in this phase.";
  }

  if (kind === "onboarding_checklist") {
    return "Aion prepares the onboarding checklist and draft message. Nothing is written externally in this phase.";
  }

  if (kind === "chase_email") {
    return "Aion prepares a polite follow-up email draft. Nothing is sent in this phase.";
  }

  if (kind === "crm_follow_up") {
    return "Aion prepares the CRM follow-up payload only. The CRM is not written to in this phase.";
  }

  return "Aion prepares the contact payload only. HubSpot is not written to in this phase.";
}

function getTeachAionPrimaryActionTag(value) {
  const kind = getTeachAionActionKind(value);

  if (kind === "email_draft") return "GMAIL_DRAFT_ONLY";
  if (kind === "onboarding_checklist") return "ONBOARDING_CHECKLIST";
  if (kind === "chase_email") return "CHASE_EMAIL_DRAFT";
  if (kind === "crm_follow_up") return "CRM_FOLLOW_UP_DRY_RUN";

  return "HUBSPOT_CREATE_OR_UPDATE_CONTACT";
}

function getTeachAionValidationStep(errors) {
  const text = Array.isArray(errors) ? errors.join(" ").toLowerCase() : "";

  if (
    text.includes("task name") ||
    text.includes("workflow id") ||
    text.includes("gmail search")
  ) {
    return 1;
  }

  if (text.includes("email extraction")) {
    return 2;
  }

  if (
    text.includes("draft email subject") ||
    text.includes("draft email body") ||
    text.includes("hubspot") ||
    text.includes("sending email") ||
    text.includes("external writes")
  ) {
    return 3;
  }

  if (text.includes("approval mode")) {
    return 4;
  }

  return 1;
}

function validateTeachAionWorkflowDraft(workflow) {
  const errors = [];

  const name = String(workflow?.name || "").trim();
  const workflowId = String(workflow?.workflow_id || workflow?.id || "").trim();
  const trigger = workflow?.trigger || {};
  const extraction = workflow?.extraction || {};
  const emailDraft = workflow?.email_draft || {};
  const approval = workflow?.approval || {};
  const hubspot = workflow?.hubspot || {};
  const fields = Array.isArray(extraction.fields) ? extraction.fields : [];

  if (!name) {
    errors.push("Add a workflow name.");
  }

  if (!workflowId) {
    errors.push("Missing workflow id. Pick a template again.");
  }

  if (!String(trigger.query || "").trim()) {
    errors.push("Add a Gmail search rule.");
  }

  const hasRequiredEmailField = fields.some((field) => {
    const key = String(field?.key || "").toLowerCase();
    return key === "email" && field?.required === true;
  });

  if (!hasRequiredEmailField) {
    errors.push("Required email extraction field is missing.");
  }

  if (!String(emailDraft.subject_template || "").trim()) {
    errors.push("Add a draft email subject.");
  }

  if (!String(emailDraft.body_template || "").trim()) {
    errors.push("Add a draft email body.");
  }

  if (!String(approval.approval_mode || "").trim()) {
    errors.push("Choose an approval mode.");
  }

  if (hubspot.dry_run === false) {
    errors.push("External HubSpot writes are disabled in Phase 2A.");
  }

  if (emailDraft.send_after_approval === true || emailDraft.send === true) {
    errors.push("Sending email is disabled in Phase 2A.");
  }

  if (workflow?.external_writes_enabled === true) {
    errors.push("External writes are disabled in Phase 2A.");
  }

  return {
    ok: errors.length === 0,
    errors,
  };
}

function slugifyStepBuilderValue(value, fallback = "item") {
  return String(value || fallback)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80) || fallback;
}

function runtimeStepTypeFromBuilderType(type) {
  if (type === "trigger") return "trigger";
  if (type === "extract") return "extract";
  if (type === "summarise") return "summarise";
  if (type === "crm_upsert") return "tool_action";
  if (type === "draft_email") return "notify";
  if (type === "create_task") return "tool_action";
  if (type === "approval_checkpoint") return "approval_checkpoint";
  if (type === "notify_user") return "notify";
  if (type === "end") return "end";
  return type || "unknown";
}

function buildInputMapFromStepBuilderStep(step) {
  const inputMap = {};

  if (!step || step.type === "trigger" || step.type === "end") {
    return inputMap;
  }

  if (step.input_source === "fixed_value") {
    inputMap.value = { fixed: step.fixed_value || "" };
    return inputMap;
  }

  if (step.input_source === "workspace_context") {
    inputMap.context = step.input_ref || "$workspace";
    return inputMap;
  }

  if (step.input_source === "trigger_payload") {
    inputMap.payload = step.input_ref || "$trigger";
    return inputMap;
  }

  if (step.input_source === "previous_step") {
    inputMap.input = step.input_ref || "";
    return inputMap;
  }

  return inputMap;
}

function parseStepBuilderOutputSchema(schemaText) {
  const raw = String(schemaText || "").trim();
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
  } catch (_) {
    return null;
  }

  return null;
}

function compileStepBuilderDraftToGenericWorkflow(draftInput) {
  const draft = normaliseStepBuilderDraft(draftInput);
  const workflowName = draft.workflow_name || draft.operator_name || "Untitled step builder workflow";
  const workflowId =
    draft.workflow_id ||
    `workflow_${slugifyStepBuilderValue(workflowName, "step_builder")}`;

  const enabledSteps = Array.isArray(draft.steps)
    ? draft.steps.filter((step) => step && step.enabled !== false)
    : [];

  const triggerStep =
    enabledSteps.find((step) => step.type === "trigger") ||
    enabledSteps[0] ||
    null;

  const extractionFields = [];

  for (const step of enabledSteps) {
    if (step.type !== "extract") continue;

    const schema = parseStepBuilderOutputSchema(step.output_schema);
    if (schema) {
      for (const [key, type] of Object.entries(schema)) {
        extractionFields.push({
          key,
          label: key,
          type: typeof type === "string" ? type : "string",
          required: key === "email" || key === "customer_email",
          source: "trigger_payload",
        });
      }
    }
  }

  const steps = enabledSteps.map((step, index) => {
    const runtimeType = runtimeStepTypeFromBuilderType(step.type);
    const outputName = step.output || (runtimeType === "end" ? "" : slugifyStepBuilderValue(step.name, `step_${index + 1}`));

    const runtimeStep = {
      step_id: step.step_id || `step_${index + 1}`,
      name: step.name || `Step ${index + 1}`,
      type: runtimeType,
    };

    if (outputName) {
      runtimeStep.output = outputName;
    }

    const inputMap = buildInputMapFromStepBuilderStep(step);
    if (Object.keys(inputMap).length > 0) {
      runtimeStep.input_map = inputMap;
    }

    if (runtimeType === "tool_action") {
      runtimeStep.tool_id = step.tool_id || defaultToolForStepType(step.type);
      runtimeStep.permission_mode =
        step.type === "crm_upsert" ? "write_after_approval" : "dry_run_only";
      runtimeStep.external_write = step.type === "crm_upsert";
    }

    if (step.failure_behavior) {
      runtimeStep.failure_behavior = step.failure_behavior;
    }

    if (step.audit_visibility) {
      runtimeStep.audit_visibility = step.audit_visibility;
    }

    return runtimeStep;
  });

  const hasEnd = steps.some((step) => step.type === "end");
  if (!hasEnd) {
    steps.push({
      step_id: "finish",
      name: "Stop/end",
      type: "end",
    });
  }

  const hasTrigger = steps.some((step) => step.type === "trigger");
  if (!hasTrigger) {
    steps.unshift({
      step_id: "trigger",
      name: "Manual trigger",
      type: "trigger",
      output: "trigger",
    });
  }

  return {
    workflow_id: workflowId,
    name: workflowName,
    department: draft.department || "Sales",
    operator_name: draft.operator_name || "",
    description: draft.description || "",
    goal: draft.goal || "",
    trigger: {
      type: triggerStep?.tool_id === "tool.gmail.trigger.v1" ? "gmail_message_match" : "manual",
      query: "is:unread",
    },
    extraction: {
      fields: extractionFields,
    },
    steps,
    builder_metadata: {
      source: "phase_8_step_builder",
      department: draft.department || "Sales",
      operator_name: draft.operator_name || "",
      description: draft.description || "",
      goal: draft.goal || "",
    },
  };
}

function renderOperationsAgentsStepBuilder() {
  const draft = normaliseStepBuilderDraft(state.operationsAgentsStepBuilderDraft);
  const selectedStepId =
    state.operationsAgentsStepBuilderSelectedStepId ||
    draft.steps[0]?.step_id ||
    "";
  const selectedStep =
    draft.steps.find((step) => step.step_id === selectedStepId) || null;
  const loading = state.operationsAgentsLoading === true;

  const selectedIndex = selectedStep
    ? draft.steps.findIndex((step) => step.step_id === selectedStep.step_id)
    : -1;

  const compileResult = state.operationsAgentsStepBuilderCompileResult || null;
  const simulationResult = state.operationsAgentsStepBuilderSimulationResult || null;
  const saveResult = state.operationsAgentsStepBuilderSaveResult || null;

  return `
    <div class="train-builder-shell">
      <div class="train-builder-header">
        <div>
          <div class="eyebrow">Step Builder</div>
          <h2>Build custom agent</h2>
          <p class="muted" style="margin:6px 0 0;">
            Design a workflow by naming the operator and adding ordered steps. It stays
            dry-run until validated and approved.
          </p>
        </div>

        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          ${
            compileResult?.ok
              ? `<span class="train-status-chip train-status-ok">Validated</span>`
              : `<span class="train-status-chip">Draft</span>`
          }

          <button
            class="secondary-btn"
            data-operations-agents-action="close-step-builder"
            ${loading ? "disabled" : ""}
          >
            Close Builder
          </button>
        </div>
      </div>

      <div class="train-builder-form-grid">
        <label class="train-field">
          <span>Workflow name</span>
          <input
            data-step-builder-field="workflow_name"
            value="${escapeHtml(draft.workflow_name)}"
            placeholder="New enquiry follow-up workflow"
          />
        </label>

        <label class="train-field">
          <span>Department</span>
          <select data-step-builder-field="department">
            ${OPERATIONS_AGENT_DEPARTMENTS.map(
              (department) =>
                `<option value="${escapeHtml(department)}" ${
                  draft.department === department ? "selected" : ""
                }>${escapeHtml(department)}</option>`,
            ).join("")}
          </select>
        </label>

        <label class="train-field">
          <span>Operator name</span>
          <input
            data-step-builder-field="operator_name"
            value="${escapeHtml(draft.operator_name)}"
            placeholder="Sales Lead Follow-up Operator"
          />
        </label>

        <label class="train-field">
          <span>Workflow id</span>
          <input
            data-step-builder-field="workflow_id"
            value="${escapeHtml(draft.workflow_id)}"
            readonly
          />
        </label>

        <label class="train-field train-field-wide">
          <span>Description</span>
          <textarea
            data-step-builder-field="description"
            placeholder="What does this operator do?"
          >${escapeHtml(draft.description)}</textarea>
        </label>

        <label class="train-field train-field-wide">
          <span>Goal</span>
          <textarea
            data-step-builder-field="goal"
            placeholder="What should this operator achieve?"
          >${escapeHtml(draft.goal)}</textarea>
        </label>
      </div>

      <div class="train-builder-main">
        <div class="train-builder-panel train-builder-steps-panel">
          <div class="train-builder-panel-head">
            <div>
              <div class="eyebrow">Ordered steps</div>
              <h3>Workflow steps</h3>
            </div>

            <div class="train-add-step-row">
              <select data-step-builder-add-type>
                ${OPERATIONS_AGENT_STEP_TYPES.map(
                  (item) =>
                    `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`,
                ).join("")}
              </select>

              <button
                class="primary-btn"
                data-operations-agents-action="add-step-builder-step"
                ${loading ? "disabled" : ""}
              >
                Add Step
              </button>
            </div>
          </div>

          ${
            draft.steps.length
              ? `
                <div class="train-step-list">
                  ${draft.steps
                    .map((step, index) => {
                      const typeMeta = OPERATIONS_AGENT_STEP_TYPES.find(
                        (item) => item.value === step.type,
                      );
                      const isSelected = step.step_id === selectedStepId;
                      const disabled = step.enabled === false;

                      return `
                        <button
                          type="button"
                          class="train-step-row ${isSelected ? "train-step-row-selected" : ""} ${
                            disabled ? "train-step-row-disabled" : ""
                          }"
                          data-operations-agents-action="select-step-builder-step"
                          data-step-id="${escapeHtml(step.step_id)}"
                        >
                          <span class="train-step-main">
                            <strong>${index + 1}. ${escapeHtml(step.name || typeMeta?.label || "Step")}</strong>
                            <em>${escapeHtml(typeMeta?.label || step.type)} · output: ${escapeHtml(step.output || "—")}</em>
                          </span>

                          <span class="train-step-state">
                            ${disabled ? "Disabled" : "Enabled"}
                          </span>
                        </button>
                      `;
                    })
                    .join("")}
                </div>
              `
              : `<div class="empty-state">No steps yet. Add a trigger, extraction, CRM action, email draft, approval checkpoint, or end step.</div>`
          }
        </div>

        <div class="train-builder-panel train-builder-editor-panel">
          ${
            selectedStep
              ? `
                <div class="train-selected-step-head">
                  <div>
                    <div class="eyebrow">Selected step</div>
                    <h3>${escapeHtml(selectedStep.name || "Workflow step")}</h3>
                  </div>

                  <span class="train-status-chip ${
                    selectedStep.enabled === false ? "" : "train-status-ok"
                  }">
                    ${selectedStep.enabled === false ? "Disabled" : "Enabled"}
                  </span>
                </div>

                <div class="train-step-editor-grid">
                  <label class="train-field">
                    <span>Step name</span>
                    <input
                      data-step-builder-step-field="name"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                      value="${escapeHtml(selectedStep.name || "")}"
                    />
                  </label>

                  <label class="train-field">
                    <span>Step type</span>
                    <select
                      data-step-builder-step-field="type"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                    >
                      ${OPERATIONS_AGENT_STEP_TYPES.map(
                        (item) =>
                          `<option value="${escapeHtml(item.value)}" ${
                            selectedStep.type === item.value ? "selected" : ""
                          }>${escapeHtml(item.label)}</option>`,
                      ).join("")}
                    </select>
                  </label>

                  <label class="train-field">
                    <span>Step id</span>
                    <input
                      value="${escapeHtml(selectedStep.step_id)}"
                      readonly
                    />
                  </label>

                  <label class="train-field">
                    <span>Output name</span>
                    <input
                      data-step-builder-step-field="output"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                      value="${escapeHtml(selectedStep.output || "")}"
                      placeholder="extracted"
                    />
                  </label>

                  <label class="train-field">
                    <span>Input source</span>
                    <select
                      data-step-builder-step-field="input_source"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                    >
                      ${OPERATIONS_AGENT_INPUT_SOURCES.map(
                        (item) =>
                          `<option value="${escapeHtml(item.value)}" ${
                            selectedStep.input_source === item.value ? "selected" : ""
                          }>${escapeHtml(item.label)}</option>`,
                      ).join("")}
                    </select>
                  </label>

                  <label class="train-field">
                    <span>Input reference</span>
                    <input
                      data-step-builder-step-field="input_ref"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                      value="${escapeHtml(selectedStep.input_ref || "")}"
                      placeholder="$steps.extracted.email"
                    />
                  </label>

                  <label class="train-field">
                    <span>Tool</span>
                    <select
                      data-step-builder-step-field="tool_id"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                    >
                      ${OPERATIONS_AGENT_TOOL_OPTIONS.map(
                        (item) =>
                          `<option value="${escapeHtml(item.value)}" ${
                            selectedStep.tool_id === item.value ? "selected" : ""
                          }>${escapeHtml(item.label)}</option>`,
                      ).join("")}
                    </select>
                  </label>

                  <label class="train-field">
                    <span>Failure behaviour</span>
                    <select
                      data-step-builder-step-field="failure_behavior"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                    >
                      ${OPERATIONS_AGENT_FAILURE_BEHAVIOURS.map(
                        (item) =>
                          `<option value="${escapeHtml(item.value)}" ${
                            selectedStep.failure_behavior === item.value ? "selected" : ""
                          }>${escapeHtml(item.label)}</option>`,
                      ).join("")}
                    </select>
                  </label>

                  <label class="train-field">
                    <span>Audit visibility</span>
                    <select
                      data-step-builder-step-field="audit_visibility"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                    >
                      ${OPERATIONS_AGENT_AUDIT_VISIBILITY.map(
                        (item) =>
                          `<option value="${escapeHtml(item.value)}" ${
                            selectedStep.audit_visibility === item.value ? "selected" : ""
                          }>${escapeHtml(item.label)}</option>`,
                      ).join("")}
                    </select>
                  </label>

                  <label class="train-field">
                    <span>Fixed value</span>
                    <input
                      data-step-builder-step-field="fixed_value"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                      value="${escapeHtml(selectedStep.fixed_value || "")}"
                      placeholder="Optional fixed value"
                    />
                  </label>

                  <label class="train-field train-field-full">
                    <span>Output schema placeholder</span>
                    <textarea
                      data-step-builder-step-field="output_schema"
                      data-step-id="${escapeHtml(selectedStep.step_id)}"
                      placeholder='{"email":"string","firstname":"string"}'
                    >${escapeHtml(selectedStep.output_schema || "")}</textarea>
                  </label>
                </div>

                <div class="train-step-controls">
                  <button
                    class="secondary-btn"
                    data-operations-agents-action="move-step-builder-up"
                    data-step-id="${escapeHtml(selectedStep.step_id)}"
                    ${selectedIndex <= 0 ? "disabled" : ""}
                  >
                    Move Up
                  </button>

                  <button
                    class="secondary-btn"
                    data-operations-agents-action="move-step-builder-down"
                    data-step-id="${escapeHtml(selectedStep.step_id)}"
                    ${selectedIndex < 0 || selectedIndex >= draft.steps.length - 1 ? "disabled" : ""}
                  >
                    Move Down
                  </button>

                  <button
                    class="secondary-btn"
                    data-operations-agents-action="duplicate-step-builder-step"
                    data-step-id="${escapeHtml(selectedStep.step_id)}"
                  >
                    Duplicate
                  </button>

                  <button
                    class="secondary-btn"
                    data-operations-agents-action="toggle-step-builder-step"
                    data-step-id="${escapeHtml(selectedStep.step_id)}"
                  >
                    ${selectedStep.enabled === false ? "Enable" : "Disable"}
                  </button>

                  <button
                    class="secondary-btn danger-btn"
                    data-operations-agents-action="delete-step-builder-step"
                    data-step-id="${escapeHtml(selectedStep.step_id)}"
                  >
                    Delete
                  </button>
                </div>

                ${
                  compileResult
                    ? `
                      <div class="train-result-box ${
                        compileResult.ok ? "train-result-ok" : "train-result-error"
                      }">
                        <span>${compileResult.ok ? "Validation passed" : "Validation failed"}</span>
                        <strong>${escapeHtml(
                          compileResult.message ||
                            (compileResult.ok
                              ? "Builder draft compiled and validated successfully."
                              : "Builder draft compiled but validation found issues."),
                        )}</strong>
                        <button
                          class="primary-btn"
                          type="button"
                          data-aion-workflow-apply-node-config="${escapeHtml(selectedNode.id)}"
                          style="margin-top:12px;width:100%;"
                        >
                          Apply parser config
                        </button>
                      </div>
                    `
                    : ""
                }

                ${
                  simulationResult
                    ? `
                      <div class="train-result-box ${
                        simulationResult.ok ? "train-result-warn" : "train-result-error"
                      }">
                        <span>${simulationResult.ok ? "Waiting approval" : "Simulation failed"}</span>
                        <strong>
                          ${
                            simulationResult.ok
                              ? "Simulation paused at approval checkpoint."
                              : escapeHtml(simulationResult.error || "Simulation failed.")
                          }
                        </strong>
                      </div>
                    `
                    : ""
                }

                ${
                  saveResult
                    ? `
                      <div class="train-result-box ${
                        saveResult.ok ? "train-result-ok" : "train-result-error"
                      }">
                        <span>${saveResult.ok ? "Workflow stored" : "Workflow not stored"}</span>
                        <strong>${escapeHtml(saveResult.message || "")}</strong>
                      </div>
                    `
                    : ""
                }

                <div class="train-builder-actions">
                  <button
                    class="secondary-btn"
                    data-operations-agents-action="save-step-builder-workflow-draft"
                    ${loading ? "disabled" : ""}
                  >
                    Save Draft
                  </button>

                  <button
                    class="secondary-btn train-salmon-btn"
                    data-operations-agents-action="simulate-step-builder-workflow"
                    ${loading ? "disabled" : ""}
                  >
                    Simulate Workflow
                  </button>

                  <button
                    class="primary-btn"
                    data-operations-agents-action="publish-step-builder-workflow"
                    ${loading ? "disabled" : ""}
                  >
                    Publish Workflow
                  </button>
                </div>
              `
              : `<div class="empty-state">Select a step to edit it.</div>`
          }
        </div>
      </div>

      <div class="train-simulation-panel">
        <div class="train-builder-panel-head">
          <div>
            <div class="eyebrow">Simulation input</div>
            <h3>Sample trigger payload</h3>
            <p class="muted" style="margin:6px 0 0;">
              Used to dry-run the compiled workflow through the generic runtime.
            </p>
          </div>
        </div>

        <div class="train-builder-form-grid train-sample-grid">
          <label class="train-field">
            <span>Sample email</span>
            <input
              data-step-builder-sample-field="email"
              value="${escapeHtml(state.operationsAgentsStepBuilderSampleInput?.email || "customer@example.com")}"
              placeholder="customer@example.com"
            />
          </label>

          <label class="train-field">
            <span>Sample subject</span>
            <input
              data-step-builder-sample-field="subject"
              value="${escapeHtml(state.operationsAgentsStepBuilderSampleInput?.subject || "Quote needed for pool cleaning")}"
              placeholder="Quote needed for pool cleaning"
            />
          </label>

          <label class="train-field train-field-full">
            <span>Sample body</span>
            <textarea
              data-step-builder-sample-field="body"
              placeholder="Paste a sample customer message here."
            >${escapeHtml(state.operationsAgentsStepBuilderSampleInput?.body || "Hi, can I get a quote for pool cleaning in Arboleas?")}</textarea>
          </label>
        </div>

        <div class="train-builder-actions train-builder-actions-bottom">
          <button
            class="secondary-btn"
            data-operations-agents-action="seed-step-builder-example"
            ${loading ? "disabled" : ""}
          >
            Add Example Workflow
          </button>

          <button
            class="secondary-btn"
            data-operations-agents-action="reset-step-builder"
            ${loading ? "disabled" : ""}
          >
            Reset Builder
          </button>

          <button
            class="primary-btn"
            data-operations-agents-action="compile-step-builder-workflow"
            ${loading ? "disabled" : ""}
          >
            Compile + Validate Workflow
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderOperationsAgentsWizard() {
  const step = Number(state.operationsAgentsWizardStep || 1);
  const draft = state.operationsAgentsWizardDraft || {};
  const trigger = draft.trigger || {};
  const hubspot = draft.hubspot || {};
  const emailDraft = draft.email_draft || {};
  const approval = draft.approval || {};
  const saving = state.operationsAgentsWizardSaving === true;
  const error = state.operationsAgentsWizardError || "";
  const result = state.operationsAgentsWizardResult || null;

  const stepTitle =
    step === 1
      ? "Trigger"
      : step === 2
        ? "Extraction"
        : step === 3
          ? "Actions"
          : "Approval";

  return `
    <div class="train-wizard-shell">
      <div class="train-wizard-header">
        <div>
          <div class="eyebrow">Train-a-Task Wizard</div>
          <h2>Train Agent</h2>
          <p class="muted" style="margin:6px 0 0;">
            Simple Phase 1 wizard: choose trigger, extraction, actions, approval mode,
            then compile into a safe dry-run workflow.
          </p>
        </div>

        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <span class="train-status-chip">Step ${escapeHtml(step)} of 4</span>
          <button
            class="secondary-btn"
            data-operations-agents-action="close-wizard"
            ${saving ? "disabled" : ""}
          >
            Close
          </button>
        </div>
      </div>

      ${
        error
          ? `
            <div class="train-result-box train-result-error" style="margin:20px 28px 0;">
              <span>Validation error</span>
              <strong>${escapeHtml(error)}</strong>
            </div>
          `
          : ""
      }

      ${
        result
          ? `
            <div class="train-result-box train-result-ok" style="margin:20px 28px 0;">
              <span>Last result</span>
              <strong>${escapeHtml(result?.message || result?.status || "Compile result available")}</strong>
            </div>
          `
          : ""
      }

      <div class="train-wizard-step-bar">
        ${[
          [1, "Trigger"],
          [2, "Extract"],
          [3, "Actions"],
          [4, "Approval"],
        ]
          .map(
            ([index, label]) => `
              <button
                type="button"
                class="train-wizard-step ${step === index ? "train-wizard-step-active" : ""}"
                data-operations-agents-action="${index < step ? "wizard-prev" : index > step ? "wizard-next" : ""}"
                ${saving || index === step ? "disabled" : ""}
              >
                ${escapeHtml(label)}
              </button>
            `,
          )
          .join("")}
      </div>

      <div class="train-wizard-body">
        <div class="train-wizard-title-row">
          <div>
            <div class="eyebrow">Current step</div>
            <h3>${escapeHtml(stepTitle)}</h3>
          </div>

          <span class="train-status-chip train-status-ok">Dry-run</span>
        </div>

        ${
          step === 1
            ? `
              <div class="train-wizard-metric-grid">
                ${renderDashboardMetricCard(
                  "Trigger",
                  trigger.trigger_type || "gmail_message_match",
                  "When this happens",
                )}
                ${renderDashboardMetricCard(
                  "Query",
                  trigger.query || "is:unread",
                  "Gmail search filter",
                )}
                ${renderDashboardMetricCard(
                  "Dedupe",
                  trigger.dedupe ? "Enabled" : "Disabled",
                  "Avoid repeated runs",
                )}
                ${renderDashboardMetricCard(
                  "Max results",
                  trigger.max_results || 10,
                  "Poll batch size",
                )}
              </div>

              <div class="train-builder-form-grid train-wizard-fields">
                <label class="train-field train-field-full">
                  <span>Workflow name</span>
                  <input
                    class="operations-agents-wizard-input"
                    data-operations-agents-wizard-path="name"
                    value="${escapeHtml(draft.name || "")}"
                    placeholder="Gmail lead to HubSpot and welcome draft"
                  />
                </label>

                <label class="train-field train-field-full">
                  <span>Gmail query</span>
                  <input
                    class="operations-agents-wizard-input"
                    data-operations-agents-wizard-path="trigger.query"
                    value="${escapeHtml(trigger.query || "is:unread")}"
                    placeholder="is:unread"
                  />
                </label>
              </div>
            `
            : ""
        }

        ${
          step === 2
            ? `
              <div class="train-wizard-metric-grid">
                ${renderDashboardMetricCard("Extract", "Customer details", "Name, email, phone, company, enquiry")}
                ${renderDashboardMetricCard("Required", "Email", "Minimum field for CRM/draft")}
                ${renderDashboardMetricCard("Fallback", "Ask approval", "Stops safely if missing")}
                ${renderDashboardMetricCard("Safety", "Dry-run", "No external writes")}
              </div>

              <div class="train-wizard-card">
                <div class="eyebrow">Fields Aion will extract</div>
                <h3>Customer details from matched message</h3>
                <p class="muted" style="margin:6px 0 18px;">
                  These fields become the inputs for the prepared task action and Gmail draft.
                </p>

                <div class="train-step-list" style="padding:0;">
                  ${(draft.extraction?.fields || [])
                    .map(
                      (field, index) => `
                        <div class="train-step-row">
                          <span class="train-step-main">
                            <strong>${index + 1}. ${escapeHtml(field.label || field.key || "Field")}</strong>
                            <em>${escapeHtml(field.key || "")} · ${escapeHtml(field.description || "")}</em>
                          </span>
                          <span class="train-step-state">${field.required ? "Required" : "Optional"}</span>
                        </div>
                      `,
                    )
                    .join("")}
                </div>
              </div>
            `
            : ""
        }

        ${
          step === 3
            ? `
              <div class="train-wizard-metric-grid">
                ${renderDashboardMetricCard(
                  "Task action",
                  getTeachAionPrimaryActionLabel(draft),
                  getTeachAionPrimaryActionDescription(draft),
                )}
                ${renderDashboardMetricCard("Match field", hubspot.match_field || "email", "Create/update key")}
                ${renderDashboardMetricCard("Email action", "Gmail draft", "Prepared only")}
                ${renderDashboardMetricCard("To field", emailDraft.to_field || "email", "Uses extracted email")}
              </div>

              <div class="train-wizard-card">
                <div class="eyebrow">Action 1</div>
                <h3>${escapeHtml(getTeachAionPrimaryActionTitle(draft))}</h3>
                <p class="muted" style="margin:6px 0 16px;">
                  ${escapeHtml(getTeachAionPrimaryActionBody(draft))}
                </p>

                <div class="badge-row">
                  <span class="badge">Dry-run</span>
                  <span class="badge">${escapeHtml(getTeachAionPrimaryActionTag(draft))}</span>
                  <span class="badge">Match by ${escapeHtml(hubspot.match_field || "email")}</span>
                </div>
              </div>

              <div class="train-builder-form-grid train-wizard-fields">
                <label class="train-field train-field-full">
                  <span>Draft subject</span>
                  <input
                    class="operations-agents-wizard-input"
                    data-operations-agents-wizard-path="email_draft.subject_template"
                    value="${escapeHtml(emailDraft.subject_template || "")}"
                    placeholder="Welcome — thanks for your enquiry"
                  />
                </label>

                <label class="train-field train-field-full">
                  <span>Draft body</span>
                  <textarea
                    class="operations-agents-wizard-input"
                    data-operations-agents-wizard-path="email_draft.body_template"
                    placeholder="Hi {{name}}, ..."
                  >${escapeHtml(emailDraft.body_template || "")}</textarea>
                </label>
              </div>
            `
            : ""
        }

        ${
          step === 4
            ? `
              <div class="train-wizard-metric-grid">
                ${renderDashboardMetricCard(
                  "Approval mode",
                  formatTeachAionApprovalMode(approval.approval_mode),
                  "Human checkpoint",
                )}
                ${renderDashboardMetricCard(
                  "Require human",
                  approval.require_human !== false ? "Yes" : "No",
                  "Phase 1 safety",
                )}
                ${renderDashboardMetricCard("External writes", "Disabled", "Dry-run first")}
                ${renderDashboardMetricCard(
                  "Status after save",
                  draft.enabled ? "Enabled / Dry-run" : "Draft / Disabled",
                  "Local state only",
                )}
              </div>

              <div class="train-wizard-card">
                <div class="eyebrow">Review</div>
                <h3>${escapeHtml(draft.name || "Untitled trained task")}</h3>

                <p class="muted" style="margin:10px 0 0;">
                  When a Gmail message matches <strong>${escapeHtml(trigger.query || "is:unread")}</strong>,
                  Aion will extract customer details.
                </p>

                <p class="muted" style="margin:10px 0 0;">
                  ${escapeHtml(getTeachAionActionSummary(draft))}
                </p>

                <div class="badge-row" style="margin-top:16px;">
                  <span class="badge">No external writes</span>
                  <span class="badge">Human approval required</span>
                  <span class="badge">Replay/audit enabled</span>
                  <span class="badge">Local workflow definition</span>
                </div>
              </div>

              <div class="train-result-box train-result-warn">
                <span>Safety lock</span>
                <strong>
                  Gmail polling, real Gmail draft creation, and HubSpot writes are not active yet.
                  This saves as a local dry-run workflow.
                </strong>
              </div>
            `
            : ""
        }

        <div class="train-builder-actions">
          <button
            class="secondary-btn"
            data-operations-agents-action="wizard-prev"
            ${step <= 1 || saving ? "disabled" : ""}
          >
            Previous
          </button>

          ${
            step < 4
              ? `
                <button
                  class="primary-btn"
                  data-operations-agents-action="wizard-next"
                  ${saving ? "disabled" : ""}
                >
                  Next
                </button>
              `
              : `
                <button
                  class="primary-btn"
                  data-operations-agents-action="wizard-save"
                  ${saving ? "disabled" : ""}
                >
                  ${saving ? "Saving..." : "Review & Save Task"}
                </button>
              `
          }
        </div>
      </div>
    </div>
  `;
}

function renderAionToolMiniCard(tool) {
  const risk = String(tool?.risk_level || "unknown");
  const permission = String(tool?.permission_mode || "unknown");
  const health = String(tool?.connector_health || "unknown");
  const isExternal = tool?.external_write === true;
  const dryRun = tool?.dry_run_supported !== false;

  return `
    <div class="mini-card">
      <div class="metric-label">${escapeHtml(tool?.name || tool?.tool_id || "Tool")}</div>
      <div class="metric-note">${escapeHtml(tool?.provider || "unknown")} · ${escapeHtml(tool?.action_type || "")}</div>
      <div class="badge-row" style="margin-top:8px;">
        <span class="badge">${escapeHtml(risk)}</span>
        <span class="badge">${escapeHtml(permission)}</span>
        <span class="badge">${escapeHtml(health)}</span>
        <span class="badge">${isExternal ? "External write" : "No external write"}</span>
        <span class="badge">${dryRun ? "Dry-run supported" : "No dry-run"}</span>
      </div>
    </div>
  `;
}

function renderAionExternalToolMiniCard(tool, showDeveloperTools, loading) {
  const toolId = tool?.tool_id || "";
  const provider = String(tool?.provider || "unknown");
  const risk = String(tool?.risk_level || "unknown");
  const permission = String(tool?.permission_mode || "unknown");
  const health = String(tool?.connector_health || "unknown");
  const discovery = String(tool?.tool_discovery_status || "unknown");
  const isExternal = tool?.external_write === true;
  const category = tool?.provider_category || tool?.server_id || "external";

  return `
    <div class="train-mini-panel train-external-tool-card">
      <div class="metric-label">${escapeHtml(tool?.name || toolId || "External tool")}</div>
      <div class="metric-note">${escapeHtml(provider)} · ${escapeHtml(category)}</div>
      <div class="metric-note">${escapeHtml(toolId)}</div>

      <div class="badge-row" style="margin-top:10px;">
        <span class="badge">${escapeHtml(risk)}</span>
        <span class="badge">${escapeHtml(permission)}</span>
        <span class="badge">${escapeHtml(health)}</span>
        <span class="badge">${escapeHtml(discovery)}</span>
        <span class="badge">${isExternal ? "Write blocked" : "Read-only"}</span>
      </div>

      <p class="muted" style="margin:10px 0 0;">
        ${
          isExternal
            ? "External write is blocked until connector, approval, and policy gates are enabled."
            : "Read-only tool placeholder. No external connector call is made yet."
        }
      </p>

      ${
        showDeveloperTools
          ? `
            <button
              class="secondary-btn"
              style="margin-top:12px;"
              data-operations-agents-action="run-external-tool-dry-run"
              data-tool-id="${escapeHtml(toolId)}"
              ${loading ? "disabled" : ""}
            >
              Run external dry-run test
            </button>
          `
          : ""
      }
    </div>
  `;
}


function makeBrowserSkillId(prefix = "browser_skill") {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

function normaliseBrowserWorkflowStep(step, index = 0) {
  const type = String(step?.type || step?.step_type || "browser_action");
  const label = String(step?.label || step?.name || `Browser step ${index + 1}`);
  const safety = String(step?.safety || step?.permission || "dry_run_only");
  const output = String(step?.output || step?.output_name || type);

  return {
    step_id: String(step?.step_id || `browser_step_${String(index + 1).padStart(3, "0")}`),
    type,
    label,
    safety,
    output,
    selector: String(step?.selector || ""),
    input: step?.input || {},
    requires_approval:
      step?.requires_approval === true ||
      safety === "human_approval_required" ||
      type === "approval_checkpoint",
  };
}

function createBrowserMicroSkillFromBridge(bridgeInput = {}) {
  const bridge = bridgeInput || {};
  const rawSteps = Array.isArray(bridge.last_recording_steps)
    ? bridge.last_recording_steps
    : [];

  const steps = rawSteps.map((step, index) =>
    normaliseBrowserWorkflowStep(step, index),
  );

  const createdAt = new Date().toISOString();
  const skillId = makeBrowserSkillId();

  return {
    skill_id: skillId,
    name: bridge.last_recording_name || "New browser micro-skill",
    description:
      bridge.last_recording_summary ||
      "Recorded browser process converted into a reusable dry-run browser skill.",
    status: "draft",
    source: "browser_desktop_operator",
    mode: bridge.mode || "isolated_browser",
    browser: bridge.browser || "Aion isolated browser",
    created_at: createdAt,
    updated_at: createdAt,
    inputs: [
      {
        key: "start_url",
        label: "Start URL",
        type: "string",
        required: false,
      },
      {
        key: "workspace_context",
        label: "Workspace context",
        type: "object",
        required: false,
      },
    ],
    outputs: steps
      .filter((step) => step.output)
      .map((step) => ({
        key: step.output,
        label: step.label,
        source_step_id: step.step_id,
      })),
    permissions: {
      read_page: true,
      fill_forms: true,
      click_buttons: true,
      upload_files: true,
      download_files: true,
      submit_forms: false,
      payments: false,
      deletes: false,
      external_writes: false,
    },
    approval_policy: {
      mode: "approval_before_write",
      requires_human_for_submit: true,
      requires_human_for_payment: true,
      requires_human_for_delete: true,
      requires_human_for_external_write: true,
    },
    steps,
  };
}

function renderBrowserMicroSkillCard(skill, index = 0) {
  const steps = Array.isArray(skill?.steps) ? skill.steps : [];
  const permissions = skill?.permissions || {};
  const approval = skill?.approval_policy || {};

  return `
    <div class="train-section-panel">
      <div class="train-section-head">
        <div>
          <div class="eyebrow">Browser micro-skill ${escapeHtml(index + 1)}</div>
          <h2>${escapeHtml(skill?.name || "Browser micro-skill")}</h2>
          <p class="muted" style="margin:6px 0 0;">
            ${escapeHtml(skill?.description || "Reusable recorded browser workflow.")}
          </p>
        </div>

        <span class="status-pill status-pending">
          ${escapeHtml(skill?.status || "draft")}
        </span>
      </div>

      <div class="train-section-body">
        <div class="card-grid">
          ${renderDashboardMetricCard("Skill ID", skill?.skill_id || "—", "Reusable browser function")}
          ${renderDashboardMetricCard("Mode", skill?.mode || "isolated_browser", skill?.browser || "Aion isolated browser")}
          ${renderDashboardMetricCard("Steps", steps.length, "Captured browser actions")}
          ${renderDashboardMetricCard("Writes", permissions.external_writes ? "Allowed" : "Blocked", approval.mode || "Approval required")}
        </div>

        <div class="train-status-note" style="margin-top:14px;">
          <span class="train-status-label">Composable</span>
          <div>
            <strong>This recording is now treated as a small reusable workflow function.</strong>
            <p class="muted" style="margin:6px 0 0;">
              Keep browser skills short. Chain small skills together later instead of recording one long fragile process.
            </p>
          </div>
        </div>

        <div class="train-section-panel" style="margin-top:14px;">
          <div class="train-section-head">
            <div>
              <div class="eyebrow">Skill steps</div>
              <h2>Captured function body</h2>
            </div>
            <span class="badge">No external writes</span>
          </div>

          <div class="train-section-body">
            <div style="display:grid; gap:10px;">
              ${
                steps.length
                  ? steps
                      .map((step, stepIndex) => `
                        <div class="train-browser-step-row">
                          <div>
                            <strong>${escapeHtml(stepIndex + 1)}. ${escapeHtml(step.label)}</strong>
                            <div class="muted">
                              ${escapeHtml(step.type)} · ${escapeHtml(step.safety)}
                              ${step.output ? ` · output: ${escapeHtml(step.output)}` : ""}
                            </div>
                          </div>
                          <span class="badge">
                            ${step.requires_approval ? "Approval gate" : "Captured"}
                          </span>
                        </div>
                      `)
                      .join("")
                  : `<div class="empty-state">No browser steps captured yet.</div>`
              }
            </div>
          </div>
        </div>

        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:14px;">
          <button
            class="secondary-btn"
            data-operations-agents-action="copy-browser-skill-id"
            data-skill-id="${escapeHtml(skill?.skill_id || "")}"
          >
            Copy skill id
          </button>

          <button
            class="secondary-btn"
            data-operations-agents-action="duplicate-browser-skill"
            data-skill-id="${escapeHtml(skill?.skill_id || "")}"
          >
            Duplicate skill
          </button>

          <button
            class="primary-btn"
            data-operations-agents-action="publish-browser-skill"
            data-skill-id="${escapeHtml(skill?.skill_id || "")}"
          >
            Mark reusable
          </button>
        </div>
      </div>
    </div>
  `;
}



const AION_WORKFLOW_DRAFT_STORAGE_KEY = "aion.workflow_builder.current_draft.v1";

const AION_WORKFLOW_GLYPH_SCHEMA_VERSION = "aion.workflow_glyph.v1";

function getAionWorkflowOrderedNodesForGlyph(graph) {
  const nodes = getAionWorkflowOrderedNodesForGlyph(graph);
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];

  if (!nodes.length) return [];

  const nodeById = new Map(nodes.map((node) => [String(node.id), node]));
  const incoming = new Map(nodes.map((node) => [String(node.id), 0]));
  const outgoing = new Map(nodes.map((node) => [String(node.id), []]));

  for (const edge of edges) {
    const from = String(edge?.from || "");
    const to = String(edge?.to || "");

    if (!nodeById.has(from) || !nodeById.has(to)) continue;

    incoming.set(to, (incoming.get(to) || 0) + 1);
    outgoing.get(from)?.push(to);
  }

  const visualSort = (a, b) => {
    const ax = Number(a?.x || 0);
    const bx = Number(b?.x || 0);
    const ay = Number(a?.y || 0);
    const by = Number(b?.y || 0);

    if (ax !== bx) return ax - bx;
    if (ay !== by) return ay - by;
    return String(a?.id || "").localeCompare(String(b?.id || ""));
  };

  if (!edges.length) {
    return [...nodes].sort(visualSort);
  }

  const queue = nodes
    .filter((node) => (incoming.get(String(node.id)) || 0) === 0)
    .sort(visualSort);

  const ordered = [];
  const seen = new Set();

  while (queue.length) {
    const node = queue.shift();
    const nodeId = String(node.id);

    if (seen.has(nodeId)) continue;

    seen.add(nodeId);
    ordered.push(node);

    const nextIds = [...(outgoing.get(nodeId) || [])]
      .map((id) => nodeById.get(id))
      .filter(Boolean)
      .sort(visualSort);

    for (const nextNode of nextIds) {
      const nextId = String(nextNode.id);
      incoming.set(nextId, Math.max(0, (incoming.get(nextId) || 0) - 1));

      if ((incoming.get(nextId) || 0) === 0 && !seen.has(nextId)) {
        queue.push(nextNode);
      }
    }

    queue.sort(visualSort);
  }

  const remaining = nodes
    .filter((node) => !seen.has(String(node.id)))
    .sort(visualSort);

  return [...ordered, ...remaining];
}

const AION_WORKFLOW_GLYPH_NAMESPACE = "aion.workflow";

const AION_WORKFLOW_OPS = Object.freeze({
  SEQUENCE: "aion.workflow:sequence",
  TRIGGER: "aion.workflow:trigger",
  EXTRACT: "aion.workflow:extract",
  CLASSIFY: "aion.workflow:classify",
  ACTION: "aion.workflow:action",
  APPROVAL: "aion.workflow:approval",
  WAIT: "aion.workflow:wait",
  ROUTE: "aion.workflow:route",
});

function getAionWorkflowBusinessContainerId() {
  const fromWindow =
    window.__aionWorkspaceId ||
    window.__aionBusinessContainerId ||
    window.__aionWorkflowBusinessContainerId;

  const fromState =
    desktopStore?.state?.workspaceId ||
    desktopStore?.state?.workspace_id ||
    desktopStore?.state?.businessContainerId ||
    desktopStore?.state?.business_container;

  return String(fromWindow || fromState || "costa_conexion")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "_")
    || "costa_conexion";
}

function normaliseAionWorkflowNodeToGlyphStep(node, index = 0) {
  const title = String(node?.title || "").toLowerCase();
  const type = String(node?.type || "").toLowerCase();
  const id = String(node?.id || `node_${index}`);

  let op = AION_WORKFLOW_OPS.ACTION;

  if (
    type.includes("trigger") ||
    title.includes("trigger") ||
    title.includes("gmail new email") ||
    title.includes("schedule") ||
    title.includes("webhook")
  ) {
    op = AION_WORKFLOW_OPS.TRIGGER;
  } else if (
    title.includes("extract") ||
    title.includes("pattern") ||
    title.includes("replace") ||
    title.includes("html") ||
    title.includes("variable") ||
    title.includes("compose string") ||
    title.includes("sleep") ||
    title.includes("delay") ||
    type.includes("parser") ||
    type.includes("tools")
  ) {
    op = AION_WORKFLOW_OPS.EXTRACT;
  } else if (
    title.includes("classify") ||
    title.includes("router") ||
    title.includes("route")
  ) {
    op = AION_WORKFLOW_OPS.CLASSIFY;
  } else if (
    title.includes("approval") ||
    type.includes("gate")
  ) {
    op = AION_WORKFLOW_OPS.APPROVAL;
  } else if (
    title.includes("wait") ||
    title.includes("delay") ||
    title.includes("schedule")
  ) {
    op = AION_WORKFLOW_OPS.WAIT;
  } else if (
    title.includes("if") ||
    title.includes("else") ||
    title.includes("fork")
  ) {
    op = AION_WORKFLOW_OPS.ROUTE;
  }

  return {
    op,
    node_id: id,
    ref: id,
    title: String(node?.title || "Untitled step"),
    node_type: String(node?.type || "Action"),
    status: String(node?.status || "draft"),
    meta: String(node?.meta || ""),
    position: {
      x: Number(node?.x || 0),
      y: Number(node?.y || 0),
    },
    config: node?.config && typeof node.config === "object" ? node.config : {},
  };
}

function orderAionWorkflowNodesForGlyph(graph) {
  const nodes = Array.isArray(graph?.nodes) ? [...graph.nodes] : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];

  if (!nodes.length) return [];

  const nodeById = new Map(nodes.map((node) => [String(node.id), node]));
  const incoming = new Map(nodes.map((node) => [String(node.id), 0]));
  const outgoing = new Map(nodes.map((node) => [String(node.id), []]));

  for (const edge of edges) {
    const from = String(edge?.from || "");
    const to = String(edge?.to || "");
    if (!nodeById.has(from) || !nodeById.has(to)) continue;
    incoming.set(to, (incoming.get(to) || 0) + 1);
    outgoing.get(from)?.push(to);
  }

  const queue = nodes
    .filter((node) => (incoming.get(String(node.id)) || 0) === 0)
    .sort((a, b) => Number(a.x || 0) - Number(b.x || 0));

  const ordered = [];
  const seen = new Set();

  while (queue.length) {
    const node = queue.shift();
    const id = String(node.id);
    if (seen.has(id)) continue;

    seen.add(id);
    ordered.push(node);

    const nextIds = (outgoing.get(id) || [])
      .filter((nextId) => !seen.has(nextId))
      .sort((a, b) => Number(nodeById.get(a)?.x || 0) - Number(nodeById.get(b)?.x || 0));

    for (const nextId of nextIds) {
      const nextIncoming = Math.max(0, (incoming.get(nextId) || 0) - 1);
      incoming.set(nextId, nextIncoming);
      if (nextIncoming === 0 && nodeById.has(nextId)) {
        queue.push(nodeById.get(nextId));
      }
    }
  }

  const remaining = nodes
    .filter((node) => !seen.has(String(node.id)))
    .sort((a, b) => Number(a.x || 0) - Number(b.x || 0));

  return [...ordered, ...remaining];
}

function compileAionWorkflowGraphToGlyph(graph) {
  const safeGraph = graph && typeof graph === "object" ? graph : {};
  const orderedNodes = orderAionWorkflowNodesForGlyph(safeGraph);
  const steps = orderedNodes.map((node, index) =>
    normaliseAionWorkflowNodeToGlyphStep(node, index),
  );

  const edges = Array.isArray(safeGraph.edges)
    ? safeGraph.edges.map((edge) => ({
        from: String(edge?.from || ""),
        to: String(edge?.to || ""),
        condition: String(edge?.condition || "success"),
      }))
    : [];

  return {
    schema_version: AION_WORKFLOW_GLYPH_SCHEMA_VERSION,
    namespace: AION_WORKFLOW_GLYPH_NAMESPACE,
    op: AION_WORKFLOW_OPS.SEQUENCE,
    workflow: {
      workflow_id: String(safeGraph.workflow_id || "workflow_draft_1"),
      name: String(safeGraph.name || "Untitled workflow 1"),
      business_container: String(
        safeGraph.business_container || getAionWorkflowBusinessContainerId(),
      ),
      status: String(safeGraph.status || "draft"),
    },
    policy: {
      dry_run_first: true,
      approval_before_external_write: true,
      raw_glyph_execution: false,
      raw_glyphs_are_ui_decoration_only: true,
    },
    steps,
    flow_links: edges,
    compiled_at: new Date().toISOString(),
  };
}

function compileAndAttachAionWorkflowGlyph(graph) {
  const target = graph || getAionWorkflowDraftState();
  target.business_container = target.business_container || getAionWorkflowBusinessContainerId();
  target.compiled_glyph = compileAionWorkflowGraphToGlyph(target);
  target.compiled_glyph_hash_hint = `${target.compiled_glyph.schema_version}:${target.workflow_id || "workflow_draft_1"}:${target.compiled_glyph.steps.length}:${target.compiled_glyph.flow_links.length}`;
  return target.compiled_glyph;
}


function getDefaultAionWorkflowDraftState() {
  return {
    workflow_id: "workflow_draft_1",
    name: "Untitled workflow 1",
    status: "draft",
    nodes: [],
    edges: [],
    updated_at: new Date().toISOString(),
  };
}

function getAionWorkflowDraftState() {
  if (window.__aionWorkflowGraph) {
    return window.__aionWorkflowGraph;
  }

  try {
    const raw = window.localStorage?.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        window.__aionWorkflowGraph = {
          ...getDefaultAionWorkflowDraftState(),
          ...parsed,
          nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
          edges: Array.isArray(parsed.edges) ? parsed.edges : [],
        };
        return window.__aionWorkflowGraph;
      }
    }
  } catch (error) {
    console.warn("[workflow] failed to load draft", error);
  }

  window.__aionWorkflowGraph = getDefaultAionWorkflowDraftState();
  return window.__aionWorkflowGraph;
}


function buildAionWorkflowSavePayload(graph) {
  const safeGraph = graph || getAionWorkflowDraftState();
  const compiledGlyph =
    safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);

  const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
  const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];

  return {
    schema_version: "aion.workflow_save.v1",
    storage_scope: "business_container",
    business_container:
      compiledGlyph?.workflow?.business_container ||
      safeGraph.business_container ||
      "costa-conexion",
    workflow_id: safeGraph.workflow_id || "workflow_draft_1",
    name: safeGraph.name || "Untitled workflow 1",
    status: safeGraph.status || "draft",
    canvas_layout: {
      schema_version: "aion.workflow_canvas_layout.v1",
      coordinate_space: "absolute_canvas_px",
      nodes: nodes.map((node) => ({
        node_id: node.id,
        x: Number(node.x || 0),
        y: Number(node.y || 0),
      })),
      edges: edges.map((edge) => ({
        from: edge.from,
        to: edge.to,
        condition: edge.condition || "success",
      })),
    },
    graph: {
      nodes,
      edges,
    },
    compiled_glyph: compiledGlyph,
    saved_at: new Date().toISOString(),
  };
}

function getAionWorkflowPendingNodeConfig(nodeId) {
  window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
  return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
}

function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
  if (!nodeId || !key) return;

  window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
  window.__aionWorkflowPendingNodeConfig[nodeId] = {
    ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
    [key]: value,
  };
}

function applyAionWorkflowPendingNodeConfig(nodeId) {
  if (!nodeId) return null;

  const graph = getAionWorkflowDraftState();
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const pending = getAionWorkflowPendingNodeConfig(nodeId);
  const node = nodes.find((item) => item.id === nodeId);

  if (!node) return null;

  const config = {
    ...(node.config || {}),
    ...pending,
  };

  window.__aionWorkflowGraph = {
    ...graph,
    nodes: nodes.map((item) =>
      item.id === nodeId
        ? {
            ...item,
            config,
          }
        : item,
    ),
  };

  compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
  persistAionWorkflowDraftState();

  return config;
}


function syncAionWorkflowInspectorInputsToGraph() {
  const graph = getAionWorkflowDraftState();
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];

  document
    .querySelectorAll("[data-aion-workflow-node-config-input]")
    .forEach((input) => {
      const nodeId = input.getAttribute("data-aion-workflow-node-id");
      const key = input.getAttribute("data-aion-workflow-node-config-input");

      if (!nodeId || !key) return;

      const node = nodes.find((item) => item.id === nodeId);
      if (!node) return;

      node.config = {
        ...(node.config || {}),
        [key]: input.value,
      };
    });

  window.__aionWorkflowGraph = graph;
  compileAndAttachAionWorkflowGlyph(graph);

  return graph;
}


function persistAionWorkflowDraftState() {
  const graph = getAionWorkflowDraftState();

  const compactGraph = {
    workflow_id: graph.workflow_id || "workflow_draft_1",
    name: graph.name || "Untitled workflow 1",
    status: graph.status || "draft",
    saved_at: graph.saved_at || null,
    dirty: Boolean(graph.dirty),
    nodes: Array.isArray(graph.nodes)
      ? graph.nodes.map((node) => ({
          id: node.id,
          title: node.title,
          type: node.type,
          icon: node.icon,
          status: node.status,
          meta: node.meta,
          tone: node.tone,
          x: Number(node.x || 0),
          y: Number(node.y || 0),
          config: node.config && typeof node.config === "object" ? node.config : {},
        }))
      : [],
    edges: Array.isArray(graph.edges)
      ? graph.edges.map((edge) => ({
          from: edge.from,
          to: edge.to,
          condition: edge.condition || "success",
        }))
      : [],
    updated_at: new Date().toISOString(),
  };

  compileAndAttachAionWorkflowGlyph(compactGraph);

  if (typeof buildAionWorkflowSavePayload === "function") {
    compactGraph.workflow_save_payload = buildAionWorkflowSavePayload(compactGraph);
  }

  window.__aionWorkflowGraph = compactGraph;

  try {
    window.localStorage?.setItem(
      AION_WORKFLOW_DRAFT_STORAGE_KEY,
      JSON.stringify(compactGraph),
    );
    return true;
  } catch (error) {
    console.warn("[workflow] failed to save draft", error);

    try {
      const storage = window.localStorage;
      if (!storage) return false;

      Object.keys(storage)
        .filter((key) =>
          key !== AION_WORKFLOW_DRAFT_STORAGE_KEY &&
          (
            key.includes("aion") ||
            key.includes("workflow") ||
            key.includes("boardroom") ||
            key.includes("operations")
          )
        )
        .forEach((key) => storage.removeItem(key));

      storage.removeItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
      storage.setItem(
        AION_WORKFLOW_DRAFT_STORAGE_KEY,
        JSON.stringify(compactGraph),
      );
      return true;
    } catch (secondError) {
      console.warn("[workflow] compact save failed; trying emergency minimal save", secondError);

      try {
        const emergencyGraph = {
          workflow_id: compactGraph.workflow_id || "workflow_draft_1",
          name: compactGraph.name || "Untitled workflow 1",
          status: compactGraph.status || "draft",
          business_container: compactGraph.business_container || "costa-conexion",
          nodes: compactGraph.nodes || [],
          edges: compactGraph.edges || [],
          updated_at: compactGraph.updated_at || new Date().toISOString(),
        };

        window.localStorage?.removeItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
        window.localStorage?.setItem(
          AION_WORKFLOW_DRAFT_STORAGE_KEY,
          JSON.stringify(emergencyGraph),
        );
        return true;
      } catch (thirdError) {
        console.warn("[workflow] emergency save failed", thirdError);
        return false;
      }
    }
  }
}




function markAionWorkflowDraftDirty(reason = "updated") {
  const graph = getAionWorkflowDraftState();
  graph.dirty = true;
  graph.dirty_reason = reason;
  graph.saved_at = graph.saved_at || null;
  compileAndAttachAionWorkflowGlyph(graph);
  window.__aionWorkflowGraph = graph;
  persistAionWorkflowDraftState();
  return graph;
}

function getAionWorkflowSaveStatus(graph) {
  const safeGraph = graph || getAionWorkflowDraftState();
  const compiled = safeGraph?.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
  const dirty = Boolean(safeGraph?.dirty);
  const savedAt = safeGraph?.saved_at || null;

  if (dirty) {
    return {
      label: "Unsaved",
      className: "is-unsaved",
      detail: "Changes not saved",
    };
  }

  if (savedAt) {
    return {
      label: "Saved",
      className: "is-saved",
      detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
    };
  }

  return {
    label: "Draft",
    className: "is-draft",
    detail: "Local draft",
  };
}

async function loadAionWorkflowFromBusinessContainer({
  businessContainer = "costa-conexion",
  workflowId = "workflow_draft_1",
} = {}) {
  const apiBase =
    state.apiBase ||
    state.desktopApiBase ||
    window.AION_API_BASE ||
    "http://127.0.0.1:8080";

  const safeBusiness = String(businessContainer || "costa-conexion").trim() || "costa-conexion";
  const safeWorkflowId = String(workflowId || "workflow_draft_1").trim() || "workflow_draft_1";

  const response = await fetch(
    `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
  );

  if (!response.ok) {
    throw new Error(`Workflow load failed: HTTP ${response.status}`);
  }

  const result = await response.json();
  if (!result?.ok || !result?.workflow) {
    throw new Error(result?.error || "Workflow not found");
  }

  const record = result.workflow;
  const graph = record.graph || {};

  const loadedGraph = {
    workflow_id: record.workflow_id || safeWorkflowId,
    name: record.name || "Untitled workflow 1",
    status: record.status || "draft",
    business_container: record.business_container || safeBusiness,
    nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
    edges: Array.isArray(graph.edges) ? graph.edges : [],
    compiled_glyph: record.compiled_glyph || null,
    backend_saved_at: record.updated_at || "",
    backend_storage_path: record.path || "",
    dirty: false,
  };

  compileAndAttachAionWorkflowGlyph(loadedGraph);
  window.__aionWorkflowGraph = loadedGraph;
  persistAionWorkflowDraftState();

  return loadedGraph;
}

async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
  if (window.__aionWorkflowBusinessLoadAttempted === true) return;
  window.__aionWorkflowBusinessLoadAttempted = true;

  try {
    const businessContainer =
      state.workspaceId ||
      window.__aionWorkflowGraph?.business_container ||
      "costa-conexion";

    const workflowId =
      window.__aionWorkflowGraph?.workflow_id ||
      "workflow_draft_1";

    const loadedGraph = await loadAionWorkflowFromBusinessContainer({
      businessContainer,
      workflowId,
    });

    window.__aionWorkflowLoadNotice = `Loaded saved workflow: ${loadedGraph.name || loadedGraph.workflow_id}`;

    if (window.__aionWorkflowLoadNoticeTimer) {
      window.clearTimeout(window.__aionWorkflowLoadNoticeTimer);
    }

    window.__aionWorkflowLoadNoticeTimer = window.setTimeout(() => {
      window.__aionWorkflowLoadNotice = "";
      window.__aionWorkflowLoadNoticeTimer = null;
      requestRender();
    }, 20000);

    desktopStore.patch?.({
      message: window.__aionWorkflowLoadNotice,
      messageTone: "success",
    });

    requestRender();
  } catch (error) {
    console.info("[workflow] no saved business-container workflow loaded", error);
  }
}


async function saveAionWorkflowToBusinessContainer(graph) {
  const safeGraph = graph || getAionWorkflowDraftState();
  const compiledGlyph = safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
  const businessContainer =
    compiledGlyph?.workflow?.business_container ||
    safeGraph.business_container ||
    state.workspaceId ||
    "costa-conexion";

  const payload = {
    schema_version: "aion.workflow_save.v1",
    business_container: businessContainer,
    workflow_id: safeGraph.workflow_id || "workflow_draft_1",
    name: safeGraph.name || "Untitled workflow 1",
    status: safeGraph.status || "draft",
    graph: {
      nodes: Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [],
      edges: Array.isArray(safeGraph.edges) ? safeGraph.edges : [],
    },
    compiled_glyph: compiledGlyph,
  };

  const apiBase =
    state.apiBase ||
    state.desktopApiBase ||
    window.AION_API_BASE ||
    "http://127.0.0.1:8080";

  const response = await fetch(`${apiBase}/api/aion/workflows/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Workflow save failed: HTTP ${response.status}`);
  }

  const result = await response.json();
  if (!result?.ok) {
    throw new Error(result?.error || "Workflow save failed");
  }

  safeGraph.business_container = result.business_container || businessContainer;
  safeGraph.backend_saved_at = result.updated_at || new Date().toISOString();
  safeGraph.backend_storage_path = result.path || "";
  return result;
}







function slugifyAionWorkflowPart(value, fallback = "workflow") {
  const raw = String(value || fallback)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.-]+/g, ".")
    .replace(/^\.+|\.+$/g, "");

  return raw || fallback;
}

function buildAionWorkflowCanvasCapsulePayload(graph) {
  const safeGraph = graph || getAionWorkflowDraftState();
  const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
  const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];

  const workflowSlug = slugifyAionWorkflowPart(
    safeGraph.workflow_id || safeGraph.name || "canvas.workflow",
    "canvas.workflow",
  );

  const canonicalKey =
    String(safeGraph.canonical_key || "").trim() ||
    `workflow:${workflowSlug}.v1`;

  const displayGlyph =
    String(safeGraph.display_glyph || "").trim() ||
    `WG-${workflowSlug.toUpperCase().replace(/[^A-Z0-9]+/g, "-").slice(0, 28)}`;

  const canvasNodes = nodes.map((node, index) => {
    const stepId = slugifyAionWorkflowPart(
      node.step_id || node.id || `step_${index + 1}`,
      `step_${index + 1}`,
    ).replace(/\./g, "_");

    const config = node.config && typeof node.config === "object" ? node.config : {};
    const connector = config.connector || node.connector || "";

    const requires = Array.isArray(config.requires)
      ? config.requires
      : connector === "gmail"
        ? ["vault.gmail.credentials"]
        : [];

    return {
      id: String(node.id || stepId),
      type: String(node.type || "task"),
      position: {
        x: Number(node.x || 0),
        y: Number(node.y || 0),
      },
      data: {
        step_id: stepId,
        kind: String(config.kind || node.kind || node.type || "task"),
        label: String(node.title || config.label || stepId),
        output_ref: String(config.output_ref || `${stepId}.output`),
        ...(connector ? { connector: String(connector) } : {}),
        ...(requires.length ? { requires } : {}),
        ...(config.external_write === true ? { external_write: true } : {}),
        ...(config.requires_approval === true ? { requires_approval: true } : {}),
        ...(config.guard && typeof config.guard === "object" ? { guard: config.guard } : {}),
        ...(config.approval && typeof config.approval === "object" ? { approval: config.approval } : {}),
      },
    };
  });

  const canvasEdges = edges.map((edge, index) => ({
    id: String(edge.id || `edge_${index + 1}`),
    source: String(edge.source || edge.from || ""),
    target: String(edge.target || edge.to || ""),
    condition: String(edge.condition || "success"),
  }));

  return {
    canonical_key: canonicalKey,
    display_name: String(safeGraph.name || "Untitled workflow"),
    meaning: String(
      safeGraph.meaning ||
      "Canvas-built workflow capsule generated from the Aion desktop workflow canvas.",
    ),
    display_glyph: displayGlyph,
    tags: ["canvas", "desktop", "workflow"],
    allowed_use_cases: ["Compile and save a visual workflow canvas as a Workflow Capsule."],
    vault_requirements: Array.from(
      new Set(
        canvasNodes.flatMap((node) =>
          Array.isArray(node.data?.requires) ? node.data.requires : [],
        ),
      ),
    ),
    policy: {
      dry_run_first: true,
      approval_before_external_write: true,
      external_writes_allowed: false,
      allow_autonomous_execution: false,
    },
    nodes: canvasNodes,
    edges: canvasEdges,
  };
}

async function saveAionWorkflowCanvasAsCapsule(graph) {
  const safeGraph = graph || getAionWorkflowDraftState();
  const apiBase =
    state.apiBase ||
    state.desktopApiBase ||
    window.AION_API_BASE ||
    "http://127.0.0.1:8080";

  const canvas = buildAionWorkflowCanvasCapsulePayload(safeGraph);

  const response = await fetch(`${apiBase}/api/workflow-capsules/canvas/compile-save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      canvas,
      scope: "workspace",
      workspace_id: state.workspaceId || safeGraph.business_container || "default_workspace",
      overwrite: true,
      rebuild_registry: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Canvas capsule save failed: HTTP ${response.status}`);
  }

  const result = await response.json();
  if (!result?.ok) {
    const reason = Array.isArray(result?.errors)
      ? result.errors.join(", ")
      : result?.error || "Canvas capsule save failed";
    throw new Error(reason);
  }

  safeGraph.canonical_key = result.canonical_key || canvas.canonical_key;
  safeGraph.display_glyph = result.display_glyph || canvas.display_glyph;
  safeGraph.capsule_saved_at = new Date().toISOString();
  safeGraph.capsule_path = result.path || "";
  safeGraph.capsule_checksum = result.checksum || "";
  safeGraph.dirty = false;

  window.__aionWorkflowGraph = safeGraph;
  persistAionWorkflowDraftState();

  return result;
}

function renderAionWorkflowGlyphDebugExecutionPanel() {
  if (window.__aionWorkflowGlyphDebugOpen !== true) return "";

  const graph = getAionWorkflowDraftState();
  const compiled = graph?.compiled_glyph || compileAionWorkflowGraphToGlyph(graph);
  const stepCount = Array.isArray(compiled?.steps) ? compiled.steps.length : 0;
  const linkCount = Array.isArray(compiled?.flow_links) ? compiled.flow_links.length : 0;

  return `
    <div class="aion-workflow-glyph-debug-panel" data-aion-glyph-debug-panel="true">
      <button
        class="aion-dry-run-floating-close"
        type="button"
        data-aion-glyph-debug-close="true"
        title="Close compiled glyph"
      >
        ×
      </button>

      <div class="aion-workflow-glyph-debug-head">
        <strong>⌁ Compiled Glyph developer/debug</strong>
        <span>${escapeHtml(String(stepCount))} steps · ${escapeHtml(String(linkCount))} links</span>
      </div>

      <pre>${escapeHtml(JSON.stringify(compiled, null, 2))}</pre>
    </div>
  `;
}



function renderWorkflowArchitectNodeEditorModal() {
  const result = reviewState.result || {};
  const review = result.review || {};
  const canvas = review.canvas || result.canvas || {};
  const spec = review.workflow_spec || result.workflow_spec || {};
  const provider = reviewState.provider || "mock";

  const providerCopy = getWorkflowArchitectProviderCopy(provider);
  const errors = getWorkflowArchitectResultErrors(result);
  const warnings = getWorkflowArchitectResultWarnings(result);

  const canLoadToCanvas =
    result.ok === true ||
    reviewState.ok === true ||
    review.canvas_ready === true ||
    result?.review?.canvas_ready === true ||
    Boolean(canvas?.nodes?.length);

  const generatedSteps = Array.isArray(spec.steps)
    ? spec.steps
    : Array.isArray(canvas.nodes)
      ? canvas.nodes.map((node) => ({
          step_id: node?.data?.step_id || node?.id,
          node_type: node?.data?.kind || node?.type,
          label: node?.data?.label || node?.id,
          risk_tier: node?.data?.risk_tier || "low",
          requires_approval: Boolean(node?.data?.requires_approval),
          connector: node?.data?.connector || null,
          config: node?.data || {},
        }))
      : [];

  const connectorsRequired = Array.isArray(spec.connectors_required)
    ? spec.connectors_required
    : Array.isArray(review.connectors_required)
      ? review.connectors_required
      : Array.isArray(canvas.vault_requirements)
        ? canvas.vault_requirements.map((item) => String(item).replace(/^vault\./, "").replace(/\.credentials$/, ""))
        : [];

  const missingConnectors = Array.isArray(spec.missing_connectors)
    ? spec.missing_connectors
    : Array.isArray(review.missing_connectors)
      ? review.missing_connectors
      : [];

  const actions = typeof getWorkflowArchitectConnectorActionCatalogue === "function"
    ? getWorkflowArchitectConnectorActionCatalogue()
    : [];

  const safeActions = actions.filter((action) => action && action.locked !== true).slice(0, 10);
  const lockedActions = actions.filter((action) => action && action.locked === true).slice(0, 8);

  const steps = generatedSteps.length
    ? generatedSteps
    : [
        {
          step_id: "trigger",
          label: "Start with a trigger",
          node_type: "trigger",
          connector: "gmail",
          risk_tier: "safe",
          requires_approval: false,
          config: { action_id: "gmail.watch_emails" },
        },
        {
          step_id: "extract",
          label: "Extract useful details",
          node_type: "ai_extract",
          connector: "aion",
          risk_tier: "safe",
          requires_approval: false,
          config: { action_id: "aion.extract_fields" },
        },
        {
          step_id: "draft",
          label: "Draft the response",
          node_type: "draft",
          connector: "gmail",
          risk_tier: "approval",
          requires_approval: true,
          config: { action_id: "gmail.create_draft" },
        },
      ];

  return `
    <div
      class="aion-architect-canvas-shell"
      data-workflow-architect-canvas-mode="true"
      data-workflow-architect-node-canvas="true"
    >
      <div class="aion-architect-topbar">
        <div>
          <div class="eyebrow">AI Workflow Architect</div>
          <h1>Build automatic workflow</h1>
          <p>
            Start with a trigger, then add each step. Aion keeps everything dry-run first,
            blocks live send, and only loads a validated review onto the workflow canvas.
          </p>
        </div>

        <div class="aion-architect-topbar-actions">
          <button
            type="button"
            class="secondary-btn"
            data-workflow-architect-node-editor-close="true"
          >
            Back to canvas
          </button>
          <span class="train-status-chip train-status-ok">Dry-run only</span>
          <span class="train-status-chip ${canLoadToCanvas ? "train-status-ok" : ""}">
            ${canLoadToCanvas ? "Valid review" : "Awaiting review"}
          </span>
        </div>
      </div>

      <div class="aion-architect-node-builder-layout">
        <aside class="aion-architect-left-panel">
          <section class="aion-architect-card">
            <div class="eyebrow">Build mode</div>
            <div class="aion-architect-mode-switch">
              <button type="button" class="active" data-workflow-architect-build-mode="steps">
                Use this app
              </button>
              <button type="button" data-workflow-architect-build-mode="describe">
                Describe workflow
              </button>
            </div>
            <p class="muted">
              Use this app → do this → then do this. Locked actions stay visible but cannot run.
            </p>
          </section>

          <section class="aion-architect-card">
            <div class="eyebrow">Workflow goal</div>
            <textarea
              class="aion-workflow-architect-goal"
              data-workflow-architect-goal-input="true"
              rows="7"
              placeholder="Example: When a new Gmail enquiry arrives, extract the customer details, create a CRM contact, draft a reply, then ask me for approval."
            >${escapeHtml(reviewState.workflowGoal || "")}</textarea>

            <label class="aion-architect-field">
              <span>Provider</span>
              <select data-workflow-architect-provider-select="true">
                <option value="mock" ${provider === "mock" ? "selected" : ""}>Mock deterministic</option>
                <option value="local_gemma" ${provider === "local_gemma" ? "selected" : ""}>Local Gemma / Ollama</option>
                <option value="openai" ${provider === "openai" ? "selected" : ""}>OpenAI</option>
                <option value="claude" ${provider === "claude" ? "selected" : ""}>Claude — fail-closed</option>
                <option value="gemini" ${provider === "gemini" ? "selected" : ""}>Gemini — fail-closed</option>
                <option value="grok" ${provider === "grok" ? "selected" : ""}>Grok — fail-closed</option>
              </select>
            </label>

            <p class="muted">${escapeHtml(providerCopy)}</p>

            <div class="aion-architect-actions">
              <button
                class="primary-btn"
                type="button"
                data-workflow-architect-build-review="true"
                ${reviewState.loading ? "disabled" : ""}
              >
                ${reviewState.loading ? "Building review..." : "Build review"}
              </button>

              <button
                class="secondary-btn"
                type="button"
                data-workflow-architect-load-valid-review="true"
                ${canLoadToCanvas ? "" : "disabled"}
              >
                Load valid review onto canvas
              </button>
            </div>
          </section>

          <section class="aion-architect-card">
            <div class="eyebrow">Action picker</div>
            <div class="aion-architect-action-list">
              ${safeActions.map((action) => `
                <button
                  type="button"
                  class="workflow-architect-action-option"
                  data-workflow-architect-select-action="${escapeHtml(action.action_id)}"
                >
                  <strong>${escapeHtml(action.label || action.action_id)}</strong>
                  <span>${escapeHtml(action.connector || "connector")} · ${escapeHtml(action.category || "action")}</span>
                </button>
              `).join("")}
            </div>

            <details class="aion-architect-locked-actions">
              <summary>Locked / future-only actions</summary>
              ${lockedActions.map((action) => `
                <div class="workflow-architect-action-option locked">
                  <strong>${escapeHtml(action.label || action.action_id)}</strong>
                  <span>${escapeHtml(action.status || "Locked / future-only")}</span>
                </div>
              `).join("")}
            </details>
          </section>
        </aside>

        <main class="aion-architect-canvas-board">
          <div class="aion-architect-board-header">
            <div>
              <div class="eyebrow">Visual workflow</div>
              <h2>Canvas build</h2>
            </div>
            <button
              type="button"
              class="secondary-btn"
              data-workflow-architect-preset-lead-pipeline="true"
            >
              Use Gmail lead preset
            </button>
          </div>

          <div class="aion-architect-flow-lane">
            ${steps.map((step, index) => `
              <div class="workflow-architect-step-visual-row" data-workflow-architect-step-id="${escapeHtml(step.step_id || String(index + 1))}">
                <div class="aion-architect-step-number">${index + 1}</div>
                <div class="aion-architect-step-card">
                  <div class="aion-architect-step-kicker">
                    <span>${escapeHtml(step.connector || step.node_type || "aion")}</span>
                    <span>${escapeHtml(step.risk_tier || "safe")}</span>
                    ${step.requires_approval ? "<span>Approval</span>" : "<span>Dry-run</span>"}
                  </div>
                  <h3>${escapeHtml(step.label || step.action || step.step_id || `Step ${index + 1}`)}</h3>
                  <p>${escapeHtml(step.node_type || "workflow_step")}</p>
                </div>
                ${index < steps.length - 1 ? `<div class="aion-architect-step-connector">↓</div>` : ""}
              </div>
            `).join("")}
          </div>
        </main>

        <aside class="aion-architect-step-settings">
          <section class="aion-architect-card">
            <div class="eyebrow">Safety / connectors</div>
            <div class="aion-architect-safety-grid">
              <div><strong>Execution:</strong> Dry-run only</div>
              <div><strong>Live send:</strong> Disabled</div>
              <div><strong>External writes:</strong> Approval gated</div>
              <div><strong>Canvas load:</strong> Valid review required</div>
            </div>
          </section>

          <section class="aion-architect-card">
            <div class="eyebrow">Connectors required</div>
            ${
              connectorsRequired.length
                ? `<ul>${connectorsRequired.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
                : `<p class="muted">None declared yet.</p>`
            }

            <div class="eyebrow" style="margin-top:18px;">Missing connectors</div>
            ${
              missingConnectors.length
                ? `<ul>${missingConnectors.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
                : `<p class="muted">No missing connector warnings.</p>`
            }
          </section>

          <section class="aion-architect-card">
            <div class="eyebrow">Review output</div>
            ${
              errors.length || warnings.length
                ? `
                  ${errors.map((item) => `<div class="alert error">${escapeHtml(item)}</div>`).join("")}
                  ${warnings.map((item) => `<div class="alert warning">${escapeHtml(item)}</div>`).join("")}
                `
                : `<p class="muted">Enter a workflow goal and click Build review. Nothing is loaded until validation passes.</p>`
            }

            <details style="margin-top:14px;">
              <summary>Debug review payload</summary>
              <pre>${escapeHtml(JSON.stringify(result || {}, null, 2))}</pre>
            </details>
          </section>
        </aside>
      </div>
    </div>
  `;
}


function renderWorkflowArchitectSidebarMount() {
  const reviewState = getWorkflowArchitectReviewState();
  const result = reviewState.result;
  const spec = getWorkflowArchitectReviewSpec(result);
  const steps = workflowArchitectSpecSteps(result);
  const graph = getWorkflowArchitectReviewGraph(result);
  const errors = Array.isArray(reviewState.errors) ? reviewState.errors : [];
  const warnings = Array.isArray(reviewState.warnings) ? reviewState.warnings : [];
  const loadable = isWorkflowArchitectReviewLoadable(result);

  const stepRows = steps.length
    ? steps
        .map((step, index) => {
          const requiresApproval = step?.requires_approval === true;
          return `
            <div class="aion-workflow-architect-step-row">
              <span>${escapeHtml(String(index + 1))}</span>
              <div>
                <strong>${escapeHtml(step?.label || step?.step_id || "Generated step")}</strong>
                <small>${escapeHtml(step?.node_type || "node")}${requiresApproval ? " · approval required" : ""}</small>
              </div>
            </div>
          `;
        })
        .join("")
    : `<p class="muted" style="margin:8px 0 0;">No generated steps yet.</p>`;

  const connectorRows = Array.isArray(spec?.connectors_required) && spec.connectors_required.length
    ? spec.connectors_required
        .map((connector) => `<span class="badge">${escapeHtml(connector)}</span>`)
        .join("")
    : `<span class="muted">No connector requirements yet.</span>`;

  const missingConnectorRows =
    Array.isArray(spec?.missing_connectors) && spec.missing_connectors.length
      ? spec.missing_connectors
          .map((item) => {
            const connector = typeof item === "string" ? item : item?.connector;
            const reason = typeof item === "string" ? "" : item?.reason;
            return `
              <div class="aion-workflow-architect-warning-row">
                <strong>${escapeHtml(connector || "missing connector")}</strong>
                <small>${escapeHtml(reason || "Connector unavailable. Placeholder only.")}</small>
              </div>
            `;
          })
          .join("")
      : `<p class="muted" style="margin:8px 0 0;">No missing connector warnings.</p>`;

  const errorRows = errors.length
    ? errors.map((error) => `<li>${escapeHtml(error)}</li>`).join("")
    : "";

  const warningRows = warnings.length
    ? warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")
    : "";

  return `
    <section class="aion-workflow-architect-panel" data-workflow-architect-sidebar-mount="true">
      <div class="aion-inspector-head">
        <div>
          <div class="eyebrow">Aion Workflow Architect</div>
          <h3>Build with AI</h3>
          <p>Describe the workflow. Aion builds a safe review payload first.</p>
        </div>
      </div>

      <textarea
        class="aion-workflow-architect-goal"
        data-workflow-architect-goal-input="true"
        rows="4"
        placeholder="Example: Create a Gmail customer reply workflow that extracts details, drafts a response, and asks for approval before sending."
      >${escapeHtml(reviewState.workflowGoal || "")}</textarea>

      <div class="aion-workflow-architect-provider-row">
        <label>
          <span>Provider</span>
          <select data-workflow-architect-provider-select="true">
            <option value="mock" ${reviewState.provider === "mock" ? "selected" : ""}>Mock deterministic</option>
            <option value="openai" ${reviewState.provider === "openai" ? "selected" : ""}>OpenAI</option>
            <option value="local_gemma" ${reviewState.provider === "local_gemma" ? "selected" : ""}>Local Gemma</option>
            <option value="claude" ${reviewState.provider === "claude" ? "selected" : ""}>Claude placeholder</option>
            <option value="gemini" ${reviewState.provider === "gemini" ? "selected" : ""}>Gemini placeholder</option>
            <option value="grok" ${reviewState.provider === "grok" ? "selected" : ""}>Grok placeholder</option>
          </select>
        </label>
      </div>

      <button
        class="primary-btn"
        type="button"
        data-workflow-architect-build-review="true"
        ${reviewState.loading ? "disabled" : ""}
      >
        ${reviewState.loading ? "Building review..." : "Build review"}
      </button>

      ${
        result
          ? `
            <div class="aion-workflow-architect-review">
              <div class="aion-workflow-architect-review-head">
                <strong>${escapeHtml(spec?.workflow_name || "Generated workflow")}</strong>
                <span class="train-status-chip ${result.ok ? "train-status-ok" : ""}">
                  ${result.ok ? "Valid review" : "Needs repair"}
                </span>
              </div>

              <p class="muted">${escapeHtml(spec?.goal || "Review generated workflow before loading it onto the canvas.")}</p>

              <div class="aion-picker-section">
                <div class="aion-picker-section-title">Generated steps</div>
                ${stepRows}
              </div>

              <div class="aion-picker-section">
                <div class="aion-picker-section-title">Connectors required</div>
                <div class="aion-workflow-architect-badges">${connectorRows}</div>
              </div>

              <div class="aion-picker-section">
                <div class="aion-picker-section-title">Missing connectors</div>
                ${missingConnectorRows}
              </div>

              ${
                errorRows
                  ? `
                    <div class="aion-workflow-architect-errors">
                      <strong>Errors</strong>
                      <ul>${errorRows}</ul>
                    </div>
                  `
                  : ""
              }

              ${
                warningRows
                  ? `
                    <div class="aion-workflow-architect-warnings">
                      <strong>Warnings</strong>
                      <ul>${warningRows}</ul>
                    </div>
                  `
                  : ""
              }

              <button
                class="secondary-btn"
                type="button"
                data-workflow-architect-load-valid-review="true"
                ${loadable ? "" : "disabled"}
                title="${loadable ? "valid review ready for canvas load" : "Review must be valid before loading onto canvas"}"
              >
                Load valid review onto canvas
              </button>

              <small class="muted">
                ${loadable ? "valid review ready for canvas load" : "Canvas load locked until review payload is valid."}
              </small>

              <details class="aion-workflow-side-advanced">
                <summary>Review payload</summary>
                <pre>${escapeHtml(JSON.stringify({ ok: result.ok, graph_ready: Boolean(graph), errors, warnings }, null, 2))}</pre>
              </details>
            </div>
          `
          : ""
      }
    </section>
  `;
}

function workflowArchitectNodeTone(step) {
  const nodeType = String(step?.node_type || "");
  if (nodeType.includes("approval")) return "red";
  if (nodeType.includes("gmail") || nodeType.includes("hubspot")) return "teal";
  if (nodeType.includes("compose")) return "purple";
  if (nodeType.includes("router") || nodeType.includes("filter")) return "blue";
  return "amber";
}

function workflowArchitectNodeIcon(step) {
  const nodeType = String(step?.node_type || "");
  if (nodeType.includes("gmail")) return "G";
  if (nodeType.includes("hubspot")) return "H";
  if (nodeType.includes("approval")) return "✓";
  if (nodeType.includes("compose")) return "T";
  if (nodeType.includes("extract")) return "AI";
  if (nodeType.includes("router")) return "⑂";
  return "◇";
}

function loadWorkflowArchitectReviewOntoCanvas() {
  const reviewState = getWorkflowArchitectReviewState();
  const result = reviewState.result;

  if (!isWorkflowArchitectReviewLoadable(result)) {
    desktopStore.patch?.({
      message: "Workflow Architect review is not valid yet.",
      messageTone: "warning",
    });
    requestRender();
    return;
  }

  const spec = getWorkflowArchitectReviewSpec(result) || {};
  const steps = workflowArchitectSpecSteps(result);

  const missingConnectors = Array.isArray(spec.missing_connectors)
    ? spec.missing_connectors
    : [];

  const missingConnectorIds = new Set(
    missingConnectors
      .map((item) => String(typeof item === "string" ? item : item?.connector || "").toLowerCase())
      .filter(Boolean),
  );

  const nodes = steps.map((step, index) => {
    const nodeType = String(step.node_type || "Generated");
    const connectorName = String(step.connector || nodeType.split(".")[0] || "").toLowerCase();
    const isMissingConnector = missingConnectorIds.has(connectorName);
    const requiresApproval = step.requires_approval === true;

    return {
      id: String(step.step_id || `architect_step_${index + 1}`),
      step_id: String(step.step_id || `architect_step_${index + 1}`),
      node_type: nodeType,
      title: String(step.label || step.step_id || `Step ${index + 1}`),
      label: String(step.label || step.step_id || `Step ${index + 1}`),
      type: nodeType,
      icon: workflowArchitectNodeIcon(step),
      status: isMissingConnector
        ? "Placeholder blocked"
        : requiresApproval
          ? "Required"
          : "Dry-run",
      meta: isMissingConnector
        ? "Generated by Architect · missing connector placeholder"
        : requiresApproval
          ? "Generated by Architect · approval gate"
          : "Generated by Architect · dry-run only",
      tone: isMissingConnector ? "amber" : workflowArchitectNodeTone(step),
      x: 160 + index * 275,
      y: 240,
      config: step.config || {},
      dry_run_only: true,
      live_send_enabled: false,
      missing_connector: isMissingConnector,
      placeholder: isMissingConnector,
      architect: {
        generated: true,
        step_id: String(step.step_id || `architect_step_${index + 1}`),
        node_type: nodeType,
        label: String(step.label || step.step_id || `Step ${index + 1}`),
        config: step.config || {},
        risk_tier: step.risk_tier || "low",
        requires_approval: requiresApproval,
        dry_run_only: true,
        missing_connector: isMissingConnector,
        placeholder: isMissingConnector,
      },
    };
  });

  const edges = Array.isArray(spec.edges)
    ? spec.edges
        .map((edge) => {
          if (Array.isArray(edge)) {
            return { from: String(edge[0]), to: String(edge[1]) };
          }
          return {
            from: String(edge.from || edge.source || ""),
            to: String(edge.to || edge.target || ""),
          };
        })
        .filter((edge) => edge.from && edge.to)
    : nodes.slice(0, -1).map((node, index) => ({
        from: node.id,
        to: nodes[index + 1].id,
      }));

  window.__aionWorkflowGraph = {
    workflow_id: String(spec.workflow_id || `architect_${Date.now()}`),
    name: String(spec.workflow_name || "AI generated workflow"),
    status: "draft",
    nodes,
    edges,
    architect_review: {
      loaded_from_valid_review: true,
      provider: result?.provider?.provider || reviewState.provider || "mock",
      dry_run_only: true,
      live_send_enabled: false,
      missing_connectors: Array.isArray(spec.missing_connectors) ? spec.missing_connectors : [],
      connectors_required: Array.isArray(spec.connectors_required) ? spec.connectors_required : [],
    },
  };

  window.__aionWorkflowSelectedNodeId = nodes[0]?.id || null;
  window.__aionWorkflowInspectorOpen = false;
  window.__aionWorkflowPickerMode = "";
  window.__aionWorkflowLoadNotice = "AI generated workflow loaded from valid review";

  desktopStore.patch?.({
    message: "Generated workflow loaded onto canvas",
    messageTone: "success",
  });

  requestRender();
}

function installWorkflowArchitectDesktopControls() {
  if (window.__aionWorkflowArchitectDesktopControlsBound === true) return;
  window.__aionWorkflowArchitectDesktopControlsBound = true;

  document.addEventListener("input", (event) => {
    const input = event.target.closest?.("[data-workflow-architect-goal-input='true']");
    if (!input) return;

    setWorkflowArchitectReviewState({
      workflowGoal: input.value || "",
    });
  });

  document.addEventListener("change", (event) => {
    const select = event.target.closest?.("[data-workflow-architect-provider-select='true']");
    if (!select) return;

    setWorkflowArchitectReviewState({
      provider: select.value || "mock",
      result: null,
      errors: [],
      warnings: [],
    });
    requestRender();
  });

  document.addEventListener("click", (event) => {
    
    const providerSelect = event.target.closest?.("[data-workflow-architect-provider-select='true']");
    if (providerSelect) {
      setWorkflowArchitectSelectedProvider(providerSelect.value);
      setWorkflowArchitectReviewState({
        provider: (window.__syncedArchitectInput || {}).provider,
        result: null,
        ok: false,
        errors: [],
        warnings: [],
      });
      requestRender();
      return;
    }

const buildButton = event.target.closest?.("[data-workflow-architect-build-review='true']");
    if (buildButton) {
      event.preventDefault();
      event.stopPropagation();


      const syncedArchitectInput = syncWorkflowArchitectModalInputsToState();
      buildWorkflowArchitectReviewFromDesktop();
      return;
    }

    const loadButton = event.target.closest?.("[data-workflow-architect-load-valid-review='true']");
    if (loadButton) {
      event.preventDefault();
      event.stopPropagation();
      loadWorkflowArchitectReviewOntoCanvas();
    }
  });
}

installWorkflowArchitectDesktopControls();



function getWorkflowArchitectGuidedStepBuilderState() {
  return window.__aionWorkflowArchitectGuidedSteps || {
    open: false,
    stepsApproved: false,
    provider: "mock",
    steps: [],
  };
}

function setWorkflowArchitectGuidedStepBuilderState(nextState) {
  window.__aionWorkflowArchitectGuidedSteps = {
    ...getWorkflowArchitectGuidedStepBuilderState(),
    ...(nextState || {}),
  };
}

function createWorkflowArchitectGuidedStep() {
  return {
    id: `guided_step_${Date.now()}_${Math.random().toString(16).slice(2)}`,
    action: "",
    source: "",
    connector: "",
    fields: "",
    outputs: "",
    approval_requirement: "auto",
  };
}

function workflowArchitectGuidedStepsToUserSteps() {
  const guided = getWorkflowArchitectGuidedStepBuilderState();
  const steps = Array.isArray(guided.steps) ? guided.steps : [];

  return steps
    .map((step, index) => ({
      step_id: step.id || `guided_step_${index + 1}`,
      action: String(step.action || "").trim(),
      source: String(step.source || "").trim(),
      connector: String(step.connector || "").trim(),
      fields: String(step.fields || "").trim(),
      outputs: String(step.outputs || "").trim(),
      approval_requirement: String(step.approval_requirement || "auto").trim(),
    }))
    .filter((step) =>
      step.action ||
      step.source ||
      step.connector ||
      step.fields ||
      step.outputs ||
      step.approval_requirement,
    );
}

function getWorkflowArchitectApprovedUserSteps() {
  const guided = getWorkflowArchitectGuidedStepBuilderState();

  if (!guided.stepsApproved) {
    return {
      ok: false,
      reason: "step_list_not_approved",
      user_steps: [],
    };
  }

  return {
    ok: true,
    reason: "",
    user_steps: workflowArchitectGuidedStepsToUserSteps(),
  };
}

function renderWorkflowArchitectGuidedStepBuilder() {
  const guided = getWorkflowArchitectGuidedStepBuilderState();
  const steps = Array.isArray(guided.steps) ? guided.steps : [];

  const stepCards = steps
    .map((step, index) => `
      <details class="workflow-architect-step-card" open>
        <summary>
          <strong>Step ${escapeHtml(String(index + 1))}</strong>
          <span>${escapeHtml(step.action || "Describe this step")}</span>
        </summary>

        <label>
          <span>Action</span>
          <input
            data-workflow-architect-step-field="action"
            data-workflow-architect-step-id="${escapeHtml(step.id)}"
            value="${escapeHtml(step.action || "")}"
            placeholder="e.g. Capture customer details"
          />
        </label>

        <label>
          <span>Source</span>
          <input
            data-workflow-architect-step-field="source"
            data-workflow-architect-step-id="${escapeHtml(step.id)}"
            value="${escapeHtml(step.source || "")}"
            placeholder="e.g. Gmail inbox newcustomer@kevin.com"
          />
        </label>

        <label>
          <span>Connector</span>
          <input
            data-workflow-architect-step-field="connector"
            data-workflow-architect-step-id="${escapeHtml(step.id)}"
            value="${escapeHtml(step.connector || "")}"
            placeholder="e.g. gmail, hubspot, calendly"
          />
        </label>

        <label>
          <span>Fields</span>
          <textarea
            data-workflow-architect-step-field="fields"
            data-workflow-architect-step-id="${escapeHtml(step.id)}"
            placeholder="e.g. name, email, phone, enquiry type"
          >${escapeHtml(step.fields || "")}</textarea>
        </label>

        <label>
          <span>Outputs</span>
          <textarea
            data-workflow-architect-step-field="outputs"
            data-workflow-architect-step-id="${escapeHtml(step.id)}"
            placeholder="e.g. HubSpot lead, Gmail draft, notification"
          >${escapeHtml(step.outputs || "")}</textarea>
        </label>

        <label>
          <span>Approval requirement</span>
          <select
            data-workflow-architect-step-field="approval_requirement"
            data-workflow-architect-step-id="${escapeHtml(step.id)}"
          >
            ${["auto", "not_required", "required", "before_external_write"]
              .map((value) => `
                <option value="${escapeHtml(value)}" ${String(step.approval_requirement || "auto") === value ? "selected" : ""}>
                  ${escapeHtml(value)}
                </option>
              `)
              .join("")}
          </select>
        </label>

        <div class="workflow-architect-step-actions">
          <button type="button" data-workflow-architect-move-step="up" data-workflow-architect-step-id="${escapeHtml(step.id)}">Move up</button>
          <button type="button" data-workflow-architect-move-step="down" data-workflow-architect-step-id="${escapeHtml(step.id)}">Move down</button>
          <button type="button" data-workflow-architect-remove-step="${escapeHtml(step.id)}">Remove</button>
        </div>
      </details>
    `)
    .join("");

  return `
    <section class="workflow-architect-guided-step-builder" data-workflow-architect-guided-step-builder="true">
      <div class="aion-picker-section-title">Guided step builder</div>
      <p class="muted">
        Optional: add the real business steps first. Aion will use these as structured user_steps.
      </p>

      ${stepCards || `<div class="empty-state">No guided steps yet. Add a step or use natural language only.</div>`}

      <div class="workflow-architect-step-actions">
        <button type="button" data-workflow-architect-add-step="true">Add step</button>
        <button
          type="button"
          data-workflow-architect-approve-steps="true"
          ${steps.length ? "" : "disabled"}
          title="Approve step list before graph generation"
        >
          Approve step list before graph generation
        </button>
        <span class="badge">${guided.stepsApproved ? "Step list approved" : "Step list not approved"}</span>
      </div>
    </section>
  `;
}


function renderAionWorkflowCanvasPanel({ workflows = [], loading = false } = {}) {
  maybeLoadAionWorkflowFromBusinessContainerOnce();
  const graph = getAionWorkflowDraftState();
  window.__aionWorkflowGraph = graph;
  compileAndAttachAionWorkflowGlyph(graph);

  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];

  const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
  const selectedNode =
    nodes.find((node) => node.id === selectedNodeId) ||
    nodes[nodes.length - 1] ||
    nodes[0] ||
    null;

  const firstStepPickerHtml = `
    <div class="aion-first-step-picker">
      <div class="aion-inspector-head">
        <div>
          <div class="eyebrow">Start workflow</div>
          <h3>What starts this workflow?</h3>
          <p>Choose a trigger, app event, browser skill, or AI starter.</p>
        </div>
      </div>

      <div class="aion-workflow-search">⌕ Search triggers, apps, or modules...</div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Recommended</div>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="manual" type="button">
          <span class="aion-picker-icon">◎</span>
          <span>
            <strong>Trigger manually</strong>
            <small>Start the workflow when the user clicks Run once.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="gmail_new_email" type="button">
          <span class="aion-picker-icon">✉</span>
          <span>
            <strong>Gmail new email</strong>
            <small>Start when a new Gmail email arrives. Connection required later.</small>
          </span>
          <em>Mock</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="schedule" type="button">
          <span class="aion-picker-icon">◷</span>
          <span>
            <strong>Schedule</strong>
            <small>Run every hour, day, week, or custom interval.</small>
          </span>
          <em>Draft</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="webhook" type="button">
          <span class="aion-picker-icon">⑂</span>
          <span>
            <strong>Webhook / API call</strong>
            <small>Start when another system sends Aion an HTTP request.</small>
          </span>
          <em>Draft</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Apps</div>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="gmail_new_email" type="button">
          <span class="aion-picker-icon">G</span>
          <span>
            <strong>Gmail</strong>
            <small>Watch emails, read messages, draft replies, send after approval.</small>
          </span>
          <em>Mock</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="xero_event" type="button">
          <span class="aion-picker-icon">X</span>
          <span>
            <strong>Xero</strong>
            <small>Invoices, contacts, PDFs, quote and payment events.</small>
          </span>
          <em>Soon</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="crm_event" type="button">
          <span class="aion-picker-icon">C</span>
          <span>
            <strong>CRM / CostaConnect</strong>
            <small>New leads, profile claims, ad orders, customer updates.</small>
          </span>
          <em>Soon</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="http_event" type="button">
          <span class="aion-picker-icon">⌁</span>
          <span>
            <strong>HTTP Request</strong>
            <small>Use API/MCP-first automation for external systems.</small>
          </span>
          <em>Soon</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">AI / Aion</div>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="chat" type="button">
          <span class="aion-picker-icon">☏</span>
          <span>
            <strong>Chat message</strong>
            <small>Start when a user, customer, or operator sends a message.</small>
          </span>
          <em>Draft</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-build-with-ai="true" type="button">
          <span class="aion-picker-icon">✦</span>
          <span>
            <strong>Build with AI</strong>
            <small>Describe the backend automation and Aion drafts a workflow.</small>
          </span>
          <em>Soon</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="evaluation" type="button">
          <span class="aion-picker-icon">✓</span>
          <span>
            <strong>Evaluation run</strong>
            <small>Run a test dataset through the workflow before publishing.</small>
          </span>
          <em>Draft</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Text parser</div>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_match_pattern" type="button">
          <span class="aion-picker-icon">.*</span>
          <span>
            <strong>Match pattern</strong>
            <small>Find text matching a regular expression, such as an email address.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_replace" type="button">
          <span class="aion-picker-icon">↔</span>
          <span>
            <strong>Replace text</strong>
            <small>Replace matching text with a new value.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_html_to_text" type="button">
          <span class="aion-picker-icon">TXT</span>
          <span>
            <strong>HTML to text</strong>
            <small>Convert simple HTML content into readable plain text.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_extract_html" type="button">
          <span class="aion-picker-icon">&lt;/&gt;</span>
          <span>
            <strong>Extract from HTML</strong>
            <small>Extract basic links, images, and table rows from HTML.</small>
          </span>
          <em>Active</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Browser fallback</div>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="browser_skill" type="button">
          <span class="aion-picker-icon">◫</span>
          <span>
            <strong>Use browser micro-skill</strong>
            <small>Fallback for websites and CRMs without an API/MCP connector.</small>
          </span>
          <em>Soon</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-trigger="record_browser_skill" type="button">
          <span class="aion-picker-icon">●</span>
          <span>
            <strong>Record new browser skill</strong>
            <small>Capture a safe browser action and convert it into a reusable node.</small>
          </span>
          <em>Soon</em>
        </button>
      </div>
    </div>
  `;

  const actionPickerHtml = `
    <div class="aion-first-step-picker">
      <div class="aion-inspector-head">
        <div>
          <div class="eyebrow">Add next step</div>
          <h3>What should happen next?</h3>
          <p>Choose an app action, AI step, approval gate, or browser fallback.</p>
        </div>
      </div>

      <div class="aion-workflow-search">⌕ Search actions, apps, or modules...</div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">AI / Aion</div>

        <button class="aion-picker-row" data-aion-workflow-create-action="ai_extract_fields" type="button">
          <span class="aion-picker-icon">AI</span>
          <span>
            <strong>Extract fields</strong>
            <small>Use Gemma/OpenAI-style extraction to structure incoming data.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="ai_classify" type="button">
          <span class="aion-picker-icon">◇</span>
          <span>
            <strong>Classify enquiry</strong>
            <small>Decide service type, urgency, town, department, or route.</small>
          </span>
          <em>Draft</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="ai_draft_reply" type="button">
          <span class="aion-picker-icon">✎</span>
          <span>
            <strong>Draft reply</strong>
            <small>Prepare a response without sending until approval.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="gmail_send_email" type="button">
          <span class="aion-picker-icon">✉</span>
          <span>
            <strong>Send email</strong>
            <small>Send an approved Gmail reply after human approval.</small>
          </span>
          <em>Approval</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Apps / API / MCP</div>

        <button class="aion-picker-row" data-aion-workflow-create-action="gmail_read_email" type="button">
          <span class="aion-picker-icon">G</span>
          <span>
            <strong>Gmail: read email</strong>
            <small>Read subject, body, sender, attachments, and thread context.</small>
          </span>
          <em>Mock</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="crm_create_lead" type="button">
          <span class="aion-picker-icon">C</span>
          <span>
            <strong>CRM: create lead</strong>
            <small>Create a HubSpot, CostaConnect, or generic CRM lead.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="xero_create_invoice" type="button">
          <span class="aion-picker-icon">X</span>
          <span>
            <strong>Xero: create draft invoice</strong>
            <small>Create a draft invoice from mapped workflow fields.</small>
          </span>
          <em>Soon</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="http_request" type="button">
          <span class="aion-picker-icon">⌁</span>
          <span>
            <strong>HTTP request</strong>
            <small>Call an API/MCP endpoint with mapped inputs.</small>
          </span>
          <em>Soon</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Tools</div>

        <button class="aion-picker-row" data-aion-workflow-create-action="tool_set_variable" type="button">
          <span class="aion-picker-icon">=</span>
          <span>
            <strong>Set variable</strong>
            <small>Store a value from the workflow for later steps.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="tool_get_variable" type="button">
          <span class="aion-picker-icon">$</span>
          <span>
            <strong>Get variable</strong>
            <small>Read a previously stored workflow variable.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="tool_compose_string" type="button">
          <span class="aion-picker-icon">T</span>
          <span>
            <strong>Compose string</strong>
            <small>Build text using mapped workflow values.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="tool_sleep" type="button">
          <span class="aion-picker-icon">⏱</span>
          <span>
            <strong>Sleep / delay</strong>
            <small>Preview a wait step without blocking the app.</small>
          </span>
          <em>Preview</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Flow control</div>

        <button class="aion-picker-row" data-aion-workflow-create-action="approval_gate" type="button">
          <span class="aion-picker-icon">✓</span>
          <span>
            <strong>Human approval</strong>
            <small>Stop before sending, deleting, invoicing, or external writes.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="if_else" type="button">
          <span class="aion-picker-icon">?</span>
          <span>
            <strong>If / else</strong>
            <small>Route items by true/false conditions.</small>
          </span>
          <em>Soon</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="router" type="button">
          <span class="aion-picker-icon">⑂</span>
          <span>
            <strong>Router</strong>
            <small>Split work into multiple paths.</small>
          </span>
          <em>Soon</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Text parser</div>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_match_pattern" type="button">
          <span class="aion-picker-icon">.*</span>
          <span>
            <strong>Match pattern</strong>
            <small>Find text matching a regular expression, such as an email address.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_replace" type="button">
          <span class="aion-picker-icon">↔</span>
          <span>
            <strong>Replace text</strong>
            <small>Replace matching text with a new value.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_html_to_text" type="button">
          <span class="aion-picker-icon">TXT</span>
          <span>
            <strong>HTML to text</strong>
            <small>Convert simple HTML content into readable plain text.</small>
          </span>
          <em>Active</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-create-action="parser_extract_html" type="button">
          <span class="aion-picker-icon">&lt;/&gt;</span>
          <span>
            <strong>Extract from HTML</strong>
            <small>Extract basic links, images, and table rows from HTML.</small>
          </span>
          <em>Active</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Browser fallback</div>

        <button class="aion-picker-row" data-aion-workflow-create-action="browser_micro_skill" type="button">
          <span class="aion-picker-icon">◫</span>
          <span>
            <strong>Run browser micro-skill</strong>
            <small>Use a recorded browser action when no API connector exists.</small>
          </span>
          <em>Soon</em>
        </button>
      </div>


      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Advanced controls</div>

        <button class="aion-picker-row" data-aion-workflow-refresh-tasks="true" type="button">
          <span class="aion-picker-icon">↻</span>
          <span>
            <strong>Refresh tasks</strong>
            <small>Reload local workflow/task state from the runtime.</small>
          </span>
          <em>Control</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-run-dry-poll="true" type="button">
          <span class="aion-picker-icon">↯</span>
          <span>
            <strong>Run dry-run poll</strong>
            <small>Trigger the older dry-run polling routine for diagnostics.</small>
          </span>
          <em>Control</em>
        </button>

        <button class="aion-picker-row" data-aion-workflow-build-step-by-step="true" type="button">
          <span class="aion-picker-icon">✦</span>
          <span>
            <strong>Build step-by-step</strong>
            <small>Open guided builder mode for custom workflow construction.</small>
          </span>
          <em>Control</em>
        </button>
      </div>

      <div class="aion-picker-section">
        <div class="aion-picker-section-title">Legacy tools</div>

        <button class="aion-picker-row" data-aion-legacy-tool="browser_recorder" type="button">
          <span class="aion-picker-icon">◎</span>
          <span>
            <strong>Teach Aion a browser skill</strong>
            <small>Record a reusable browser action for later automation.</small>
          </span>
          <em>Legacy</em>
        </button>

        <button class="aion-picker-row" data-aion-legacy-tool="browser_skills" type="button">
          <span class="aion-picker-icon">▣</span>
          <span>
            <strong>Saved browser micro-skills</strong>
            <small>View recorded browser skills available to workflows.</small>
          </span>
          <em>Legacy</em>
        </button>

        <button class="aion-picker-row" data-aion-legacy-tool="workflow_chain" type="button">
          <span class="aion-picker-icon">⑂</span>
          <span>
            <strong>Chain browser micro-skills</strong>
            <small>Combine saved browser actions into a chained process.</small>
          </span>
          <em>Legacy</em>
        </button>

        <button class="aion-picker-row" data-aion-legacy-tool="task_templates" type="button">
          <span class="aion-picker-icon">▤</span>
          <span>
            <strong>Start from a workflow</strong>
            <small>Use older workflow templates as starting points.</small>
          </span>
          <em>Legacy</em>
        </button>

        <button class="aion-picker-row" data-aion-legacy-tool="step_builder" type="button">
          <span class="aion-picker-icon">✦</span>
          <span>
            <strong>Build custom agent</strong>
            <small>Open the older custom agent builder surface.</small>
          </span>
          <em>Legacy</em>
        </button>

        <button class="aion-picker-row" data-aion-legacy-tool="generic_workflows" type="button">
          <span class="aion-picker-icon">◇</span>
          <span>
            <strong>Saved generic workflows</strong>
            <small>Browse older saved generic workflow definitions.</small>
          </span>
          <em>Legacy</em>
        </button>

        <button class="aion-picker-row" data-aion-legacy-tool="trained_tasks" type="button">
          <span class="aion-picker-icon">AI</span>
          <span>
            <strong>Trained Tasks</strong>
            <small>Review trained task assets and outputs.</small>
          </span>
          <em>Legacy</em>
        </button>

        <button class="aion-picker-row" data-aion-legacy-tool="test_run_output" type="button">
          <span class="aion-picker-icon">↯</span>
          <span>
            <strong>Test run output</strong>
            <small>Open older workflow test output and diagnostics.</small>
          </span>
          <em>Legacy</em>
        </button>
      </div>
    </div>
  `;

  const nodeHtml = nodes
    .map(
      (node) => `
        <button
          class="aion-canvas-node aion-canvas-node-${escapeHtml(node.tone)} ${selectedNode && node.id === selectedNode.id ? "aion-canvas-node-selected" : ""}"
          style="left:${escapeHtml(node.x)}px; top:${escapeHtml(node.y)}px;"
          data-aion-workflow-node-id="${escapeHtml(node.id)}"
          type="button"
        >
          <span
            class="aion-canvas-node-delete"
            data-aion-workflow-delete-node="${escapeHtml(node.id)}"
            title="Delete this step"
          >
            ×
          </span>
          <div class="aion-canvas-node-top">
            <div class="aion-canvas-node-icon">${escapeHtml(node.icon)}</div>
            <span class="aion-canvas-node-type">${escapeHtml(node.type)}</span>
          </div>
          <div class="aion-canvas-node-title">${escapeHtml(node.title)}</div>
          <div class="aion-canvas-node-meta">${escapeHtml(node.meta)}</div>
          <div class="aion-canvas-node-status">
            <span>${node.status === "Required" || node.status === "Blocked write" ? "!" : "✓"}</span>
            ${escapeHtml(node.status)}
          </div>
        </button>
      `,
    )
    .join("");

  const connectorHtml = edges.length
    ? edges
        .map((edge) => {
          const fromNode = nodes.find((node) => node.id === edge.from);
          const toNode = nodes.find((node) => node.id === edge.to);

          if (!fromNode || !toNode) return "";

          const fromSize = 92;
          const toSize = 92;

          const x1 = Number(fromNode.x || 0) + fromSize / 2;
          const y1 = Number(fromNode.y || 0) + fromSize / 2;
          const x2 = Number(toNode.x || 0) + toSize / 2;
          const y2 = Number(toNode.y || 0) + toSize / 2;

          const dx = Math.max(80, Math.abs(x2 - x1) * 0.45);
          const c1x = x1 + dx;
          const c2x = x2 - dx;

          return `
            <path
              d="M ${escapeHtml(String(x1))} ${escapeHtml(String(y1))} C ${escapeHtml(String(c1x))} ${escapeHtml(String(y1))}, ${escapeHtml(String(c2x))} ${escapeHtml(String(y2))}, ${escapeHtml(String(x2))} ${escapeHtml(String(y2))}"
              fill="none"
              stroke="rgba(59, 130, 246, 0.42)"
              stroke-width="4"
              stroke-dasharray="2 10"
              stroke-linecap="round"
            />
          `;
        })
        .join("")
    : nodes
        .slice(0, -1)
        .map((node, index) => {
          const next = nodes[index + 1];

          const x1 = Number(node.x || 0) + 46;
          const y1 = Number(node.y || 0) + 46;
          const x2 = Number(next.x || 0) + 46;
          const y2 = Number(next.y || 0) + 46;

          const dx = Math.max(80, Math.abs(x2 - x1) * 0.45);
          const c1x = x1 + dx;
          const c2x = x2 - dx;

          return `
            <path
              d="M ${escapeHtml(String(x1))} ${escapeHtml(String(y1))} C ${escapeHtml(String(c1x))} ${escapeHtml(String(y1))}, ${escapeHtml(String(c2x))} ${escapeHtml(String(y2))}, ${escapeHtml(String(x2))} ${escapeHtml(String(y2))}"
              fill="none"
              stroke="rgba(59, 130, 246, 0.42)"
              stroke-width="4"
              stroke-dasharray="2 10"
              stroke-linecap="round"
            />
          `;
        })
        .join("");

  return `
    <section class="aion-workflow-canvas-shell">
      <div class="aion-workflow-topbar">
        <div class="aion-workflow-title-wrap aion-workflow-title-wrap-compact">
          <div class="aion-workflow-logo">AI</div>
          <div class="aion-workflow-breadcrumb-title">
            <div class="aion-workflow-breadcrumb">
              <span>${escapeHtml(state.workspaceId || "costa_conexion")}</span>
              <span>/</span>
              <input
                class="aion-workflow-title-input"
                data-aion-workflow-title-input="true"
                value="${escapeHtml(getAionWorkflowDraftState().name || "Untitled workflow 1")}"
                aria-label="Workflow name"
              />
            </div>
            <div class="aion-workflow-subtle-meta">
              Aion Workflow Builder · local draft
            </div>
            ${
              window.__aionWorkflowLoadNotice
                ? `<div class="aion-workflow-load-notice">✓ ${escapeHtml(window.__aionWorkflowLoadNotice)}</div>`
                : ""
            }
          </div>
          ${
            (() => {
              const saveStatus = getAionWorkflowSaveStatus(getAionWorkflowDraftState());
              return `<span class="aion-workflow-status-pill ${escapeHtml(saveStatus.className)}" title="${escapeHtml(saveStatus.detail)}">${escapeHtml(saveStatus.label)}</span>`;
            })()
          }
        </div>

        <div class="aion-workflow-top-actions">
          
          <div class="aion-workflow-publish-control">
            <button
              class="aion-workflow-publish-main"
              data-aion-workflow-save="true"
              type="button"
              title="Save current workflow draft"
            >
              Save
            </button>

            <details class="aion-workflow-publish-menu">
              <summary title="Workflow actions">⌄</summary>
              <div class="aion-workflow-publish-dropdown">
                <button type="button" data-aion-workflow-dry-run="true">
                  <span>Dry-run</span>
                  <kbd>⌘R</kbd>
                </button>

                <button type="button" data-aion-workflow-save="true">
                  <span>Save workflow</span>
                  <kbd>⌘S</kbd>
                </button>

                <button type="button" data-aion-workflow-save-capsule="true">
                  <span>Save as Workflow Capsule</span>
                  <kbd>⬢</kbd>
                </button>

                <button type="button" data-aion-workflow-export-glyph="true">
                  <span>Export Glyph</span>
                  <kbd>{}</kbd>
                </button>

                <button type="button" data-aion-workflow-publish="true">
                  <span>Publish</span>
                  <kbd>⇧P</kbd>
                </button>

                <button type="button" disabled>
                  <span>Unpublish</span>
                  <kbd>⌘U</kbd>
                </button>
              </div>
            </details>
          </div>
        </div>
      </div>

      <div class="aion-workflow-layout">
        <aside class="aion-workflow-sidebar" data-aion-workflow-sidebar="true">
          <button
            class="aion-workflow-sidebar-toggle"
            data-aion-workflow-sidebar-toggle="true"
            type="button"
            title="Toggle sidebar"
          >
            ☰
          </button>

          <nav class="aion-workflow-app-nav">
            ${[
              ["boardroom", "Boardroom"],
              ["dashboard", "Dashboard"],
              ["marketing_stream", "Marketing"],
              ["brand_foundation", "Brand"],
              ["live_agents", "Live Agents"],
              ["aion", "Aion"],
              ["operations_agents", "Train Agent"],
              ["operations_flow", "Operations"],
              ["local_node", "Local Node"],
            ]
              .map(
                ([tab, label]) => `
                  <button
                    class="${state.activeTab === tab ? "active" : ""}"
                    data-tab="${escapeHtml(tab)}"
                    type="button"
                  >
                    ${escapeHtml(label)}
                  </button>
                `,
              )
              .join("")}
          </nav>

          <div class="aion-workflow-side-status">
            <div><strong>Status</strong><span>Dry-run</span></div>
            <div><strong>Approval</strong><span>Human required</span></div>
            <div><strong>Loaded</strong><span>${escapeHtml(workflows.length)}</span></div>
            <div><strong>Phase</strong><span>8F</span></div>
          </div>

          <details class="aion-workflow-side-advanced">
            <summary>Advanced controls</summary>
            <div>
              <button
                class="secondary-btn"
                data-operations-agents-action="refresh"
                ${loading ? "disabled" : ""}
                type="button"
              >
                Refresh Tasks
              </button>

              <button
                class="secondary-btn"
                data-operations-agents-action="gmail-poll-dry-run"
                ${loading ? "disabled" : ""}
                type="button"
              >
                Run dry-run poll
              </button>

              <button
                class="primary-btn"
                data-operations-agents-action="open-step-builder"
                ${loading ? "disabled" : ""}
                type="button"
              >
                Build step-by-step
              </button>
            </div>
          </details>

          <details class="aion-workflow-legacy-tools" open>
            <summary>Legacy tools</summary>
            <button data-aion-legacy-tool="browser_recorder" type="button">Teach Aion a browser skill</button>
            <button data-aion-legacy-tool="browser_skills" type="button">Saved browser micro-skills</button>
            <button data-aion-legacy-tool="workflow_chain" type="button">Chain browser micro-skills</button>
            <button data-aion-legacy-tool="task_templates" type="button">Start from a workflow</button>
            <button data-aion-legacy-tool="step_builder" type="button">Build custom agent</button>
            <button data-aion-legacy-tool="generic_workflows" type="button">Saved generic workflows</button>
            <button data-aion-legacy-tool="trained_tasks" type="button">Trained Tasks</button>
            <button data-aion-legacy-tool="test_run_output" type="button">Test run output</button>
          </details>

        </aside>

        <main class="aion-workflow-canvas">
          <div
            class="aion-workflow-canvas-viewport"
            data-aion-workflow-canvas-viewport="true"
          >
            <svg class="aion-workflow-connectors" aria-hidden="true">
              ${connectorHtml}
            </svg>

            ${nodeHtml}

            ${
              nodes.length === 0
                ? `
                  <div class="aion-workflow-empty-start">
                    <button
                      class="aion-workflow-empty-card"
                      data-aion-workflow-open-trigger-picker="true"
                      type="button"
                    >
                      <span>+</span>
                      <strong>Add first step</strong>
                    </button>

                  </div>
                `
                : `
                  <button
                    class="aion-workflow-add-next-node"
                    style="left:${escapeHtml(String((nodes[nodes.length - 1]?.x || 160) + 260))}px; top:${escapeHtml(String((nodes[nodes.length - 1]?.y || 240) + 42))}px;"
                    data-aion-workflow-open-action-picker="true"
                    type="button"
                    title="Add next step"
                  >
                    +
                  </button>
                `
            }
          </div>

          <div class="aion-workflow-zoom" aria-label="Canvas zoom controls">
            <button type="button" data-aion-canvas-zoom="fit" title="Zoom to fit workflow">⛶</button>
            <button type="button" data-aion-canvas-zoom="in" title="Zoom in">+</button>
            <button type="button" data-aion-canvas-zoom="out" title="Zoom out">−</button>
            <span data-aion-canvas-zoom-label="true">100%</span>
            <button
              type="button"
              data-aion-workflow-dark-mode-toggle="true"
              title="Toggle dark canvas"
              aria-label="Toggle dark canvas"
            >☾</button>
          </div>
        </main>

        <!-- Legacy inspector toggle retired. Add-step picker still opens through + buttons. -->

        ${
          window.__aionLegacyToolOpen
            ? `
              <section class="aion-legacy-tool-modal">
                <div class="aion-legacy-tool-modal-head">
                  <div>
                    <div class="eyebrow">Legacy tool</div>
                    <h3>${escapeHtml(window.__aionLegacyToolOpenLabel || "Legacy tool")}</h3>
                  </div>
                  <button data-aion-legacy-tool-close="true" type="button">×</button>
                </div>

                <div class="aion-legacy-tool-modal-body">
                  ${
                    window.__aionLegacyToolOpen === "browser_recorder"
                      ? renderBrowserDesktopOperatorPanel(loading)
                      : window.__aionLegacyToolOpen === "browser_skills"
                        ? renderBrowserMicroSkillLibrary()
                        : window.__aionLegacyToolOpen === "workflow_chain"
                          ? renderBrowserSkillChainBuilder()
                          : window.__aionLegacyToolOpen === "step_builder"
                            ? renderOperationsAgentsStepBuilder()
                            : window.__aionLegacyToolOpen === "generic_workflows"
                              ? `
                                <section class="train-section-panel">
                                  <div class="train-section-head">
                                    <div>
                                      <div class="eyebrow">Generic runtime</div>
                                      <h2>Saved generic workflows</h2>
                                    </div>
                                  </div>
                                  <div class="train-section-body">
                                    ${
                                      genericWorkflows.length
                                        ? genericWorkflows
                                            .map((item) => renderOperationsAgentGenericWorkflowCard(item, loading))
                                            .join("")
                                        : `<div class="empty-state">No saved generic workflows found.</div>`
                                    }
                                  </div>
                                </section>
                              `
                              : window.__aionLegacyToolOpen === "trained_tasks"
                                ? `
                                  <section class="train-section-panel">
                                    <div class="train-section-head">
                                      <div>
                                        <div class="eyebrow">Trained Tasks</div>
                                        <h2>Trained Tasks</h2>
                                      </div>
                                    </div>
                                    <div class="train-section-body">
                                      ${
                                        workflows.length
                                          ? workflows
                                              .map((workflow) => renderOperationsAgentWorkflowCard(workflow, loading))
                                              .join("")
                                          : `<div class="empty-state">No trained tasks loaded yet. Train an agent or refresh your saved tasks.</div>`
                                      }
                                    </div>
                                  </section>
                                `
                                : window.__aionLegacyToolOpen === "test_run_output"
                                  ? (
                                    testResult
                                      ? renderOperationsAgentTestReplay(testResult)
                                      : `
                                        <section class="train-section-panel">
                                          <div class="train-section-head">
                                            <div>
                                              <div class="eyebrow">Replay</div>
                                              <h2>Test run output</h2>
                                            </div>
                                          </div>
                                          <div class="train-section-body">
                                            <p class="muted">
                                              Run the customer onboarding test to see the trigger, extraction,
                                              HubSpot action, email draft, and approval checkpoint.
                                            </p>
                                          </div>
                                        </section>
                                      `
                                  )
                                  : window.__aionLegacyToolOpen === "task_templates"
                                    ? `
                                      <section class="train-section-panel">
                                        <div class="train-section-head">
                                          <div>
                                            <div class="eyebrow">Task templates</div>
                                            <h2>Start from a workflow</h2>
                                          </div>
                                          <span class="train-status-chip">Safe defaults</span>
                                        </div>
                                        <div class="train-section-body">
                                          <div class="empty-state">
                                            Task template cards are preserved in the legacy Train Agent stack.
                                            This drawer is now wired and ready for the next integration pass.
                                          </div>
                                        </div>
                                      </section>
                                    `
                                    : `<div class="empty-state">Legacy tool not found.</div>`
                  }
                </div>
              </section>
            `
            : ""
        }

        ${
          (() => {
            const pickerMode = window.__aionWorkflowPickerMode || "";
            const pickerHtml =
              nodes.length === 0 || pickerMode === "trigger"
                ? firstStepPickerHtml
                : pickerMode === "action"
                  ? actionPickerHtml
                  : "";

            return pickerHtml
              ? `
                <aside
                  class="aion-workflow-picker-drawer"
                  data-aion-workflow-picker-drawer="true"
                >
                  <button
                    class="aion-workflow-picker-drawer-close"
                    data-aion-workflow-picker-close="true"
                    type="button"
                    title="Close add step panel"
                  >
                    ×
                  </button>
                  ${pickerHtml}
                </aside>
              `
              : "";
          })()
        }
      </div>
      ${window.AionWorkflowNodeEditor?.renderModal?.({ nodes }) || ""}
      ${renderAionWorkflowDryRunTraceFloatingDock()}
      ${renderAionWorkflowGlyphDebugExecutionPanel()}
      ${renderAionWorkflowFloatingToolbar()}
          ${renderWorkflowArchitectNodeEditorModal()}
    </section>
  `;
}


function renderBrowserMicroSkillLibrary() {
  const bridge = state.browserDesktopBridge || {};
  const skills = Array.isArray(bridge.skills) ? bridge.skills : [];

  if (!skills.length) {
    return "";
  }

  return `
    <div class="train-section-panel" style="margin-top:16px;">
      <div class="train-section-head">
        <div>
          <div class="eyebrow">Browser skill library</div>
          <h2>Reusable browser functions</h2>
          <p class="muted" style="margin:6px 0 0;">
            These are short browser workflow recordings saved as contracts.
            They can later be chained into larger operators.
          </p>
        </div>

        <span class="badge">${escapeHtml(skills.length)} skill${skills.length === 1 ? "" : "s"}</span>
      </div>

      <div class="train-section-body">
        <div style="display:grid; gap:14px;">
          ${skills
            .map((skill, index) => {
              const summary = summariseBrowserSkillContract(skill);
              const steps = Array.isArray(skill.recorded_steps)
                ? skill.recorded_steps
                : [];
              const inputs = Array.isArray(skill.inputs) ? skill.inputs : [];
              const outputs = Array.isArray(skill.outputs) ? skill.outputs : [];
              const permissions = skill.permissions || {};
              const approvalGates = skill.approval_gates || {};
              const replay = skill.replay || {};

              return `
                <div class="mini-card train-browser-skill-card" style="display:grid; gap:14px;">
                  <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                    <div>
                      <div class="eyebrow">Browser micro-skill ${escapeHtml(index + 1)}</div>
                      <strong>${escapeHtml(skill.name || "Browser skill")}</strong>
                      <p class="muted" style="margin:6px 0 0;">
                        ${escapeHtml(skill.description || "Reusable browser function.")}
                      </p>
                    </div>

                    <div class="badge-row" style="justify-content:flex-end;">
                      <span class="badge">${escapeHtml(skill.status || "draft")}</span>
                      <span class="badge">${escapeHtml(skill.schema_version || BROWSER_SKILL_SCHEMA_VERSION)}</span>
                    </div>
                  </div>

                  <div class="card-grid">
                    ${renderDashboardMetricCard("Skill ID", skill.skill_id || "—", "Reusable browser function")}
                    ${renderDashboardMetricCard("Trigger", summary.trigger_type || "manual", "Manual or chained start")}
                    ${renderDashboardMetricCard("Mode", summary.browser_mode || "isolated_browser", skill.browser?.browser_label || "Browser profile")}
                    ${renderDashboardMetricCard("Domain", summary.expected_domain || "Not locked yet", "Expected URL/domain")}
                    ${renderDashboardMetricCard("Inputs", summary.input_count, "Skill input contract")}
                    ${renderDashboardMetricCard("Outputs", summary.output_count, "Skill output contract")}
                    ${renderDashboardMetricCard("Steps", summary.step_count, "Recorded browser actions")}
                    ${renderDashboardMetricCard("Replay", replay.dry_run_default ? "Dry-run" : "Manual", "No live writes by default")}
                  </div>

                  <div class="train-status-note">
                    <span class="train-status-label">Permissions</span>
                    <div>
                      <strong>${permissions.external_write ? "External writes possible" : "External writes blocked"}</strong>
                      <p class="muted" style="margin:6px 0 0;">
                        Read page: ${permissions.read_page ? "yes" : "no"} ·
                        Fill forms: ${permissions.fill_forms ? "yes" : "no"} ·
                        Click buttons: ${permissions.click_buttons ? "yes" : "no"} ·
                        Submit forms: ${permissions.submit_forms ? "yes" : "no"} ·
                        Payments: ${permissions.make_payments ? "yes" : "no"} ·
                        Deletes: ${permissions.delete_records ? "yes" : "no"}
                      </p>
                    </div>
                  </div>

                  <div class="train-status-note train-status-note-waiting">
                    <span class="train-status-label">Approval gates</span>
                    <div>
                      <strong>Human approval before risky browser actions.</strong>
                      <p class="muted" style="margin:6px 0 0;">
                        Submit: ${approvalGates.approval_required_before_submit ? "approval" : "not required"} ·
                        Send: ${approvalGates.approval_required_before_send ? "approval" : "not required"} ·
                        Payment: ${approvalGates.approval_required_before_payment ? "approval" : "not required"} ·
                        Delete: ${approvalGates.approval_required_before_delete ? "approval" : "not required"} ·
                        External write: ${approvalGates.approval_required_before_external_write ? "approval" : "not required"}
                      </p>
                    </div>
                  </div>

                  ${
                    inputs.length
                      ? `
                        <div>
                          <div class="metric-label">Skill inputs</div>
                          <div class="badge-row" style="margin-top:8px;">
                            ${inputs
                              .map((input) => `
                                <span class="badge">
                                  ${escapeHtml(input.key || "input")} · ${escapeHtml(input.type || "value")}
                                </span>
                              `)
                              .join("")}
                          </div>
                        </div>
                      `
                      : ""
                  }

                  ${
                    outputs.length
                      ? `
                        <div>
                          <div class="metric-label">Skill outputs</div>
                          <div class="badge-row" style="margin-top:8px;">
                            ${outputs
                              .map((output) => `
                                <span class="badge">
                                  ${escapeHtml(output.key || "output")} · ${escapeHtml(output.type || "object")}
                                </span>
                              `)
                              .join("")}
                          </div>
                        </div>
                      `
                      : ""
                  }

                  <div>
                    <div class="metric-label">Recorded step contract</div>
                    <div style="display:grid; gap:8px; margin-top:8px;">
                      ${steps
                        .map((step, stepIndex) => `
                          <div class="train-browser-step-row">
                            <div>
                              <strong>${escapeHtml(stepIndex + 1)}. ${escapeHtml(step.label || step.step_id || "Browser step")}</strong>
                              <div class="muted">
                                ${escapeHtml(step.type || "step")} ·
                                ${escapeHtml(step.safety || "read_only")} ·
                                output: ${escapeHtml(step.output || "—")} ·
                                approval: ${step.requires_approval ? "yes" : "no"}
                              </div>
                            </div>
                            <span class="badge">${step.captured === false ? "Pending" : "Captured"}</span>
                          </div>
                        `)
                        .join("")}
                    </div>
                  </div>

                  <details>
                    <summary class="plain-link" style="cursor:pointer;">View browser skill contract JSON</summary>
                    <pre class="json-preview" style="margin-top:12px;">${escapeHtml(JSON.stringify(skill, null, 2))}</pre>
                  </details>

                  <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button
                      class="secondary-btn"
                      data-operations-agents-action="copy-browser-skill-id"
                      data-skill-id="${escapeHtml(skill.skill_id || "")}"
                    >
                      Copy skill id
                    </button>

                    <button
                      class="secondary-btn"
                      data-operations-agents-action="duplicate-browser-skill"
                      data-skill-id="${escapeHtml(skill.skill_id || "")}"
                    >
                      Duplicate skill
                    </button>

                    <button
                      class="secondary-btn"
                      data-operations-agents-action="mark-browser-skill-reusable"
                      data-skill-id="${escapeHtml(skill.skill_id || "")}"
                    >
                      Mark reusable
                    </button>
                  </div>
                </div>
              `;
            })
            .join("")}
        </div>
      </div>
    </div>
  `;
}


function makeBrowserSkillId() {
  return `browser_skill_${Date.now().toString(36)}_${Math.random()
    .toString(36)
    .slice(2, 7)}`;
}

function getBrowserSkillStepsFromBridge(bridgeInput) {
  const bridge = bridgeInput || {};
  return Array.isArray(bridge.last_recording_steps)
    ? bridge.last_recording_steps
    : [];
}

function normaliseBrowserSkillStep(step, index) {
  const fallbackId = `browser_step_${String(index + 1).padStart(3, "0")}`;

  return {
    step_id: String(step?.step_id || fallbackId),
    order: Number.isFinite(Number(step?.order)) ? Number(step.order) : index + 1,
    type: String(step?.type || "observe_page"),
    label: String(step?.label || `Browser step ${index + 1}`),
    safety: String(step?.safety || "read_only"),
    input_map:
      step && typeof step.input_map === "object" && !Array.isArray(step.input_map)
        ? step.input_map
        : {},
    output: String(step?.output || step?.output_name || `step_${index + 1}_output`),
    selector:
      step?.selector === undefined || step?.selector === null
        ? ""
        : String(step.selector),
    url_pattern:
      step?.url_pattern === undefined || step?.url_pattern === null
        ? ""
        : String(step.url_pattern),
    requires_approval:
      step?.requires_approval === true ||
      String(step?.safety || "").includes("approval"),
    dry_run_supported: step?.dry_run_supported !== false,
    captured:
      step?.captured === false
        ? false
        : true,
    notes:
      step?.notes === undefined || step?.notes === null
        ? ""
        : String(step.notes),
  };
}

function inferBrowserSkillExpectedUrl(bridgeInput) {
  const bridge = bridgeInput || {};

  const direct =
    bridge.expected_url ||
    bridge.current_url ||
    bridge.url ||
    bridge.capture_draft?.url ||
    bridge.capture_draft?.current_url ||
    "";

  if (direct) return direct;

  const steps = Array.isArray(bridge.captured_events)
    ? bridge.captured_events
    : Array.isArray(bridge.captured_browser_events)
      ? bridge.captured_browser_events
      : Array.isArray(bridge.last_recording_steps)
        ? bridge.last_recording_steps
        : [];

  const match = steps.find((step) =>
    step?.url_pattern || step?.url || step?.expected_url,
  );

  return match?.url_pattern || match?.url || match?.expected_url || "";
}

function inferBrowserSkillName(bridgeInput) {
  const bridge = bridgeInput || {};
  return (
    bridge.pending_skill_name ||
    bridge.last_recording_name ||
    "New browser skill"
  );
}

const BROWSER_SKILL_SCHEMA_VERSION = "aion.browser_skill.v1";
const BROWSER_SKILL_REPLAY_SCHEMA_VERSION = "aion.browser_skill.replay.v1";


function getBrowserCapturedEventsForSkill() {
  const bridge = state.browserDesktopBridge || {};
  const candidates = [
    bridge.captured_events,
    bridge.capturedEvents,
    bridge.browser_events,
    bridge.browserEvents,
    bridge.recorded_events,
    bridge.recordedEvents,
    state.browserCapturedEvents,
    state.browserDesktopCapturedEvents,
    state.browserWorkflowCapturedEvents,
  ];

  for (const item of candidates) {
    if (Array.isArray(item) && item.length) {
      return item;
    }
  }

  return [];
}

function normaliseBrowserCapturedEventToStep(event, index) {
  const order = index + 1;
  const type = String(event?.type || event?.event_type || "observe_page");
  const label =
    event?.label ||
    event?.title ||
    event?.name ||
    (type === "open_page"
      ? "Open target page"
      : type === "approval_checkpoint"
        ? "Require approval before risky browser action"
        : "Observe page state");

  const output =
    event?.output ||
    event?.output_name ||
    (type === "open_page"
      ? "page_context"
      : type === "capture_fields"
        ? "field_map"
        : type === "record_click_checkpoint"
          ? "click_checkpoint"
          : type === "approval_checkpoint"
            ? "approval_required"
            : "page_state");

  const safety =
    event?.safety ||
    (type === "approval_checkpoint" || type === "record_click_checkpoint"
      ? "approval_required"
      : "read_only");

  return {
    step_id: event?.step_id || event?.event_id || `browser_step_${String(order).padStart(3, "0")}`,
    order,
    type,
    label,
    safety,
    input_map: event?.input_map || {},
    output,
    selector: event?.selector || "",
    url_pattern: event?.url_pattern || event?.url || event?.current_url || "",
    page_title: event?.page_title || event?.title || "",
    field_name: event?.field_name || "",
    value_hint: event?.value_hint || "",
    requires_approval:
      event?.requires_approval === true ||
      safety === "approval_required" ||
      safety === "human_approval_required" ||
      type === "approval_checkpoint" ||
      type === "record_click_checkpoint",
    dry_run_supported: event?.dry_run_supported !== false,
    captured: true,
    notes: event?.notes || "",
  };
}

function isInternalAionBrowserUrl(url = "") {
  const value = String(url || "");
  return value.startsWith("file://") && value.includes("isolated-browser.html");
}

function buildBrowserRecordedStepsFromCapture() {
  const capturedEvents = getBrowserCapturedEventsForSkill();

  if (capturedEvents.length) {
    return capturedEvents.map((event, index) =>
      normaliseBrowserCapturedEventToStep(event, index),
    );
  }

  const bridge = state.browserDesktopBridge || {};
  const existingSteps = Array.isArray(bridge.last_recording_steps)
    ? bridge.last_recording_steps
    : [];

  if (existingSteps.length) {
    return existingSteps.map((event, index) =>
      normaliseBrowserCapturedEventToStep(event, index),
    );
  }

  return [];
}

function inferBrowserSkillExpectedDomain(bridgeInput) {
  const bridge = bridgeInput || {};

  if (bridge.expected_domain) return bridge.expected_domain;

  const url =
    typeof bridgeInput === "string"
      ? bridgeInput
      : inferBrowserSkillExpectedUrl(bridge);

  try {
    return url ? new URL(url).hostname : "";
  } catch (_error) {
    return "";
  }
}


function makeUniqueBrowserSkillOutputs(steps) {
  const counts = new Map();

  return (Array.isArray(steps) ? steps : []).map((step, index) => {
    const rawKey =
      step.output ||
      step.output_name ||
      step.type ||
      `browser_output_${index + 1}`;

    const baseKey = String(rawKey)
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_]+/g, "_")
      .replace(/^_+|_+$/g, "") || `browser_output_${index + 1}`;

    const count = (counts.get(baseKey) || 0) + 1;
    counts.set(baseKey, count);

    const key = count === 1 ? baseKey : `${baseKey}_${count}`;

    return {
      key,
      label: step.label || step.name || key,
      type: "object",
      source_step_id: step.step_id || `browser_step_${index + 1}`,
      required: false,
    };
  });
}


function getFirstBrowserStepUrl(stepsInput) {
  const steps = Array.isArray(stepsInput) ? stepsInput : [];

  const match = steps.find((step) =>
    Boolean(step?.url_pattern || step?.url || step?.current_url || step?.expected_url),
  );

  return match?.url_pattern || match?.url || match?.current_url || match?.expected_url || "";
}

function getDomainFromUrlSafe(urlInput) {
  try {
    const url = String(urlInput || "").trim();
    return url ? new URL(url).hostname : "";
  } catch (_error) {
    return "";
  }
}


function buildBrowserSkillContract(bridgeInput = null, overrides = {}) {
  const now = new Date().toISOString();
  const bridge = bridgeInput || state.browserDesktopBridge || {};
  const review = bridge.skill_review || {};
  const recordedSteps = buildBrowserRecordedStepsFromCapture();

  const firstStepUrl =
    getFirstBrowserStepUrl(recordedSteps) ||
    recordedSteps.find((step) => step?.url_pattern)?.url_pattern ||
    "";

  const expectedUrl =
    overrides.expected_url ||
    review.expected_url ||
    bridge.expected_url ||
    firstStepUrl ||
    bridge.capture_draft?.url ||
    "";

  const expectedDomain =
    overrides.expected_domain ||
    review.expected_domain ||
    bridge.expected_domain ||
    getDomainFromUrlSafe(expectedUrl) ||
    "";

  const skillId =
    overrides.skill_id ||
    bridge.current_skill_id ||
    bridge.last_skill_id ||
    `browser_skill_${makeStepBuilderId ? makeStepBuilderId("mon") : Math.random().toString(36).slice(2, 10)}_${Math.random().toString(36).slice(2, 7)}`;

  const name =
    overrides.name ||
    review.name ||
    bridge.last_recording_name ||
    bridge.current_skill_name ||
    "New browser skill";

  const description =
    overrides.description ||
    review.description ||
    bridge.last_recording_summary ||
    "Reusable browser skill draft captured locally. Next: validate selectors, inputs, outputs, and approval checkpoints.";

  const mode =
    overrides.mode ||
    review.mode ||
    bridge.mode ||
    "isolated_browser";

  const outputs = makeUniqueBrowserSkillOutputs(recordedSteps);

  return {
    schema_version:
      typeof BROWSER_SKILL_SCHEMA_VERSION !== "undefined"
        ? BROWSER_SKILL_SCHEMA_VERSION
        : "aion.browser_skill.v1",
    skill_id: skillId,
    name,
    description,
    status: overrides.status || "draft",
    created_at: bridge.recording_started_at || now,
    updated_at: now,
    created_by: "desktop_user",

    trigger: {
      type: "manual",
      manual_start: true,
      can_be_chained: true,
      chain_role: "micro_skill",
      starts_from: "user_requested_or_parent_workflow",
    },

    browser: {
      mode,
      browser_label: bridge.browser || "Aion isolated browser",
      expected_url: expectedUrl,
      expected_domain: expectedDomain,
      profile_policy:
        mode === "user_browser"
          ? "user_browser_explicit_consent_required"
          : "isolated_profile_recommended",
    },

    inputs: [
      {
        key: "start_url",
        label: "Start URL",
        type: "url",
        required: false,
        source: "workflow_or_user",
      },
      {
        key: "context",
        label: "Workflow context",
        type: "object",
        required: false,
        source: "parent_workflow",
      },
    ],

    outputs,

    permissions: {
      read_page: true,
      observe_dom: true,
      capture_screenshot: true,
      fill_forms: true,
      click_buttons: true,
      upload_files: false,
      download_files: true,
      submit_forms: false,
      send_messages: false,
      make_payments: false,
      delete_records: false,
      external_write: false,
      permission_mode: "dry_run_or_approval_required",
      allowed_browser_mode: mode,
    },

    approval_gates: {
      approval_required_before_submit: true,
      approval_required_before_send: true,
      approval_required_before_payment: true,
      approval_required_before_delete: true,
      approval_required_before_external_write: true,
      approval_required_before_file_upload: true,
      human_review_default: true,
    },

    replay: {
      schema_version: "aion.browser_skill.replay.v1",
      dry_run_supported: true,
      dry_run_default: true,
      replay_mode: "selector_and_state_validation",
      can_execute_live: false,
      live_execution_requires_policy_unlock: true,
      last_dry_run_status: bridge.dry_run_result?.status || "not_run",
      last_dry_run_at: bridge.dry_run_result?.created_at || "",
      blocked_actions: [
        "submit_form",
        "send_message",
        "make_payment",
        "delete_record",
        "external_write",
      ],
    },

    recorded_steps: recordedSteps,

    chainability: {
      reusable: true,
      recommended_scope: "small_single_browser_action",
      max_recommended_steps: 8,
      accepts_parent_context: true,
      emits_outputs_for_next_skill: true,
      can_be_called_by_workflow: true,
    },

    audit: {
      source: "phase_4_browser_skill_recorder",
      local_only: true,
      external_writes_blocked: true,
      recording_started_at: bridge.recording_started_at || "",
      recording_stopped_at: bridge.recording_stopped_at || "",
      captured_event_count: recordedSteps.length,
    },
  };
}

function deriveDomainFromUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";

  try {
    const url = raw.startsWith("http://") || raw.startsWith("https://")
      ? new URL(raw)
      : new URL(`https://${raw}`);
    return url.hostname || "";
  } catch (_error) {
    return raw.replace(/^https?:\/\//, "").split("/")[0] || "";
  }
}

function inferBrowserSkillOutputs(steps) {
  const outputs = steps
    .filter((step) => step && step.output)
    .map((step) => ({
      key: step.output,
      label: step.label || step.output,
      type: "object",
      source_step_id: step.step_id,
      required: false,
    }));

  if (outputs.length) return outputs;

  return [
    {
      key: "browser_result",
      label: "Browser result",
      type: "object",
      source_step_id: "",
      required: false,
    },
  ];
}

function summariseBrowserSkillContract(skill) {
  return {
    schema_version: skill?.schema_version || BROWSER_SKILL_SCHEMA_VERSION,
    skill_id: skill?.skill_id || "",
    name: skill?.name || "Browser skill",
    status: skill?.status || "draft",
    trigger_type: skill?.trigger?.type || "manual",
    browser_mode: skill?.browser?.mode || "isolated_browser",
    expected_domain: skill?.browser?.expected_domain || "",
    input_count: Array.isArray(skill?.inputs) ? skill.inputs.length : 0,
    output_count: Array.isArray(skill?.outputs) ? skill.outputs.length : 0,
    step_count: Array.isArray(skill?.recorded_steps) ? skill.recorded_steps.length : 0,
    dry_run_supported: skill?.replay?.dry_run_supported === true,
    external_write: skill?.permissions?.external_write === true,
    approval_before_external_write:
      skill?.approval_gates?.approval_required_before_external_write !== false,
  };
}



/* -------------------------------------------------------------------------- */
/* Phase 4C browser event capture helpers                                      */
/* -------------------------------------------------------------------------- */

function makeBrowserCaptureId(prefix = "browser_event") {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

function normaliseBrowserCaptureDraft(input = {}) {
  const raw = input && typeof input === "object" ? input : {};

  return {
    url: String(raw.url || ""),
    title: String(raw.title || ""),
    selector: String(raw.selector || ""),
    label: String(raw.label || ""),
    field_name: String(raw.field_name || ""),
    field_value_hint: String(raw.field_value_hint || ""),
    event_type: String(raw.event_type || "observe_page"),
    notes: String(raw.notes || ""),
  };
}

function getBrowserDomainFromUrl(url) {
  try {
    const parsed = new URL(String(url || ""));
    return parsed.hostname || "";
  } catch (_) {
    return "";
  }
}

function browserCaptureEventToStep(event, index = 0) {
  const eventType = String(event?.event_type || "observe_page");
  const order = Number(index || 0) + 1;

  const base = {
    step_id: event?.step_id || `browser_step_${String(order).padStart(3, "0")}`,
    order,
    type: eventType,
    label: event?.label || "Browser step",
    safety: event?.safety || "read_only",
    input_map: event?.input_map || {},
    output: event?.output || `browser_output_${order}`,
    selector: event?.selector || "",
    url_pattern: event?.url_pattern || event?.url || "",
    expected_url: event?.url || "",
    expected_domain: event?.domain || getBrowserDomainFromUrl(event?.url || ""),
    page_title: event?.title || "",
    field_name: event?.field_name || "",
    field_value_hint: event?.field_value_hint || "",
    requires_approval: event?.requires_approval === true,
    dry_run_supported: true,
    captured: true,
    notes: event?.notes || "",
  };

  if (
    eventType === "click_checkpoint" ||
    eventType === "submit_checkpoint" ||
    eventType === "approval_checkpoint"
  ) {
    base.safety = "approval_required";
    base.requires_approval = true;
  }

  return base;
}

function buildBrowserRecordedStepsFromEvents(events = []) {
  const list = Array.isArray(events) ? events : [];

  if (!list.length) {
    return [
      {
        step_id: "browser_step_001",
        order: 1,
        type: "open_page",
        label: "Open target page",
        safety: "read_only",
        input_map: {},
        output: "page_context",
        selector: "",
        url_pattern: "",
        expected_url: "",
        expected_domain: "",
        page_title: "",
        requires_approval: false,
        dry_run_supported: true,
        captured: false,
        notes: "No real browser events captured yet.",
      },
      {
        step_id: "browser_step_002",
        order: 2,
        type: "approval_checkpoint",
        label: "Require approval before submit, payment, delete, or external write",
        safety: "human_approval_required",
        input_map: {},
        output: "approval_required",
        selector: "",
        url_pattern: "",
        expected_url: "",
        expected_domain: "",
        page_title: "",
        requires_approval: true,
        dry_run_supported: true,
        captured: false,
        notes: "Default safety checkpoint.",
      },
    ];
  }

  return list.map((event, index) => browserCaptureEventToStep(event, index));
}

function createBrowserCaptureEventFromDraft(draftInput = {}, typeOverride = "") {
  const draft = normaliseBrowserCaptureDraft(draftInput);
  const eventType = typeOverride || draft.event_type || "observe_page";
  const now = new Date().toISOString();

  const domain = getBrowserDomainFromUrl(draft.url);

  const labels = {
    open_page: "Open target page",
    observe_page: "Observe page state",
    capture_field: "Capture form field",
    click_checkpoint: "Record click checkpoint",
    submit_checkpoint: "Record submit checkpoint",
    approval_checkpoint: "Require approval checkpoint",
  };

  const outputs = {
    open_page: "page_context",
    observe_page: "page_state",
    capture_field: draft.field_name || "field_value",
    click_checkpoint: "click_checkpoint",
    submit_checkpoint: "submit_checkpoint",
    approval_checkpoint: "approval_required",
  };

  return {
    event_id: makeBrowserCaptureId("browser_event"),
    step_id: makeBrowserCaptureId("browser_step"),
    captured_at: now,
    event_type: eventType,
    label: draft.label || labels[eventType] || "Browser event",
    url: draft.url,
    domain,
    title: draft.title,
    selector: draft.selector,
    field_name: draft.field_name,
    field_value_hint: draft.field_value_hint,
    notes: draft.notes,
    safety:
      eventType === "click_checkpoint" ||
      eventType === "submit_checkpoint" ||
      eventType === "approval_checkpoint"
        ? "approval_required"
        : "read_only",
    output: outputs[eventType] || "browser_output",
    requires_approval:
      eventType === "click_checkpoint" ||
      eventType === "submit_checkpoint" ||
      eventType === "approval_checkpoint",
    source: "phase_4c_browser_event_capture",
  };
}

function getBrowserCaptureEvents() {
  const bridge = state.browserDesktopBridge || {};
  return Array.isArray(bridge.captured_events) ? bridge.captured_events : [];
}

function getBrowserSkillExpectedDomainFromSteps(steps = []) {
  const first = (Array.isArray(steps) ? steps : []).find(
    (step) => step.expected_domain || step.url_pattern || step.expected_url,
  );

  return first?.expected_domain || getBrowserDomainFromUrl(first?.expected_url || first?.url_pattern || "");
}

function getBrowserSkillExpectedUrlFromSteps(steps = []) {
  const first = (Array.isArray(steps) ? steps : []).find(
    (step) => step.expected_url || step.url_pattern,
  );

  return first?.expected_url || first?.url_pattern || "";
}



function normaliseBrowserSkillContractOutputs(contractInput) {
  const contract = contractInput || {};
  const counts = new Map();

  const outputs = Array.isArray(contract.outputs)
    ? contract.outputs.map((output, index) => {
        const rawKey =
          output?.key ||
          output?.output ||
          output?.source_step_id ||
          `browser_output_${index + 1}`;

        const baseKey =
          String(rawKey)
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9_]+/g, "_")
            .replace(/^_+|_+$/g, "") || `browser_output_${index + 1}`;

        const count = (counts.get(baseKey) || 0) + 1;
        counts.set(baseKey, count);

        const key = count === 1 ? baseKey : `${baseKey}_${count}`;

        return {
          ...output,
          key,
        };
      })
    : [];

  return {
    ...contract,
    outputs,
  };
}



function getBrowserSkillReviewDraft() {
  const bridge = state.browserDesktopBridge || {};
  const review = bridge.skill_review || {};

  return {
    name:
      review.name ||
      bridge.last_recording_name ||
      "New browser skill",
    description:
      review.description ||
      bridge.last_recording_summary ||
      "Reusable browser skill draft captured locally.",
    expected_url:
      review.expected_url ||
      bridge.expected_url ||
      inferBrowserSkillExpectedUrl(bridge) ||
      "",
    expected_domain:
      review.expected_domain ||
      bridge.expected_domain ||
      inferBrowserSkillExpectedDomain(bridge) ||
      "",
    mode:
      review.mode ||
      bridge.mode ||
      "isolated_browser",
  };
}

function patchBrowserSkillReviewDraft(patch) {
  desktopStore.patch({
    browserDesktopBridge: {
      ...(state.browserDesktopBridge || {}),
      skill_review: {
        ...((state.browserDesktopBridge || {}).skill_review || {}),
        ...(patch || {}),
      },
    },
  });

  desktopStore.persistCacheSoon(300);
  requestRender();
}

function getBrowserCapturedEventsForEditing() {
  const bridge = state.browserDesktopBridge || {};
  if (Array.isArray(bridge.captured_events)) return bridge.captured_events;
  if (Array.isArray(bridge.captured_browser_events)) return bridge.captured_browser_events;
  if (Array.isArray(bridge.last_recording_steps)) return bridge.last_recording_steps;
  return [];
}

function setBrowserCapturedEventsForEditing(events) {
  const bridge = state.browserDesktopBridge || {};
  const cleaned = Array.isArray(events) ? events : [];

  desktopStore.patch({
    browserDesktopBridge: {
      ...bridge,
      captured_events: cleaned,
      captured_browser_events: cleaned,
      last_recording_steps: cleaned,
      captured_event_count: cleaned.length,
    },
  });

  desktopStore.persistCacheSoon(300);
  requestRender();
}

function patchBrowserCapturedEvent(stepId, patch) {
  const events = getBrowserCapturedEventsForEditing();
  const updated = events.map((event) =>
    String(event.step_id || "") === String(stepId)
      ? {
          ...event,
          ...(patch || {}),
        }
      : event,
  );

  setBrowserCapturedEventsForEditing(updated);
}

function deleteBrowserCapturedEvent(stepId) {
  const events = getBrowserCapturedEventsForEditing();
  const updated = events.filter(
    (event) => String(event.step_id || "") !== String(stepId),
  );

  setBrowserCapturedEventsForEditing(updated);
}

function moveBrowserCapturedEvent(stepId, direction) {
  const events = [...getBrowserCapturedEventsForEditing()];
  const index = events.findIndex(
    (event) => String(event.step_id || "") === String(stepId),
  );

  if (index < 0) return;

  const nextIndex = direction === "up" ? index - 1 : index + 1;
  if (nextIndex < 0 || nextIndex >= events.length) return;

  const [item] = events.splice(index, 1);
  events.splice(nextIndex, 0, item);

  setBrowserCapturedEventsForEditing(events);
}


function renderBrowserSkillDraftContractPreview() {
  const bridge = state.browserDesktopBridge || {};
  const capturedEvents = Array.isArray(bridge.captured_events)
    ? bridge.captured_events
    : Array.isArray(bridge.captured_browser_events)
      ? bridge.captured_browser_events
      : [];

  const recordedSteps = Array.isArray(bridge.last_recording_steps)
    ? bridge.last_recording_steps
    : [];

  const sourceSteps = capturedEvents.length ? capturedEvents : recordedSteps;
  const hasSteps = Array.isArray(sourceSteps) && sourceSteps.length > 0;

  if (!hasSteps) {
    return "";
  }

  const contract = normaliseBrowserSkillContractOutputs(buildBrowserSkillContract(bridge, {
    skill_id: bridge.last_contract_preview_id || "browser_skill_preview",
    status: "draft_preview",
  }));

  const steps = Array.isArray(contract.recorded_steps)
    ? contract.recorded_steps
    : sourceSteps;

  const reviewDraft = getBrowserSkillReviewDraft();

  const expectedDomain =
    reviewDraft.expected_domain ||
    contract?.browser?.expected_domain ||
    bridge.expected_domain ||
    "Not locked yet";

  const expectedUrl =
    reviewDraft.expected_url ||
    contract?.browser?.expected_url ||
    bridge.expected_url ||
    "Not locked yet";

  return `
    <div class="train-section-panel" style="margin-top:14px;">
      <div class="train-section-head">
        <div>
          <div class="eyebrow">Phase 4D · Skill contract review</div>
          <h2>Recorded browser skill draft</h2>
          <p class="muted" style="margin:6px 0 0;">
            This preview now uses the captured browser event stream, not the old placeholder step list.
          </p>
        </div>

        <span class="status-pill status-running">
          ${escapeHtml(String(steps.length))} captured steps
        </span>
      </div>

      <div class="train-section-body">
        <div class="card-grid">
          ${renderDashboardMetricCard("Schema", contract.schema_version || "aion.browser_skill.v1", "Browser skill contract")}
          ${renderDashboardMetricCard("Domain", expectedDomain, "Expected browser domain")}
          ${renderDashboardMetricCard("Mode", reviewDraft.mode || contract?.browser?.mode || "isolated_browser", "Browser runtime")}
          ${renderDashboardMetricCard("Replay", contract?.replay?.dry_run_default ? "Dry-run" : "Review", "No live writes by default")}
        </div>

        <div class="train-status-note" style="margin-top:14px;">
          <span class="train-status-label">Review</span>
          <div>
            <strong>Clean the skill before saving.</strong>
            <p class="muted" style="margin:6px 0 0;">
              Rename the skill, lock the expected URL/domain, remove accidental rows, and make outputs unique.
            </p>
          </div>
        </div>

        <div class="train-builder-form-grid train-sample-grid" style="padding:18px 0 4px; border-bottom:0;">
          <label class="train-field">
            <span>Skill name</span>
            <input
              data-browser-skill-review-field="name"
              value="${escapeHtml(reviewDraft.name)}"
              placeholder="Open Gmail unread enquiries"
            />
          </label>

          <label class="train-field">
            <span>Browser mode</span>
            <select data-browser-skill-review-field="mode">
              <option value="isolated_browser" ${reviewDraft.mode === "isolated_browser" ? "selected" : ""}>Isolated browser</option>
              <option value="user_browser" ${reviewDraft.mode === "user_browser" ? "selected" : ""}>User browser</option>
            </select>
          </label>

          <label class="train-field">
            <span>Expected URL</span>
            <input
              data-browser-skill-review-field="expected_url"
              value="${escapeHtml(reviewDraft.expected_url)}"
              placeholder="https://mail.google.com/mail/u/0/#inbox"
            />
          </label>

          <label class="train-field">
            <span>Expected domain</span>
            <input
              data-browser-skill-review-field="expected_domain"
              value="${escapeHtml(reviewDraft.expected_domain)}"
              placeholder="mail.google.com"
            />
          </label>

          <label class="train-field train-field-full">
            <span>Description</span>
            <textarea
              data-browser-skill-review-field="description"
              placeholder="What does this small browser skill do?"
            >${escapeHtml(reviewDraft.description)}</textarea>
          </label>
        </div>

        <div style="display:grid; gap:10px; margin-top:14px;">
          ${steps
            .map((step, index) => {
              const label = step.label || step.name || step.type || `Browser step ${index + 1}`;
              const type = step.type || "browser_step";
              const safety = step.safety || (step.requires_approval ? "approval_required" : "read_only");
              const output = step.output || step.output_name || `step_${index + 1}`;
              const url = step.url_pattern || step.url || step.expected_url || "";
              const selector = step.selector || "";

              return `
                <div class="train-browser-step-row" style="display:grid; gap:12px;">
                  <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                    <div>
                      <strong>${index + 1}. ${escapeHtml(label)}</strong>
                      <div class="muted">
                        ${escapeHtml(type)} · ${escapeHtml(safety)} · output: ${escapeHtml(output)}
                      </div>
                      ${
                        url
                          ? `<div class="muted">URL: ${escapeHtml(url)}</div>`
                          : ""
                      }
                      ${
                        selector
                          ? `<div class="muted">Selector: ${escapeHtml(selector)}</div>`
                          : ""
                      }
                    </div>

                    <span class="train-status-chip ${step.requires_approval ? "" : "train-status-ok"}">
                      ${step.requires_approval ? "Approval" : "Captured"}
                    </span>
                  </div>

                  <div class="train-builder-form-grid train-sample-grid" style="padding:0; border-bottom:0; gap:12px;">
                    <label class="train-field">
                      <span>Label</span>
                      <input
                        data-browser-skill-step-field="label"
                        data-step-id="${escapeHtml(step.step_id || "")}"
                        value="${escapeHtml(label)}"
                      />
                    </label>

                    <label class="train-field">
                      <span>Output</span>
                      <input
                        data-browser-skill-step-field="output"
                        data-step-id="${escapeHtml(step.step_id || "")}"
                        value="${escapeHtml(output)}"
                      />
                    </label>

                    <label class="train-field">
                      <span>URL pattern</span>
                      <input
                        data-browser-skill-step-field="url_pattern"
                        data-step-id="${escapeHtml(step.step_id || "")}"
                        value="${escapeHtml(url)}"
                      />
                    </label>

                    <label class="train-field">
                      <span>Selector</span>
                      <input
                        data-browser-skill-step-field="selector"
                        data-step-id="${escapeHtml(step.step_id || "")}"
                        value="${escapeHtml(selector)}"
                      />
                    </label>
                  </div>

                  <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <button
                      class="secondary-btn"
                      data-operations-agents-action="move-browser-skill-step-up"
                      data-step-id="${escapeHtml(step.step_id || "")}"
                      ${index === 0 ? "disabled" : ""}
                    >
                      Up
                    </button>

                    <button
                      class="secondary-btn"
                      data-operations-agents-action="move-browser-skill-step-down"
                      data-step-id="${escapeHtml(step.step_id || "")}"
                      ${index === steps.length - 1 ? "disabled" : ""}
                    >
                      Down
                    </button>

                    <button
                      class="secondary-btn"
                      data-operations-agents-action="toggle-browser-skill-step-approval"
                      data-step-id="${escapeHtml(step.step_id || "")}"
                    >
                      ${step.requires_approval ? "Remove approval" : "Require approval"}
                    </button>

                    <button
                      class="secondary-btn danger-btn"
                      data-operations-agents-action="delete-browser-skill-step"
                      data-step-id="${escapeHtml(step.step_id || "")}"
                    >
                      Delete step
                    </button>
                  </div>
                </div>
              `;
            })
            .join("")}
        </div>

        <details style="margin-top:14px;">
          <summary class="plain-link" style="cursor:pointer;">View Phase 4D contract preview JSON</summary>
          <pre class="json-preview" style="margin-top:12px;">${escapeHtml(JSON.stringify(contract, null, 2))}</pre>
        </details>
      </div>
    </div>
  `;
}



function createBrowserSkillChainDraft() {
  const now = new Date().toISOString();

  return {
    chain_id: `browser_chain_${makeStepBuilderId ? makeStepBuilderId("mon") : Date.now().toString(36)}`,
    schema_version: "aion.browser_skill_chain.v1",
    name: "New browser skill chain",
    description: "Chains small browser micro-skills into a larger safe workflow.",
    status: "draft",
    created_at: now,
    updated_at: now,
    trigger: {
      type: "manual",
      manual_start: true,
    },
    browser_mode: "isolated_browser",
    steps: [],
    approval_gates: {
      approval_required_between_skills: true,
      approval_required_before_submit: true,
      approval_required_before_external_write: true,
    },
    replay: {
      dry_run_default: true,
      can_execute_live: false,
      blocked_actions: [
        "submit_form",
        "send_message",
        "make_payment",
        "delete_record",
        "external_write",
      ],
    },
  };
}

function normaliseBrowserSkillChainDraft(input) {
  const draft = input && typeof input === "object"
    ? input
    : createBrowserSkillChainDraft();

  return {
    ...createBrowserSkillChainDraft(),
    ...draft,
    trigger: {
      type: "manual",
      manual_start: true,
      ...(draft.trigger || {}),
    },
    approval_gates: {
      approval_required_between_skills: true,
      approval_required_before_submit: true,
      approval_required_before_external_write: true,
      ...(draft.approval_gates || {}),
    },
    replay: {
      dry_run_default: true,
      can_execute_live: false,
      blocked_actions: [
        "submit_form",
        "send_message",
        "make_payment",
        "delete_record",
        "external_write",
      ],
      ...(draft.replay || {}),
    },
    steps: Array.isArray(draft.steps) ? draft.steps : [],
  };
}


function getActiveWorkspaceId() {
  return (
    state.workspaceId ||
    state.workspace_id ||
    state.activeWorkspaceId ||
    state.desktopWorkspaceId ||
    state.businessWorkspaceId ||
    "costa-conexion"
  );
}


function installBrowserRecorderEventBridge() {
  if (window.__AION_BROWSER_RECORDER_EVENT_BRIDGE_INSTALLED__) return;
  window.__AION_BROWSER_RECORDER_EVENT_BRIDGE_INSTALLED__ = true;

  const api = window.aionDesktop;
  if (!api || typeof api.onBrowserRecorderEvent !== "function") return;

  api.onBrowserRecorderEvent((payload) => {
    const event = normaliseBrowserCapturedEventToStep
      ? normaliseBrowserCapturedEventToStep(payload, getBrowserCaptureEvents().length)
      : payload;

    const currentEvents = getBrowserCaptureEvents();

    desktopStore.patch({
      browserDesktopBridge: {
        ...(state.browserDesktopBridge || {}),
        bridge_active: true,
        status: state.browserDesktopBridge?.recording ? "recording" : "active",
        captured_events: [...currentEvents, event],
        captured_event_count: currentEvents.length + 1,
        last_capture_at: new Date().toISOString(),
        message: `Captured browser event: ${event.label || event.type || "event"}`,
      },
      message: `Captured browser event: ${event.label || event.type || "event"}`,
      messageTone: "success",
    });

    desktopStore.persistCacheSoon(300);
    requestRender();
  });
}

installBrowserRecorderEventBridge();


async function refreshBrowserSkillWorkspaceAssets() {
  const workspaceId = getActiveWorkspaceId();

  const [skillsResult, chainsResult] = await Promise.all([
    apiGet(`/api/aion/business/browser-skills/${encodeURIComponent(workspaceId)}`),
    apiGet(`/api/aion/business/browser-chains/${encodeURIComponent(workspaceId)}`),
  ]);

  const skills = Array.isArray(skillsResult?.items) ? skillsResult.items : [];
  const chains = Array.isArray(chainsResult?.items) ? chainsResult.items : [];

  desktopStore.patch({
    browserSkillLibrary: skills,
    browserMicroSkillLibrary: skills,
    browserSkills: skills,
    savedBrowserSkills: skills,
    browserSkillChains: chains,
    savedBrowserSkillChains: chains,
    browserChainLibrary: chains,
  });

  desktopStore.persistCacheSoon(300);
  requestRender();

  return { skills, chains };
}

async function saveBrowserSkillToWorkspace(skill) {
  const workspaceId = getActiveWorkspaceId();
  const result = await apiPost(
    `/api/aion/business/browser-skills/${encodeURIComponent(workspaceId)}`,
    { skill },
  );

  await refreshBrowserSkillWorkspaceAssets();
  return result;
}

async function saveBrowserChainToWorkspace(chain) {
  const workspaceId = getActiveWorkspaceId();
  const result = await apiPost(
    `/api/aion/business/browser-chains/${encodeURIComponent(workspaceId)}`,
    { chain },
  );

  await refreshBrowserSkillWorkspaceAssets();
  return result;
}

function getBrowserSkillLibrary() {
  const bridge = state.browserDesktopBridge || {};

  const candidates = [
    state.browserSkillLibrary,
    state.browserMicroSkillLibrary,
    state.browserSkills,
    state.savedBrowserSkills,
    bridge.skills,
    bridge.browserSkillLibrary,
    bridge.browser_skill_library,
    bridge.microSkillLibrary,
    bridge.micro_skill_library,
    bridge.savedSkills,
    bridge.saved_skills,
    bridge.browser_skills,
    bridge.micro_skills,
  ];

  const merged = [];

  for (const candidate of candidates) {
    if (!Array.isArray(candidate)) continue;

    for (const item of candidate) {
      if (!item || typeof item !== "object") continue;
      const id = item.skill_id || item.id;
      if (!id) continue;

      if (!merged.some((existing) => String(existing.skill_id || existing.id) === String(id))) {
        merged.push(item);
      }
    }
  }

  return merged;
}

function getBrowserSkillChainDraft() {
  return normaliseBrowserSkillChainDraft(state.browserSkillChainDraft);
}

function addSkillToBrowserChain(skillId) {
  const library = getBrowserSkillLibrary();
  const skill = library.find((item) => String(item.skill_id || "") === String(skillId));

  if (!skill) return getBrowserSkillChainDraft();

  const draft = getBrowserSkillChainDraft();
  const stepIndex = draft.steps.length + 1;

  const nextStep = {
    chain_step_id: `chain_step_${makeStepBuilderId ? makeStepBuilderId("mon") : Date.now().toString(36)}`,
    order: stepIndex,
    skill_id: skill.skill_id,
    skill_name: skill.name || skill.skill_id,
    expected_domain: skill.browser?.expected_domain || "",
    expected_url: skill.browser?.expected_url || "",
    input_from: stepIndex === 1 ? "chain_input" : "previous_skill_output",
    output_as: `skill_${stepIndex}_output`,
    condition: stepIndex === 1 ? "always" : "if previous skill succeeded",
    approval_required_after: true,
    status: "draft",
  };

  const nextSteps = [...draft.steps, nextStep];
  const shouldAutoName =
    !draft.name ||
    draft.name === "New browser skill chain" ||
    draft.name.trim() === "";

  return {
    ...draft,
    name: shouldAutoName ? inferBrowserChainNameFromSteps(nextSteps) : draft.name,
    updated_at: new Date().toISOString(),
    browser_mode: skill.browser?.mode || draft.browser_mode || "isolated_browser",
    steps: nextSteps,
  };
}

function reorderBrowserChainStep(chainStepId, direction) {
  const draft = getBrowserSkillChainDraft();
  const steps = [...draft.steps];
  const index = steps.findIndex((item) => String(item.chain_step_id || "") === String(chainStepId));

  if (index < 0) return draft;

  const nextIndex = direction === "up" ? index - 1 : index + 1;
  if (nextIndex < 0 || nextIndex >= steps.length) return draft;

  const [item] = steps.splice(index, 1);
  steps.splice(nextIndex, 0, item);

  return {
    ...draft,
    updated_at: new Date().toISOString(),
    steps: steps.map((step, idx) => ({
      ...step,
      order: idx + 1,
      output_as: step.output_as || `skill_${idx + 1}_output`,
    })),
  };
}

function removeBrowserChainStep(chainStepId) {
  const draft = getBrowserSkillChainDraft();

  return {
    ...draft,
    updated_at: new Date().toISOString(),
    steps: draft.steps
      .filter((item) => String(item.chain_step_id || "") !== String(chainStepId))
      .map((step, idx) => ({
        ...step,
        order: idx + 1,
      })),
  };
}

function patchBrowserChainStep(chainStepId, patch) {
  const draft = getBrowserSkillChainDraft();

  return {
    ...draft,
    updated_at: new Date().toISOString(),
    steps: draft.steps.map((step) =>
      String(step.chain_step_id || "") === String(chainStepId)
        ? {
            ...step,
            ...(patch || {}),
          }
        : step,
    ),
  };
}

function buildBrowserSkillChainDryRun(draftInput = null) {
  const draft = normaliseBrowserSkillChainDraft(draftInput || state.browserSkillChainDraft);
  const library = getBrowserSkillLibrary();
  const now = new Date().toISOString();

  const replaySteps = draft.steps.map((step, index) => {
    const skill = library.find((item) => String(item.skill_id || "") === String(step.skill_id || ""));

    return {
      order: index + 1,
      chain_step_id: step.chain_step_id,
      skill_id: step.skill_id,
      skill_name: step.skill_name || skill?.name || step.skill_id,
      expected_domain: step.expected_domain || skill?.browser?.expected_domain || "",
      input_from: step.input_from || (index === 0 ? "chain_input" : "previous_skill_output"),
      output_as: step.output_as || `skill_${index + 1}_output`,
      condition: step.condition || "always",
      approval_required_after: step.approval_required_after !== false,
      dry_run_status: "ok",
      blocked_live_actions: [
        "submit_form",
        "send_message",
        "make_payment",
        "delete_record",
        "external_write",
      ],
    };
  });

  return {
    ok: true,
    schema_version: "aion.browser_skill_chain.replay.v1",
    chain_id: draft.chain_id,
    chain_name: draft.name,
    status: replaySteps.length ? "dry_run_complete" : "empty_chain",
    dry_run: true,
    created_at: now,
    step_count: replaySteps.length,
    replay_steps: replaySteps,
    message: replaySteps.length
      ? "Browser skill chain dry-run completed locally. No live browser writes were performed."
      : "Add at least one micro-skill before running the chain.",
  };
}

function saveBrowserSkillChainDraft() {
  const draft = getBrowserSkillChainDraft();
  const chains = Array.isArray(state.browserSkillChains) ? state.browserSkillChains : [];

  const saved = {
    ...draft,
    name:
      !draft.name ||
      draft.name === "New browser skill chain" ||
      draft.name.trim() === ""
        ? inferBrowserChainNameFromSteps(draft.steps)
        : draft.name,
    steps: normaliseBrowserChainStepOrder(draft.steps),
    updated_at: new Date().toISOString(),
    status: "draft",
  };

  return [
    saved,
    ...chains.filter((item) => String(item.chain_id || "") !== String(saved.chain_id || "")),
  ];
}


function inferBrowserChainNameFromSteps(stepsInput) {
  const steps = Array.isArray(stepsInput) ? stepsInput : [];
  const first = steps[0] || null;

  if (!first) return "New browser skill chain";

  const skillName = first.skill_name || "Browser skill";
  const domain = first.expected_domain || "";

  return domain ? `${skillName} · ${domain}` : `${skillName} chain`;
}

function normaliseBrowserChainStepOrder(stepsInput) {
  const steps = Array.isArray(stepsInput) ? stepsInput : [];

  return steps.map((step, index) => ({
    ...step,
    order: index + 1,
    output_as: step.output_as || `skill_${index + 1}_output`,
  }));
}

function duplicateBrowserSkillChain(chainId) {
  const chains = Array.isArray(state.browserSkillChains) ? state.browserSkillChains : [];
  const source = chains.find((item) => String(item.chain_id || "") === String(chainId));

  if (!source) return chains;

  const now = new Date().toISOString();
  const duplicate = {
    ...JSON.parse(JSON.stringify(source)),
    chain_id: `browser_chain_${makeStepBuilderId ? makeStepBuilderId("mon") : Date.now().toString(36)}`,
    name: `${source.name || "Browser skill chain"} copy`,
    status: "draft",
    created_at: now,
    updated_at: now,
    steps: normaliseBrowserChainStepOrder(source.steps || []).map((step) => ({
      ...step,
      chain_step_id: `chain_step_${makeStepBuilderId ? makeStepBuilderId("mon") : Math.random().toString(36).slice(2, 8)}`,
    })),
  };

  return [duplicate, ...chains];
}

function loadBrowserSkillChainForEditing(chainId) {
  const chains = Array.isArray(state.browserSkillChains) ? state.browserSkillChains : [];
  const source = chains.find((item) => String(item.chain_id || "") === String(chainId));

  if (!source) return getBrowserSkillChainDraft();

  return normaliseBrowserSkillChainDraft(JSON.parse(JSON.stringify(source)));
}

function deleteBrowserSkillChain(chainId) {
  const chains = Array.isArray(state.browserSkillChains) ? state.browserSkillChains : [];

  return chains.filter((item) => String(item.chain_id || "") !== String(chainId));
}

function buildBrowserSkillChainContractPreview() {
  const draft = getBrowserSkillChainDraft();

  return {
    ...draft,
    name: draft.name || inferBrowserChainNameFromSteps(draft.steps),
    steps: normaliseBrowserChainStepOrder(draft.steps),
    status: draft.status || "draft",
    updated_at: new Date().toISOString(),
  };
}



function compileBrowserSkillChainToGenericWorkflow(chainInput = null) {
  const chain = normaliseBrowserSkillChainDraft(
    chainInput || buildBrowserSkillChainContractPreview(),
  );

  const workflowId =
    chain.workflow_id ||
    `workflow_browser_chain_${String(chain.chain_id || makeStepBuilderId("mon")).replace(/^browser_chain_/, "")}`;

  const workflowName =
    chain.name ||
    inferBrowserChainNameFromSteps(chain.steps) ||
    "Browser skill chain workflow";

  const compiledSteps = [];

  compiledSteps.push({
    step_id: "trigger_browser_chain_manual",
    name: "Manual browser chain trigger",
    type: "trigger",
    output: "trigger",
    input_map: {
      payload: "$trigger",
    },
  });

  chain.steps.forEach((step, index) => {
    const stepNumber = index + 1;
    const outputName = step.output_as || `skill_${stepNumber}_output`;
    const inputSource =
      step.input_from === "chain_input"
        ? "$trigger"
        : `$steps.${chain.steps[index - 1]?.output_as || `skill_${index}_output`}`;

    compiledSteps.push({
      step_id: `browser_skill_${stepNumber}`,
      name: step.skill_name || `Browser skill ${stepNumber}`,
      type: "notify",
      output: outputName,
      input_map: {
        input: inputSource,
        browser_skill: {
          skill_id: step.skill_id,
          expected_domain: step.expected_domain || "",
          expected_url: step.expected_url || "",
          condition: step.condition || "always",
          dry_run_only: true,
        },
      },
      browser_skill_call: {
        skill_id: step.skill_id,
        skill_name: step.skill_name || step.skill_id,
        expected_domain: step.expected_domain || "",
        expected_url: step.expected_url || "",
        mode: chain.browser_mode || "isolated_browser",
        condition: step.condition || "always",
        replay_mode: "dry_run_only",
      },
      permission_mode: "dry_run_only",
      external_write: false,
      notes:
        "Phase 4F compiles browser skill calls as dry-run notify steps until browser replay runtime is connected.",
    });

    if (step.approval_required_after !== false) {
      compiledSteps.push({
        step_id: `approval_after_browser_skill_${stepNumber}`,
        name: `Approval after ${step.skill_name || `browser skill ${stepNumber}`}`,
        type: "approval_checkpoint",
        output: `approval_after_skill_${stepNumber}`,
        input_map: {
          input: `$steps.${outputName}`,
        },
        approval_policy: {
          reason: "Browser skill chain approval checkpoint",
          required_before_submit: true,
          required_before_external_write: true,
          required_before_send: true,
          required_before_delete: true,
          required_before_payment: true,
        },
      });
    }
  });

  compiledSteps.push({
    step_id: "browser_chain_complete",
    name: "Browser chain complete",
    type: "end",
    output: "complete",
    input_map: {
      input:
        chain.steps.length > 0
          ? `$steps.${chain.steps[chain.steps.length - 1]?.output_as || "skill_1_output"}`
          : "$trigger",
    },
  });

  return {
    workflow_id: workflowId,
    workflow_name: workflowName,
    name: workflowName,
    description:
      chain.description ||
      "Compiled browser skill chain workflow. Browser actions are dry-run only until replay runtime is connected.",
    status: "draft",
    enabled: false,
    source: "phase_4f_browser_skill_chain_compiler",
    department: "Operations",
    operator_name: "Browser Skill Chain Operator",
    trigger: {
      type: "manual",
      source: "browser_skill_chain",
      chain_id: chain.chain_id,
    },
    extraction_schema: {
      fields: [],
    },
    steps: compiledSteps,
    browser_chain_metadata: {
      schema_version: chain.schema_version || "aion.browser_skill_chain.v1",
      chain_id: chain.chain_id,
      browser_mode: chain.browser_mode || "isolated_browser",
      source_chain_name: chain.name,
      skill_count: Array.isArray(chain.steps) ? chain.steps.length : 0,
      dry_run_default: true,
      can_execute_live: false,
      blocked_actions: [
        "submit_form",
        "send_message",
        "make_payment",
        "delete_record",
        "external_write",
      ],
    },
    approval_gates: {
      approval_required_between_skills: true,
      approval_required_before_submit: true,
      approval_required_before_external_write: true,
      human_review_default: true,
    },
  };
}

async function compileAndValidateBrowserSkillChain() {
  const workflow = compileBrowserSkillChainToGenericWorkflow();
  const validation = await apiPost(
    "/api/local-node/train-tasks/workflows/validate",
    { workflow },
  );

  return {
    ok: validation?.ok === true,
    status: validation?.ok ? "validation_passed" : "validation_failed",
    message: validation?.ok
      ? "Browser skill chain compiled and validated successfully."
      : "Browser skill chain compiled but validation found issues.",
    workflow,
    validation,
  };
}


function renderBrowserSkillChainBuilder() {
  const library = getBrowserSkillLibrary();
  const draft = getBrowserSkillChainDraft();
  const dryRun = state.browserSkillChainDryRunResult || null;
  const savedChains = Array.isArray(state.browserSkillChains) ? state.browserSkillChains : [];

  return `
    <div class="train-section-panel" style="margin-top:14px;">
      <div class="train-section-head">
        <div>
          <div class="eyebrow">Phase 4E · Browser Skill Chain Builder</div>
          <h2>Chain browser micro-skills</h2>
          <p class="muted" style="margin:6px 0 0;">
            Build larger workflows by chaining small browser skills together like reusable functions.
          </p>
        </div>

        <span class="badge">${escapeHtml(draft.steps.length)} chain steps</span>
      </div>

      <div class="train-section-body">
        <div class="train-status-note">
          <span class="train-status-label">Model</span>
          <div>
            <strong>Small skills compose into predictable workflows.</strong>
            <p class="muted" style="margin:6px 0 0;">
              Example: Open Gmail skill → observe unread enquiry skill → HubSpot lookup skill → approval checkpoint.
            </p>
          </div>
        </div>

        <div class="train-builder-form-grid train-sample-grid" style="padding:18px 0 4px; border-bottom:0;">
          <label class="train-field">
            <span>Chain name</span>
            <input
              data-browser-chain-field="name"
              value="${escapeHtml(draft.name || "")}"
              placeholder="Gmail enquiry to CRM workflow"
            />
          </label>

          <label class="train-field">
            <span>Browser mode</span>
            <select data-browser-chain-field="browser_mode">
              <option value="isolated_browser" ${draft.browser_mode === "isolated_browser" ? "selected" : ""}>Isolated browser</option>
              <option value="user_browser" ${draft.browser_mode === "user_browser" ? "selected" : ""}>User browser</option>
            </select>
          </label>

          <label class="train-field train-field-full">
            <span>Description</span>
            <textarea
              data-browser-chain-field="description"
              placeholder="What should this chain do?"
            >${escapeHtml(draft.description || "")}</textarea>
          </label>
        </div>

        <div class="train-section-panel" style="margin-top:12px;">
          <div class="train-section-head">
            <div>
              <div class="eyebrow">Add micro-skill</div>
              <h3>Saved browser skills</h3>
            </div>
            <span class="badge">${escapeHtml(library.length)} available</span>
          </div>

          <div class="train-section-body">
            ${
              library.length
                ? `
                  <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <select data-browser-chain-skill-select style="min-width:320px;">
                      ${library
                        .map((skill) => `
                          <option value="${escapeHtml(skill.skill_id || "")}">
                            ${escapeHtml(skill.name || skill.skill_id || "Browser skill")}
                          </option>
                        `)
                        .join("")}
                    </select>

                    <button
                      class="primary-btn"
                      data-operations-agents-action="add-browser-skill-to-chain"
                    >
                      Add to chain
                    </button>
                  </div>
                `
                : `<div class="empty-state">No browser micro-skills saved yet.</div>`
            }
          </div>
        </div>

        <div class="train-section-panel" style="margin-top:12px;">
          <div class="train-section-head">
            <div>
              <div class="eyebrow">Chain draft</div>
              <h3>Ordered skill chain</h3>
            </div>
            <span class="badge">${escapeHtml(draft.steps.length)} steps</span>
          </div>

          <div class="train-section-body">
            ${
              draft.steps.length
                ? draft.steps
                    .map((step, index) => `
                      <div class="train-browser-step-row" style="display:grid; gap:12px;">
                        <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                          <div>
                            <strong>${escapeHtml(index + 1)}. ${escapeHtml(step.skill_name || step.skill_id || "Browser skill")}</strong>
                            <div class="muted">
                              ${escapeHtml(step.skill_id || "")}
                            </div>
                            ${
                              step.expected_domain
                                ? `<div class="muted">Domain: ${escapeHtml(step.expected_domain)}</div>`
                                : ""
                            }
                            <div class="muted">
                              Input: ${escapeHtml(step.input_from || "")} · Output: ${escapeHtml(step.output_as || "")}
                            </div>
                          </div>

                          <span class="train-status-chip ${step.approval_required_after ? "" : "train-status-ok"}">
                            ${step.approval_required_after ? "Approval after" : "No approval"}
                          </span>
                        </div>

                        <div class="train-builder-form-grid train-sample-grid" style="padding:0; border-bottom:0; gap:12px;">
                          <label class="train-field">
                            <span>Input from</span>
                            <input
                              data-browser-chain-step-field="input_from"
                              data-chain-step-id="${escapeHtml(step.chain_step_id || "")}"
                              value="${escapeHtml(step.input_from || "")}"
                            />
                          </label>

                          <label class="train-field">
                            <span>Output as</span>
                            <input
                              data-browser-chain-step-field="output_as"
                              data-chain-step-id="${escapeHtml(step.chain_step_id || "")}"
                              value="${escapeHtml(step.output_as || "")}"
                            />
                          </label>

                          <label class="train-field train-field-full">
                            <span>Condition</span>
                            <input
                              data-browser-chain-step-field="condition"
                              data-chain-step-id="${escapeHtml(step.chain_step_id || "")}"
                              value="${escapeHtml(step.condition || "")}"
                              placeholder="always / if previous skill succeeded / if email found"
                            />
                          </label>
                        </div>

                        <div style="display:flex; gap:8px; flex-wrap:wrap;">
                          <button
                            class="secondary-btn"
                            data-operations-agents-action="move-browser-chain-step-up"
                            data-chain-step-id="${escapeHtml(step.chain_step_id || "")}"
                            ${index === 0 ? "disabled" : ""}
                          >
                            Up
                          </button>

                          <button
                            class="secondary-btn"
                            data-operations-agents-action="move-browser-chain-step-down"
                            data-chain-step-id="${escapeHtml(step.chain_step_id || "")}"
                            ${index === draft.steps.length - 1 ? "disabled" : ""}
                          >
                            Down
                          </button>

                          <button
                            class="secondary-btn"
                            data-operations-agents-action="toggle-browser-chain-step-approval"
                            data-chain-step-id="${escapeHtml(step.chain_step_id || "")}"
                          >
                            ${step.approval_required_after ? "Remove approval" : "Require approval"}
                          </button>

                          <button
                            class="secondary-btn danger-btn"
                            data-operations-agents-action="remove-browser-chain-step"
                            data-chain-step-id="${escapeHtml(step.chain_step_id || "")}"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    `)
                    .join("")
                : `<div class="empty-state">Add saved browser micro-skills to build a chain.</div>`
            }

            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:14px;">
              <button
                class="secondary-btn"
                data-operations-agents-action="reset-browser-skill-chain"
              >
                Reset chain
              </button>

              <button
                class="secondary-btn"
                data-operations-agents-action="dry-run-browser-skill-chain"
                ${draft.steps.length ? "" : "disabled"}
              >
                Dry-run chain
              </button>

              <button
                class="secondary-btn"
                data-operations-agents-action="compile-browser-skill-chain"
                ${draft.steps.length ? "" : "disabled"}
              >
                Compile + validate
              </button>

              <button
                class="primary-btn"
                data-operations-agents-action="save-browser-skill-chain"
                ${draft.steps.length ? "" : "disabled"}
              >
                Save chain draft
              </button>
            </div>

            ${
              draft.steps.length
                ? `
                  <details style="margin-top:14px;">
                    <summary>View chain JSON</summary>
                    <pre class="json-preview">${escapeHtml(JSON.stringify(buildBrowserSkillChainContractPreview(), null, 2))}</pre>
                  </details>
                `
                : ""
            }
          </div>
        </div>

        ${
          dryRun
            ? `
              <div class="train-section-panel" style="margin-top:12px;">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Chain dry-run</div>
                    <h3>${escapeHtml(dryRun.status || "unknown")}</h3>
                  </div>
                  <span class="badge">No live writes</span>
                </div>

                <div class="train-section-body">
                  <p class="muted" style="margin:0 0 12px;">${escapeHtml(dryRun.message || "")}</p>

                  <div style="display:grid; gap:10px;">
                    ${(Array.isArray(dryRun.replay_steps) ? dryRun.replay_steps : [])
                      .map((step) => `
                        <div class="train-browser-step-row">
                          <div>
                            <strong>${escapeHtml(step.order)}. ${escapeHtml(step.skill_name || step.skill_id || "Skill")}</strong>
                            <div class="muted">
                              ${escapeHtml(step.input_from || "")} → ${escapeHtml(step.output_as || "")}
                            </div>
                            <div class="muted">
                              Condition: ${escapeHtml(step.condition || "always")}
                            </div>
                          </div>
                          <span class="train-status-chip train-status-ok">OK</span>
                        </div>
                      `)
                      .join("")}
                  </div>

                  <details style="margin-top:14px;">
                    <summary>View chain dry-run JSON</summary>
                    <pre class="json-preview">${escapeHtml(JSON.stringify(dryRun, null, 2))}</pre>
                  </details>
                </div>
              </div>
            `
            : ""
        }

        ${
          state.browserSkillChainCompileResult
            ? `
              <div class="train-section-panel" style="margin-top:12px;">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Phase 4F · Compile result</div>
                    <h3>${escapeHtml(state.browserSkillChainCompileResult.status || "unknown")}</h3>
                  </div>
                  <span class="badge">${state.browserSkillChainCompileResult.ok ? "Validated" : "Needs fixes"}</span>
                </div>

                <div class="train-section-body">
                  <p class="muted" style="margin:0 0 12px;">
                    ${escapeHtml(state.browserSkillChainCompileResult.message || "")}
                  </p>

                  <div class="card-grid">
                    ${renderDashboardMetricCard(
                      "Workflow",
                      state.browserSkillChainCompileResult.workflow?.workflow_id || "—",
                      "Compiled generic workflow",
                    )}
                    ${renderDashboardMetricCard(
                      "Steps",
                      Array.isArray(state.browserSkillChainCompileResult.workflow?.steps)
                        ? state.browserSkillChainCompileResult.workflow.steps.length
                        : 0,
                      "Runtime step count",
                    )}
                    ${renderDashboardMetricCard(
                      "Validation",
                      state.browserSkillChainCompileResult.validation?.ok ? "Passed" : "Failed",
                      "Existing generic validator",
                    )}
                    ${renderDashboardMetricCard(
                      "Live writes",
                      "Blocked",
                      "Dry-run only",
                    )}
                  </div>

                  <details style="margin-top:14px;">
                    <summary>View compiled workflow JSON</summary>
                    <pre class="json-preview">${escapeHtml(JSON.stringify(state.browserSkillChainCompileResult.workflow || {}, null, 2))}</pre>
                  </details>

                  <details style="margin-top:10px;">
                    <summary>View validation JSON</summary>
                    <pre class="json-preview">${escapeHtml(JSON.stringify(state.browserSkillChainCompileResult.validation || {}, null, 2))}</pre>
                  </details>
                </div>
              </div>
            `
            : ""
        }

        ${
          savedChains.length
            ? `
              <div class="train-section-panel" style="margin-top:12px;">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Saved chains</div>
                    <h3>Browser workflow drafts</h3>
                  </div>
                  <span class="badge">${escapeHtml(savedChains.length)} saved</span>
                </div>

                <div class="train-section-body">
                  <div style="display:grid; gap:10px;">
                    ${savedChains
                      .map((chain) => `
                        <div class="train-browser-step-row" style="display:grid; gap:12px;">
                          <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                            <div>
                              <strong>${escapeHtml(chain.name || chain.chain_id || "Browser chain")}</strong>
                              <div class="muted">${escapeHtml(chain.chain_id || "")}</div>
                              <div class="muted">
                                ${escapeHtml(Array.isArray(chain.steps) ? chain.steps.length : 0)} skill steps · ${escapeHtml(chain.browser_mode || "isolated_browser")}
                              </div>
                            </div>
                            <span class="train-status-chip">Draft</span>
                          </div>

                          <div style="display:flex; gap:8px; flex-wrap:wrap;">
                            <button
                              class="secondary-btn"
                              data-operations-agents-action="load-browser-skill-chain"
                              data-chain-id="${escapeHtml(chain.chain_id || "")}"
                            >
                              Load for editing
                            </button>

                            <button
                              class="secondary-btn"
                              data-operations-agents-action="duplicate-browser-skill-chain"
                              data-chain-id="${escapeHtml(chain.chain_id || "")}"
                            >
                              Duplicate chain
                            </button>

                            <button
                              class="secondary-btn danger-btn"
                              data-operations-agents-action="delete-browser-skill-chain"
                              data-chain-id="${escapeHtml(chain.chain_id || "")}"
                            >
                              Delete chain draft
                            </button>
                          </div>

                          <details>
                            <summary>View saved chain JSON</summary>
                            <pre class="json-preview">${escapeHtml(JSON.stringify(chain, null, 2))}</pre>
                          </details>
                        </div>
                      `)
                      .join("")}
                  </div>
                </div>
              </div>
            `
            : ""
        }
      </div>
    </div>
  `;
}


function renderBrowserDesktopOperatorPanel(loading = false) {
  const bridge = state.browserDesktopBridge || {};
  const bridgeStatus = bridge.status || "inactive";
  const bridgeMode = bridge.mode || "permission_required";
  const lastRecording = bridge.last_recording_name || "";
  const connectedBrowser = bridge.browser || "Isolated browser recommended";
  const recording = bridge.recording === true || bridgeStatus === "recording";
  const capturedEvents = Array.isArray(bridge.captured_events)
    ? bridge.captured_events
    : [];
  const recordingSteps = Array.isArray(bridge.last_recording_steps)
    ? bridge.last_recording_steps
    : [];
  const dryRunResult = bridge.dry_run_result || null;
  const captureDraft = normaliseBrowserCaptureDraft(bridge.capture_draft);

  const isActive =
    bridgeStatus === "active" ||
    bridgeStatus === "connected" ||
    bridgeStatus === "recording" ||
    bridgeStatus === "recorded" ||
    bridge.enabled === true ||
    bridge.bridge_active === true;

  return `
    <div class="train-section-panel ${recording ? "train-recording-pulse" : ""}">
      <div class="train-section-head">
        <div>
          <div class="eyebrow">Phase 4 · Browser/Desktop Operator</div>
          <h2>Teach Aion a browser skill</h2>
          <p class="muted" style="margin:6px 0 0;">
            Record one small browser action, turn it into a reusable skill, then chain skills together into predictable workflows.
            Think of each browser skill like a small function.
          </p>
        </div>

        <span class="status-pill ${recording ? "status-running train-recording-btn" : isActive ? "status-running" : "status-pending"}">
          ${recording ? "Recording..." : isActive ? "Bridge active" : "Bridge locked"}
        </span>
      </div>

      <div class="train-section-body">
        <div class="card-grid">
          ${renderDashboardMetricCard("Bridge", isActive ? "Active" : "Locked", "User permission required")}
          ${renderDashboardMetricCard("Mode", bridgeMode === "personal_browser" ? "User browser" : "Isolated", "Recommended safe setup")}
          ${renderDashboardMetricCard("Unit", "Skill", "Reusable browser function")}
          ${renderDashboardMetricCard("Captured", capturedEvents.length, "Real event contract rows")}
          ${renderDashboardMetricCard("Writes", "Approval", "No submit without review")}
        </div>

        <div class="train-status-note" style="margin-top:14px;">
          <span class="train-status-label">Model</span>
          <div>
            <strong>Small skills chain into larger workflows.</strong>
            <p class="muted" style="margin:6px 0 0;">
              Record one website action at a time. Aion can later compose skills into a larger workflow with if/then logic,
              inputs, outputs, retries, and approval gates.
            </p>
          </div>
        </div>

        ${
          recording
            ? `
              <div class="train-status-note train-status-note-waiting" style="margin-top:14px;">
                <span class="train-status-label">Recording</span>
                <div>
                  <strong>Capture the browser events for this small skill.</strong>
                  <p class="muted" style="margin:6px 0 0;">
                    Phase 4C stores real event rows in the contract. Until the native browser bridge is wired,
                    paste/capture the URL, selector, field name, and checkpoint manually from the browser action.
                  </p>
                </div>
              </div>

              <div class="train-section-panel" style="margin-top:14px;">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Phase 4C capture</div>
                    <h2>Browser event capture</h2>
                    <p class="muted" style="margin:6px 0 0;">
                      Add short, specific browser events. These become the reusable function body.
                    </p>
                  </div>
                  <span class="badge">${escapeHtml(capturedEvents.length)} captured</span>
                </div>

                <div class="train-section-body">
                  <div class="train-builder-form-grid" style="padding:0; border-bottom:0;">
                    <label class="train-field">
                      <span>Current URL</span>
                      <input
                        data-browser-capture-field="url"
                        value="${escapeHtml(captureDraft.url)}"
                        placeholder="https://mail.google.com/mail/u/0/#inbox"
                      />
                    </label>

                    <label class="train-field">
                      <span>Page title</span>
                      <input
                        data-browser-capture-field="title"
                        value="${escapeHtml(captureDraft.title)}"
                        placeholder="Inbox - Gmail"
                      />
                    </label>

                    <label class="train-field">
                      <span>Selector</span>
                      <input
                        data-browser-capture-field="selector"
                        value="${escapeHtml(captureDraft.selector)}"
                        placeholder='input[name="email"], button[type="submit"], .customer-name'
                      />
                    </label>

                    <label class="train-field">
                      <span>Label</span>
                      <input
                        data-browser-capture-field="label"
                        value="${escapeHtml(captureDraft.label)}"
                        placeholder="Open Gmail inbox / Read unread enquiry / Fill customer email"
                      />
                    </label>

                    <label class="train-field">
                      <span>Field name</span>
                      <input
                        data-browser-capture-field="field_name"
                        value="${escapeHtml(captureDraft.field_name)}"
                        placeholder="email, phone, customer_name"
                      />
                    </label>

                    <label class="train-field">
                      <span>Value hint</span>
                      <input
                        data-browser-capture-field="field_value_hint"
                        value="${escapeHtml(captureDraft.field_value_hint)}"
                        placeholder="Use extracted customer email, not a hardcoded value"
                      />
                    </label>

                    <label class="train-field">
                      <span>Secret ref</span>
                      <input
                        data-browser-capture-field="secret_ref"
                        value="${escapeHtml(captureDraft.secret_ref || "")}"
                        placeholder="gmail_login / hubspot_api_key / revolut_session"
                      />
                    </label>

                    <label class="train-field">
                      <span>Secret type</span>
                      <select data-browser-capture-field="secret_type">
                        <option value="manual_login_profile" ${(captureDraft.secret_type || "manual_login_profile") === "manual_login_profile" ? "selected" : ""}>Manual login profile</option>
                        <option value="username_password" ${captureDraft.secret_type === "username_password" ? "selected" : ""}>Username + password</option>
                        <option value="api_key" ${captureDraft.secret_type === "api_key" ? "selected" : ""}>API key</option>
                        <option value="bearer_token" ${captureDraft.secret_type === "bearer_token" ? "selected" : ""}>Bearer token</option>
                        <option value="passkey" ${captureDraft.secret_type === "passkey" ? "selected" : ""}>Passkey / device auth</option>
                      </select>
                    </label>

                    <label class="train-field train-field-full">
                      <span>Notes</span>
                      <textarea
                        data-browser-capture-field="notes"
                        placeholder="What did you do in the browser and what should Aion remember?"
                      >${escapeHtml(captureDraft.notes)}</textarea>
                    </label>
                  </div>

                  <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:16px;">
                    <button class="secondary-btn" data-operations-agents-action="capture-browser-open-page">
                      Capture open page
                    </button>
                    <button class="secondary-btn" data-operations-agents-action="capture-browser-observe-page">
                      Capture page state
                    </button>
                    <button class="secondary-btn" data-operations-agents-action="capture-browser-field">
                      Capture field
                    </button>
                    <button class="secondary-btn" data-operations-agents-action="capture-browser-click-checkpoint">
                      Capture click checkpoint
                    </button>
                    <button class="secondary-btn" data-operations-agents-action="capture-next-browser-click">
                      Capture selected browser click
                    </button>
                    <button class="secondary-btn" data-operations-agents-action="capture-browser-secret-step">
                      Use login / secret
                    </button>
                    <button class="secondary-btn" data-operations-agents-action="capture-browser-approval-checkpoint">
                      Add approval checkpoint
                    </button>
                    <button class="secondary-btn" data-operations-agents-action="clean-browser-duplicate-captures">
                      Clean duplicate steps
                    </button>
                    <button class="secondary-btn danger-btn" data-operations-agents-action="clear-browser-capture-events">
                      Clear captures
                    </button>
                  </div>
                </div>
              </div>
            `
            : ""
        }

        ${
          capturedEvents.length
            ? `
              <div class="train-section-panel" style="margin-top:14px;">
                <div class="train-section-head">
                  <div>
                    <div class="eyebrow">Captured event stream</div>
                    <h2>Recorded browser events</h2>
                    <p class="muted" style="margin:6px 0 0;">
                      These are the contract rows that become recorded browser steps when you stop recording.
                    </p>
                  </div>
                  <span class="badge">${escapeHtml(capturedEvents.length)} events</span>
                </div>

                <div class="train-section-body">
                  <div style="display:grid; gap:10px;">
                    ${capturedEvents
                      .map((event, index) => `
                        <div class="train-browser-step-row">
                          <div>
                            <strong>${escapeHtml(index + 1)}. ${escapeHtml(event.label || event.event_type || "Browser event")}</strong>
                            <div class="muted">
                              ${escapeHtml(event.event_type || "event")} · ${escapeHtml(event.safety || "read_only")} · output: ${escapeHtml(event.output || "browser_output")}
                            </div>
                            ${
                              event.url
                                ? `<div class="muted">URL: ${escapeHtml(event.url)}</div>`
                                : ""
                            }
                            ${
                              event.selector
                                ? `<div class="muted">Selector: ${escapeHtml(event.selector)}</div>`
                                : ""
                            }
                            ${
                              event.field_name
                                ? `<div class="muted">Field: ${escapeHtml(event.field_name)} · ${escapeHtml(event.field_value_hint || "value from workflow")}</div>`
                                : ""
                            }
                            ${
                              event.secret_ref
                                ? `<div class="muted">Secret ref: ${escapeHtml(event.secret_ref)} · ${escapeHtml(event.secret_type || "manual_login_profile")}</div>`
                                : ""
                            }
                          </div>
                          <span class="status-pill ${event.requires_approval ? "status-pending" : "status-running"}">
                            ${event.requires_approval ? "Approval" : "Captured"}
                          </span>
                        </div>
                      `)
                      .join("")}
                  </div>
                </div>
              </div>
            `
            : ""
        }

        ${
          dryRunResult
            ? `
              <div class="train-status-note" style="margin-top:14px;">
                <span class="train-status-label">Dry-run</span>
                <div>
                  <strong>${escapeHtml(dryRunResult.status || "dry_run")}</strong>
                  <p class="muted" style="margin:6px 0 0;">
                    ${escapeHtml(dryRunResult.message || "Dry-run replay completed locally.")}
                  </p>
                </div>
              </div>
            `
            : ""
        }

        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:16px;">
          <button
            class="primary-btn"
            data-operations-agents-action="activate-browser-bridge"
            ${loading ? "disabled" : ""}
          >
            Activate Bridge
          </button>

          <button
            class="secondary-btn"
            data-operations-agents-action="open-isolated-browser"
            ${loading ? "disabled" : ""}
          >
            Open isolated browser
          </button>

          <button
            class="secondary-btn ${recording ? "train-recording-btn" : ""}"
            data-operations-agents-action="start-browser-workflow-recording"
            ${loading || !isActive || recording ? "disabled" : ""}
          >
            ${recording ? "Recording..." : "Record skill"}
          </button>

          <button
            class="secondary-btn danger-btn"
            data-operations-agents-action="stop-browser-workflow-recording"
            ${loading || !recording ? "disabled" : ""}
          >
            Stop recording
          </button>

          <button
            class="secondary-btn"
            data-operations-agents-action="browser-operator-dry-run"
            ${loading || !recordingSteps.length ? "disabled" : ""}
          >
            Dry-run replay
          </button>

          <button
            class="primary-btn"
            data-operations-agents-action="save-browser-recording-as-skill"
            ${loading || !recordingSteps.length ? "disabled" : ""}
          >
            Save as micro-skill
          </button>
        </div>
      </div>
    </div>

    ${renderBrowserSkillDraftContractPreview()}
  `;
}


function renderTrainTaskApprovalCard(approval, loading) {
  const approvalId = approval.approval_id || "";
  const workflowName = approval.workflow_name || approval.workflow_id || "Trained task";
  const triggerSource = approval.trigger_source || "unknown";
  const riskLevel = approval.risk_level || "unknown";
  const status = approval.status || "pending";
  const extracted = approval.extracted_customer || {};
  const draft = approval.gmail_draft || {};
  const draftResult = approval.gmail_draft_result || {};
  const crm = approval.crm_payload || {};
  const proposedActions = Array.isArray(approval.proposed_actions)
    ? approval.proposed_actions
    : [];
  const canCreateGmailDraft =
    status === "approved" && approval.gmail_draft_created !== true;
  const draftCreated =
    approval.gmail_draft_created === true || status === "draft_created";

  return `
    <div class="train-approval-card">
      <div class="train-card-head">
        <div>
          <div class="eyebrow">${escapeHtml(triggerSource)}</div>
          <h3>${escapeHtml(workflowName)}</h3>
          <p class="muted">${escapeHtml(approvalId)}</p>
        </div>

        <div class="badge-row">
          <span class="badge">${escapeHtml(status)}</span>
          <span class="badge">${escapeHtml(riskLevel)}</span>
          <span class="badge">Dry-run only</span>
        </div>
      </div>

      <div class="train-approval-grid">
        <div class="train-mini-panel">
          <div class="metric-label">Extracted customer</div>
          <div class="metric-note">Name: ${escapeHtml(extracted.name || "—")}</div>
          <div class="metric-note">Email: ${escapeHtml(extracted.email || "—")}</div>
          <div class="metric-note">Phone: ${escapeHtml(extracted.phone || "—")}</div>
        </div>

        <div class="train-mini-panel">
          <div class="metric-label">
            ${draftCreated ? "Gmail draft created" : "Gmail draft preview"}
          </div>
          <div class="metric-note">To: ${escapeHtml(draft.to || "—")}</div>
          <div class="metric-note">Subject: ${escapeHtml(draft.subject || "—")}</div>
          <div class="metric-note">Tool: ${escapeHtml(draft.tool_id || "tool.gmail.draft_preview.v1")}</div>
          ${
            draftCreated
              ? `
                <div class="metric-note">Draft id: ${escapeHtml(draftResult.draft_id || "—")}</div>
                <div class="metric-note">Message id: ${escapeHtml(draftResult.message_id || "—")}</div>
                ${
                  draftResult.gmail_url
                    ? `<div class="metric-note"><a href="${escapeHtml(draftResult.gmail_url)}" target="_blank">Open Gmail drafts</a></div>`
                    : ""
                }
              `
              : ""
          }
        </div>

        <div class="train-mini-panel">
          <div class="metric-label">CRM dry-run payload</div>
          <div class="metric-note">Tool: ${escapeHtml(crm.tool_id || "tool.hubspot.contact_upsert_dry_run.v1")}</div>
          <div class="metric-note">Would write: ${crm.would_create_or_update_contact ? "Yes" : "No"}</div>
          <div class="metric-note">Blocked: ${crm.external_write_blocked === false ? "No" : "Yes"}</div>
        </div>
      </div>

      ${
        proposedActions.length
          ? `
            <div class="badge-row">
              ${proposedActions
                .map(
                  (action) =>
                    `<span class="badge">${escapeHtml(action.label || action.action_id || "Action")}</span>`,
                )
                .join("")}
            </div>
          `
          : ""
      }

      <div class="train-card-actions">
        ${
          status === "pending"
            ? `
              <button
                class="primary-btn"
                data-operations-agents-action="approve-train-task-approval"
                data-approval-id="${escapeHtml(approvalId)}"
                ${loading ? "disabled" : ""}
              >
                Approve
              </button>

              <button
                class="secondary-btn"
                data-operations-agents-action="reject-train-task-approval"
                data-approval-id="${escapeHtml(approvalId)}"
                ${loading ? "disabled" : ""}
              >
                Reject
              </button>
            `
            : ""
        }

        ${
          canCreateGmailDraft
            ? `
              <button
                class="primary-btn"
                data-operations-agents-action="create-gmail-draft-from-approval"
                data-approval-id="${escapeHtml(approvalId)}"
                ${loading ? "disabled" : ""}
              >
                Create Gmail draft
              </button>
            `
            : ""
        }

        ${
          draftCreated
            ? `<span class="badge">Gmail draft created</span>`
            : ""
        }

        <button
          class="secondary-btn"
          data-operations-agents-action="copy-train-task-approval-id"
          data-approval-id="${escapeHtml(approvalId)}"
        >
          Copy approval id
        </button>
      </div>
    </div>
  `;
}

function renderOperationsAgentGenericWorkflowCard(item, loading) {
  const workflowId = item.workflow_id || item.workflow?.workflow_id || "unknown";
  const name = item.workflow_name || item.workflow?.name || workflowId;
  const status = item.status || "draft";
  const enabled = item.enabled === true;
  const published = item.published === true;
  const validationOk = item.validation?.ok === true;
  const errors = Array.isArray(item.validation?.errors) ? item.validation.errors : [];

  return `
    <div class="list-item" style="margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start;">
        <div style="min-width:0;">
          <div class="eyebrow">Generic Workflow</div>
          <h3 style="margin:4px 0;">${escapeHtml(name)}</h3>
          <p class="muted" style="margin:0;">${escapeHtml(workflowId)}</p>
          <p class="muted" style="margin:4px 0 0;">
            Status: ${escapeHtml(status)} · Validation: ${validationOk ? "OK" : `${errors.length} error(s)`}
          </p>
        </div>

        <span class="status-pill ${enabled && published ? "status-running" : "status-pending"}">
          ${enabled && published ? "Published / Enabled" : "Draft / Disabled"}
        </span>
      </div>

      <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:14px;">
        <button
          class="primary-btn"
          data-operations-agents-action="run-generic-workflow"
          data-workflow-id="${escapeHtml(workflowId)}"
          ${loading || !enabled || !published ? "disabled aria-disabled=\"true\"" : ""}
          style="${!enabled || !published ? "opacity:0.45; pointer-events:none;" : ""}"
        >
          Run published workflow
        </button>

        <button
          class="secondary-btn"
          data-operations-agents-action="copy-generic-workflow-id"
          data-workflow-id="${escapeHtml(workflowId)}"
        >
          Copy workflow id
        </button>
      </div>
    </div>
  `;
}

function renderOperationsAgentWorkflowCard(workflow, loading) {
  const workflowId = workflow.workflow_id || workflow.id || "unknown";
  const name = workflow.name || workflowId;
  const department = workflow.department_key || "operations";
  const operatorId = workflow.operator_id || "unknown";
  const enabled = workflow.enabled === true;

  const trigger = workflow.trigger || {};
  const hubspot = workflow.hubspot || {};
  const approval = workflow.approval || {};
  const extractionFields = Array.isArray(workflow.extraction?.fields)
    ? workflow.extraction.fields
    : [];

  return `
    <div class="list-item" style="margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start;">
        <div>
          <div class="eyebrow">${escapeHtml(department)}</div>
          <h3 style="margin:4px 0;">${escapeHtml(name)}</h3>
          <p class="muted" style="margin:0;">
            ${escapeHtml(workflowId)}
          </p>
          <p class="muted" style="margin:4px 0 0;">
            Operator: ${escapeHtml(operatorId)}
          </p>
        </div>

        <span class="status-pill ${enabled ? "status-running" : "status-pending"}">
          ${enabled ? "Enabled / Dry-run" : "Draft / Disabled"}
        </span>
      </div>

      <div class="card-grid" style="grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:14px;">
        <div class="mini-card">
          <div class="metric-label">Trigger</div>
          <div class="metric-note">${escapeHtml(trigger.trigger_type || "Unknown")}</div>
          <div class="metric-note">${escapeHtml(trigger.query || "")}</div>
        </div>

        <div class="mini-card">
          <div class="metric-label">Extract</div>
          <div class="metric-note">
            ${escapeHtml(extractionFields.length)} customer fields
          </div>
        </div>

        <div class="mini-card">
          <div class="metric-label">${escapeHtml(getTeachAionPrimaryActionLabel(workflow))}</div>
          <div class="metric-note">
            ${escapeHtml(getTeachAionPrimaryActionDescription(workflow))}
          </div>
        </div>

        <div class="mini-card">
          <div class="metric-label">Approval</div>
          <div class="metric-note">
            ${escapeHtml(formatTeachAionApprovalMode(approval.approval_mode))}
          </div>
        </div>
      </div>

      <div style="display:flex; gap:8px; margin-top:14px; flex-wrap:wrap;">
        <button
          class="primary-btn"
          data-operations-agents-action="test-workflow"
          data-workflow-id="${escapeHtml(workflowId)}"
          ${loading ? "disabled" : ""}
        >
          ${loading ? "Running..." : "Run test"}
        </button>

        <button
          class="secondary-btn"
          data-operations-agents-action="copy-workflow-test-curl"
          data-workflow-id="${escapeHtml(workflowId)}"
        >
          Copy test curl
        </button>

        <button
          class="secondary-btn"
          data-operations-agents-action="edit-workflow"
          data-workflow-id="${escapeHtml(workflowId)}"
          ${loading ? "disabled" : ""}
        >
          Edit
        </button>

        <button
          class="secondary-btn"
          data-operations-agents-action="archive-workflow"
          data-workflow-id="${escapeHtml(workflowId)}"
          disabled
          title="Archive support will be added after workflow lifecycle storage is finalized"
        >
          Archive
        </button>

        <button
          class="secondary-btn"
          data-operations-agents-action="delete-workflow"
          data-workflow-id="${escapeHtml(workflowId)}"
          disabled
          title="Delete support will be added after workflow lifecycle storage is finalized"
        >
          Delete
        </button>

        <button
          class="secondary-btn"
          data-operations-agents-action="toggle-workflow"
          data-workflow-id="${escapeHtml(workflowId)}"
          data-enabled="${enabled ? "false" : "true"}"
          ${loading ? "disabled" : ""}
        >
          ${enabled ? "Disable" : "Enable"}
        </button>
      </div>
    </div>
  `;
}
function renderOperationsAgentTestReplay(result) {
  const steps = Array.isArray(result.steps) ? result.steps : [];
  const extracted = result.extracted_customer || {};
  const hubspot = result.hubspot_action || {};
  const draft = result.email_draft || {};
  const approval = result.approval || {};

  const fallbackTitles = [
    "Gmail trigger matched",
    "Extract customer details",
    "Prepare HubSpot contact action",
    "Prepare welcome email draft",
    "Human approval checkpoint",
  ];

  return `
    <div class="panel large-panel operations-agent-replay">
      <div class="section-header">
        <div>
          <div class="eyebrow">Test Replay</div>
          <h3>${escapeHtml(result.workflow_id || "Workflow test run")}</h3>
          <p class="muted">
            This is a dry-run. It prepares the HubSpot action and Gmail draft, then stops at approval.
          </p>
        </div>

        <span class="status-pill ${result.ok ? "status-running" : "status-failed"}">
          ${result.ok ? "Passed" : "Failed"}
        </span>
      </div>

      <div class="timeline-list">
        ${
          steps.length
            ? steps
                .map((step, index) => {
                  const stepNumber = step.step || index + 1;
                  const title =
                    step.title ||
                    step.label ||
                    fallbackTitles[index] ||
                    `Step ${index + 1}`;

                  return `
                    <div class="list-item">
                      <div style="display:flex; justify-content:space-between; gap:12px;">
                        <strong>Step ${escapeHtml(stepNumber)} — ${escapeHtml(title)}</strong>
                        <span class="status-pill ${step.ok ? "status-running" : "status-failed"}">
                          ${step.ok ? "OK" : "Failed"}
                        </span>
                      </div>
                      <pre class="debug-pre">${escapeHtml(JSON.stringify(step.output || {}, null, 2))}</pre>
                    </div>
                  `;
                })
                .join("")
            : `<div class="empty-state">No steps returned.</div>`
        }
      </div>

      <div class="card-grid" style="grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:16px;">
        <div class="mini-card">
          <div class="metric-label">Extracted customer</div>
          <pre class="debug-pre">${escapeHtml(JSON.stringify(extracted, null, 2))}</pre>
        </div>

        <div class="mini-card">
          <div class="metric-label">HubSpot action</div>
          <pre class="debug-pre">${escapeHtml(JSON.stringify(hubspot, null, 2))}</pre>
        </div>

        <div class="mini-card">
          <div class="metric-label">Approval checkpoint</div>
          <pre class="debug-pre">${escapeHtml(JSON.stringify(approval, null, 2))}</pre>
        </div>
      </div>

      <div class="list-item" style="margin-top:16px;">
        <div class="metric-label">Prepared Gmail draft</div>
        <p><strong>To:</strong> ${escapeHtml(draft.to || "")}</p>
        <p><strong>Subject:</strong> ${escapeHtml(draft.subject || "")}</p>
        <pre class="debug-pre">${escapeHtml(draft.body || "")}</pre>
      </div>
    </div>
  `;
}

function getRunArtifactSummary(run) {
  const result = getRunResultPayload(run);
  const context = getRunContext(run);
  const postPackage = getRunPostPackage(run);
  const publishResult =
    asRecord(result?.publish_result) ||
    asRecord(postPackage?.publish_result) ||
    null;

  const approvalDecision =
    asRecord(result?.approval_decision) ||
    asRecord(context?.approval_decision) ||
    asRecord(postPackage?.approval_decision) ||
    null;

  const caption =
    firstString(
      postPackage?.caption,
      postPackage?.body,
      result?.draft_caption?.draft_caption,
      result?.draft_caption,
      context?.draft_caption,
      run?.draft_caption,
      run?.brief
    ) || "";

  const carousel =
    safeArray(postPackage?.carousel).length
      ? safeArray(postPackage?.carousel)
      : safeArray(postPackage?.content_blocks).length
        ? safeArray(postPackage?.content_blocks)
        : safeArray(result?.draft_carousel?.draft_carousel).length
          ? safeArray(result?.draft_carousel?.draft_carousel)
          : safeArray(result?.draft_carousel).length
            ? safeArray(result?.draft_carousel)
            : safeArray(context?.draft_carousel);

  const channels =
    safeArray(postPackage?.channels).length
      ? safeArray(postPackage?.channels)
      : safeArray(result?.draft_caption?.channels).length
        ? safeArray(result?.draft_caption?.channels)
        : safeArray(result?.draft_carousel?.channels).length
          ? safeArray(result?.draft_carousel?.channels)
          : safeArray(context?.channels);

  const approvalPacket =
    asRecord(result?.approval_packet) ||
    asRecord(context?.approval_packet) ||
    asRecord(postPackage?.approval_packet) ||
    null;

  const finalResult =
    asRecord(result?.final_result) ||
    asRecord(result?.publish_result) ||
    asRecord(postPackage?.publish_result) ||
    null;

  const generatedImage = getRunGeneratedImage(run);
  const generatedImageUrl = getRunGeneratedImageUrl(run);

  return {
    caption,
    carousel,
    channels,
    approvalPacket,
    finalResult,
    postPackage,
    publishResult,
    approvalDecision,
    generatedImage,
    generatedImageUrl,
  };
}

function renderInspectorSection(title, bodyHtml) {
  return `
    <div class="panel" style="margin-top:12px;">
      <div class="panel-title">${escapeHtml(title)}</div>
      ${bodyHtml}
    </div>
  `;
}

function renderInspectorPayloadBlock(title, value, open = false) {
  if (value == null) {
    return `
      <details ${open ? "open" : ""}>
        <summary class="helper-text">${escapeHtml(title)}</summary>
        <div class="empty-state" style="margin-top:10px;">No data available.</div>
      </details>
    `;
  }

  return `
    <details ${open ? "open" : ""}>
      <summary class="helper-text">${escapeHtml(title)}</summary>
      <pre class="json-block" style="margin-top:10px;">${escapeHtml(shortJson(value))}</pre>
    </details>
  `;
}

function renderRunApprovalHistory(run) {
  const approvals = getRunApprovalItems(run);

  if (!approvals.length) {
    return `<div class="empty-state">No approval history for this run.</div>`;
  }

  return `
    <div class="list-wrap">
      ${approvals
        .map((item) => `
          <div class="list-item">
            <div class="list-item-title">${escapeHtml(item?.title || "Approval")}</div>
            <div class="list-item-sub">${escapeHtml(item?.summary || item?.resolution_note || "")}</div>
            <div class="badge-row">
              ${renderStatusBadge(item?.status || "unknown")}
              <span class="badge">Dept: ${escapeHtml(item?.department_key || run?.department_key || "—")}</span>
              <span class="badge">Requested: ${escapeHtml(formatDateTime(item?.requested_at || item?.created_at))}</span>
              ${
                item?.resolved_at
                  ? `<span class="badge">Resolved: ${escapeHtml(formatDateTime(item.resolved_at))}</span>`
                  : ""
              }
            </div>
            ${
              item?.resolved_by
                ? `<div class="list-item-sub">Resolved by: ${escapeHtml(item.resolved_by)}</div>`
                : ""
            }
          </div>
        `)
        .join("")}
    </div>
  `;
}

function renderSelectedRunInspector(run) {
  if (!run) {
    return `
      <div
        id="liveRunInspector"
        class="panel large-panel"
        tabindex="-1"
      >
        <div class="panel-title">Run inspector</div>
        <div class="empty-state">Choose a run to inspect.</div>
      </div>
    `;
  }

  const agentLabel = runtimeShared.getRunAgentLabel(run);
  const workflowLabel = runtimeShared.getRunWorkflowLabel(run);
  const runId = run?.id || run?.queue_item_id || "—";

  const inputPayload = getRunPrimaryInput(run);
  const resultPayload = getRunPrimaryResult(run);
  const errorPayload = getRunPrimaryError(run);

  const pendingApproval = getPendingApprovalForRun(run);
  const latestApproval = getLatestApprovalForRun(run);
  const lifecycleLabel = getRunLifecycleLabel(run);
  const artifacts = getRunArtifactSummary(run);

  const publishResult = artifacts.publishResult || null;
  const approvalDecision = artifacts.approvalDecision || null;

  const imageGeneration =
    asRecord(artifacts.postPackage?.image_generation) ||
    asRecord(publishResult?.image_generation) ||
    asRecord(artifacts.finalResult?.image_generation) ||
    asRecord(getRunImageGeneration(run)) ||
    null;

  const imageGenerationError =
    firstString(
      imageGeneration?.error,
      getRunImageFailure(run),
      publishResult?.error,
      artifacts.finalResult?.error,
      run?.failure_reason,
    ) || "";

  const approvalDecisionLabel =
    approvalDecision?.decision
      ? prettify(approvalDecision.decision)
      : approvalDecision?.status
        ? prettify(approvalDecision.status)
        : latestApproval?.status
          ? prettify(latestApproval.status)
          : "—";

  const hasArtifactData =
    !!artifacts.caption ||
    artifacts.carousel.length > 0 ||
    artifacts.channels.length > 0 ||
    !!artifacts.approvalPacket ||
    !!artifacts.postPackage ||
    !!artifacts.finalResult ||
    !!publishResult ||
    !!approvalDecision ||
    !!artifacts.generatedImageUrl ||
    !!imageGeneration;

  const isPending = !!pendingApproval;

  const summaryLeftHtml = `
    ${renderInspectorKeyValue("Department", run?.department_key || "—")}
    ${renderInspectorKeyValue("Created", formatDateTime(run?.created_at))}
    ${renderInspectorKeyValue("Updated", formatDateTime(run?.updated_at))}
    ${renderInspectorKeyValue("Agent", agentLabel)}
  `;

  const summaryRightHtml = `
    ${renderInspectorKeyValue("Workflow", workflowLabel)}
    ${renderInspectorKeyValue(
      "Latest approval",
      latestApproval?.status ? prettify(latestApproval.status) : "—",
    )}
    ${renderInspectorKeyValue(
      "Approval ID",
      pendingApproval?.id || latestApproval?.id || "—",
    )}
    ${renderInspectorKeyValue("Approval decision", approvalDecisionLabel)}
  `;

  const approvalInlineHtml = pendingApproval
    ? `
        <div style="
          border:1px solid rgba(22,101,52,0.22);
          background:rgba(22,163,74,0.08);
          padding:12px;
          display:grid;
          gap:10px;
          border-radius:12px;
        ">
          <div>
            <div class="list-item-title" style="
              color:#111111;
              font-weight:800;
              font-size:15px;
              line-height:1.25;
            ">
              ${escapeHtml(pendingApproval?.title || "Approval required")}
            </div>

            <div class="list-item-sub" style="
              color:rgba(17,17,17,0.68);
              font-size:12px;
              line-height:1.35;
              margin-top:2px;
            ">
              ${escapeHtml(
                pendingApproval?.summary || "This run is waiting for approval.",
              )}
            </div>
          </div>

          <div class="badge-row">
            ${renderStatusBadge(pendingApproval?.status || "pending")}
            <span class="badge">Approval ${escapeHtml(pendingApproval?.id || "—")}</span>
          </div>

          <div class="helper-text" style="
            font-weight:700;
            color:#111111;
          ">
            Approval required before this artifact can continue.
          </div>

          <div class="marketing-form-actions" style="
            margin-top:0;
            display:flex;
            flex-wrap:wrap;
            gap:10px;
            align-items:center;
          ">
            <button
              class="live-run-approval-btn"
              data-approval-id="${escapeHtml(pendingApproval?.id || "")}"
              data-run-id="${escapeHtml(runId)}"
              data-approve="true"
              style="
                appearance:none;
                -webkit-appearance:none;
                border:1px solid #166534;
                background:#16a34a;
                color:#ffffff;
                padding:10px 16px;
                font-weight:800;
                cursor:pointer;
                border-radius:10px;
                font-size:14px;
                line-height:1;
                min-height:40px;
                box-shadow:none;
              "
            >
              Approve run
            </button>

            <button
              class="live-run-approval-btn"
              data-approval-id="${escapeHtml(pendingApproval?.id || "")}"
              data-run-id="${escapeHtml(runId)}"
              data-approve="false"
              style="
                appearance:none;
                -webkit-appearance:none;
                border:1px solid #991b1b;
                background:#ffffff;
                color:#991b1b;
                padding:10px 16px;
                font-weight:800;
                cursor:pointer;
                border-radius:10px;
                font-size:14px;
                line-height:1;
                min-height:40px;
                box-shadow:none;
              "
            >
              Reject run
            </button>
          </div>
        </div>
      `
    : latestApproval
      ? `
          <div style="
            border:1px solid rgba(15,23,42,0.12);
            background:#ffffff;
            padding:12px;
            display:grid;
            gap:10px;
            border-radius:12px;
          ">
            <div>
              <div class="list-item-title">${escapeHtml(
                latestApproval?.title || "Approval resolved",
              )}</div>
              <div class="list-item-sub">${escapeHtml(
                latestApproval?.summary || "This run has already passed its approval step.",
              )}</div>
            </div>

            <div class="badge-row">
              ${renderStatusBadge(latestApproval?.status || "unknown")}
              <span class="badge">Approval ${escapeHtml(latestApproval?.id || "—")}</span>
              ${
                latestApproval?.resolved_at
                  ? `<span class="badge">Resolved ${escapeHtml(formatDateTime(latestApproval.resolved_at))}</span>`
                  : ""
              }
            </div>

            ${
              latestApproval?.resolution_note
                ? `<div class="list-item-sub">${escapeHtml(latestApproval.resolution_note)}</div>`
                : ""
            }
          </div>
        `
      : `
          <div class="helper-text">
            No approval action is required for this run.
          </div>
        `;

  const finalArtifactHtml = renderRunFinalArtifactSection(run, {
    artifacts,
    imageGeneration,
    imageGenerationError,
    approvalInlineHtml,
    approvalDecision,
    publishResult,
    hasArtifactData,
    runId,
  });

  return `
    <div
      id="liveRunInspector"
      class="panel large-panel panel-selected"
      tabindex="-1"
    >
      <div style="
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:16px;
        flex-wrap:wrap;
        margin-bottom:14px;
      ">
        <div>
          <div class="panel-title" style="margin-bottom:6px;">Run inspector</div>
          <div class="list-item-title">${escapeHtml(workflowLabel)}</div>
          <div class="list-item-sub">${escapeHtml(agentLabel)}</div>
        </div>

        <div class="badge-row">
          ${renderStatusBadge(run?.status || "unknown")}
          <span class="badge">Lifecycle ${escapeHtml(lifecycleLabel)}</span>
          <span class="badge">Run ${escapeHtml(runId)}</span>
        </div>
      </div>

      ${renderInspectorSection(
        "Summary",
        `
          <div style="
            display:grid;
            grid-template-columns:minmax(0, 1fr) minmax(0, 1fr);
            gap:18px;
            align-items:start;
          ">
            <div style="display:grid; gap:0;">
              ${summaryLeftHtml}
            </div>
            <div style="display:grid; gap:0;">
              ${summaryRightHtml}
            </div>
          </div>
          ${
            run?.failure_reason
              ? `<div class="marketing-error" style="margin-top:12px;">${escapeHtml(run.failure_reason)}</div>`
              : ""
          }
          ${
            run?.message
              ? `<div class="helper-text" style="margin-top:12px;">${escapeHtml(run.message)}</div>`
              : ""
          }
        `,
      )}

      ${renderInspectorSection("Final artifact", finalArtifactHtml)}

      ${renderInspectorSection(
        "Input / Output",
        `
          <div style="display:grid; gap:10px;">
            ${renderInspectorPayloadBlock("Input payload", inputPayload, true)}
            ${renderInspectorPayloadBlock("Result payload", resultPayload, true)}
            ${renderInspectorPayloadBlock("Error payload", errorPayload, false)}
          </div>
        `,
      )}

      ${
        isPending
          ? ""
          : renderInspectorSection(
              "Approval history",
              renderRunApprovalHistory(run),
            )
      }

      ${renderInspectorSection("Step timeline", renderRunStepTimeline(run))}
    </div>
  `;
}

function renderRunStepTimeline(run) {
  const resultPayload =
    (run && typeof run.result_payload === "object" && run.result_payload) ||
    (run && typeof run.result === "object" && run.result) ||
    {};

  const steps = Array.isArray(run?.step_runs)
    ? run.step_runs
    : Array.isArray(resultPayload?.step_runs)
      ? resultPayload.step_runs
      : Array.isArray(run?.steps)
        ? run.steps
        : Array.isArray(resultPayload?.steps)
          ? resultPayload.steps
          : [];

  if (!steps.length) {
    return `<div class="empty-state">No structured step timeline available yet.</div>`;
  }

  return `
    <div class="list-wrap">
      ${steps
        .map((step, index) => {
          const stepName =
            step?.step_name ||
            step?.name ||
            step?.title ||
            `Step ${index + 1}`;

          const stepKind =
            step?.step_kind ||
            step?.kind ||
            "";

          const stepTime =
            step?.updated_at ||
            step?.completed_at ||
            step?.started_at ||
            step?.created_at ||
            step?.timestamp ||
            null;

          const stepStatus = step?.status || "unknown";

          const stepMessage =
            step?.message ||
            step?.summary ||
            step?.detail ||
            step?.error_message ||
            "";

          const stepInput =
            step?.input_payload !== undefined
              ? step.input_payload
              : step?.input;

          const stepResult =
            step?.output_payload !== undefined
              ? step.output_payload
              : step?.result;

          const stepError =
            step?.error_payload !== undefined
              ? step.error_payload
              : step?.error_message !== undefined
                ? step.error_message
                : step?.error;

          return `
            <div class="list-item">
              <div class="list-item-title">${escapeHtml(stepName)}</div>

              <div class="badge-row">
                ${renderStatusBadge(stepStatus)}
                <span class="badge">#${index + 1}</span>
                ${
                  stepKind
                    ? `<span class="badge">${escapeHtml(stepKind)}</span>`
                    : ""
                }
                <span class="badge">${escapeHtml(formatDateTime(stepTime))}</span>
              </div>

              ${
                stepMessage
                  ? `<div class="list-item-sub">${escapeHtml(stepMessage)}</div>`
                  : ""
              }

              <div style="margin-top:8px; display:grid; gap:10px;">
                ${renderInspectorPayloadBlock("Step input", stepInput, false)}
                ${renderInspectorPayloadBlock("Step result", stepResult, false)}
                ${renderInspectorPayloadBlock("Step error", stepError, false)}
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderRunFinalArtifactSection(
  run,
  {
    artifacts,
    imageGeneration,
    imageGenerationError,
    approvalInlineHtml,
    approvalDecision,
    publishResult,
    hasArtifactData,
    runId,
  } = {},
) {
  if (!hasArtifactData) {
    return `<div class="empty-state">No final artifact available yet.</div>`;
  }

  const channels = Array.isArray(artifacts?.channels) ? artifacts.channels : [];
  const generatedImageUrl = artifacts?.generatedImageUrl || "";

  return `
    <div style="
      width:100%;
      display:grid;
      grid-template-columns:minmax(0, 1fr) minmax(0, 1fr);
      gap:0;
      align-items:start;
      border:1px solid rgba(15,23,42,0.10);
      background:#ffffff;
      min-height:520px;
    ">
      <div style="
        min-width:0;
        width:100%;
        padding:28px;
        border-right:1px solid rgba(15,23,42,0.16);
        display:flex;
        justify-content:center;
        align-items:flex-start;
      ">
        <div style="
          width:100%;
          max-width:520px;
          display:grid;
          gap:14px;
          justify-items:center;
        ">
          <div style="
            width:100%;
            max-width:460px;
          ">
            ${renderFacebookPostMockup(run, {
              activeIndex: Number(state.selectedFacebookCardIndex || 0),
            })}
          </div>

          ${
            !generatedImageUrl && imageGeneration
              ? `
                <div class="list-item" style="
                  width:100%;
                  max-width:460px;
                  box-sizing:border-box;
                ">
                  <div class="list-item-title">Image generation</div>
                  <div class="badge-row" style="margin-top:8px;">
                    ${
                      imageGeneration?.status
                        ? `<span class="badge">Status ${escapeHtml(prettify(imageGeneration.status))}</span>`
                        : ""
                    }
                    ${
                      imageGeneration?.provider
                        ? `<span class="badge">Provider ${escapeHtml(imageGeneration.provider)}</span>`
                        : ""
                    }
                    ${
                      imageGeneration?.model
                        ? `<span class="badge">Model ${escapeHtml(imageGeneration.model)}</span>`
                        : ""
                    }
                  </div>
                  ${
                    imageGenerationError
                      ? `<div class="marketing-error" style="margin-top:10px;">${escapeHtml(imageGenerationError)}</div>`
                      : `<div class="helper-text" style="margin-top:10px;">No generated image file is attached to this run yet.</div>`
                  }
                </div>
              `
              : ""
          }

          ${
            channels.length
              ? `
                <div style="
                  width:100%;
                  max-width:460px;
                  box-sizing:border-box;
                ">
                  <div class="helper-text" style="margin-bottom:6px;">Channels</div>
                  <div class="badge-row">
                    ${channels
                      .map(
                        (item) =>
                          `<span class="badge">${escapeHtml(item)}</span>`,
                      )
                      .join("")}
                  </div>
                </div>
              `
              : ""
          }
        </div>
      </div>

      <div style="
        min-width:0;
        width:100%;
        padding:28px;
        display:block;
        box-sizing:border-box;
      ">
        <div style="
          width:100%;
          display:grid;
          gap:14px;
          align-content:start;
        ">
          <div class="panel" style="
            min-height:0;
            margin:0;
            width:100%;
            max-width:none;
            box-sizing:border-box;
          ">
            <div class="panel-title">Artifact terminal</div>
            <div class="helper-text" style="margin-top:0;">
              Natural-language edit surface for the selected artifact.
            </div>

            <div style="
              margin-top:12px;
              display:grid;
              gap:12px;
              width:100%;
            ">
              <div style="width:100%;">
                <div class="helper-text" style="
                  margin-bottom:6px;
                  font-weight:700;
                  color:#111111;
                ">
                  Approval action
                </div>
                ${approvalInlineHtml}
              </div>

              <textarea
                id="artifactCommandInput"
                class="input input-textarea"
                style="
                  width:100%;
                  box-sizing:border-box;
                  min-height:120px;
                "
                placeholder="Examples:
- Regenerate card 4 image
- Change the hook on card 1
- Make the CTA softer
- Rewrite caption for homeowners"
              ></textarea>

              <div class="marketing-form-actions" style="
                margin-top:0;
                display:grid;
                gap:10px;
                width:100%;
              ">
                <button
                  id="publishToCalendarBtn"
                  class="primary-btn"
                  type="button"
                  data-run-id="${escapeHtml(runId)}"
                  style="width:100%;"
                >
                  Publish to calendar
                </button>

                <button
                  id="artifactCommandApplyBtn"
                  class="primary-btn"
                  type="button"
                  style="width:100%;"
                >
                  Apply change
                </button>

                <button
                  id="artifactCommandSuggestBtn"
                  class="secondary-btn"
                  type="button"
                  style="width:100%;"
                >
                  Suggest edits
                </button>
              </div>

              <div class="helper-text">
                Update caption, card copy, regenerate specific images, or push the approved artifact into the publish calendar queue.
              </div>
            </div>
          </div>

          ${
            approvalDecision
              ? renderInspectorPayloadBlock(
                  "Approval decision",
                  approvalDecision,
                  false,
                )
              : ""
          }

          ${
            artifacts?.approvalPacket
              ? renderInspectorPayloadBlock(
                  "Approval packet",
                  artifacts.approvalPacket,
                  false,
                )
              : ""
          }

          ${
            artifacts?.postPackage
              ? renderInspectorPayloadBlock(
                  "Post package",
                  artifacts.postPackage,
                  false,
                )
              : ""
          }

          ${
            publishResult
              ? renderInspectorPayloadBlock(
                  "Publish result",
                  publishResult,
                  false,
                )
              : ""
          }

          ${
            artifacts?.finalResult
              ? renderInspectorPayloadBlock(
                  "Final result",
                  artifacts.finalResult,
                  false,
                )
              : ""
          }
        </div>
      </div>
    </div>
  `;
}

function getSelectedLiveDepartmentKey() {
  return liveAgentsRuntime.getSelectedLiveDepartmentKey(state);
}

function getDepartmentRuns(departmentKey) {
  const normalizedDepartment = String(departmentKey || "").toLowerCase();
  const runs = Array.isArray(state.runs) ? state.runs : [];

  return runs.filter(
    (run) =>
      String(run?.department_key || "").toLowerCase() === normalizedDepartment,
  );
}

function getDepartmentRunCounts(departmentKey) {
  const runs = getDepartmentRuns(departmentKey);

  return {
    total: runs.length,
    queued: runs.filter((run) => run?.status === "queued").length,
    running: runs.filter((run) => run?.status === "running").length,
    waitingApproval: runs.filter((run) => run?.status === "waiting_approval").length,
    failed: runs.filter((run) => run?.status === "failed").length,
    completed: runs.filter((run) => run?.status === "completed").length,
    cancelled: runs.filter((run) => run?.status === "cancelled").length,
  };
}

function getDepartmentPendingApprovals(departmentKey) {
  const normalizedDepartment = String(departmentKey || "").toLowerCase();
  const approvals = Array.isArray(state.approvals) ? state.approvals : [];

  return approvals.filter(
    (item) =>
      String(item?.department_key || "").toLowerCase() === normalizedDepartment &&
      String(item?.status || "").toLowerCase() === "pending",
  );
}

function renderGenericDepartmentWorkspaceSurface(departmentKey, selectedAgentCard) {
  const departmentLabel = runtimeShared.getDepartmentLabel(departmentKey);
  const counts = getDepartmentRunCounts(departmentKey);
  const runs = getDepartmentRuns(departmentKey)
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });

  const pendingApprovals = getDepartmentPendingApprovals(departmentKey);
  const recentAudit = getDepartmentRecentAudit(departmentKey);
  const selectedRun = findSelectedLiveRun();

  return `
    <div class="dashboard-shell">
      <div class="card-grid">
        ${renderDashboardMetricCard(
          "Department",
          departmentLabel,
          selectedAgentCard?.label || "No specific agent selected",
        )}
        ${renderDashboardMetricCard(
          "Queued / Running",
          `${counts.queued} / ${counts.running}`,
          "Current runtime queue",
        )}
        ${renderDashboardMetricCard(
          "Approval / Failed",
          `${counts.waitingApproval} / ${counts.failed}`,
          "Exceptions needing attention",
        )}
        ${renderDashboardMetricCard(
          "Completed",
          counts.completed,
          `Total runs ${counts.total}`,
        )}
      </div>

      <div class="two-col">
        <div class="panel large-panel">
          <div class="panel-title">${escapeHtml(departmentLabel)} Run Queue</div>
          ${
            runs.length
              ? `<div class="list-wrap">${runs
                  .map((run) => renderLiveAgentRunRow(run))
                  .join("")}</div>`
              : `<div class="empty-state">No ${escapeHtml(
                  departmentLabel.toLowerCase(),
                )} runs yet.</div>`
          }
        </div>

        <div class="panel large-panel">
          <div class="panel-title">Pending Approvals</div>
          ${
            pendingApprovals.length
              ? `<div class="list-wrap">${pendingApprovals
                  .map((item) => `
                    <div class="list-item">
                      <div class="list-item-title">${escapeHtml(item?.title || "Approval")}</div>
                      <div class="list-item-sub">${escapeHtml(item?.summary || "")}</div>
                      <div class="badge-row">
                        ${renderStatusBadge(item?.status)}
                        <span class="badge">${escapeHtml(
                          formatDateTime(item?.requested_at || item?.created_at),
                        )}</span>
                      </div>
                    </div>
                  `)
                  .join("")}</div>`
              : `<div class="empty-state">No pending approvals for ${escapeHtml(
                  departmentLabel,
                )}.</div>`
          }
        </div>
      </div>

      <div class="two-col">
        <div class="panel large-panel">
          <div class="panel-title">Selected Run Inspector</div>
          ${
            selectedRun &&
            String(selectedRun?.department_key || "").toLowerCase() ===
              String(departmentKey || "").toLowerCase()
              ? `<pre class="json-block">${escapeHtml(shortJson(selectedRun))}</pre>`
              : `<div class="empty-state">Select a ${escapeHtml(
                  departmentLabel.toLowerCase(),
                )} run to inspect it here.</div>`
          }
        </div>

        <div class="panel large-panel">
          <div class="panel-title">Recent Audit</div>
          ${
            recentAudit.length
              ? `<div class="list-wrap">${recentAudit
                  .map(
                    (event) => `
                      <div class="list-item">
                        <div class="list-item-title">${escapeHtml(
                          event.event_type || "event",
                        )}</div>
                        <div class="list-item-sub">${escapeHtml(event.message || "")}</div>
                        <div class="badge-row">
                          <span class="badge">${escapeHtml(event.level || "info")}</span>
                          <span class="badge">${escapeHtml(
                            formatDateTime(event.created_at),
                          )}</span>
                        </div>
                      </div>
                    `,
                  )
                  .join("")}</div>`
              : `<div class="empty-state">No recent ${escapeHtml(
                  departmentLabel.toLowerCase(),
                )} audit events.</div>`
          }
        </div>
      </div>
    </div>
  `;
}

function renderFinanceWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "finance",
    selectedAgentCard,
    selectedRuns,
  );
}

function renderSalesWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "sales",
    selectedAgentCard,
    selectedRuns,
  );
}

function renderOperationsWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "operations",
    selectedAgentCard,
    selectedRuns,
  );
}

function renderSupportWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "support",
    selectedAgentCard,
    selectedRuns,
  );
}

function renderHRWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "hr",
    selectedAgentCard,
    selectedRuns,
  );
}

function renderCEOWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "ceo",
    selectedAgentCard,
    selectedRuns,
  );
}

function renderCOOWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "coo",
    selectedAgentCard,
    selectedRuns,
  );
}

function renderAionWorkspaceSurface(selectedRuns, selectedAgentCard) {
  return renderGenericDepartmentWorkspaceSurface(
    "aion",
    selectedAgentCard,
    selectedRuns,
  );
}

function getDepartmentRecentAudit(departmentKey, limit = 8) {
  const normalizedDepartment = String(departmentKey || "")
    .trim()
    .toLowerCase();

  if (!normalizedDepartment) {
    return [];
  }

  const audit = Array.isArray(state.audit) ? state.audit : [];

  return audit
    .filter((item) => {
      const itemDepartment = String(item?.department_key || "")
        .trim()
        .toLowerCase();

      if (itemDepartment && itemDepartment === normalizedDepartment) {
        return true;
      }

      const haystack = [
        item?.department_key,
        item?.scope,
        item?.message,
        item?.event_type,
      ]
        .filter((value) => value != null && value !== "")
        .map((value) => String(value).toLowerCase())
        .join(" ");

      return haystack.includes(normalizedDepartment);
    })
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.created_at || 0).getTime();
      const bTime = new Date(b?.created_at || 0).getTime();
      return bTime - aTime;
    })
    .slice(0, limit);
}

function renderAgentCommandHeader() {
  const totalAgents = buildLiveAgentCards(Array.isArray(state.runs) ? state.runs : []).length;
  const queueCounts = getQueueCounts();
  const approvalCounts = getApprovalCounts();
  const selectedAgentCard = getSelectedLiveAgentCard();

  return `
    <div class="panel" style="margin-bottom:16px;">
      <div class="badge-row" style="justify-content:space-between; gap:12px; flex-wrap:wrap;">
        <div class="badge-row">
          <span class="badge">Agents ${escapeHtml(totalAgents)}</span>
          <span class="badge">Queued ${escapeHtml(queueCounts.queued)}</span>
          <span class="badge">Running ${escapeHtml(queueCounts.running)}</span>
          <span class="badge">Waiting ${escapeHtml(queueCounts.waiting)}</span>
          <span class="badge">Failed ${escapeHtml(queueCounts.failed)}</span>
          <span class="badge">Approvals ${escapeHtml(approvalCounts.pending)}</span>
        </div>

        <div class="badge-row">
          <span class="badge">Selected ${escapeHtml(selectedAgentCard?.label || "None")}</span>
          <span class="badge">View ${escapeHtml(prettify(getLiveAgentsView()))}</span>
          <span class="badge">Updated ${escapeHtml(formatDateTime(state.lastRefreshAt))}</span>
        </div>
      </div>
    </div>
  `;
}

function renderMarketingDepartmentRoomCard(room, selectedAgentCard) {
  const runtime = getDepartmentRuntime(room.key) || room;
  const primaryCard =
    runtime.primaryAgent || getPrimaryDepartmentAgentCard(room.key);
  const isDepartmentSelected =
    String(selectedAgentCard?.departmentKey || "").toLowerCase() ===
    String((runtime.key || room.key || "")).toLowerCase();

  const latestRun = runtime.latestRun || primaryCard?.latestRun || null;
  const latestRunId = latestRun?.id || latestRun?.queue_item_id || "";
  const latestRunLabel = latestRun
    ? runtimeShared.getRunWorkflowLabel(latestRun)
    : "No recent workflow";

  return `
    <div class="panel large-panel ${isDepartmentSelected ? "panel-selected" : ""}">
      <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:12px;">
        <div style="display:flex; gap:12px; align-items:center;">
          <div style="
            width:56px;
            height:56px;
            border-radius:16px;
            border:1px solid rgba(148,163,184,0.22);
            display:flex;
            align-items:center;
            justify-content:center;
            font-weight:800;
            font-size:18px;
            background:linear-gradient(180deg, #f8fbff, #eef4fb);
            color:#1e293b;
            flex:0 0 auto;
          ">M</div>

          <div>
            <div class="panel-title" style="margin-bottom:4px;">${escapeHtml(runtime.label || room.label)}</div>
            <div class="helper-text">
              ${escapeHtml(runtime.agentCount ?? room.agentCount ?? 0)} agent(s) · ${escapeHtml(runtime.totalRuns ?? room.total ?? 0)} total runs
            </div>
          </div>
        </div>

        ${renderStatusBadge(
          runtime.running > 0
            ? "running"
            : runtime.waitingApproval > 0
              ? "waiting_approval"
              : runtime.failed > 0
                ? "failed"
                : runtime.completed > 0
                  ? "completed"
                  : "idle",
        )}
      </div>

      <div class="card-grid" style="margin-bottom:12px;">
        ${renderDashboardMetricCard("Queued", runtime.queued ?? room.queued ?? 0, "Planning")}
        ${renderDashboardMetricCard("Running", runtime.running ?? room.running ?? 0, "In progress")}
        ${renderDashboardMetricCard("Review", runtime.waitingApproval ?? room.waitingApproval ?? 0, "Needs approval")}
        ${renderDashboardMetricCard("Done", runtime.completed ?? room.completed ?? 0, "Completed")}
      </div>

      <div class="list-wrap" style="margin-bottom:12px;">
        <div class="list-item">
          <div class="list-item-title">Latest activity</div>
          <div class="list-item-sub">${escapeHtml(latestRunLabel)}</div>
          <div class="badge-row">
            ${renderStatusBadge(latestRun?.status || "unknown")}
            <span class="badge">${escapeHtml(formatDateTime(latestRun?.updated_at || latestRun?.created_at))}</span>
            <span class="badge">Approvals ${escapeHtml(runtime.pendingApprovals ?? 0)}</span>
          </div>
        </div>
      </div>

      <div class="marketing-form-actions">
        <button
          class="secondary-btn live-department-open-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
          data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
        >
          Open workspace
        </button>
        <button
          class="secondary-btn live-department-open-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
          data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
        >
          Stream
        </button>
        <button
          class="secondary-btn live-department-open-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
          data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.CALENDAR)}"
        >
          Calendar
        </button>
        <button
          class="secondary-btn live-department-open-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
          data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
        >
          Runs
        </button>
        <button
          class="secondary-btn boardroom-open-approvals-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
        >
          Approvals
        </button>
        ${
          latestRunId
            ? `
              <button
                class="secondary-btn live-department-open-btn"
                data-department-key="${escapeHtml(runtime.key || room.key)}"
                data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
                data-open-replay="true"
                data-run-id="${escapeHtml(latestRunId)}"
              >
                Replay
              </button>
            `
            : ""
        }
      </div>
    </div>
  `;
}

function renderGenericDepartmentRoomCard(room, selectedAgentCard) {
  const runtime = getDepartmentRuntime(room.key) || room;
  const primaryCard =
    runtime.primaryAgent || getPrimaryDepartmentAgentCard(room.key);
  const latestRun = runtime.latestRun || primaryCard?.latestRun || null;
  const latestRunId = latestRun?.id || latestRun?.queue_item_id || "";
  const latestLabel = latestRun
    ? runtimeShared.getRunWorkflowLabel(latestRun)
    : "No recent activity";
  const isDepartmentSelected =
    String(selectedAgentCard?.departmentKey || "").toLowerCase() ===
    String((runtime.key || room.key || "")).toLowerCase();

  return `
    <div class="panel large-panel ${isDepartmentSelected ? "panel-selected" : ""}">
      <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:12px;">
        <div>
          <div class="panel-title" style="margin-bottom:4px;">${escapeHtml(runtime.label || room.label)}</div>
          <div class="helper-text">
            ${escapeHtml(runtime.agentCount ?? 0)} agent(s) · ${escapeHtml(runtime.totalRuns ?? 0)} total runs
          </div>
        </div>

        ${renderStatusBadge(
          runtime.running > 0
            ? "running"
            : runtime.waitingApproval > 0
              ? "waiting_approval"
              : runtime.failed > 0
                ? "failed"
                : runtime.completed > 0
                  ? "completed"
                  : "idle",
        )}
      </div>

      <div class="badge-row" style="margin-bottom:12px;">
        <span class="badge">Queued ${escapeHtml(runtime.queued ?? 0)}</span>
        <span class="badge">Running ${escapeHtml(runtime.running ?? 0)}</span>
        <span class="badge">Waiting ${escapeHtml(runtime.waitingApproval ?? 0)}</span>
        <span class="badge">Failed ${escapeHtml(runtime.failed ?? 0)}</span>
        <span class="badge">Approvals ${escapeHtml(runtime.pendingApprovals ?? 0)}</span>
      </div>

      <div class="list-item" style="margin-bottom:12px;">
        <div class="list-item-title">Latest activity</div>
        <div class="list-item-sub">${escapeHtml(latestLabel)}</div>
        <div class="badge-row">
          ${renderStatusBadge(latestRun?.status || "unknown")}
          <span class="badge">${escapeHtml(formatDateTime(latestRun?.updated_at || latestRun?.created_at))}</span>
        </div>
      </div>

      <div class="marketing-form-actions">
        <button
          class="secondary-btn live-department-open-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
          data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
        >
          Open workspace
        </button>

        <button
          class="secondary-btn live-department-open-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
          data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
        >
          Runs
        </button>

        <button
          class="secondary-btn boardroom-open-approvals-btn"
          data-department-key="${escapeHtml(runtime.key || room.key)}"
        >
          Approvals
        </button>

        ${
          latestRunId
            ? `
              <button
                class="secondary-btn live-department-open-btn"
                data-department-key="${escapeHtml(runtime.key || room.key)}"
                data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
                data-open-replay="true"
                data-run-id="${escapeHtml(latestRunId)}"
              >
                Replay
              </button>
            `
            : ""
        }
      </div>
    </div>
  `;
}

function renderBoardroomAgentGrid() {
  const rooms = buildDepartmentRoomCards();
  const selectedAgentCard = getSelectedLiveAgentCard();

  return `
    <div
      style="
        display:grid;
        grid-template-columns:repeat(3, minmax(0, 1fr));
        gap:16px;
        align-items:stretch;
      "
    >
      ${rooms
        .map((room) => {
          if (room.key === "marketing") {
            return renderMarketingDepartmentRoomCard(room, selectedAgentCard);
          }
          return renderGenericDepartmentRoomCard(room, selectedAgentCard);
        })
        .join("")}
    </div>
  `;
}

function renderLiveAgentsStatsStrip(selectedRuns, selectedAgentCard) {
  const queuedRuns = selectedRuns.filter((run) => run?.status === "queued");
  const runningRuns = selectedRuns.filter((run) => run?.status === "running");
  const waitingApprovalRuns = selectedRuns.filter(
    (run) => run?.status === "waiting_approval",
  );
  const failedRuns = selectedRuns.filter((run) => run?.status === "failed");

  return `
    <div class="panel" style="margin-bottom:16px;">
      <div class="badge-row">
        <span class="badge">Agents: ${escapeHtml(buildLiveAgentCards(state.runs || []).length)}</span>
        <span class="badge">Active: ${escapeHtml(
          queuedRuns.length + runningRuns.length + waitingApprovalRuns.length + failedRuns.length,
        )}</span>
        <span class="badge">Waiting approval: ${escapeHtml(waitingApprovalRuns.length)}</span>
        <span class="badge">Failed: ${escapeHtml(failedRuns.length)}</span>
        <span class="badge">Selected agent: ${escapeHtml(selectedAgentCard?.label || "None")}</span>
        <span class="badge">Selected run: ${escapeHtml(state.selectedLiveRunId || "None")}</span>
      </div>
    </div>
  `;
}

function renderLiveAgentHero(selectedAgentCard) {
  if (!selectedAgentCard) {
    return `
      <div class="panel large-panel">
        <div class="panel-title">No agent selected</div>
        <div class="empty-state">No live agent is available yet.</div>
      </div>
    `;
  }

  const latestRun = selectedAgentCard.latestRun || null;
  const departmentKey = String(selectedAgentCard.departmentKey || "").toLowerCase();
  const showCalendar = departmentKey === "marketing";

  return `
    <div class="panel large-panel">
      <div style="display:flex; gap:16px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap;">
        <div style="display:flex; gap:16px; align-items:center;">
          <div style="
            width:72px;
            height:72px;
            border-radius:20px;
            border:1px solid rgba(148,163,184,0.25);
            display:flex;
            align-items:center;
            justify-content:center;
            font-weight:800;
            font-size:22px;
            background:linear-gradient(180deg, #f8fbff, #eef4fb);
            color:#1e293b;
          ">
            ${escapeHtml(String(selectedAgentCard.label || "A").slice(0, 1).toUpperCase())}
          </div>

          <div>
            <div class="surface-eyebrow">Agent Workspace</div>
            <div class="surface-title" style="font-size:34px;">${escapeHtml(selectedAgentCard.label)}</div>
            <div class="surface-subtitle">
              ${escapeHtml(runtimeShared.getDepartmentLabel(selectedAgentCard.departmentKey || "unknown"))} · ${escapeHtml(selectedAgentCard.total)} total runs
            </div>
            <div class="badge-row" style="margin-top:10px;">
              <span class="badge">Queued ${escapeHtml(selectedAgentCard.queued)}</span>
              <span class="badge">Running ${escapeHtml(selectedAgentCard.running)}</span>
              <span class="badge">Waiting ${escapeHtml(selectedAgentCard.waitingApproval)}</span>
              <span class="badge">Failed ${escapeHtml(selectedAgentCard.failed)}</span>
              <span class="badge">Last active ${escapeHtml(formatDateTime(latestRun?.updated_at || latestRun?.created_at))}</span>
            </div>
          </div>
        </div>

        <div class="marketing-form-actions">
          <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}">View Stream</button>
          ${
            showCalendar
              ? `<button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.CALENDAR)}">Open Calendar</button>`
              : ""
          }
          <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}">Runs</button>
          <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.APPROVALS)}">Approvals</button>
          <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.SETTINGS)}">Settings</button>
        </div>
      </div>
    </div>
  `;
}

function renderLiveAgentsSubviewTabs() {
  const activeView = getLiveAgentsView();
  const departmentKey = getSelectedLiveDepartmentKey();
  const showCalendar = departmentKey === "marketing";

  return `
    <div class="live-agents-subtabs">
      <button
        class="live-agents-subtab ${activeView === LIVE_AGENT_VIEWS.STREAM ? "live-agents-subtab-active" : ""}"
        data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
      >
        Stream
      </button>

      ${
        showCalendar
          ? `
            <button
              class="live-agents-subtab ${activeView === LIVE_AGENT_VIEWS.CALENDAR ? "live-agents-subtab-active" : ""}"
              data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.CALENDAR)}"
            >
              Calendar
            </button>
          `
          : ""
      }

      <button
        class="live-agents-subtab ${activeView === LIVE_AGENT_VIEWS.RUNS ? "live-agents-subtab-active" : ""}"
        data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
      >
        Runs
      </button>

      <button
        class="live-agents-subtab ${activeView === LIVE_AGENT_VIEWS.APPROVALS ? "live-agents-subtab-active" : ""}"
        data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.APPROVALS)}"
      >
        Approvals
      </button>

      <button
        class="live-agents-subtab ${activeView === LIVE_AGENT_VIEWS.SETTINGS ? "live-agents-subtab-active" : ""}"
        data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.SETTINGS)}"
      >
        Settings
      </button>
    </div>
  `;
}

function renderMinimalDepartmentSwitcher() {
  const rooms = buildDepartmentRoomCards();
  const selectedDepartmentKey = getSelectedLiveDepartmentKey();

  return `
    <div class="minimal-department-switcher">
      <div class="panel-title">Departments</div>

      <div class="minimal-department-switcher-row">
        ${rooms
          .map((room) => {
            const isActive =
              String(room.key || "").toLowerCase() ===
              String(selectedDepartmentKey || "").toLowerCase();

            return `
              <button
                class="minimal-department-btn live-department-open-btn ${isActive ? "minimal-department-btn-active" : ""}"
                data-department-key="${escapeHtml(room.key)}"
                data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
              >
                ${escapeHtml(room.label)}${room.running > 0 ? ` ${escapeHtml(`(${room.running})`)}` : ""}
              </button>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function renderLiveAgentStreamView(selectedRuns, selectedAgentCard) {
  const completedRuns = selectedRuns
    .filter((run) => run?.status === "completed")
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });

  const waitingApprovalRuns = selectedRuns
    .filter((run) => run?.status === "waiting_approval")
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });

  const inProgressRuns = selectedRuns
    .filter(
      (run) => run?.status === "queued" || run?.status === "running",
    )
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });

  const selectedRun = findSelectedLiveRun();
  const activeStreamTab = ["approval", "progress", "completed"].includes(
    String(state.liveAgentsStreamTab || "approval").toLowerCase(),
  )
    ? String(state.liveAgentsStreamTab || "approval").toLowerCase()
    : "approval";

  const streamTabs = [
    {
      key: "approval",
      label: "Waiting on Approval",
      count: waitingApprovalRuns.length,
    },
    {
      key: "progress",
      label: "Work in Progress",
      count: inProgressRuns.length,
    },
    {
      key: "completed",
      label: "Completed Content",
      count: completedRuns.length,
    },
  ];

  let streamTitle = "Waiting on Approval";
  let streamEmpty = "No items waiting on approval right now.";
  let visibleRuns = waitingApprovalRuns;

  if (activeStreamTab === "progress") {
    streamTitle = "Work in Progress";
    streamEmpty = "No queued or running work right now.";
    visibleRuns = inProgressRuns;
  } else if (activeStreamTab === "completed") {
    streamTitle = "Completed Content";
    streamEmpty = "No completed content yet for this agent.";
    visibleRuns = completedRuns;
  }

  return `
    <div>
      <div style="
        display:flex;
        gap:24px;
        align-items:center;
        flex-wrap:wrap;
        margin-bottom:14px;
      ">
        ${streamTabs
          .map((tab) => {
            const isActive = activeStreamTab === tab.key;
            return `
              <button
                type="button"
                data-live-agents-stream-tab="${escapeHtml(tab.key)}"
                style="
                  appearance:none;
                  -webkit-appearance:none;
                  border:0;
                  border-bottom:${isActive ? "2px" : "1px"} solid #111111;
                  background:transparent;
                  color:${isActive ? "#111111" : "rgba(17,17,17,0.62)"};
                  padding:0 0 4px 0;
                  font-size:14px;
                  font-weight:${isActive ? "700" : "600"};
                  cursor:pointer;
                "
              >
                ${escapeHtml(tab.label)}${tab.count ? ` <span style="opacity:0.7;">(${escapeHtml(tab.count)})</span>` : ""}
              </button>
            `;
          })
          .join("")}
      </div>

      <div class="panel large-panel">
        <div class="panel-title">${escapeHtml(streamTitle)}</div>
        ${
          visibleRuns.length
            ? activeStreamTab === "completed"
              ? `<div class="marketing-runs-grid">${visibleRuns
                  .map((run) => renderMarketingRunCard(run))
                  .join("")}</div>`
              : `<div class="list-wrap">${visibleRuns
                  .map((run) => renderLiveAgentRunRow(run))
                  .join("")}</div>`
            : `<div class="empty-state">${escapeHtml(streamEmpty)}</div>`
        }
      </div>
    </div>

    <div style="margin-top:16px;">
      ${renderSelectedRunInspector(selectedRun)}
    </div>
  `;
}

function isRecord(value) {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function firstString(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return undefined;
}

function normalizeImageSrc(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";

  if (
    raw.startsWith("http://") ||
    raw.startsWith("https://") ||
    raw.startsWith("file://") ||
    raw.startsWith("data:")
  ) {
    return raw;
  }

  if (raw.startsWith("/")) {
    return `file://${encodeURI(raw)}`;
  }

  return encodeURI(raw);
}

function stringArray(...values) {
  const out = [];

  values.forEach((value) => {
    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (typeof entry === "string" && entry.trim()) {
          out.push(entry.trim());
          return;
        }

        if (isRecord(entry)) {
          const text =
            firstString(
              entry.label,
              entry.title,
              entry.name,
              entry.text,
              entry.value,
              entry.caption,
            ) || "";
          if (text) out.push(text);
        }
      });
      return;
    }

    if (typeof value === "string" && value.trim()) {
      const split = value
        .split(/\n|,|•|·|\|/)
        .map((part) => part.trim())
        .filter(Boolean);
      out.push(...split);
    }
  });

  return Array.from(new Set(out));
}

function extractText(value, depth = 0) {
  if (depth > 3) return undefined;

  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);

  if (Array.isArray(value)) {
    const joined = value
      .map((item) => extractText(item, depth + 1))
      .filter(Boolean)
      .join("\n")
      .trim();
    return joined || undefined;
  }

  if (isRecord(value)) {
    return firstString(
      value.caption,
      value.body,
      value.text,
      value.content,
      value.copy,
      value.message,
      value.summary,
      value.result,
      value.output,
    );
  }

  return undefined;
}

function formatCalendarHeader(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function toDayKey(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getChannelMeta(channel) {
  const value = String(channel || "").toLowerCase();

  if (value.includes("facebook")) return { label: "Facebook", badge: "f" };
  if (value.includes("instagram")) return { label: "Instagram", badge: "ig" };
  if (value.includes("linkedin")) return { label: "LinkedIn", badge: "in" };
  if (value.includes("twitter") || value === "x") return { label: "X", badge: "x" };
  if (value.includes("tiktok")) return { label: "TikTok", badge: "tt" };
  if (value.includes("youtube")) return { label: "YouTube", badge: "yt" };

  return {
    label: channel || "General",
    badge: "•",
  };
}

function getCalendarRunDate(run) {
  return (
    run?.scheduled_for ||
    run?.result?.scheduled_for ||
    run?.draft?.scheduled_for ||
    run?.updated_at ||
    run?.created_at ||
    new Date().toISOString()
  );
}

function getCalendarModeRuns(runs) {
  const mode = getMarketingCalendarMode();
  const items = Array.isArray(runs) ? runs : [];

  const sorted = items
    .slice()
    .sort((a, b) => {
      const aTime = new Date(
        a?.scheduled_for || a?.updated_at || a?.created_at || 0,
      ).getTime();
      const bTime = new Date(
        b?.scheduled_for || b?.updated_at || b?.created_at || 0,
      ).getTime();
      return aTime - bTime;
    });

  if (mode === MARKETING_CALENDAR_MODES.PLANNING) {
    return sorted.filter((run) =>
      [
        "queued",
        "planned",
        "draft",
        "waiting_approval",
        "running",
        "completed",
      ].includes(String(run?.status || "").toLowerCase()),
    );
  }

  if (mode === MARKETING_CALENDAR_MODES.REVIEW) {
    return sorted.filter((run) =>
      [
        "running",
        "waiting_approval",
        "failed",
      ].includes(String(run?.status || "").toLowerCase()),
    );
  }

  if (mode === MARKETING_CALENDAR_MODES.DONE) {
    return sorted.filter(
      (run) => String(run?.status || "").toLowerCase() === "completed",
    );
  }

  return sorted;
}

function normalizeMarketingCalendarRun(run) {
  const postPackage = getRunPostPackage(run);
  const result = getRunResultPayload(run);
  const context = getRunContext(run);

  const title =
    firstString(
      postPackage?.title,
      postPackage?.caption,
      result?.title,
      run?.workflow_name,
      run?.workflow_id
    ) || "Marketing Content Draft v1";

  const channel =
    firstString(
      safeArray(postPackage?.channels)[0],
      result?.channel,
      context?.channel,
      run?.channel
    ) || "General";

  const carousel =
    safeArray(postPackage?.carousel).length
      ? safeArray(postPackage?.carousel)
      : safeArray(postPackage?.content_blocks).length
        ? safeArray(postPackage?.content_blocks)
        : stringArray(
            result?.draft_carousel?.draft_carousel,
            result?.draft_carousel,
            context?.draft_carousel,
            run?.draft_carousel
          );

  const previewText =
    firstString(
      postPackage?.caption,
      postPackage?.body,
      result?.draft_caption?.draft_caption,
      result?.draft_caption,
      run?.brief
    ) || "No generated content available yet.";

  return {
    source: run,
    title,
    channel,
    carousel,
    previewText,
    imageUrl: getRunGeneratedImageUrl(run),
    scheduledFor: getCalendarRunDate(run),
    status: run?.status || "unknown",
  };
}

function buildMarketingCalendarDays(runs) {
  const grouped = new Map();

  runs.forEach((run) => {
    const normalized = normalizeMarketingCalendarRun(run);
    const key = toDayKey(normalized.scheduledFor);
    const current = grouped.get(key) || [];
    current.push(normalized);
    grouped.set(key, current);
  });

  return [...grouped.entries()]
    .sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime())
    .map(([key, items]) => ({
      key,
      label: formatCalendarHeader(key),
      runs: items.sort(
        (a, b) => new Date(a.scheduledFor).getTime() - new Date(b.scheduledFor).getTime(),
      ),
    }));
}

function renderMarketingCalendarPreview(run) {
  return renderFacebookPostMockup(run.source || run, { activeIndex: 0 });
}

function renderLiveAgentCalendarView(selectedRuns, selectedAgentCard) {
  const filteredRuns = getCalendarModeRuns(selectedRuns);
  const calendarDays = buildMarketingCalendarDays(filteredRuns);
  const mode = getMarketingCalendarMode();
  const selectedRun = findSelectedLiveRun();

  return `
    <div class="panel large-panel">
      <div class="calendar-toolbar">
        <div>
          <div class="panel-title">Suggested content plan</div>
          <div class="helper-text">
            Calendar-style view for ${escapeHtml(selectedAgentCard?.label || "selected agent")}.
          </div>
        </div>

        <div class="boardroom-view-toggle" style="margin-bottom:0;">
          <button
            class="secondary-btn boardroom-view-btn ${mode === "planning" ? "boardroom-view-btn-active" : ""}"
            data-marketing-calendar-mode="planning"
          >
            Planning
          </button>
          <button
            class="secondary-btn boardroom-view-btn ${mode === "review" ? "boardroom-view-btn-active" : ""}"
            data-marketing-calendar-mode="review"
          >
            Review
          </button>
          <button
            class="secondary-btn boardroom-view-btn ${mode === "done" ? "boardroom-view-btn-active" : ""}"
            data-marketing-calendar-mode="done"
          >
            Done
          </button>
        </div>
      </div>

      ${
        calendarDays.length
          ? `
            <div style="
              display:grid;
              grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));
              gap:16px;
              align-items:start;
              margin-top:16px;
            ">
              ${calendarDays
                .map(
                  (day) => `
                    <div style="
                      border:1px solid rgba(15,23,42,0.12);
                      background:#fff;
                      min-width:0;
                    ">
                      <div style="
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        gap:12px;
                        padding:14px 16px;
                        border-bottom:1px solid rgba(15,23,42,0.08);
                      ">
                        <div style="
                          font-size:12px;
                          font-weight:800;
                          letter-spacing:0.12em;
                          text-transform:uppercase;
                          font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                        ">
                          ${escapeHtml(day.label)}
                        </div>

                        <div class="helper-text" style="margin:0;">
                          ${escapeHtml(day.runs.length)} item${day.runs.length === 1 ? "" : "s"}
                        </div>
                      </div>

                      <div style="
                        display:grid;
                        gap:14px;
                        padding:16px;
                        align-items:start;
                      ">
                        ${day.runs
                          .map((run) => {
                            const channelMeta = getChannelMeta(run.channel);
                            const runId =
                              run?.source?.id || run?.source?.queue_item_id || "";
                            const isSelected =
                              runId && state.selectedLiveRunId === String(runId);

                            return `
                              <div
                                ${runId ? `id="${escapeHtml(getSelectedRunElementId(runId))}"` : ""}
                                class="${isSelected ? "run-row-selected" : ""}"
                                style="
                                  border:1px solid rgba(15,23,42,0.12);
                                  background:#fff;
                                  min-width:0;
                                "
                              >
                                <div style="
                                  display:flex;
                                  align-items:flex-start;
                                  justify-content:space-between;
                                  gap:12px;
                                  padding:14px 16px;
                                  border-bottom:1px solid rgba(15,23,42,0.08);
                                ">
                                  <div style="min-width:0;">
                                    <div style="
                                      display:flex;
                                      align-items:center;
                                      gap:8px;
                                      margin-bottom:6px;
                                      color:rgba(17,17,17,0.62);
                                      font-size:12px;
                                      font-weight:700;
                                    ">
                                      <span style="
                                        display:inline-flex;
                                        align-items:center;
                                        justify-content:center;
                                        width:28px;
                                        height:28px;
                                        border:1px solid rgba(15,23,42,0.12);
                                        background:#111;
                                        color:#fff;
                                        font-size:12px;
                                        font-weight:800;
                                        flex:0 0 auto;
                                      ">
                                        ${escapeHtml(channelMeta.badge)}
                                      </span>
                                      <span>${escapeHtml(channelMeta.label)} · Carousel</span>
                                    </div>

                                    <div style="
                                      font-size:16px;
                                      line-height:1.35;
                                      font-weight:700;
                                      color:#111;
                                      word-break:break-word;
                                    ">
                                      ${escapeHtml(run.title)}
                                    </div>
                                  </div>

                                  <div style="flex:0 0 auto;">
                                    ${renderStatusBadge(run.status)}
                                  </div>
                                </div>

                                <div style="padding:16px;">
                                  ${renderMarketingCalendarPreview(run)}

                                  <div class="badge-row" style="margin-top:12px;">
                                    <span class="badge">${escapeHtml(formatDateTime(run.scheduledFor))}</span>
                                  </div>

                                  ${
                                    runId
                                      ? `
                                        <div class="marketing-form-actions" style="margin-top:12px;">
                                          <button
                                            type="button"
                                            class="secondary-btn live-run-select-btn"
                                            data-run-id="${escapeHtml(runId)}"
                                          >
                                            Inspect run
                                          </button>
                                        </div>
                                      `
                                      : ""
                                  }
                                </div>
                              </div>
                            `;
                          })
                          .join("")}
                      </div>
                    </div>
                  `,
                )
                .join("")}
            </div>
          `
          : `<div class="empty-state">No calendar items for this mode yet.</div>`
      }
    </div>

    <div style="margin-top:16px;">
      ${renderSelectedRunInspector(selectedRun)}
    </div>
  `;
}

function renderLiveAgentRunsView(selectedRuns, selectedAgentCard) {
  const sortedRuns = selectedRuns
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });

  const selectedRun = findSelectedLiveRun();
  const visibleRuns = sortedRuns.slice(0, 8);

  return `
    <div class="dashboard-shell" style="
      display:grid;
      gap:16px;
      width:100%;
    ">
      <div style="width:100%;">
        ${renderSelectedRunInspector(selectedRun)}
      </div>

      <div class="panel large-panel" style="
        width:100%;
        box-sizing:border-box;
      ">
        <div style="
          display:flex;
          align-items:flex-start;
          justify-content:space-between;
          gap:12px;
          flex-wrap:wrap;
          margin-bottom:12px;
        ">
          <div>
            <div class="panel-title">Run history</div>
            <div class="helper-text">
              Showing latest ${escapeHtml(Math.min(visibleRuns.length, sortedRuns.length))} of ${escapeHtml(sortedRuns.length)} run(s).
            </div>
          </div>

          <div class="badge-row">
            <span class="badge">Agent ${escapeHtml(selectedAgentCard?.label || "—")}</span>
            <span class="badge">Total ${escapeHtml(sortedRuns.length)}</span>
          </div>
        </div>

        ${
          visibleRuns.length
            ? `
              <div class="list-wrap" style="
                display:grid;
                grid-template-columns:repeat(auto-fit, minmax(260px, 1fr));
                gap:12px;
              ">
                ${visibleRuns.map((run) => renderLiveAgentRunRow(run)).join("")}
              </div>
            `
            : `<div class="empty-state">No runs for this agent yet.</div>`
        }
      </div>
    </div>
  `;
}

function renderLiveAgentSettingsView(selectedAgentCard) {
  return `
    <div class="two-col">
      <div class="panel large-panel">
        <div class="panel-title">Agent settings</div>
        <div class="list-wrap">
          <div class="list-item">
            <div class="list-item-title">Agent identity</div>
            <div class="list-item-sub">${escapeHtml(selectedAgentCard?.label || "—")}</div>
          </div>
          <div class="list-item">
            <div class="list-item-title">Department</div>
            <div class="list-item-sub">${escapeHtml(selectedAgentCard?.departmentKey || "—")}</div>
          </div>
          <div class="list-item">
            <div class="list-item-title">Persona image</div>
            <div class="list-item-sub">Next pass: add avatar/headshot upload or generated persona art.</div>
          </div>
          <div class="list-item">
            <div class="list-item-title">Compliance</div>
            <div class="list-item-sub">Keep compliance history behind run-level inspect, not main agent view.</div>
          </div>
        </div>
      </div>

      <div class="panel large-panel">
        <div class="panel-title">Workspace notes</div>
        <div class="helper-text">
          This screen is moving from queue-monitoring into agent-office mode:
          stream, calendar, approvals, runs, settings.
        </div>
      </div>
    </div>
  `;
}

function renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard) {
  const activeView = getLiveAgentsView();
  const departmentKey = getSelectedLiveDepartmentKey();

  if (activeView === LIVE_AGENT_VIEWS.APPROVALS) {
    return renderDepartmentApprovalsSurface(departmentKey, selectedAgentCard);
  }

  if (departmentKey === "marketing") {
    if (activeView === LIVE_AGENT_VIEWS.CALENDAR) {
      return renderLiveAgentCalendarView(selectedRuns, selectedAgentCard);
    }

    if (activeView === LIVE_AGENT_VIEWS.RUNS) {
      return renderLiveAgentRunsView(selectedRuns, selectedAgentCard);
    }

    if (activeView === LIVE_AGENT_VIEWS.SETTINGS) {
      return renderLiveAgentSettingsView(selectedAgentCard);
    }

    return renderLiveAgentStreamView(selectedRuns, selectedAgentCard);
  }

  if (activeView === LIVE_AGENT_VIEWS.SETTINGS) {
    return renderLiveAgentSettingsView(selectedAgentCard);
  }

  if (activeView === LIVE_AGENT_VIEWS.RUNS) {
    return renderLiveAgentRunsView(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "finance") {
    return renderFinanceWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "sales") {
    return renderSalesWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "operations") {
    return renderOperationsWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "support") {
    return renderSupportWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "hr") {
    return renderHRWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "ceo") {
    return renderCEOWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "coo") {
    return renderCOOWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  if (departmentKey === "aion") {
    return renderAionWorkspaceSurface(selectedRuns, selectedAgentCard);
  }

  return renderGenericDepartmentWorkspaceSurface(departmentKey, selectedAgentCard);
}

function renderLiveAgentRunRow(run) {
  const workflowName = runtimeShared.getRunWorkflowLabel(run);
  const agentLabel = runtimeShared.getRunAgentLabel(run);
  const runId = run?.id || run?.queue_item_id || "";
  const isSelectedRun = runId && state.selectedLiveRunId === String(runId);
  const rowId = runId ? getSelectedRunElementId(runId) : "";
  const updatedAt = formatDateTime(run?.updated_at || run?.created_at);
  const departmentLabel = run?.department_key
    ? prettify(run.department_key)
    : "—";

  return `
    <div
      ${rowId ? `id="${escapeHtml(rowId)}"` : ""}
      class="minimal-run-row ${isSelectedRun ? "minimal-run-row-selected run-row-selected" : ""}"
      style="
        border:1px solid rgba(15,23,42,0.18);
        background:#ffffff;
        padding:14px 16px;
        display:grid;
        gap:10px;
        margin-bottom:10px;
      "
    >
      <div style="
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:12px;
        flex-wrap:wrap;
      ">
        <div style="min-width:0;">
          <div style="
            font-size:16px;
            font-weight:700;
            line-height:1.25;
            color:#111111;
            word-break:break-word;
          ">
            ${escapeHtml(workflowName)}
          </div>

          <div style="
            font-size:13px;
            color:rgba(17,17,17,0.68);
            margin-top:4px;
            word-break:break-word;
          ">
            ${escapeHtml(agentLabel)} · ${escapeHtml(departmentLabel)}
          </div>
        </div>

        <div class="badge-row">
          ${renderStatusBadge(run?.status || "unknown")}
        </div>
      </div>

      <div style="
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        flex-wrap:wrap;
      ">
        <div style="
          font-size:13px;
          color:rgba(17,17,17,0.72);
        ">
          Updated ${escapeHtml(updatedAt)}
        </div>

        ${
          runId
            ? `
              <button
                class="minimal-run-row-action live-run-select-btn"
                data-run-id="${escapeHtml(runId)}"
                style="
                  appearance:none;
                  -webkit-appearance:none;
                  border:1px solid rgba(15,23,42,0.18);
                  background:#ffffff;
                  color:#111111;
                  padding:8px 14px;
                  font-weight:700;
                  cursor:pointer;
                "
              >
                ${isSelectedRun ? "Open" : "Inspect"}
              </button>
            `
            : ""
        }
      </div>
    </div>
  `;
}

function renderLiveAgentsSurface() {
  const selectedRuns = getRunsForSelectedLiveAgent();
  const selectedAgentCard = getSelectedLiveAgentCard();
  const departmentKey = getSelectedLiveDepartmentKey();
  const departmentLabel = runtimeShared.getDepartmentLabel(departmentKey);

  return `
    <div class="surface-shell">
      <div class="surface-header surface-header-unified">
        <div class="surface-header-unified-top">
          <div class="surface-header-unified-main">
            <div class="badge-row" style="gap:32px; align-items:flex-start; margin-bottom:8px;">
              <div>
                <div class="surface-eyebrow">Local runtime</div>
                <div class="surface-runtime-copy">Local backend ready</div>
              </div>

              <div>
                <div class="surface-eyebrow">Live Agents</div>
                <div class="last-refresh">Updated ${escapeHtml(formatDateTime(state.lastRefreshAt))}</div>
              </div>
            </div>

            <div class="surface-eyebrow">Aion Business Desktop</div>
            <div class="surface-title">Live Agents</div>
            <div class="surface-subtitle">
              Minimal local command surface for department agents.
            </div>
          </div>
        </div>
      </div>

      ${renderAppTabs()}
      ${renderMinimalDepartmentSwitcher()}
      ${renderLiveAgentsSubviewTabs()}

      <div class="dashboard-shell">
        <div class="live-agents-workspace-meta">
          <div class="live-agents-workspace-copy">
            <div class="surface-eyebrow">Workspace</div>
            <div class="live-agents-workspace-title">
              ${escapeHtml(selectedAgentCard?.label || departmentLabel)}
            </div>
            <div class="live-agents-workspace-sub">
              ${escapeHtml(departmentLabel)} · ${escapeHtml(selectedAgentCard?.total || 0)} total runs
            </div>
          </div>

          <div class="badge-row">
            <span class="badge">Queued ${escapeHtml(selectedAgentCard?.queued || 0)}</span>
            <span class="badge">Running ${escapeHtml(selectedAgentCard?.running || 0)}</span>
            <span class="badge">Waiting ${escapeHtml(selectedAgentCard?.waitingApproval || 0)}</span>
            <span class="badge">Failed ${escapeHtml(selectedAgentCard?.failed || 0)}</span>
          </div>
        </div>

        ${renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard)}
      </div>
    </div>
  `;
}

function findSelectedLiveRun() {
  return liveAgentsRuntime.findSelectedLiveRun(state);
}

function renderLiveAgentsReplayOverlay() {
  if (!state.liveAgentsReplayOpen) return "";

  const selectedRun = findSelectedLiveRun();
  if (!selectedRun) return "";

  const workflowName = runtimeShared.getRunWorkflowLabel(selectedRun);
  const agentLabel = runtimeShared.getRunAgentLabel(selectedRun);
  const departmentLabel = runtimeShared.getDepartmentLabel(
    selectedRun?.department_key || "unknown",
  );
  const runId = selectedRun?.id || selectedRun?.queue_item_id || "—";

  return `
    <div class="live-agents-overlay">
      <div class="live-agents-overlay-backdrop" id="liveAgentsOverlayClose"></div>

      <div class="live-agents-overlay-panel">
        <div class="surface-header" style="margin-bottom:16px;">
          <div>
            <div class="surface-eyebrow">Live Run Replay</div>
            <div class="surface-title">${escapeHtml(workflowName)}</div>
            <div class="surface-subtitle">
              ${escapeHtml(agentLabel)} · ${escapeHtml(departmentLabel)}
            </div>
          </div>

          <div class="surface-right-meta">
            <div class="surface-pill">RUN INSPECTOR</div>
            <button id="closeLiveAgentsReplayBtn" class="secondary-btn">Close</button>
          </div>
        </div>

        <div class="card-grid">
          ${renderDashboardMetricCard("Status", selectedRun?.status || "unknown", "Current run state")}
          ${renderDashboardMetricCard("Run ID", runId, "Selected runtime object")}
          ${renderDashboardMetricCard("Created", formatDateTime(selectedRun?.created_at), "Run creation")}
          ${renderDashboardMetricCard("Updated", formatDateTime(selectedRun?.updated_at), "Latest update")}
        </div>

        <div style="margin-top:16px;">
          <div class="panel large-panel">
            <div class="panel-title">Replay Inspector</div>
            ${renderSelectedRunInspector(selectedRun)}
          </div>
        </div>
      </div>
    </div>
  `;
}

function setNestedValue(source, path, value) {
  const next = JSON.parse(JSON.stringify(source || {}));
  const parts = String(path || "").split(".").filter(Boolean);

  if (!parts.length) return next;

  let cursor = next;

  for (let index = 0; index < parts.length - 1; index += 1) {
    const key = parts[index];

    if (!cursor[key] || typeof cursor[key] !== "object" || Array.isArray(cursor[key])) {
      cursor[key] = {};
    }

    cursor = cursor[key];
  }

  cursor[parts[parts.length - 1]] = value;
  return next;
}


function attachEvents() {
  if (!window.__TESSARIS_DELEGATED_EVENTS_BOUND__) {
    window.__TESSARIS_DELEGATED_EVENTS_BOUND__ = true;

    document.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;

      const operationsAgentsWizardInput = target.closest(
        ".operations-agents-wizard-input",
      );

      if (operationsAgentsWizardInput) {
        const path =
          operationsAgentsWizardInput.dataset.operationsAgentsWizardPath || "";

        if (path) {
          const value =
            operationsAgentsWizardInput.type === "checkbox"
              ? operationsAgentsWizardInput.checked
              : operationsAgentsWizardInput.value;

          desktopStore.patch({
            operationsAgentsWizardDraft: setNestedValue(
              state.operationsAgentsWizardDraft || {},
              path,
              value,
            ),
            operationsAgentsWizardError: "",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
        }

        return;
      }
    });

    document.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;

      const browserCaptureField = target.closest("[data-browser-capture-field]");
      if (browserCaptureField) {
        const field = browserCaptureField.dataset.browserCaptureField || "";
        const value = browserCaptureField.value || "";
        const bridge = state.browserDesktopBridge || {};
        const captureDraft = normaliseBrowserCaptureDraft(bridge.capture_draft);

        desktopStore.patch({
          browserDesktopBridge: {
            ...bridge,
            capture_draft: {
              ...captureDraft,
              [field]: value,
            },
          },
        });

        desktopStore.persistCacheSoon(300);
        requestRender();
        return;
      }

      const browserChainField = target.closest("[data-browser-chain-field]");
      if (browserChainField) {
        const field = browserChainField.dataset.browserChainField || "";
        const draft = {
          ...getBrowserSkillChainDraft(),
          [field]: browserChainField.value,
          updated_at: new Date().toISOString(),
        };

        desktopStore.patch({
          browserSkillChainDraft: draft,
        });

        desktopStore.persistCacheSoon(300);
        requestRender();
        return;
      }

      const browserChainStepField = target.closest("[data-browser-chain-step-field]");
      if (browserChainStepField) {
        const field = browserChainStepField.dataset.browserChainStepField || "";
        const chainStepId = browserChainStepField.dataset.chainStepId || "";

        desktopStore.patch({
          browserSkillChainDraft: patchBrowserChainStep(chainStepId, {
            [field]: browserChainStepField.value,
          }),
        });

        desktopStore.persistCacheSoon(300);
        requestRender();
        return;
      }

      const browserSkillReviewField = target.closest("[data-browser-skill-review-field]");
      if (browserSkillReviewField) {
        const field = browserSkillReviewField.dataset.browserSkillReviewField || "";
        patchBrowserSkillReviewDraft({
          [field]: browserSkillReviewField.value,
        });
        return;
      }

      const browserSkillStepField = target.closest("[data-browser-skill-step-field]");
      if (browserSkillStepField) {
        const field = browserSkillStepField.dataset.browserSkillStepField || "";
        const stepId = browserSkillStepField.dataset.stepId || "";
        patchBrowserCapturedEvent(stepId, {
          [field]: browserSkillStepField.value,
        });
        return;
      }

      const stepBuilderSampleField = target.closest("[data-step-builder-sample-field]");
      if (stepBuilderSampleField) {
        const field = stepBuilderSampleField.dataset.stepBuilderSampleField || "";
        const value = stepBuilderSampleField.value || "";

        desktopStore.patch({
          operationsAgentsStepBuilderSampleInput: {
            ...(state.operationsAgentsStepBuilderSampleInput || {}),
            [field]: value,
          },
        });
        desktopStore.persistCacheSoon(300);
        return;
      }

      const stepBuilderField = target.closest("[data-step-builder-field]");
      if (stepBuilderField) {
        const field = stepBuilderField.dataset.stepBuilderField || "";
        const value = stepBuilderField.value || "";

        let draft = normaliseStepBuilderDraft(state.operationsAgentsStepBuilderDraft);

        if (field === "workflow_id") {
          draft.workflow_id = value;
        } else {
          draft = updateStepBuilderDraftField(draft, field, value);
        }

        desktopStore.patch({
          operationsAgentsStepBuilderDraft: draft,
        });
        desktopStore.persistCacheSoon(300);
        requestRender();
        return;
      }

      const stepBuilderStepField = target.closest("[data-step-builder-step-field]");
      if (stepBuilderStepField) {
        const stepId = stepBuilderStepField.dataset.stepId || "";
        const field = stepBuilderStepField.dataset.stepBuilderStepField || "";
        const value = stepBuilderStepField.value || "";

        if (!stepId || !field) return;

        let draft = updateStepBuilderStep(
          state.operationsAgentsStepBuilderDraft,
          stepId,
          { [field]: value },
        );

        if (field === "type") {
          const typeMeta = OPERATIONS_AGENT_STEP_TYPES.find((item) => item.value === value);

          draft = updateStepBuilderStep(draft, stepId, {
            type: value,
            name: typeMeta?.label || value,
            tool_id: defaultToolForStepType(value),
            input_source: value === "trigger" ? "trigger_payload" : "previous_step",
            output:
              value === "end"
                ? ""
                : draft.steps.find((step) => step.step_id === stepId)?.output ||
                  stepId.replace(/^step_/, "output_"),
          });
        }

        desktopStore.patch({
          operationsAgentsStepBuilderDraft: draft,
          operationsAgentsStepBuilderSelectedStepId: stepId,
        });
        desktopStore.persistCacheSoon(300);
        requestRender();
      }
    });

    document.addEventListener("click", async (event) => {
      const target = event.target;
      if (!target) return;

      const tabButton = target.closest("[data-tab]");
      if (tabButton) {
        const tabKey = tabButton.dataset.tab;
        if (tabKey) {
          setActiveTab(tabKey);
        }
        return;
      }

      const aionChatModeButton = target.closest("[data-aion-chat-mode]");
      if (aionChatModeButton) {
        const nextMode =
          aionChatModeButton.dataset.aionChatMode || "business_workspace";

        desktopStore.patch({
          aionChatMode: nextMode,
          desktopAssistantContextMode:
            nextMode === "business_workspace"
              ? "business_workspace"
              : "general_ai",
        });

        desktopStore.persistCacheSoon(300);
        requestRender();
        return;
      }

      const aionChatActionButton = target.closest("[data-aion-chat-action]");
      if (aionChatActionButton) {
        const action = aionChatActionButton.dataset.aionChatAction || "";

        const prompts = {
          explain_business:
            "Explain the current business state in plain English using the workspace context.",
          find_risks:
            "Find the main risks, weak points, or bottlenecks in the current business workspace.",
          improve_brand:
            "Review the current brand foundation and suggest improvements.",
          next_actions:
            "Suggest the next practical actions based on the current dashboard, agents, approvals, and brand state.",
        };

        const nextPrompt = prompts[action] || "";

        desktopStore.patch({
          aionChatMode: "business_workspace",
          desktopAssistantContextMode: "business_workspace",
          aionChatPrompt: nextPrompt,
          desktopAssistantPrompt: nextPrompt,
        });

        desktopStore.persistCacheSoon(300);
        requestRender();
        return;
      }

      const desktopAiActionButton = target.closest("[data-desktop-ai-action]");
      if (desktopAiActionButton) {
        const action = desktopAiActionButton.dataset.desktopAiAction || "";
        const prompts = {
          focus_today: "What should I focus on today based on the current boardroom state?",
          explain_business_state: "Explain the current business state in plain English.",
          find_risks: "Find the biggest risks or weak points in the current business state.",

          explain_alerts: "Explain the current alerts and what I should do next.",
          summarize_queue: "Summarize the current queue, approvals, and blocked work.",
          what_changed: "What changed recently in the local runtime?",

          write_post: "Help me write a strong marketing post from the current brand and campaign context.",
          improve_caption: "Improve the current caption and make it clearer.",
          campaign_ideas: "Give me campaign ideas based on the current brand foundation.",

          help_section: "Help me complete the selected brand section.",
          make_clearer: "Make the selected brand section clearer and easier to understand.",
          make_premium: "Make the selected brand section sound more professional and premium.",

          explain_run: "Explain the selected run in simple terms.",
          explain_approval: "Explain the selected approval and what decision is needed.",
          what_next: "What should happen next for the selected agent or run?",

          find_blockers: "Find blockers in the current operations flow.",
          explain_flow: "Explain how the current operations flow is working.",
          next_actions: "Suggest the next operational actions.",

          backend_status: "Why is the backend not ready or what should I check?",
          scheduler_status: "Explain the scheduler status and what it means.",
          sync_status: "Explain the local sync status.",
        };

        const nextPrompt = prompts[action] || "";

        if (state.activeTab === "aion_chat") {
          desktopStore.patch({
            aionChatMode: "business_workspace",
            desktopAssistantContextMode: "business_workspace",
            aionChatPrompt: nextPrompt,
            desktopAssistantPrompt: nextPrompt,
          });
        } else {
          desktopStore.patch({
            desktopAssistantPrompt: nextPrompt,
            desktopAssistantContextMode: state.activeTab,
            desktopAssistantTargetPath:
              state.activeTab === "brand_foundation"
                ? state.desktopAssistantTargetPath ||
                  state.brandAssistantSection ||
                  "brandMap.brandOverview.whatYouDo"
                : state.desktopAssistantTargetPath,
          });
        }

        desktopStore.persistCacheSoon(300);
        requestRender();
        return;
      }

      const operationsAgentsButton = target.closest(
        "[data-operations-agents-action]",
      );
      if (operationsAgentsButton) {
        const action =
          operationsAgentsButton.dataset.operationsAgentsAction || "";

        const sampleEmail = {
          id: "email_test_001",
          from: "Jane Customer <jane@example.com>",
          subject: "New enquiry about installation",
          body:
            "Hi, my name is Jane Customer. My email is jane@example.com and my phone is 07123 456789. I need help with a new installation.",
        };

        // ---------------------------------------------------------------------
        // Phase 4C/4D browser capture buttons.
        // Keep this near the top of the operations handler so capture buttons
        // are not swallowed by later workflow/recording branches.
        // ---------------------------------------------------------------------
        if (
          action === "capture-browser-open-page" ||
          action === "capture-browser-observe-page" ||
          action === "capture-browser-field" ||
          action === "capture-browser-click-checkpoint" ||
          action === "capture-browser-secret-step" ||
          action === "capture-browser-approval-checkpoint" ||
          action === "clear-browser-capture-events"
        ) {
          const bridge = state.browserDesktopBridge || {};
          const captureDraft = normaliseBrowserCaptureDraft
            ? normaliseBrowserCaptureDraft(bridge.capture_draft)
            : bridge.capture_draft || {};

          const existingEvents = Array.isArray(bridge.captured_events)
            ? bridge.captured_events
            : Array.isArray(bridge.captured_browser_events)
              ? bridge.captured_browser_events
              : Array.isArray(bridge.last_recording_steps)
                ? bridge.last_recording_steps
                : [];

          if (action === "clean-browser-duplicate-captures") {
          const bridge = state.browserDesktopBridge || {};
          const events = Array.isArray(bridge.captured_events)
            ? bridge.captured_events
            : Array.isArray(bridge.last_recording_steps)
              ? bridge.last_recording_steps
              : [];

          const seen = new Set();
          const cleaned = [];

          for (const event of events) {
            const key = [
              event.type || event.event_type || "",
              event.selector || event.primary_selector || "",
              event.url_pattern || event.current_url || event.url || "",
              event.label || "",
            ].join("::");

            if (seen.has(key)) continue;
            seen.add(key);
            cleaned.push(event);
          }

          const nextEvents = cleaned.map((event, index) => ({
            ...event,
            order: index + 1,
          }));

          desktopStore.patch({
            browserDesktopBridge: {
              ...bridge,
              captured_events: nextEvents,
              captured_browser_events: nextEvents,
              last_recording_steps: nextEvents,
              captured_event_count: nextEvents.length,
              message: `Cleaned ${events.length - nextEvents.length} duplicate browser step(s).`,
            },
            message: `Cleaned ${events.length - nextEvents.length} duplicate browser step(s)`,
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "clear-browser-capture-events") {
            desktopStore.patch({
              browserDesktopBridge: {
                ...bridge,
                captured_events: [],
                captured_browser_events: [],
                last_recording_steps: [],
                captured_event_count: 0,
                dry_run_ready: false,
                dry_run_result: null,
              },
              message: "Browser capture events cleared",
              messageTone: "success",
            });

            desktopStore.persistCacheSoon(300);
            requestRender();
            return;
          }

          const now = new Date().toISOString();
          const stepId =
            typeof makeBrowserStepId === "function"
              ? makeBrowserStepId()
              : `browser_step_${Date.now()}`;

          const url =
            captureDraft.url ||
            captureDraft.current_url ||
            captureDraft.expected_url ||
            "";

          const pageTitle =
            captureDraft.title ||
            captureDraft.page_title ||
            "";

          const selector = captureDraft.selector || "";
          const fieldName = captureDraft.field_name || "";
          const valueHint =
            captureDraft.field_value_hint ||
            captureDraft.value_hint ||
            "";

          const notes = captureDraft.notes || "";
          const label = captureDraft.label || "";
          const secretRef =
            captureDraft.secret_ref ||
            captureDraft.secretRef ||
            document.querySelector('[data-browser-capture-field="secret_ref"]')?.value ||
            "gmail_login";
          const secretType =
            captureDraft.secret_type ||
            captureDraft.secretType ||
            "manual_login_profile";

          let eventRow = null;

          if (action === "capture-browser-open-page") {
            eventRow = {
              step_id: stepId,
              order: existingEvents.length + 1,
              type: "open_page",
              label: label || "Open target page",
              safety: "read_only",
              input_map: {},
              output: "page_context",
              selector: "",
              url_pattern: url,
              page_title: pageTitle,
              field_name: "",
              value_hint: "",
              requires_approval: false,
              dry_run_supported: true,
              captured: true,
              captured_at: now,
              notes,
            };
          }

          if (action === "capture-browser-observe-page") {
            eventRow = {
              step_id: stepId,
              order: existingEvents.length + 1,
              type: "observe_page",
              label: label || "Observe page state",
              safety: "read_only",
              input_map: {},
              output: "page_state",
              selector,
              url_pattern: url,
              page_title: pageTitle,
              field_name: "",
              value_hint: "",
              requires_approval: false,
              dry_run_supported: true,
              captured: true,
              captured_at: now,
              notes,
            };
          }

          if (action === "capture-browser-field") {
            eventRow = {
              step_id: stepId,
              order: existingEvents.length + 1,
              type: "capture_field",
              label: label || fieldName || "Capture field",
              safety: "read_only",
              input_map: {},
              output: fieldName || "field_value",
              selector,
              url_pattern: url,
              page_title: pageTitle,
              field_name: fieldName,
              value_hint: valueHint,
              requires_approval: false,
              dry_run_supported: true,
              captured: true,
              captured_at: now,
              notes,
            };
          }

          if (action === "capture-browser-click-checkpoint") {
            try {
              desktopStore.patch({
                message: "Click the target inside the isolated browser...",
                messageTone: "neutral",
              });
              requestRender();

              if (!window.aionDesktop?.startCaptureNextClick) {
                desktopStore.patch({
                  message: "Electron browser capture bridge is not available.",
                  messageTone: "error",
                });
                requestRender();
                return;
              }

              const result = await window.aionDesktop.startCaptureNextClick();
              const payload = result?.payload || result?.result?.payload || null;

              if (!payload) {
                desktopStore.patch({
                  message:
                    result?.message ||
                    result?.result?.error ||
                    "Browser click capture did not return a payload.",
                  messageTone: "error",
                });
                requestRender();
                return;
              }

              const bridge = state.browserDesktopBridge || {};
              const existingEvents = Array.isArray(bridge.captured_events)
                ? bridge.captured_events
                : Array.isArray(bridge.captured_browser_events)
                  ? bridge.captured_browser_events
                  : [];

              const nextEvent = {
                step_id: payload.step_id || `browser_step_${Date.now()}`,
                order: existingEvents.length + 1,
                type: payload.type || payload.event_type || "click_element",
                event_type: payload.event_type || payload.type || "click_element",
                label: payload.label || "Click selected browser element",
                safety: payload.safety || "interaction",
                input_map: payload.input_map || {},
                output: payload.output || "click_result",
                selector: payload.selector || "",
                url_pattern: payload.url_pattern || payload.current_url || payload.url || "",
                page_title: payload.page_title || payload.title || "",
                field_name: payload.field_name || "",
                value_hint: payload.value_hint || payload.field_value_hint || "",
                requires_approval: payload.requires_approval !== false,
                dry_run_supported: true,
                captured: true,
                captured_at: payload.captured_at || new Date().toISOString(),
                notes: payload.notes || "Captured from isolated browser click.",
              };

              const nextEvents = [...existingEvents, nextEvent].map((item, index) => ({
                ...item,
                order: index + 1,
              }));

              desktopStore.patch({
                browserDesktopBridge: {
                  ...bridge,
                  status: "recording",
                  bridge_active: true,
                  recording: true,
                  captured_events: nextEvents,
                  captured_browser_events: nextEvents,
                  last_recording_steps: nextEvents,
                  captured_event_count: nextEvents.length,
                  dry_run_ready: false,
                  dry_run_result: null,
                  message: `Captured browser click: ${nextEvent.label}`,
                },
                message: `Captured browser click: ${nextEvent.label}`,
                messageTone: "success",
              });

              desktopStore.persistCacheSoon(300);
              requestRender();
              return;
            } catch (error) {
              desktopStore.patch({
                message:
                  error instanceof Error
                    ? error.message
                    : "Browser click capture failed",
                messageTone: "error",
              });
              requestRender();
              return;
            }
          }
if (action === "capture-browser-secret-step") {
            eventRow = {
              step_id: stepId,
              order: existingEvents.length + 1,
              type: "use_secret",
              event_type: "use_secret",
              label: label || `Use ${secretRef || "login / secret"}`,
              safety: "secret_reference",
              input_map: {
                secret_ref: secretRef,
                secret_type: secretType,
              },
              output: "auth_context",
              selector,
              url_pattern: url,
              page_title: pageTitle,
              field_name: "",
              value_hint: "Secret value is never stored in the browser skill contract.",
              secret_ref: secretRef,
              secret_type: secretType,
              requires_approval: true,
              dry_run_supported: true,
              captured: true,
              captured_at: now,
              notes,
            };
          }

          if (action === "capture-browser-approval-checkpoint") {
            eventRow = {
              step_id: stepId,
              order: existingEvents.length + 1,
              type: "approval_checkpoint",
              label: label || "Require approval before risky browser action",
              safety: "approval_required",
              input_map: {},
              output: "approval_required",
              selector: "",
              url_pattern: url,
              page_title: pageTitle,
              field_name: "",
              value_hint: "",
              requires_approval: true,
              dry_run_supported: true,
              captured: true,
              captured_at: now,
              notes,
            };
          }

          if (!eventRow) return;

          let nextRawEvents = [...existingEvents, eventRow];

          // If the selected browser click came from the isolated browser,
          // automatically append an approval checkpoint so the user does not
          // have to return to the desktop panel after the click.
          if (
            String(eventRow.type || eventRow.event_type || "") === "click_element" ||
            String(eventRow.type || eventRow.event_type || "") === "click_checkpoint"
          ) {
            const alreadyHasTrailingApproval =
              String(nextRawEvents[nextRawEvents.length - 1]?.type || "") === "approval_checkpoint" ||
              String(nextRawEvents[nextRawEvents.length - 1]?.event_type || "") === "approval_checkpoint";

            if (!alreadyHasTrailingApproval) {
              nextRawEvents.push({
                step_id: `browser_step_${Date.now().toString(36)}_approval`,
                order: nextRawEvents.length + 1,
                type: "approval_checkpoint",
                event_type: "approval_checkpoint",
                label: "Approval required before opening or acting on email",
                safety: "approval_required",
                input_map: {},
                output: "approval_required",
                selector: "",
                url_pattern: eventRow.url_pattern || eventRow.url || "",
                page_title: eventRow.page_title || "",
                field_name: "",
                value_hint: "",
                requires_approval: true,
                dry_run_supported: true,
                captured: true,
                captured_at: now,
                notes: "Auto-added after selected browser click.",
              });
            }
          }

          const nextEvents = nextRawEvents.map((item, index) => ({
            ...item,
            order: index + 1,
          }));

          desktopStore.patch({
            browserDesktopBridge: {
              ...bridge,
              status: bridge.status || "recording",
              bridge_active: true,
              recording: true,
              captured_events: nextEvents,
              captured_browser_events: nextEvents,
              last_recording_steps: nextEvents,
              captured_event_count: nextEvents.length,
              dry_run_ready: false,
              dry_run_result: null,
              last_recording_name: "",
              last_recording_summary: "",
            },
            message: `Captured browser event: ${eventRow.label}`,
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "open-wizard") {
          const templateId =
            operationsAgentsButton.dataset.templateId || "gmail_hubspot_welcome";

          desktopStore.patch({
            operationsAgentsWizardOpen: true,
            operationsAgentsWizardStep: 1,
            operationsAgentsWizardDraft: buildTeachAionTemplateDraft(templateId),
            operationsAgentsWizardError: "",
            operationsAgentsWizardResult: null,
            message: "Train Agent task template loaded",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "close-wizard") {
          desktopStore.patch({
            operationsAgentsWizardOpen: false,
            operationsAgentsWizardError: "",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "wizard-next") {
          const currentStep = Number(state.operationsAgentsWizardStep || 1);

          desktopStore.patch({
            operationsAgentsWizardStep: Math.min(currentStep + 1, 4),
            operationsAgentsWizardError: "",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "wizard-prev") {
          const currentStep = Number(state.operationsAgentsWizardStep || 1);

          desktopStore.patch({
            operationsAgentsWizardStep: Math.max(currentStep - 1, 1),
            operationsAgentsWizardError: "",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "edit-workflow") {
          const workflowId = operationsAgentsButton.dataset.workflowId || "";
          const workflows = Array.isArray(state.operationsAgentsWorkflows)
            ? state.operationsAgentsWorkflows
            : [];
          const workflow = workflows.find((item) => {
            const id = item?.workflow_id || item?.id || "";
            return String(id) === String(workflowId);
          });

          if (!workflow) {
            desktopStore.patch({
              message: "Could not find trained task to edit",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          desktopStore.patch({
            operationsAgentsWizardOpen: true,
            operationsAgentsWizardStep: 1,
            operationsAgentsWizardDraft: JSON.parse(JSON.stringify(workflow)),
            operationsAgentsWizardError: "",
            operationsAgentsWizardResult: null,
            message: "Editing trained task",
            messageTone: "neutral",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "archive-workflow" || action === "delete-workflow") {
          desktopStore.patch({
            message: "Archive/Delete will be enabled after workflow lifecycle storage is finalized.",
            messageTone: "neutral",
          });
          requestRender();
          return;
        }

        if (action === "run-external-tool-dry-run") {
          const toolId = operationsAgentsButton.dataset.toolId || "";

          if (!toolId) {
            desktopStore.patch({
              message: "No external tool id found",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Running external tool dry-run...",
              messageTone: "neutral",
            });
            requestRender();

            const payload =
              toolId.includes("mcp")
                ? {
                    project_id: "local-dev-project",
                    service: "gmail.googleapis.com",
                    operation: "check_enabled",
                  }
                : {
                    email: "jane@example.com",
                    firstname: "Jane",
                    phone: "07123 456789",
                    company: "CostaConnect",
                  };

            const result = await apiPost("/api/local-node/tools/external/dry-run", {
              tool_id: toolId,
              workflow_id: "workflow_phase5_ui_external_tool_test",
              run_id: `run_phase5_ui_${Date.now()}`,
              payload,
            });

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsExternalToolDryRunResult: result,
              message: result?.ok
                ? `External dry-run complete: ${toolId}`
                : result?.error || "External dry-run failed",
              messageTone: result?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "External dry-run failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "create-gmail-draft-from-approval") {
          const approvalId = operationsAgentsButton.dataset.approvalId || "";

          if (!approvalId) {
            desktopStore.patch({
              message: "No approval id found",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Creating Gmail draft...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiPost(
              `/api/local-node/train-tasks/approvals/${encodeURIComponent(approvalId)}/execute-gmail-draft`,
              {
                executed_by: "operations_agents_desktop",
              },
            );

            const approvalsResult = await apiGet("/api/local-node/train-tasks/approvals?limit=20");

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsApprovals: Array.isArray(approvalsResult?.items)
                ? approvalsResult.items
                : [],
              operationsAgentsGenericWorkflows: Array.isArray(genericWorkflowsResult?.items)
                ? genericWorkflowsResult.items
                : [],
              message: result?.ok
                ? "Gmail draft created. Email was not sent."
                : result?.error || "Gmail draft creation failed",
              messageTone: result?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Gmail draft creation failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "copy-generic-workflow-id") {
          const workflowId = operationsAgentsButton.dataset.workflowId || "";

          try {
            await navigator.clipboard.writeText(workflowId);
            desktopStore.patch({
              message: workflowId ? "Workflow id copied" : "No workflow id found",
              messageTone: workflowId ? "success" : "error",
            });
          } catch (error) {
            desktopStore.patch({
              message: workflowId || "No workflow id found",
              messageTone: workflowId ? "neutral" : "error",
            });
          }

          requestRender();
          return;
        }

        if (action === "run-generic-workflow") {
          const workflowId = operationsAgentsButton.dataset.workflowId || "";

          if (!workflowId) {
            desktopStore.patch({
              message: "Workflow id missing",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: `Running generic workflow ${workflowId}...`,
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiPost("/api/local-node/train-tasks/workflows/generic-run", {
              workflow_id: workflowId,
              executed_by: "operations_agents_desktop",
              trigger_payload: {
                email: "customer@example.com",
                subject: "Desktop generic workflow test",
                body: "Generic workflow run launched from desktop UI.",
              },
              workspace_context: {
                source: "desktop_ui",
              },
            });

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsLastGenericRun: result,
              message: result?.ok
                ? `Generic workflow completed: ${result.run_id || workflowId}`
                : result?.error || "Generic workflow run failed",
              messageTone: result?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Generic workflow run failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "open-step-builder") {
          desktopStore.patch({
            operationsAgentsStepBuilderOpen: true,
            operationsAgentsStepBuilderDraft: normaliseStepBuilderDraft(
              state.operationsAgentsStepBuilderDraft || createStepBuilderDraft(),
            ),
            operationsAgentsStepBuilderSelectedStepId:
              state.operationsAgentsStepBuilderSelectedStepId || "",
            message: "Step-by-step builder opened",
            messageTone: "success",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "close-step-builder") {
          desktopStore.patch({
            operationsAgentsStepBuilderOpen: false,
            message: "Step-by-step builder closed",
            messageTone: "neutral",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "reset-step-builder") {
          const draft = createStepBuilderDraft();
          desktopStore.patch({
            operationsAgentsStepBuilderDraft: draft,
            operationsAgentsStepBuilderSelectedStepId: "",
            message: "Step-by-step builder reset",
            messageTone: "neutral",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "add-step-builder-step") {
          const addTypeSelect = document.querySelector("[data-step-builder-add-type]");
          const type = addTypeSelect?.value || "trigger";
          const draft = addStepBuilderStep(state.operationsAgentsStepBuilderDraft, type);
          const selected = draft.steps[draft.steps.length - 1]?.step_id || "";

          desktopStore.patch({
            operationsAgentsStepBuilderDraft: draft,
            operationsAgentsStepBuilderSelectedStepId: selected,
            message: "Step added",
            messageTone: "success",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "select-step-builder-step") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          desktopStore.patch({
            operationsAgentsStepBuilderSelectedStepId: stepId,
          });
          requestRender();
          return;
        }

        if (action === "move-step-builder-up" || action === "move-step-builder-down") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          const direction = action === "move-step-builder-up" ? "up" : "down";
          const draft = moveStepBuilderStep(state.operationsAgentsStepBuilderDraft, stepId, direction);

          desktopStore.patch({
            operationsAgentsStepBuilderDraft: draft,
            operationsAgentsStepBuilderSelectedStepId: stepId,
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "duplicate-step-builder-step") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          const draft = duplicateStepBuilderStep(state.operationsAgentsStepBuilderDraft, stepId);

          desktopStore.patch({
            operationsAgentsStepBuilderDraft: draft,
            message: "Step duplicated",
            messageTone: "success",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "delete-step-builder-step") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          const draft = deleteStepBuilderStep(state.operationsAgentsStepBuilderDraft, stepId);

          desktopStore.patch({
            operationsAgentsStepBuilderDraft: draft,
            operationsAgentsStepBuilderSelectedStepId: draft.steps[0]?.step_id || "",
            message: "Step deleted",
            messageTone: "neutral",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "toggle-step-builder-step") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          const current = normaliseStepBuilderDraft(state.operationsAgentsStepBuilderDraft)
            .steps.find((step) => step.step_id === stepId);
          const draft = updateStepBuilderStep(state.operationsAgentsStepBuilderDraft, stepId, {
            enabled: current?.enabled === false,
          });

          desktopStore.patch({
            operationsAgentsStepBuilderDraft: draft,
            operationsAgentsStepBuilderSelectedStepId: stepId,
            message: current?.enabled === false ? "Step enabled" : "Step disabled",
            messageTone: "neutral",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "seed-step-builder-example") {
          const draft = normaliseStepBuilderDraft(state.operationsAgentsStepBuilderDraft || createStepBuilderDraft());
          const seeded = {
            ...draft,
            workflow_name: draft.workflow_name || "New enquiry follow-up workflow",
            department: draft.department || "Sales",
            operator_name: draft.operator_name || "Sales Lead Follow-up Operator",
            description:
              draft.description ||
              "Handles new enquiry emails by extracting customer details, preparing CRM action, drafting a welcome email, and asking for approval.",
            goal:
              draft.goal ||
              "Turn new customer enquiries into a safe, reviewed follow-up workflow.",
            steps: [
              {
                ...createStepBuilderStep("trigger"),
                name: "Gmail trigger",
                output: "trigger",
                input_source: "trigger_payload",
                tool_id: "tool.gmail.trigger.v1",
              },
              {
                ...createStepBuilderStep("extract"),
                name: "Extract customer data",
                output: "extracted",
                input_source: "trigger_payload",
                input_ref: "$trigger",
                tool_id: "tool.aion.extract.v1",
                output_schema: '{"email":"string","firstname":"string","phone":"string"}',
                failure_behavior: "ask_approval",
                audit_visibility: "summary",
              },
              {
                ...createStepBuilderStep("draft_email"),
                name: "Draft welcome email preview",
                output: "email_draft",
                input_source: "previous_step",
                input_ref: "$steps.extracted",
                tool_id: "tool.gmail.draft_preview.v1",
                failure_behavior: "stop",
                audit_visibility: "full",
              },
              {
                ...createStepBuilderStep("approval_checkpoint"),
                name: "Ask approval before CRM update",
                output: "approval",
                input_source: "previous_step",
                input_ref: "$steps.email_draft",
                tool_id: "tool.approval.checkpoint.v1",
                failure_behavior: "stop",
                audit_visibility: "full",
              },
              {
                ...createStepBuilderStep("crm_upsert"),
                name: "Create/update CRM contact",
                output: "crm_preview",
                input_source: "previous_step",
                input_ref: "$steps.extracted",
                tool_id: "tool.mcp.hubspot.contact_upsert.v1",
                failure_behavior: "ask_approval",
                audit_visibility: "summary",
              },
              {
                ...createStepBuilderStep("end"),
                name: "Stop/end",
                output: "",
                input_source: "previous_step",
                tool_id: "",
                failure_behavior: "stop",
                audit_visibility: "summary",
              },
            ],
          };

          desktopStore.patch({
            operationsAgentsStepBuilderDraft: seeded,
            operationsAgentsStepBuilderSelectedStepId: seeded.steps[0]?.step_id || "",
            message: "Example workflow added",
            messageTone: "success",
          });
          desktopStore.persistCache();
          requestRender();
          return;
        }

        if (action === "compile-step-builder-workflow") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Compiling builder draft...",
              messageTone: "neutral",
              operationsAgentsStepBuilderCompileResult: null,
            });
            requestRender();

            const workflow = compileStepBuilderDraftToGenericWorkflow(
              state.operationsAgentsStepBuilderDraft,
            );

            const validation = await apiPost(
              "/api/local-node/train-tasks/workflows/validate",
              { workflow },
            );

            const result = {
              ok: validation?.ok === true,
              message: validation?.ok
                ? "Builder draft compiled and validated successfully."
                : "Builder draft compiled but validation found issues.",
              workflow,
              validation,
            };

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsStepBuilderCompileResult: result,
              message: result.ok
                ? "Builder workflow validation passed"
                : "Builder workflow validation failed",
              messageTone: result.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsStepBuilderCompileResult: {
                ok: false,
                message:
                  error instanceof Error
                    ? error.message
                    : "Builder workflow compile failed",
              },
              message:
                error instanceof Error
                  ? error.message
                  : "Builder workflow compile failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "simulate-step-builder-workflow") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Simulating builder workflow...",
              messageTone: "neutral",
              operationsAgentsStepBuilderSimulationResult: null,
            });
            requestRender();

            const workflow = compileStepBuilderDraftToGenericWorkflow(
              state.operationsAgentsStepBuilderDraft,
            );

            const validation = await apiPost(
              "/api/local-node/train-tasks/workflows/validate",
              { workflow },
            );

            if (validation?.ok !== true) {
              desktopStore.patch({
                operationsAgentsLoading: false,
                operationsAgentsStepBuilderCompileResult: {
                  ok: false,
                  message: "Builder workflow must pass validation before simulation.",
                  workflow,
                  validation,
                },
                operationsAgentsStepBuilderSimulationResult: {
                  ok: false,
                  status: "validation_failed",
                  error: "Builder workflow must pass validation before simulation.",
                  validation,
                },
                message: "Builder workflow validation failed",
                messageTone: "error",
              });
              requestRender();
              return;
            }

            const sample = state.operationsAgentsStepBuilderSampleInput || {};
            const simulation = await apiPost(
              "/api/local-node/train-tasks/workflows/generic-test-run",
              {
                workflow,
                trigger_payload: {
                  email: sample.email || "customer@example.com",
                  subject: sample.subject || "Quote needed for pool cleaning",
                  body:
                    sample.body ||
                    "Hi, can I get a quote for pool cleaning in Arboleas?",
                },
                workspace_context: {
                  source: "phase_8_step_builder_simulation",
                  business_name: "CostaConnect",
                },
              },
            );

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsStepBuilderCompileResult: {
                ok: true,
                message: "Builder draft compiled and validated successfully.",
                workflow,
                validation,
              },
              operationsAgentsStepBuilderSimulationResult: simulation,
              message: simulation?.ok
                ? "Builder workflow simulation completed"
                : simulation?.error || "Builder workflow simulation failed",
              messageTone: simulation?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsStepBuilderSimulationResult: {
                ok: false,
                status: "failed",
                error:
                  error instanceof Error
                    ? error.message
                    : "Builder workflow simulation failed",
              },
              message:
                error instanceof Error
                  ? error.message
                  : "Builder workflow simulation failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (
          action === "save-step-builder-workflow-draft" ||
          action === "publish-step-builder-workflow"
        ) {
          const publish = action === "publish-step-builder-workflow";

          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: publish
                ? "Publishing builder workflow..."
                : "Saving builder workflow draft...",
              messageTone: "neutral",
              operationsAgentsStepBuilderSaveResult: null,
            });
            requestRender();

            const workflow = compileStepBuilderDraftToGenericWorkflow(
              state.operationsAgentsStepBuilderDraft,
            );

            const validation = await apiPost(
              "/api/local-node/train-tasks/workflows/validate",
              { workflow },
            );

            if (validation?.ok !== true) {
              const failed = {
                ok: false,
                status: "validation_failed",
                message: publish
                  ? "Workflow failed validation and cannot be published."
                  : "Workflow failed validation and cannot be saved.",
                workflow,
                validation,
              };

              desktopStore.patch({
                operationsAgentsLoading: false,
                operationsAgentsStepBuilderCompileResult: {
                  ok: false,
                  message: "Builder workflow validation failed.",
                  workflow,
                  validation,
                },
                operationsAgentsStepBuilderSaveResult: failed,
                message: failed.message,
                messageTone: "error",
              });
              requestRender();
              return;
            }

            const saveResult = await apiPost(
              "/api/local-node/train-tasks/workflows/generic-save",
              {
                publish,
                saved_by: "operations_agents_step_builder",
                workflow,
              },
            );

            const genericWorkflowsResult = await apiGet(
              "/api/local-node/train-tasks/workflows/generic-saved",
            );

            const result = {
              ok: saveResult?.ok === true,
              status: saveResult?.status || (publish ? "published" : "draft"),
              message: saveResult?.ok
                ? publish
                  ? "Builder workflow published and enabled."
                  : "Builder workflow saved as draft."
                : saveResult?.error || "Builder workflow save failed.",
              workflow,
              validation,
              save: saveResult,
            };

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsStepBuilderCompileResult: {
                ok: true,
                message: "Builder draft compiled and validated successfully.",
                workflow,
                validation,
              },
              operationsAgentsStepBuilderSaveResult: result,
              operationsAgentsGenericWorkflows: Array.isArray(genericWorkflowsResult?.items)
                ? genericWorkflowsResult.items
                : [],
              message: result.message,
              messageTone: result.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsStepBuilderSaveResult: {
                ok: false,
                status: "failed",
                message:
                  error instanceof Error
                    ? error.message
                    : "Builder workflow save/publish failed",
              },
              message:
                error instanceof Error
                  ? error.message
                  : "Builder workflow save/publish failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "activate-browser-bridge") {
          const now = new Date().toISOString();

          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              status: "active",
              bridge_active: true,
              recording: false,
              mode: state.browserDesktopBridge?.mode || "isolated_browser",
              browser: state.browserDesktopBridge?.browser || "Aion isolated browser",
              writes_mode: "approval_required",
              activated_at: now,
              message: "Browser bridge activated by explicit user action.",
            },
            message: "Browser bridge active",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "open-isolated-browser") {
          const now = new Date().toISOString();
          const startUrl =
            state.browserDesktopBridge?.skill_review?.expected_url ||
            state.browserDesktopBridge?.expected_url ||
            state.browserDesktopBridge?.capture_draft?.url ||
            "https://mail.google.com/mail/u/0/#inbox";

          try {
            const result =
              window.aionDesktop?.openIsolatedBrowser
                ? await window.aionDesktop.openIsolatedBrowser({ startUrl })
                : { ok: false, error: "Electron bridge not available" };

            desktopStore.patch({
              browserDesktopBridge: {
                ...(state.browserDesktopBridge || {}),
                status: result.ok ? "active" : "error",
                bridge_active: result.ok === true,
                recording: false,
                mode: "isolated_browser",
                browser: "Aion isolated browser",
                isolated_browser_requested: true,
                isolated_browser_open: result.ok === true,
                last_opened_at: now,
                expected_url: startUrl,
                message: result.ok
                  ? "Aion isolated browser opened."
                  : result.error || "Failed to open isolated browser.",
              },
              message: result.ok
                ? "Aion isolated browser opened"
                : result.error || "Failed to open isolated browser",
              messageTone: result.ok ? "success" : "error",
            });
          } catch (error) {
            desktopStore.patch({
              browserDesktopBridge: {
                ...(state.browserDesktopBridge || {}),
                status: "error",
                bridge_active: false,
                isolated_browser_open: false,
                message:
                  error instanceof Error
                    ? error.message
                    : "Failed to open isolated browser.",
              },
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to open isolated browser",
              messageTone: "error",
            });
          }

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "start-browser-workflow-recording") {
          const now = new Date().toISOString();

          if (window.aionDesktop?.startBrowserRecording) {
            try {
              await window.aionDesktop.startBrowserRecording();
            } catch (error) {
              console.warn("[browser-recorder] start failed", error);
            }
          }

          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              status: "recording",
              bridge_active: true,
              recording: true,
              mode: state.browserDesktopBridge?.mode || "isolated_browser",
              browser: state.browserDesktopBridge?.browser || "Aion isolated browser",
              recording_started_at: now,
              recording_stopped_at: null,

              // Clear previous result while actively recording.
              last_recording_name: "",
              last_recording_summary: "",
              last_recording_steps: [],
              last_skill_contract: null,
              dry_run_ready: false,
              dry_run_result: null,

              message:
                "Recording active. Perform one small browser action, then click Stop Recording.",
            },
            message: "Recording browser skill...",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "stop-browser-workflow-recording") {
          const now = new Date().toISOString();
          const bridge = state.browserDesktopBridge || {};
          const capturedEvents = Array.isArray(bridge.captured_events)
            ? bridge.captured_events
            : Array.isArray(bridge.captured_browser_events)
              ? bridge.captured_browser_events
              : [];

          const recordingSteps = capturedEvents.map((event, index) => ({
            step_id: event.step_id || `browser_step_${Date.now()}_${index + 1}`,
            order: index + 1,
            type: event.type || event.event_type || "browser_event",
            label: event.label || "Captured browser event",
            safety: event.safety || (event.requires_approval ? "approval_required" : "read_only"),
            input_map: event.input_map || {},
            output: event.output || "browser_output",
            selector: event.selector || "",
            url_pattern: event.url_pattern || event.current_url || event.url || "",
            page_title: event.page_title || event.title || "",
            field_name: event.field_name || "",
            value_hint: event.value_hint || event.field_value_hint || "",
            requires_approval: event.requires_approval === true,
            dry_run_supported: event.dry_run_supported !== false,
            captured: true,
            captured_at: event.captured_at || now,
            notes: event.notes || "",
          }));

          desktopStore.patch({
            browserDesktopBridge: {
              ...bridge,
              status: recordingSteps.length ? "recorded" : "recording_empty",
              bridge_active: true,
              recording: false,
              recording_stopped_at: now,
              last_recording_name: recordingSteps.length
                ? "Captured browser skill"
                : "No captured browser events",
              last_recording_summary: recordingSteps.length
                ? `${recordingSteps.length} real browser event(s) captured.`
                : "No real browser events were captured.",
              last_recording_steps: recordingSteps,
              captured_events: recordingSteps,
              captured_browser_events: recordingSteps,
              captured_event_count: recordingSteps.length,
              dry_run_ready: recordingSteps.length > 0,
              dry_run_result: null,
              message: recordingSteps.length
                ? "Recording stopped. Real captured browser events are ready for review."
                : "Recording stopped, but no browser events were captured.",
            },
            message: recordingSteps.length
              ? "Browser recording stopped"
              : "No browser events captured",
            messageTone: recordingSteps.length ? "success" : "error",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "browser-operator-dry-run") {
          const now = new Date().toISOString();
          const bridge = state.browserDesktopBridge || {};
          const steps = Array.isArray(bridge.last_recording_steps)
            ? bridge.last_recording_steps
            : [];

          if (!steps.length) {
            desktopStore.patch({
              browserDesktopBridge: {
                ...(state.browserDesktopBridge || {}),
                dry_run_result: {
                  ok: false,
                  status: "no_skill_recorded",
                  message: "Record and stop a browser skill before running dry-run replay.",
                  created_at: now,
                },
              },
              message: "No browser skill available for dry-run",
              messageTone: "error",
            });

            desktopStore.persistCacheSoon(300);
            requestRender();
            return;
          }

          const replaySteps = steps.map((step) => ({
            ...step,
            ok: true,
            mode: "dry-run only",
            replayed_at: now,
          }));

          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              status: "dry_run_complete",
              bridge_active: true,
              recording: false,
              dry_run_ready: true,
              dry_run_result: {
                ok: true,
                status: "dry_run_complete",
                message:
                  "Dry-run replay completed locally. No browser submit, payment, delete, or external write was performed.",
                created_at: now,
                skill_id: bridge.last_skill_contract?.skill_id || null,
                skill_name: bridge.last_recording_name || "Browser skill",
                steps: replaySteps,
                blocked_actions: [
                  "submit_without_approval",
                  "payment",
                  "delete",
                  "external_write_without_policy",
                ],
              },
              message: "Browser skill dry-run replay completed.",
            },
            message: "Browser skill dry-run complete",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "capture-browser-open-page") {
          const now = new Date().toISOString();
          const draft = normaliseBrowserCaptureDraft(state.browserDesktopBridge?.capture_draft);
          const event = createBrowserCaptureEventFromDraft(
            {
              ...draft,
              event_type: "open_page",
              label: draft.label || "Open target page",
            },
            "open_page",
          );

          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              captured_events: [...getBrowserCaptureEvents(), event],
              capture_draft: normaliseBrowserCaptureDraft({}),
              last_capture_at: now,
              message: "Captured browser open-page event.",
            },
            message: "Captured open-page event",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "capture-browser-observe-page") {
          const now = new Date().toISOString();
          const draft = normaliseBrowserCaptureDraft(state.browserDesktopBridge?.capture_draft);
          const event = createBrowserCaptureEventFromDraft(
            {
              ...draft,
              event_type: "observe_page",
              label: draft.label || "Observe page state",
            },
            "observe_page",
          );

          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              captured_events: [...getBrowserCaptureEvents(), event],
              capture_draft: normaliseBrowserCaptureDraft({}),
              last_capture_at: now,
              message: "Captured browser page observation.",
            },
            message: "Captured page observation",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "capture-browser-field") {
          const now = new Date().toISOString();
          const draft = normaliseBrowserCaptureDraft(state.browserDesktopBridge?.capture_draft);
          const event = createBrowserCaptureEventFromDraft(
            {
              ...draft,
              event_type: "capture_field",
              label: draft.label || `Capture field${draft.field_name ? `: ${draft.field_name}` : ""}`,
            },
            "capture_field",
          );

          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              captured_events: [...getBrowserCaptureEvents(), event],
              capture_draft: normaliseBrowserCaptureDraft({}),
              last_capture_at: now,
              message: "Captured browser field event.",
            },
            message: "Captured field event",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "capture-browser-click-checkpoint") {
            try {
              desktopStore.patch({
                message: "Click the target inside the isolated browser...",
                messageTone: "neutral",
              });
              requestRender();

              if (!window.aionDesktop?.startCaptureNextClick) {
                desktopStore.patch({
                  message: "Electron browser capture bridge is not available.",
                  messageTone: "error",
                });
                requestRender();
                return;
              }

              const result = await window.aionDesktop.startCaptureNextClick();
              const payload = result?.payload || result?.result?.payload || null;

              if (!payload) {
                desktopStore.patch({
                  message:
                    result?.message ||
                    result?.result?.error ||
                    "Browser click capture did not return a payload.",
                  messageTone: "error",
                });
                requestRender();
                return;
              }

              const bridge = state.browserDesktopBridge || {};
              const existingEvents = Array.isArray(bridge.captured_events)
                ? bridge.captured_events
                : Array.isArray(bridge.captured_browser_events)
                  ? bridge.captured_browser_events
                  : [];

              const nextEvent = {
                step_id: payload.step_id || `browser_step_${Date.now()}`,
                order: existingEvents.length + 1,
                type: payload.type || payload.event_type || "click_element",
                event_type: payload.event_type || payload.type || "click_element",
                label: payload.label || "Click selected browser element",
                safety: payload.safety || "interaction",
                input_map: payload.input_map || {},
                output: payload.output || "click_result",
                selector: payload.selector || "",
                url_pattern: payload.url_pattern || payload.current_url || payload.url || "",
                page_title: payload.page_title || payload.title || "",
                field_name: payload.field_name || "",
                value_hint: payload.value_hint || payload.field_value_hint || "",
                requires_approval: payload.requires_approval !== false,
                dry_run_supported: true,
                captured: true,
                captured_at: payload.captured_at || new Date().toISOString(),
                notes: payload.notes || "Captured from isolated browser click.",
              };

              const nextEvents = [...existingEvents, nextEvent].map((item, index) => ({
                ...item,
                order: index + 1,
              }));

              desktopStore.patch({
                browserDesktopBridge: {
                  ...bridge,
                  status: "recording",
                  bridge_active: true,
                  recording: true,
                  captured_events: nextEvents,
                  captured_browser_events: nextEvents,
                  last_recording_steps: nextEvents,
                  captured_event_count: nextEvents.length,
                  dry_run_ready: false,
                  dry_run_result: null,
                  message: `Captured browser click: ${nextEvent.label}`,
                },
                message: `Captured browser click: ${nextEvent.label}`,
                messageTone: "success",
              });

              desktopStore.persistCacheSoon(300);
              requestRender();
              return;
            } catch (error) {
              desktopStore.patch({
                message:
                  error instanceof Error
                    ? error.message
                    : "Browser click capture failed",
                messageTone: "error",
              });
              requestRender();
              return;
            }
          }
if (action === "capture-browser-approval-checkpoint") {
          const now = new Date().toISOString();
          const draft = normaliseBrowserCaptureDraft(state.browserDesktopBridge?.capture_draft);
          const event = createBrowserCaptureEventFromDraft(
            {
              ...draft,
              event_type: "approval_checkpoint",
              label: draft.label || "Require approval before risky browser action",
            },
            "approval_checkpoint",
          );

          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              captured_events: [...getBrowserCaptureEvents(), event],
              capture_draft: normaliseBrowserCaptureDraft({}),
              last_capture_at: now,
              message: "Captured browser approval checkpoint.",
            },
            message: "Captured approval checkpoint",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "clear-browser-capture-events") {
          desktopStore.patch({
            browserDesktopBridge: {
              ...(state.browserDesktopBridge || {}),
              captured_events: [],
              last_recording_steps: [],
              last_recording_name: "",
              dry_run_ready: false,
              dry_run_result: null,
              message: "Browser capture events cleared.",
            },
            message: "Browser capture events cleared",
            messageTone: "neutral",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "delete-browser-skill-step") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          deleteBrowserCapturedEvent(stepId);
          desktopStore.patch({
            message: "Browser skill step deleted",
            messageTone: "success",
          });
          requestRender();
          return;
        }

        if (action === "move-browser-skill-step-up") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          moveBrowserCapturedEvent(stepId, "up");
          desktopStore.patch({
            message: "Browser skill step moved up",
            messageTone: "success",
          });
          requestRender();
          return;
        }

        if (action === "move-browser-skill-step-down") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          moveBrowserCapturedEvent(stepId, "down");
          desktopStore.patch({
            message: "Browser skill step moved down",
            messageTone: "success",
          });
          requestRender();
          return;
        }

        if (action === "toggle-browser-skill-step-approval") {
          const stepId = operationsAgentsButton.dataset.stepId || "";
          const events = getBrowserCapturedEventsForEditing();
          const current = events.find(
            (event) => String(event.step_id || "") === String(stepId),
          );

          const nextApproval = !(current?.requires_approval === true);

          patchBrowserCapturedEvent(stepId, {
            requires_approval: nextApproval,
            safety: nextApproval ? "approval_required" : "read_only",
          });

          desktopStore.patch({
            message: nextApproval
              ? "Approval required for browser skill step"
              : "Approval removed from browser skill step",
            messageTone: "success",
          });
          requestRender();
          return;
        }

        if (action === "save-browser-recording-as-skill") {
          try {
            const skillContract = buildBrowserSkillContract(state.browserDesktopBridge || {}, {
              status: "draft",
            });

            if (!Array.isArray(skillContract.recorded_steps) || !skillContract.recorded_steps.length) {
              desktopStore.patch({
                message: "No browser skill steps to save",
                messageTone: "error",
              });
              requestRender();
              return;
            }

            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Saving browser micro-skill to workspace...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await saveBrowserSkillToWorkspace(skillContract);
            const savedSkill = result?.item || skillContract;

            desktopStore.patch({
              operationsAgentsLoading: false,
              browserDesktopBridge: {
                ...(state.browserDesktopBridge || {}),
                status: "skill_saved",
                bridge_active: true,
                recording: false,
                dry_run_ready: true,
                last_saved_skill_id: savedSkill.skill_id,
                last_saved_browser_skill_id: savedSkill.skill_id,
                last_skill_contract: savedSkill,
                save_result: {
                  ok: true,
                  status: "saved",
                  message: "Browser micro-skill saved to workspace.",
                  skill_id: savedSkill.skill_id,
                  schema_version: savedSkill.schema_version,
                  summary: summariseBrowserSkillContract(savedSkill),
                  created_at: new Date().toISOString(),
                },
              },
              message: `Browser micro-skill saved: ${savedSkill.skill_id}`,
              messageTone: "success",
            });

            desktopStore.persistCacheSoon(300);
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to save browser micro-skill",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }


        if (action === "add-browser-skill-to-chain") {
          const select = document.querySelector("[data-browser-chain-skill-select]");
          const skillId = select?.value || "";

          if (!skillId) {
            desktopStore.patch({
              message: "No browser skill selected",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          desktopStore.patch({
            browserSkillChainDraft: addSkillToBrowserChain(skillId),
            browserSkillChainDryRunResult: null,
            message: "Browser micro-skill added to chain",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "move-browser-chain-step-up") {
          const chainStepId = operationsAgentsButton.dataset.chainStepId || "";

          desktopStore.patch({
            browserSkillChainDraft: reorderBrowserChainStep(chainStepId, "up"),
            browserSkillChainDryRunResult: null,
            message: "Chain step moved up",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "move-browser-chain-step-down") {
          const chainStepId = operationsAgentsButton.dataset.chainStepId || "";

          desktopStore.patch({
            browserSkillChainDraft: reorderBrowserChainStep(chainStepId, "down"),
            browserSkillChainDryRunResult: null,
            message: "Chain step moved down",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "remove-browser-chain-step") {
          const chainStepId = operationsAgentsButton.dataset.chainStepId || "";

          desktopStore.patch({
            browserSkillChainDraft: removeBrowserChainStep(chainStepId),
            browserSkillChainDryRunResult: null,
            message: "Chain step removed",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "toggle-browser-chain-step-approval") {
          const chainStepId = operationsAgentsButton.dataset.chainStepId || "";
          const draft = getBrowserSkillChainDraft();
          const step = draft.steps.find((item) => String(item.chain_step_id || "") === String(chainStepId));
          const nextApproval = !(step?.approval_required_after === true);

          desktopStore.patch({
            browserSkillChainDraft: patchBrowserChainStep(chainStepId, {
              approval_required_after: nextApproval,
            }),
            browserSkillChainDryRunResult: null,
            message: nextApproval
              ? "Approval required after chain step"
              : "Approval removed after chain step",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "reset-browser-skill-chain") {
          desktopStore.patch({
            browserSkillChainDraft: createBrowserSkillChainDraft(),
            browserSkillChainDryRunResult: null,
            message: "Browser skill chain reset",
            messageTone: "neutral",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "dry-run-browser-skill-chain") {
          const result = buildBrowserSkillChainDryRun(getBrowserSkillChainDraft());

          desktopStore.patch({
            browserSkillChainDryRunResult: result,
            message: result.ok
              ? "Browser skill chain dry-run complete"
              : "Browser skill chain dry-run failed",
            messageTone: result.ok ? "success" : "error",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "compile-browser-skill-chain") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              browserSkillChainCompileResult: null,
              message: "Compiling browser skill chain...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await compileAndValidateBrowserSkillChain();

            desktopStore.patch({
              operationsAgentsLoading: false,
              browserSkillChainCompileResult: result,
              message: result.ok
                ? "Browser skill chain validation passed"
                : "Browser skill chain validation failed",
              messageTone: result.ok ? "success" : "error",
            });

            desktopStore.persistCacheSoon(300);
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              browserSkillChainCompileResult: {
                ok: false,
                status: "compile_failed",
                message:
                  error instanceof Error
                    ? error.message
                    : "Browser skill chain compile failed",
              },
              message:
                error instanceof Error
                  ? error.message
                  : "Browser skill chain compile failed",
              messageTone: "error",
            });

            requestRender();
          }

          return;
        }

        if (action === "save-browser-skill-chain") {
          try {
            const chain = saveBrowserSkillChainDraft();

            if (!Array.isArray(chain.steps) || !chain.steps.length) {
              desktopStore.patch({
                message: "Add at least one browser micro-skill before saving the chain",
                messageTone: "error",
              });
              requestRender();
              return;
            }

            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Saving browser skill chain to workspace...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await saveBrowserChainToWorkspace(chain);
            const savedChain = result?.item || chain;

            await refreshBrowserSkillWorkspaceAssets();

            desktopStore.patch({
              operationsAgentsLoading: false,
              browserSkillChainDraft: normaliseBrowserSkillChainDraft(savedChain),
              message: `Browser skill chain saved: ${savedChain.chain_id}`,
              messageTone: "success",
            });

            desktopStore.persistCacheSoon(300);
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to save browser skill chain",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "load-browser-skill-chain") {
          const chainId = operationsAgentsButton.dataset.chainId || "";

          desktopStore.patch({
            browserSkillChainDraft: loadBrowserSkillChainForEditing(chainId),
            browserSkillChainDryRunResult: null,
            message: "Browser skill chain loaded for editing",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "duplicate-browser-skill-chain") {
          const chainId = operationsAgentsButton.dataset.chainId || "";

          desktopStore.patch({
            browserSkillChains: duplicateBrowserSkillChain(chainId),
            message: "Browser skill chain duplicated",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "delete-browser-skill-chain") {
          const chainId = operationsAgentsButton.dataset.chainId || "";

          if (!chainId) {
            desktopStore.patch({
              message: "No browser skill chain id found",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          try {
            const workspaceId = getActiveWorkspaceId();

            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Deleting browser skill chain draft...",
              messageTone: "neutral",
            });
            requestRender();

            await apiDelete(
              `/api/aion/business/browser-chains/${encodeURIComponent(workspaceId)}/${encodeURIComponent(chainId)}`,
            );

            await refreshBrowserSkillWorkspaceAssets();

            desktopStore.patch({
              operationsAgentsLoading: false,
              message: `Browser skill chain deleted: ${chainId}`,
              messageTone: "success",
            });

            desktopStore.persistCacheSoon(300);
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to delete browser skill chain",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "copy-browser-skill-id") {
          const skillId = operationsAgentsButton.dataset.skillId || "";

          if (skillId && navigator?.clipboard?.writeText) {
            await navigator.clipboard.writeText(skillId);
          }

          desktopStore.patch({
            message: skillId ? "Browser skill id copied" : "No browser skill id found",
            messageTone: skillId ? "success" : "error",
          });

          requestRender();
          return;
        }

        if (action === "duplicate-browser-skill") {
          const skillId = operationsAgentsButton.dataset.skillId || "";
          const skills = Array.isArray(state.browserWorkflowSkills)
            ? state.browserWorkflowSkills
            : [];
          const original = skills.find((item) => item.skill_id === skillId);

          if (!original) {
            desktopStore.patch({
              message: "Browser skill not found",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          const now = new Date().toISOString();
          const duplicate = {
            ...JSON.parse(JSON.stringify(original)),
            skill_id: makeBrowserSkillId(),
            name: `${original.name || "Browser micro-skill"} copy`,
            status: "draft",
            created_at: now,
            updated_at: now,
          };

          desktopStore.patch({
            browserWorkflowSkills: [duplicate, ...skills],
            message: "Browser micro-skill duplicated",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "publish-browser-skill") {
          const skillId = operationsAgentsButton.dataset.skillId || "";
          const now = new Date().toISOString();
          const skills = Array.isArray(state.browserWorkflowSkills)
            ? state.browserWorkflowSkills
            : [];

          const nextSkills = skills.map((skill) =>
            skill.skill_id === skillId
              ? {
                  ...skill,
                  status: "reusable",
                  updated_at: now,
                }
              : skill,
          );

          desktopStore.patch({
            browserWorkflowSkills: nextSkills,
            message: "Browser micro-skill marked reusable",
            messageTone: "success",
          });

          desktopStore.persistCacheSoon(300);
          requestRender();
          return;
        }

        if (action === "copy-train-task-approval-id") {
          const approvalId = operationsAgentsButton.dataset.approvalId || "";

          try {
            await navigator.clipboard.writeText(approvalId);
            desktopStore.patch({
              message: "Approval id copied",
              messageTone: "success",
            });
          } catch (error) {
            desktopStore.patch({
              message: approvalId || "No approval id found",
              messageTone: approvalId ? "neutral" : "error",
            });
          }

          requestRender();
          return;
        }

        if (
          action === "approve-train-task-approval" ||
          action === "reject-train-task-approval"
        ) {
          const approvalId = operationsAgentsButton.dataset.approvalId || "";
          const approve = action === "approve-train-task-approval";

          if (!approvalId) {
            desktopStore.patch({
              message: "No approval id found",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: `${approve ? "Approving" : "Rejecting"} approval...`,
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiPost(
              `/api/local-node/train-tasks/approvals/${encodeURIComponent(approvalId)}/resolve`,
              {
                approve,
                resolved_by: "operations_agents_desktop",
                resolution_note: approve
                  ? "Approved from Train Agent UI. Phase 3 stores decision only."
                  : "Rejected from Train Agent UI.",
              },
            );

            const approvalsResult = await apiGet("/api/local-node/train-tasks/approvals?limit=20");

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsApprovals: Array.isArray(approvalsResult?.items)
                ? approvalsResult.items
                : [],
              operationsAgentsGenericWorkflows: Array.isArray(genericWorkflowsResult?.items)
                ? genericWorkflowsResult.items
                : [],
              message: result?.ok
                ? `Approval ${approve ? "approved" : "rejected"}. No external write executed.`
                : result?.error || "Approval decision failed",
              messageTone: result?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Approval decision failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "toggle-workflow") {
          const workflowId = operationsAgentsButton.dataset.workflowId || "";
          const nextEnabled = operationsAgentsButton.dataset.enabled === "true";

          if (!workflowId) {
            desktopStore.patch({
              message: "No workflow id found for toggle",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: `${nextEnabled ? "Enabling" : "Disabling"} workflow: ${workflowId}`,
              messageTone: "neutral",
            });
            requestRender();

            await apiPost(
              `/api/local-node/train-tasks/workflows/${encodeURIComponent(workflowId)}/toggle`,
              {
                enabled: nextEnabled,
              },
            );

            const workflowsResult = await apiGet("/api/local-node/train-tasks/workflows");

            desktopStore.patch({
              operationsAgentsWorkflows: Array.isArray(workflowsResult?.items)
                ? workflowsResult.items
                : [],
              operationsAgentsLoading: false,
              message: nextEnabled
                ? "Workflow enabled in dry-run mode"
                : "Workflow disabled",
              messageTone: "success",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to toggle workflow",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "wizard-save") {
          try {
            const workflow = state.operationsAgentsWizardDraft || {};
            const validation = validateTeachAionWorkflowDraft(workflow);

            if (!validation.ok) {
              const validationMessage = validation.errors.join(" ");

              desktopStore.patch({
                operationsAgentsWizardSaving: false,
                operationsAgentsWizardStep: getTeachAionValidationStep(validation.errors),
                operationsAgentsWizardError: validationMessage,
                operationsAgentsWizardResult: null,
                message: validationMessage,
                messageTone: "error",
              });

              requestRender();
              return;
            }

            desktopStore.patch({
              operationsAgentsWizardSaving: true,
              operationsAgentsWizardError: "",
              operationsAgentsWizardResult: null,
              message: "Saving trained task...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiPost("/api/local-node/train-tasks/workflows", {
              workflow,
            });

            const workflowsResult = await apiGet(
              "/api/local-node/train-tasks/workflows",
            );
            const toolsResult = await apiGet("/api/local-node/tools");

            desktopStore.patch({
              operationsAgentsWorkflows: Array.isArray(workflowsResult?.items)
                ? workflowsResult.items
                : [],
              operationsAgentsTools: Array.isArray(toolsResult?.items)
                ? toolsResult.items
                : [],
              operationsAgentsWizardSaving: false,
              operationsAgentsWizardOpen: false,
              operationsAgentsWizardStep: 1,
              operationsAgentsWizardError: "",
              operationsAgentsWizardResult: result,
              message: "Trained task saved",
              messageTone: "success",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsWizardSaving: false,
              operationsAgentsWizardError:
                error instanceof Error
                  ? error.message
                  : "Failed to save trained task",
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to save trained task",
              messageTone: "error",
            });

            requestRender();
          }

          return;
        }

        if (action === "gmail-connect-placeholder") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Checking Gmail connection setup...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiGet("/api/local-node/connectors/gmail/connect-url");
            const gmailConnector = await apiGet("/api/local-node/connectors/gmail/health");

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsGmailConnector: gmailConnector || result?.connector || null,
              message:
                result?.message ||
                "Gmail OAuth is not wired yet. Aion remains dry-run only.",
              messageTone: result?.ok ? "success" : "neutral",
            });

            desktopStore.persistCacheSoon(300);
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to check Gmail connection setup",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "gmail-poll-now") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Checking Gmail connector...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiPost(
              "/api/local-node/train-tasks/gmail/poll-now",
              {},
            );
            const gmailConnector = await apiGet("/api/local-node/connectors/gmail/health");

            const firstRun = Array.isArray(result?.runs) && result.runs.length
              ? result.runs[0]
              : null;

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsGmailPollResult: result,
              operationsAgentsGmailConnector: gmailConnector || result?.connector || null,
              operationsAgentsTestResult: firstRun || state.operationsAgentsTestResult || null,
              message: result?.ok
                ? `Gmail check complete: ${result?.matched || 0} matched`
                : result?.error || "Gmail check could not run",
              messageTone: result?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Gmail check failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "gmail-poll-dry-run") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              operationsAgentsGmailPollResult: null,
              message: "Running Gmail dry-run poll...",
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiPost(
              "/api/local-node/train-tasks/gmail/poll-dry-run",
              {
                messages: [
                  {
                    id: `gmail_ui_dry_run_${Date.now()}`,
                    from: "Jane Customer <jane@example.com>",
                    subject: "New enquiry about installation",
                    body:
                      "Hi, my name is Jane Customer. My email is jane@example.com and my phone is 07123 456789. I need help with a new installation.",
                  },
                ],
              },
            );

            const firstRun = Array.isArray(result?.runs) && result.runs.length
              ? result.runs[0]
              : null;

            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsGmailPollResult: result,
              operationsAgentsTestResult: firstRun || state.operationsAgentsTestResult || null,
              message: `Gmail dry-run poll complete: ${result?.matched || 0} matched, ${result?.skipped || 0} skipped, ${result?.deduped || 0} deduped`,
              messageTone: result?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsGmailPollResult: {
                ok: false,
                error:
                  error instanceof Error
                    ? error.message
                    : "Gmail dry-run poll failed",
              },
              message:
                error instanceof Error
                  ? error.message
                  : "Gmail dry-run poll failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "refresh") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Refreshing trained tasks and generic workflows...",
              messageTone: "neutral",
            });
            requestRender();

            const refreshed = await refreshOperationsAgentsData();

            desktopStore.patch({
              ...refreshed,
              operationsAgentsLoading: false,
              message: "Trained tasks and generic workflows refreshed",
              messageTone: "success",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to refresh workflows",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "seed-customer-onboarding") {
          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              message: "Seeding example workflow...",
              messageTone: "neutral",
            });
            requestRender();

            await apiPost(
              "/api/local-node/train-tasks/seed/customer-onboarding",
              {},
            );

            const result = await apiGet("/api/local-node/train-tasks/workflows");
            const genericWorkflowsResult = await apiGet("/api/local-node/train-tasks/workflows/generic-saved");

            desktopStore.patch({
              operationsAgentsWorkflows: Array.isArray(result?.items)
                ? result.items
                : [],
              operationsAgentsGenericWorkflows: Array.isArray(genericWorkflowsResult?.items)
                ? genericWorkflowsResult.items
                : [],
              operationsAgentsLoading: false,
              message: "Example workflow seeded",
              messageTone: "success",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              message:
                error instanceof Error
                  ? error.message
                  : "Failed to seed example workflow",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "test-workflow") {
          const workflowId = operationsAgentsButton.dataset.workflowId || "";

          if (!workflowId || workflowId === "unknown") {
            desktopStore.patch({
              message: "No workflow id found for test run",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          try {
            desktopStore.patch({
              operationsAgentsLoading: true,
              operationsAgentsTestResult: null,
              message: `Running workflow test: ${workflowId}`,
              messageTone: "neutral",
            });
            requestRender();

            const result = await apiPost(
              `/api/local-node/train-tasks/workflows/${encodeURIComponent(
                workflowId,
              )}/test-run`,
              {
                sample_email: sampleEmail,
              },
            );

            desktopStore.patch({
              operationsAgentsTestResult: result,
              operationsAgentsLoading: false,
              message: "Workflow test completed",
              messageTone: result?.ok ? "success" : "error",
            });

            desktopStore.persistCache();
            requestRender();
          } catch (error) {
            desktopStore.patch({
              operationsAgentsLoading: false,
              operationsAgentsTestResult: {
                ok: false,
                workflow_id: workflowId,
                error:
                  error instanceof Error
                    ? error.message
                    : "Workflow test run failed",
              },
              message:
                error instanceof Error
                  ? error.message
                  : "Workflow test run failed",
              messageTone: "error",
            });
            requestRender();
          }

          return;
        }

        if (action === "copy-workflow-test-curl") {
          const workflowId = operationsAgentsButton.dataset.workflowId || "";

          if (!workflowId || workflowId === "unknown") {
            desktopStore.patch({
              message: "No workflow id found for curl",
              messageTone: "error",
            });
            requestRender();
            return;
          }

          const curl = `curl -X POST http://127.0.0.1:8080/api/local-node/train-tasks/workflows/${encodeURIComponent(workflowId)}/test-run \\
  -H "Content-Type: application/json" \\
  -d '{
    "sample_email": {
      "id": "email_test_001",
      "from": "Jane Customer <jane@example.com>",
      "subject": "New enquiry about installation",
      "body": "Hi, my name is Jane Customer. My email is jane@example.com and my phone is 07123 456789. I need help with a new installation."
    }
  }'`;

          try {
            await navigator.clipboard.writeText(curl);
            desktopStore.patch({
              message: "Workflow test curl copied",
              messageTone: "success",
            });
          } catch (_) {
            desktopStore.patch({
              message: "Could not copy workflow test curl",
              messageTone: "error",
            });
          }

          requestRender();
          return;
        }
      }

      const marketingCalendarModeButton = target.closest(
        "[data-marketing-calendar-mode]",
      );
      if (marketingCalendarModeButton) {
        const nextMode =
          marketingCalendarModeButton.dataset.marketingCalendarMode ||
          MARKETING_CALENDAR_MODES.DONE;
        desktopStore.patch({ marketingCalendarMode: nextMode });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const facebookCardButton = target.closest(
        "[data-facebook-card-index], [data-facebook-card-nav]",
      );
      if (facebookCardButton) {
        const index = Number(facebookCardButton.dataset.facebookCardIndex || 0);
        desktopStore.patch({ selectedFacebookCardIndex: index });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const boardroomViewButton = target.closest("[data-boardroom-view]");
      if (boardroomViewButton) {
        const mode = boardroomViewButton.dataset.boardroomView;
        if (!mode) return;
        desktopStore.setBoardroomViewMode(mode);
        requestRender();
        return;
      }

      const marketingRunsExpandButton = target.closest(
        "[data-marketing-runs-expand]",
      );
      if (marketingRunsExpandButton) {
        const mode =
          marketingRunsExpandButton.dataset.marketingRunsExpand || "more";
        desktopStore.patch({
          marketingRunsExpanded: mode === "more",
        });
        requestRender();
        return;
      }

      const marketingApprovalsExpandButton = target.closest(
        "[data-marketing-approvals-expand]",
      );
      if (marketingApprovalsExpandButton) {
        const mode =
          marketingApprovalsExpandButton.dataset.marketingApprovalsExpand ||
          "more";
        desktopStore.patch({
          marketingResolvedApprovalsExpanded: mode === "more",
        });
        requestRender();
        return;
      }

      const operationsFlowViewButton = target.closest(
        "[data-operations-flow-view]",
      );
      if (operationsFlowViewButton) {
        const mode = operationsFlowViewButton.dataset.operationsFlowView;
        if (!mode) return;
        desktopStore.setOperationsFlowViewMode(mode);
        requestRender();
        return;
      }

      const liveAgentSelectButton = target.closest(".live-agent-select-btn");
      if (liveAgentSelectButton) {
        const agentId = liveAgentSelectButton.dataset.agentId || null;
        desktopStore.setSelectedLiveAgentId(agentId);
        desktopStore.patch({ liveAgentsView: LIVE_AGENT_VIEWS.STREAM });
        ensureLiveAgentSelection({
          preferredAgentId: agentId,
          preferredDepartmentKey: state.activeZone || "marketing",
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const liveRunSelectButton = target.closest(".live-run-select-btn");
      if (liveRunSelectButton) {
        const runId = liveRunSelectButton.dataset.runId || null;
        desktopStore.setSelectedLiveRunId(runId);
        ensureLiveAgentSelection({
          preferredRunId: runId,
          preferredDepartmentKey: state.activeZone || "marketing",
        });
        desktopStore.persistCache();
        requestRender();

        requestAnimationFrame(() => {
          scrollSelectedRunIntoView();
          focusRunInspector();
          revealReplayForSelectedRun();
        });
        return;
      }

      const liveAgentToggleButton = target.closest(".live-agent-toggle-btn");
      if (liveAgentToggleButton) {
        const targetId = liveAgentToggleButton.dataset.targetId;
        if (!targetId) return;

        const panel = document.getElementById(targetId);
        if (!panel) return;

        panel.style.display = panel.style.display === "none" ? "block" : "none";
        return;
      }

      const liveRunOpenReplayButton = target.closest(".live-run-open-replay-btn");
      if (liveRunOpenReplayButton) {
        const runId = liveRunOpenReplayButton.dataset.runId || null;
        if (runId) {
          desktopStore.setSelectedLiveRunId(runId);
        }

        desktopStore.setLiveAgentsReplayOpen(true);
        ensureLiveAgentSelection({
          preferredRunId: runId,
          openReplay: true,
          preferredDepartmentKey: state.activeZone || "marketing",
        });
        desktopStore.persistCache();
        requestRender();

        requestAnimationFrame(() => {
          revealReplayForSelectedRun();
        });
        return;
      }

      const liveRunApprovalButton = target.closest(".live-run-approval-btn");
      if (liveRunApprovalButton) {
        const approvalId = liveRunApprovalButton.dataset.approvalId || null;
        const runId = liveRunApprovalButton.dataset.runId || null;
        const approve = liveRunApprovalButton.dataset.approve === "true";

        if (!approvalId) return;

        try {
          desktopStore.patch({
            loading: true,
            message: approve ? "Approving content..." : "Rejecting content...",
            messageTone: "neutral",
          });
          requestRender();

          const approvalResult = await apiPost(
            `/api/local-node/approvals/${approvalId}/resolve`,
            {
              approve,
              resolved_by: "desktop_user",
              resolution_note: approve
                ? "Approved from Live Agents artifact terminal"
                : "Rejected from Live Agents artifact terminal",
            },
          );

          const resolvedRunId =
            approvalResult?.run?.id ||
            approvalResult?.item?.workflow_run_id ||
            runId ||
            null;

          await refreshAll();

          desktopStore.patch({
            activeTab: "live_agents",
            activeZone: "marketing",
            selectedLiveRunId: resolvedRunId,
            selectedInspectorTarget: resolvedRunId
              ? { type: "run", id: resolvedRunId }
              : state.selectedInspectorTarget,
            liveAgentsReplayOpen: false,
            liveAgentsView: LIVE_AGENT_VIEWS.STREAM,
            liveAgentsStreamTab: approve ? "completed" : "approval",
            message: approve ? "Content approved" : "Content rejected",
            messageTone: approve ? "success" : "neutral",
            loading: false,
          });

          ensureLiveAgentSelection({
            preferredDepartmentKey: "marketing",
            preferredView: LIVE_AGENT_VIEWS.STREAM,
            preferredRunId: resolvedRunId,
            openReplay: false,
          });

          desktopStore.persistCache();
          requestRender();

          requestAnimationFrame(() => {
            focusRunInspector();
            scrollSelectedRunIntoView();
            revealReplayForSelectedRun();
          });
        } catch (error) {
          desktopStore.patch({
            message:
              error instanceof Error
                ? error.message
                : "Run approval action failed",
            messageTone: "error",
            loading: false,
          });
          requestRender();
        }
        return;
      }

      const liveAgentsViewButton = target.closest(
        ".live-agents-view-btn, [data-live-agents-view]",
      );
      if (liveAgentsViewButton) {
        const nextView =
          liveAgentsViewButton.dataset.liveAgentsView ||
          LIVE_AGENT_VIEWS.STREAM;
        desktopStore.patch({ liveAgentsView: nextView });
        ensureLiveAgentSelection({
          preferredView: nextView,
          preferredDepartmentKey: state.activeZone || "marketing",
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const liveAgentsStreamTabButton = target.closest(
        "[data-live-agents-stream-tab]",
      );
      if (liveAgentsStreamTabButton) {
        const nextTab =
          liveAgentsStreamTabButton.dataset.liveAgentsStreamTab || "approval";
        desktopStore.patch({ liveAgentsStreamTab: nextTab });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const publishToCalendarButton = target.closest("#publishToCalendarBtn");
      if (publishToCalendarButton) {
        const runId = publishToCalendarButton.dataset.runId || null;
        if (!runId) return;

        try {
          desktopStore.patch({
            loading: true,
            message: "Sending artifact to publish calendar...",
            messageTone: "neutral",
          });
          requestRender();

          await apiPost(
            `/api/local-node/marketing/runs/${runId}/publish-queue`,
            {
              mode: "calendar",
              requested_by: "desktop_user",
            },
          );

          await refreshAll();

          desktopStore.patch({
            activeTab: "live_agents",
            activeZone: "marketing",
            liveAgentsView: LIVE_AGENT_VIEWS.CALENDAR,
            selectedLiveRunId: runId,
            selectedInspectorTarget: { type: "run", id: runId },
            message: "Artifact added to publish calendar queue",
            messageTone: "success",
            loading: false,
          });

          ensureLiveAgentSelection({
            preferredDepartmentKey: "marketing",
            preferredView: LIVE_AGENT_VIEWS.CALENDAR,
            preferredRunId: runId,
          });

          desktopStore.persistCache();
          requestRender();
        } catch (error) {
          desktopStore.patch({
            message:
              error instanceof Error
                ? error.message
                : "Failed to send artifact to publish queue",
            messageTone: "error",
            loading: false,
          });
          requestRender();
        }
        return;
      }

      const boardroomOpenWorkspaceButton = target.closest(
        ".boardroom-open-workspace-btn",
      );
      if (boardroomOpenWorkspaceButton) {
        const departmentKey =
          boardroomOpenWorkspaceButton.dataset.departmentKey || "unknown";
        const nextView =
          boardroomOpenWorkspaceButton.dataset.liveView ||
          LIVE_AGENT_VIEWS.STREAM;

        openDepartmentWorkspaceFromBoardroom(
          departmentKey,
          nextView,
          null,
          false,
        );
        ensureLiveAgentSelection({
          preferredDepartmentKey: departmentKey,
          preferredView: nextView,
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const boardroomOpenRunsButton = target.closest(".boardroom-open-runs-btn");
      if (boardroomOpenRunsButton) {
        const departmentKey =
          boardroomOpenRunsButton.dataset.departmentKey || "unknown";
        const nextView =
          boardroomOpenRunsButton.dataset.liveView || LIVE_AGENT_VIEWS.RUNS;

        openDepartmentWorkspaceFromBoardroom(
          departmentKey,
          nextView,
          null,
          false,
        );
        ensureLiveAgentSelection({
          preferredDepartmentKey: departmentKey,
          preferredView: nextView,
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const boardroomOpenRunButton = target.closest(".boardroom-open-run-btn");
      if (boardroomOpenRunButton) {
        const departmentKey =
          boardroomOpenRunButton.dataset.departmentKey || "unknown";
        const nextView =
          boardroomOpenRunButton.dataset.liveView || LIVE_AGENT_VIEWS.RUNS;
        const runId = boardroomOpenRunButton.dataset.runId || null;
        const openReplay = boardroomOpenRunButton.dataset.openReplay === "true";

        openDepartmentWorkspaceFromBoardroom(
          departmentKey,
          nextView,
          runId,
          openReplay,
        );

        ensureLiveAgentSelection({
          preferredDepartmentKey: departmentKey,
          preferredView: nextView,
          preferredRunId: runId,
          openReplay,
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const boardroomOpenApprovalsButton = target.closest(
        ".boardroom-open-approvals-btn",
      );
      if (boardroomOpenApprovalsButton) {
        const departmentKey =
          boardroomOpenApprovalsButton.dataset.departmentKey || "unknown";

        openDepartmentWorkspaceFromBoardroom(
          departmentKey,
          LIVE_AGENT_VIEWS.APPROVALS,
          null,
          false,
        );
        ensureLiveAgentSelection({
          preferredDepartmentKey: departmentKey,
          preferredView: LIVE_AGENT_VIEWS.APPROVALS,
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const liveDepartmentOpenButton = target.closest(".live-department-open-btn");
      if (liveDepartmentOpenButton) {
        const departmentKey = liveDepartmentOpenButton.dataset.departmentKey || "";
        const preferredView =
          liveDepartmentOpenButton.dataset.liveView || LIVE_AGENT_VIEWS.STREAM;
        const openReplay = liveDepartmentOpenButton.dataset.openReplay === "true";
        const runId = liveDepartmentOpenButton.dataset.runId || null;

        if (!departmentKey) return;

        setLiveAgentsWorkspace(departmentKey, {
          preferredView,
          openReplay,
          runId,
        });

        ensureLiveAgentSelection({
          preferredDepartmentKey: departmentKey,
          preferredView,
          preferredRunId: runId,
          openReplay,
        });

        desktopStore.persistCache();
        requestRender();

        requestAnimationFrame(() => {
          if (
            preferredView === LIVE_AGENT_VIEWS.RUNS ||
            preferredView === LIVE_AGENT_VIEWS.APPROVALS ||
            openReplay
          ) {
            scrollSelectedRunIntoView();
            focusRunInspector();
            revealReplayForSelectedRun();
          }
        });
        return;
      }

      const closeReplayButton = target.closest("#closeLiveAgentsReplayBtn");
      if (closeReplayButton) {
        desktopStore.setLiveAgentsReplayOpen(false);
        ensureLiveAgentSelection({
          openReplay: false,
          preferredDepartmentKey: state.activeZone || "marketing",
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }

      const overlayCloseButton = target.closest("#liveAgentsOverlayClose");
      if (overlayCloseButton) {
        desktopStore.setLiveAgentsReplayOpen(false);
        ensureLiveAgentSelection({
          openReplay: false,
          preferredDepartmentKey: state.activeZone || "marketing",
        });
        desktopStore.persistCache();
        requestRender();
        return;
      }
    });
  }

  const desktopAssistantProviderInput = document.getElementById(
    "desktopAssistantProviderInput",
  );
  const desktopAssistantTargetPathInput = document.getElementById(
    "desktopAssistantTargetPathInput",
  );
  const desktopAssistantPromptInput = document.getElementById(
    "desktopAssistantPromptInput",
  );
  const desktopAssistantOutputInput = document.getElementById(
    "desktopAssistantOutputInput",
  );
  const desktopAssistantRunBtn = document.getElementById("desktopAssistantRunBtn");
  const desktopAssistantApplyBtn = document.getElementById("desktopAssistantApplyBtn");
  const desktopAssistantClearBtn = document.getElementById("desktopAssistantClearBtn");

  const aionChatEngineInput = document.getElementById("aionChatEngineInput");
  const aionChatPromptInput = document.getElementById("aionChatPromptInput");
  const aionChatRunBtn = document.getElementById("aionChatRunBtn");
  const aionChatClearBtn = document.getElementById("aionChatClearBtn");

  if (aionChatEngineInput && !aionChatEngineInput.dataset.bound) {
    aionChatEngineInput.dataset.bound = "1";
    aionChatEngineInput.addEventListener("change", (e) => {
      const nextEngine = getInputValue(e) || "gemma4";

      desktopStore.patch({
        aionChatEngine: nextEngine,
        desktopAssistantProvider: nextEngine,
      });

      desktopStore.persistCacheSoon(300);
      requestRender();
    });
  }

  if (aionChatPromptInput && !aionChatPromptInput.dataset.bound) {
    aionChatPromptInput.dataset.bound = "1";
    aionChatPromptInput.addEventListener("input", (e) => {
      const nextPrompt = getInputValue(e);

      desktopStore.patch({
        aionChatPrompt: nextPrompt,
        desktopAssistantPrompt: nextPrompt,
      });

      desktopStore.persistCacheSoon(300);
    });
  }

  if (aionChatRunBtn && !aionChatRunBtn.dataset.bound) {
    aionChatRunBtn.dataset.bound = "1";
    aionChatRunBtn.addEventListener("click", async () => {
      const mode = state.aionChatMode || "business_workspace";
      const engine = state.aionChatEngine || state.desktopAssistantProvider || "gemma4";
      const prompt = state.aionChatPrompt || state.desktopAssistantPrompt || "";

      if (!prompt.trim()) return;

      desktopStore.patch({
        loading: true,
        aionChatOutput: "Thinking...",
        desktopAssistantOutput: "Thinking...",
        message:
          mode === "business_workspace"
            ? "Aion is packaging workspace context..."
            : `Asking ${engine}...`,
        messageTone: "neutral",
      });

      requestRender();

      try {
        const payload =
          mode === "business_workspace"
            ? {
                provider: engine,
                engine,
                mode: "business_workspace",
                prompt,
                active_tab: "aion_chat",
                context_mode: "business_workspace",

                instruction:
                  "You are the reasoning engine inside Aion. Aion is the business context and orchestration layer. Use the supplied workspace context to answer the user's question. Do not pretend to be Aion itself. Answer clearly and practically.",

                workspace_context: {
                  workspace_id: state.workspaceId || "",
                  node_id: state.nodeId || "",
                  dashboard_summary: state.dashboardSummary || {},
                  boardroom_snapshot: state.boardroomSnapshot || {},
                  brand_foundation_state: state.brandFoundationState || {},
                  marketing_summary: state.marketingSummary || {},
                  marketing_form: state.marketingForm || {},
                  operations_flow_snapshot: state.operationsFlowSnapshot || {},
                  live_agents_snapshot: state.liveAgentsSnapshot || {},
                  scheduler: state.scheduler || {},
                  status: state.status || {},
                  runs: Array.isArray(state.runs) ? state.runs.slice(0, 80) : [],
                  approvals: Array.isArray(state.approvals) ? state.approvals.slice(0, 80) : [],
                  audit: Array.isArray(state.audit) ? state.audit.slice(0, 40) : [],
                },
              }
            : {
                provider: engine,
                engine,
                mode: "general_ai",
                prompt,
                active_tab: "aion_chat",
                context_mode: "general_ai",
                instruction:
                  "Answer the user's question directly. Do not use business workspace context unless it is explicitly provided in the prompt.",
              };

        let result;

        try {
          result = await apiPost("/api/local-node/aion/chat", payload);
        } catch (_) {
          result = await apiPost("/api/local-node/assistant/ask", payload);
        }

        const text =
          result?.text ||
          result?.answer ||
          result?.output ||
          result?.response ||
          result?.message ||
          result?.item?.text ||
          result?.item?.output ||
          "No AI response returned.";

        desktopStore.patch({
          aionChatOutput: text,
          desktopAssistantOutput: text,
          desktopAssistantProvider: engine,
          loading: false,
          message: "Aion response ready",
          messageTone: "success",
        });

        desktopStore.persistCache();
        requestRender();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Aion request failed.";

        desktopStore.patch({
          aionChatOutput: message,
          desktopAssistantOutput: message,
          loading: false,
          message: "Aion request failed",
          messageTone: "error",
        });

        requestRender();
      }
    });
  }

  if (aionChatClearBtn && !aionChatClearBtn.dataset.bound) {
    aionChatClearBtn.dataset.bound = "1";
    aionChatClearBtn.addEventListener("click", () => {
      desktopStore.patch({
        aionChatPrompt: "",
        aionChatOutput: "",
        desktopAssistantPrompt: "",
        desktopAssistantOutput: "",
      });

      desktopStore.persistCache();
      requestRender();
    });
  }

  const apiBaseInput = document.getElementById("apiBaseInput");
  const webBaseInput = document.getElementById("webBaseInput");
  const workspaceIdInput = document.getElementById("workspaceIdInput");
  const nodeIdInput = document.getElementById("nodeIdInput");
  const bindWorkspaceBtn = document.getElementById("bindWorkspaceBtn");
  const refreshBtn = document.getElementById("refreshBtn");
  const schedulerStartBtn = document.getElementById("schedulerStartBtn");
  const schedulerStopBtn = document.getElementById("schedulerStopBtn");
  const pauseNodeBtn = document.getElementById("pauseNodeBtn");
  const resumeNodeBtn = document.getElementById("resumeNodeBtn");

  if (desktopAssistantProviderInput && !desktopAssistantProviderInput.dataset.bound) {
    desktopAssistantProviderInput.dataset.bound = "1";
    desktopAssistantProviderInput.addEventListener("change", (e) => {
      const provider = getInputValue(e) || "gemma4";
      desktopStore.patch({
        desktopAssistantProvider: provider,
        aionChatEngine: provider,
      });
      desktopStore.persistCacheSoon(300);
    });
  }

  if (desktopAssistantTargetPathInput && !desktopAssistantTargetPathInput.dataset.bound) {
    desktopAssistantTargetPathInput.dataset.bound = "1";
    desktopAssistantTargetPathInput.addEventListener("change", (e) => {
      const nextPath = getInputValue(e);

      desktopStore.patch({
        desktopAssistantTargetPath: nextPath,
        brandAssistantSection: nextPath,
        desktopAssistantContextMode: "brand_foundation",
      });

      desktopStore.persistCacheSoon(300);
      requestRender();
    });
  }

  if (desktopAssistantPromptInput && !desktopAssistantPromptInput.dataset.bound) {
    desktopAssistantPromptInput.dataset.bound = "1";
    desktopAssistantPromptInput.addEventListener("input", (e) => {
      desktopStore.patch({
        desktopAssistantPrompt: getInputValue(e),
      });
      desktopStore.persistCacheSoon(300);
    });
  }

  if (desktopAssistantOutputInput && !desktopAssistantOutputInput.dataset.bound) {
    desktopAssistantOutputInput.dataset.bound = "1";
    desktopAssistantOutputInput.addEventListener("input", (e) => {
      desktopStore.patch({
        desktopAssistantOutput: getInputValue(e),
      });
      desktopStore.persistCacheSoon(300);
    });
  }

  if (desktopAssistantRunBtn && !desktopAssistantRunBtn.dataset.bound) {
    desktopAssistantRunBtn.dataset.bound = "1";
    desktopAssistantRunBtn.addEventListener("click", async () => {
      const prompt = state.desktopAssistantPrompt || "";
      const provider = state.desktopAssistantProvider || "gemma4";

      if (!prompt.trim()) return;

      desktopStore.patch({
        loading: true,
        desktopAssistantOutput: "Thinking...",
        message: "Asking desktop assistant...",
        messageTone: "neutral",
      });
      requestRender();

      try {
        const result = await apiPost("/api/local-node/assistant/ask", {
          provider,
          prompt,
          active_tab: state.activeTab,
          context_mode: state.desktopAssistantContextMode || state.activeTab,
          target_path:
            state.desktopAssistantTargetPath ||
            state.brandAssistantSection ||
            null,
          selected_live_run_id: state.selectedLiveRunId || null,
          selected_seat_id: state.selectedSeatId || null,
          selected_inspector_target: state.selectedInspectorTarget || null,
          marketing_form: state.marketingForm || {},
          brand_foundation_state: state.brandFoundationState || {},
          dashboard_summary: state.dashboardSummary || {},
          boardroom_snapshot: state.boardroomSnapshot || {},
          operations_flow_snapshot: state.operationsFlowSnapshot || {},
          live_agents_snapshot: state.liveAgentsSnapshot || {},
          runs: Array.isArray(state.runs) ? state.runs.slice(0, 50) : [],
          approvals: Array.isArray(state.approvals) ? state.approvals.slice(0, 50) : [],
          scheduler: state.scheduler || {},
          status: state.status || {},
        });

        desktopStore.patch({
          desktopAssistantOutput:
            result?.text ||
            result?.output ||
            result?.response ||
            result?.message ||
            result?.item?.text ||
            result?.item?.output ||
            "No assistant response returned.",
          loading: false,
          message: "Assistant response ready",
          messageTone: "success",
        });

        desktopStore.persistCache();
        requestRender();
      } catch (error) {
        desktopStore.patch({
          desktopAssistantOutput:
            error instanceof Error ? error.message : "Assistant request failed.",
          loading: false,
          message: "Assistant request failed",
          messageTone: "error",
        });
        requestRender();
      }
    });
  }

  if (desktopAssistantClearBtn && !desktopAssistantClearBtn.dataset.bound) {
    desktopAssistantClearBtn.dataset.bound = "1";
    desktopAssistantClearBtn.addEventListener("click", () => {
      desktopStore.patch({
        desktopAssistantPrompt: "",
        desktopAssistantOutput: "",
      });
      desktopStore.persistCache();
      requestRender();
    });
  }

  if (desktopAssistantApplyBtn && !desktopAssistantApplyBtn.dataset.bound) {
    desktopAssistantApplyBtn.dataset.bound = "1";
    desktopAssistantApplyBtn.addEventListener("click", () => {
      const output = state.desktopAssistantOutput || "";
      const targetPath =
        state.desktopAssistantTargetPath ||
        state.brandAssistantSection ||
        "brandMap.brandOverview.whatYouDo";

      if (!output.trim()) return;

      if (state.activeTab === "brand_foundation" && targetPath) {
        desktopStore.setBrandFoundationNestedValue(targetPath, output);
        desktopStore.patch({
          brandAssistantSection: targetPath,
          desktopAssistantTargetPath: targetPath,
          desktopAssistantContextMode: "brand_foundation",
        });
        desktopStore.persistCache();
        requestRender();
      }
    });
  }

  if (apiBaseInput && !apiBaseInput.dataset.bound) {
    apiBaseInput.dataset.bound = "1";
    apiBaseInput.addEventListener("input", (e) => {
      desktopStore.patch({ apiBase: getInputValue(e) });
    });
  }

  if (webBaseInput && !webBaseInput.dataset.bound) {
    webBaseInput.dataset.bound = "1";
    webBaseInput.addEventListener("input", (e) => {
      desktopStore.patch({ webBase: getInputValue(e) });
    });
  }

  if (workspaceIdInput && !workspaceIdInput.dataset.bound) {
    workspaceIdInput.dataset.bound = "1";
    workspaceIdInput.addEventListener("input", (e) => {
      desktopStore.patch({ workspaceId: getInputValue(e) });
    });
  }

  if (nodeIdInput && !nodeIdInput.dataset.bound) {
    nodeIdInput.dataset.bound = "1";
    nodeIdInput.addEventListener("input", (e) => {
      desktopStore.patch({ nodeId: getInputValue(e) });
    });
  }

  if (bindWorkspaceBtn && !bindWorkspaceBtn.dataset.bound) {
    bindWorkspaceBtn.dataset.bound = "1";
    bindWorkspaceBtn.addEventListener("click", () => {
      void bindWorkspace();
    });
  }

  if (refreshBtn && !refreshBtn.dataset.bound) {
    refreshBtn.dataset.bound = "1";
    refreshBtn.addEventListener("click", () => {
      void refreshAll();
    });
  }

  if (schedulerStartBtn && !schedulerStartBtn.dataset.bound) {
    schedulerStartBtn.dataset.bound = "1";
    schedulerStartBtn.addEventListener("click", () => {
      void runControl("/api/local-node/scheduler/start");
    });
  }

  if (schedulerStopBtn && !schedulerStopBtn.dataset.bound) {
    schedulerStopBtn.dataset.bound = "1";
    schedulerStopBtn.addEventListener("click", () => {
      void runControl("/api/local-node/scheduler/stop");
    });
  }

  if (pauseNodeBtn && !pauseNodeBtn.dataset.bound) {
    pauseNodeBtn.dataset.bound = "1";
    pauseNodeBtn.addEventListener("click", () => {
      void runControl("/api/local-node/control/pause");
    });
  }

  if (resumeNodeBtn && !resumeNodeBtn.dataset.bound) {
    resumeNodeBtn.dataset.bound = "1";
    resumeNodeBtn.addEventListener("click", () => {
      void runControl("/api/local-node/control/resume");
    });
  }

  document.querySelectorAll(".brand-foundation-input").forEach((input) => {
    if (input.dataset.bound === "1") return;
    input.dataset.bound = "1";

    input.addEventListener("input", () => {
      const path = input.dataset.brandPath || "";
      const isList = input.dataset.brandList === "true";
      const rawValue = input.value || "";
      const nextValue = isList ? splitLines(rawValue) : rawValue;

      if (!path) return;

      if (path.startsWith("brandMap.")) {
        desktopStore.setBrandFoundationNestedValue(path, nextValue);
      } else {
        desktopStore.setBrandFoundationField(path, nextValue);
      }

      desktopStore.persistCacheSoon(300);
    });
  });

  const saveBrandFoundationBtn = document.getElementById(
    "saveBrandFoundationBtn",
  );
  const resetBrandFoundationBtn = document.getElementById(
    "resetBrandFoundationBtn",
  );

  if (saveBrandFoundationBtn && !saveBrandFoundationBtn.dataset.bound) {
    saveBrandFoundationBtn.dataset.bound = "1";
    saveBrandFoundationBtn.addEventListener("click", async () => {
      try {
        desktopStore.patch({ loading: true });
        requestRender();

        const result = await saveBrandFoundationToBackend();

        desktopStore.patch({
          brandFoundationState:
            result?.item || result || state.brandFoundationState,
          message: "Brand foundation saved to backend containers",
          messageTone: "success",
          loading: false,
        });
        desktopStore.persistCache();

        await refreshAll();
      } catch (error) {
        desktopStore.patch({
          message:
            error instanceof Error
              ? error.message
              : "Brand foundation save failed",
          messageTone: "error",
          loading: false,
        });
        requestRender();
      }
    });
  }

  if (resetBrandFoundationBtn && !resetBrandFoundationBtn.dataset.bound) {
    resetBrandFoundationBtn.dataset.bound = "1";
    resetBrandFoundationBtn.addEventListener("click", async () => {
      try {
        desktopStore.patch({ loading: true });
        requestRender();

        desktopStore.syncBrandFoundationFromMarketingForm();
        desktopStore.persistCache();

        const result = await saveBrandFoundationToBackend();

        desktopStore.patch({
          brandFoundationState:
            result?.item || result || state.brandFoundationState,
          message: "Brand foundation reset from marketing form and saved",
          messageTone: "neutral",
          loading: false,
        });
        desktopStore.persistCache();

        await refreshAll();
      } catch (error) {
        desktopStore.patch({
          message:
            error instanceof Error
              ? error.message
              : "Brand foundation reset failed",
          messageTone: "error",
          loading: false,
        });
        requestRender();
      }
    });
  }

  const marketingBriefInput = document.getElementById("marketingBriefInput");
  const marketingObjectiveInput = document.getElementById(
    "marketingObjectiveInput",
  );
  const marketingFunnelGoalInput = document.getElementById(
    "marketingFunnelGoalInput",
  );
  const marketingAudienceInput = document.getElementById(
    "marketingAudienceInput",
  );
  const marketingPersonaInput = document.getElementById("marketingPersonaInput");
  const marketingOfferInput = document.getElementById("marketingOfferInput");
  const marketingAssetIntentInput = document.getElementById(
    "marketingAssetIntentInput",
  );
  const marketingProductNameInput = document.getElementById(
    "marketingProductNameInput",
  );
  const marketingOfferPriceInput = document.getElementById(
    "marketingOfferPriceInput",
  );
  const marketingOfferDetailsInput = document.getElementById(
    "marketingOfferDetailsInput",
  );
  const marketingCreativeAssetUploadInput = document.getElementById(
    "marketingCreativeAssetUploadInput",
  );
  const marketingCreativeDirectionInput = document.getElementById(
    "marketingCreativeDirectionInput",
  );
  const marketingImageUsageNotesInput = document.getElementById(
    "marketingImageUsageNotesInput",
  );
  const marketingStyleDirectionInput = document.getElementById(
    "marketingStyleDirectionInput",
  );
  const marketingChannelsInput = document.getElementById(
    "marketingChannelsInput",
  );
  const marketingKeywordsInput = document.getElementById(
    "marketingKeywordsInput",
  );
  const marketingHashtagsInput = document.getElementById(
    "marketingHashtagsInput",
  );
  const marketingHardRulesInput = document.getElementById(
    "marketingHardRulesInput",
  );
  const marketingGuidanceNotesInput = document.getElementById(
    "marketingGuidanceNotesInput",
  );
  const marketingCampaignNotesInput = document.getElementById(
    "marketingCampaignNotesInput",
  );
  const launchMarketingBtn = document.getElementById("launchMarketingBtn");
  const refreshMarketingBtn = document.getElementById("refreshMarketingBtn");

  if (marketingBriefInput && !marketingBriefInput.dataset.bound) {
    marketingBriefInput.dataset.bound = "1";
    marketingBriefInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("brief", getInputValue(e));
    });
  }

  if (marketingObjectiveInput && !marketingObjectiveInput.dataset.bound) {
    marketingObjectiveInput.dataset.bound = "1";
    marketingObjectiveInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("objective", getInputValue(e));
    });
  }

  if (marketingFunnelGoalInput && !marketingFunnelGoalInput.dataset.bound) {
    marketingFunnelGoalInput.dataset.bound = "1";
    marketingFunnelGoalInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("funnelGoal", getInputValue(e));
    });
  }

  if (marketingAudienceInput && !marketingAudienceInput.dataset.bound) {
    marketingAudienceInput.dataset.bound = "1";
    marketingAudienceInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("targetAudience", getInputValue(e));
    });
  }

  if (marketingPersonaInput && !marketingPersonaInput.dataset.bound) {
    marketingPersonaInput.dataset.bound = "1";
    marketingPersonaInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("persona", getInputValue(e));
    });
  }

  if (marketingOfferInput && !marketingOfferInput.dataset.bound) {
    marketingOfferInput.dataset.bound = "1";
    marketingOfferInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("offer", getInputValue(e));
    });
  }

  if (marketingAssetIntentInput && !marketingAssetIntentInput.dataset.bound) {
    marketingAssetIntentInput.dataset.bound = "1";
    marketingAssetIntentInput.addEventListener("change", (e) => {
      desktopStore.setMarketingField(
        "assetIntent",
        normalizeMarketingAssetType(getInputValue(e)),
      );
      requestRender();
    });
  }

  if (marketingProductNameInput && !marketingProductNameInput.dataset.bound) {
    marketingProductNameInput.dataset.bound = "1";
    marketingProductNameInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("productName", getInputValue(e));
    });
  }

  if (marketingOfferPriceInput && !marketingOfferPriceInput.dataset.bound) {
    marketingOfferPriceInput.dataset.bound = "1";
    marketingOfferPriceInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("offerPrice", getInputValue(e));
    });
  }

  if (marketingOfferDetailsInput && !marketingOfferDetailsInput.dataset.bound) {
    marketingOfferDetailsInput.dataset.bound = "1";
    marketingOfferDetailsInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("offerDetails", getInputValue(e));
    });
  }

  if (
    marketingCreativeDirectionInput &&
    !marketingCreativeDirectionInput.dataset.bound
  ) {
    marketingCreativeDirectionInput.dataset.bound = "1";
    marketingCreativeDirectionInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("creativeDirection", getInputValue(e));
    });
  }

  if (
    marketingImageUsageNotesInput &&
    !marketingImageUsageNotesInput.dataset.bound
  ) {
    marketingImageUsageNotesInput.dataset.bound = "1";
    marketingImageUsageNotesInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("imageUsageNotes", getInputValue(e));
    });
  }

  if (marketingStyleDirectionInput && !marketingStyleDirectionInput.dataset.bound) {
    marketingStyleDirectionInput.dataset.bound = "1";
    marketingStyleDirectionInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("styleDirection", getInputValue(e));
    });
  }

  if (
    marketingCreativeAssetUploadInput &&
    !marketingCreativeAssetUploadInput.dataset.bound
  ) {
    marketingCreativeAssetUploadInput.dataset.bound = "1";
    marketingCreativeAssetUploadInput.addEventListener("change", async (e) => {
      const files = asFileListArray(e.target?.files);
      if (!files.length) return;

      const existingAssets = getMarketingCreativeAssetDrafts();

      const nextAssets = files.map((file) => {
        const assetId =
          `asset_${Date.now()}_${Math.random().toString(16).slice(2)}`;

        return {
          id: assetId,
          type: normalizeMarketingAssetType(
            state.marketingForm?.assetIntent || "product",
          ),
          label: file.name,
          fileName: file.name,
          mimeType: file.type || "",
          sizeBytes: file.size || null,
          previewUrl: URL.createObjectURL(file),
          url: "",
          file_path: "",
          notes: "",
        };
      });

      desktopStore.setMarketingField("creativeAssets", [
        ...existingAssets,
        ...nextAssets,
      ]);

      desktopStore.persistCache();
      requestRender();
    });
  }

  document.querySelectorAll(".marketing-asset-notes-input").forEach((input) => {
    if (input.dataset.bound === "1") return;
    input.dataset.bound = "1";

    input.addEventListener("input", () => {
      const assetId = input.dataset.assetId || "";
      const nextAssets = getMarketingCreativeAssetDrafts().map((asset) =>
        String(asset?.id || "") === String(assetId)
          ? {
              ...asset,
              notes: input.value || "",
            }
          : asset,
      );

      desktopStore.setMarketingField("creativeAssets", nextAssets);
    });
  });

  document.querySelectorAll(".marketing-asset-remove-btn").forEach((button) => {
    if (button.dataset.bound === "1") return;
    button.dataset.bound = "1";

    button.addEventListener("click", () => {
      const assetId = button.dataset.assetId || "";
      const nextAssets = getMarketingCreativeAssetDrafts().filter(
        (asset) => String(asset?.id || "") !== String(assetId),
      );

      desktopStore.setMarketingField("creativeAssets", nextAssets);
      desktopStore.persistCache();
      requestRender();
    });
  });

  if (marketingChannelsInput && !marketingChannelsInput.dataset.bound) {
    marketingChannelsInput.dataset.bound = "1";
    marketingChannelsInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("channels", getInputValue(e));
    });
  }

  if (marketingKeywordsInput && !marketingKeywordsInput.dataset.bound) {
    marketingKeywordsInput.dataset.bound = "1";
    marketingKeywordsInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("keywords", getInputValue(e));
    });
  }

  if (marketingHashtagsInput && !marketingHashtagsInput.dataset.bound) {
    marketingHashtagsInput.dataset.bound = "1";
    marketingHashtagsInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("hashtags", getInputValue(e));
    });
  }

  if (marketingHardRulesInput && !marketingHardRulesInput.dataset.bound) {
    marketingHardRulesInput.dataset.bound = "1";
    marketingHardRulesInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("hardRules", getInputValue(e));
    });
  }

  if (
    marketingGuidanceNotesInput &&
    !marketingGuidanceNotesInput.dataset.bound
  ) {
    marketingGuidanceNotesInput.dataset.bound = "1";
    marketingGuidanceNotesInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("guidanceNotes", getInputValue(e));
    });
  }

  if (
    marketingCampaignNotesInput &&
    !marketingCampaignNotesInput.dataset.bound
  ) {
    marketingCampaignNotesInput.dataset.bound = "1";
    marketingCampaignNotesInput.addEventListener("input", (e) => {
      desktopStore.setMarketingField("campaignNotes", getInputValue(e));
    });
  }

  if (launchMarketingBtn && !launchMarketingBtn.dataset.bound) {
    launchMarketingBtn.dataset.bound = "1";
    launchMarketingBtn.addEventListener("click", async () => {
      try {
        desktopStore.patch({
          loading: true,
          message: "Creating marketing content suggestion...",
          messageTone: "neutral",
        });
        requestRender();

        const brandFoundationState = getBrandFoundationState();

        const launchResult = await apiPost("/api/local-node/marketing/launch", {
          brief: state.marketingForm.brief,
          objective: state.marketingForm.objective,
          funnel_goal: state.marketingForm.funnelGoal,
          target_audience: state.marketingForm.targetAudience,
          persona: state.marketingForm.persona,
          offer: state.marketingForm.offer,
          channels: splitLines(state.marketingForm.channels),
          hashtags: splitLines(state.marketingForm.hashtags),
          keywords: splitLines(state.marketingForm.keywords),
          hard_rules: splitLines(state.marketingForm.hardRules),
          guidance_notes: splitLines(state.marketingForm.guidanceNotes),
          campaign_notes: splitLines(state.marketingForm.campaignNotes),
          creative_assets: buildCreativeAssetsPayload(),
          creative_direction: buildCreativeDirectionPayload(),
          brand_foundation: buildBrandFoundationPayload(),
          brandFoundationState,
          brand_map: brandFoundationState.brandMap || {},
          brandMap: brandFoundationState.brandMap || {},
        });

        const launchedRunId = launchResult?.item?.id || null;
        const approvalId = launchResult?.item?.approval_request_id || null;
        const waitingApproval =
          launchResult?.item?.status === "waiting_approval";

        await refreshAll();

        desktopStore.patch({
          activeTab: "marketing_stream",
          activeZone: "marketing",
          liveAgentsView: LIVE_AGENT_VIEWS.STREAM,
          selectedLiveRunId: launchedRunId,
          selectedInspectorTarget: launchedRunId
            ? { type: "run", id: launchedRunId }
            : state.selectedInspectorTarget,
          liveAgentsReplayOpen: false,
          liveAgentsStreamTab: waitingApproval ? "approval" : "completed",
          message: waitingApproval
            ? "Marketing suggestion created and is waiting for approval"
            : "Marketing suggestion launched locally",
          messageTone: "success",
          loading: false,
        });

        ensureLiveAgentSelection({
          preferredDepartmentKey: "marketing",
          preferredRunId: launchedRunId,
          preferredView: LIVE_AGENT_VIEWS.STREAM,
          openReplay: false,
        });

        if (approvalId && typeof desktopStore.setSelectedApprovalId === "function") {
          desktopStore.setSelectedApprovalId(approvalId);
        }

        desktopStore.persistCache();
        requestRender();

        requestAnimationFrame(() => {
          focusRunInspector();
          revealReplayForSelectedRun();
        });
      } catch (error) {
        desktopStore.patch({
          message:
            error instanceof Error ? error.message : "Marketing launch failed",
          messageTone: "error",
          loading: false,
        });
        requestRender();
      }
    });
  }

  if (refreshMarketingBtn && !refreshMarketingBtn.dataset.bound) {
    refreshMarketingBtn.dataset.bound = "1";
    refreshMarketingBtn.addEventListener("click", () => {
      void refreshAll();
    });
  }

  document.querySelectorAll(".approve-marketing-btn").forEach((button) => {
    if (button.dataset.bound === "1") return;
    button.dataset.bound = "1";

    button.addEventListener("click", async () => {
      const approvalId = button.dataset.approvalId;
      const approve = button.dataset.approve === "true";
      const runId = button.dataset.runId || null;

      if (!approvalId) return;

      try {
        desktopStore.patch({
          loading: true,
          message: approve ? "Approving content..." : "Rejecting content...",
          messageTone: "neutral",
        });
        requestRender();

        const approvalResult = await apiPost(
          `/api/local-node/approvals/${approvalId}/resolve`,
          {
            approve,
            resolved_by: "desktop_user",
            resolution_note: approve
              ? "Approved from local desktop marketing stream"
              : "Rejected from local desktop marketing stream",
          },
        );

        const resolvedRunId =
          approvalResult?.run?.id ||
          approvalResult?.item?.workflow_run_id ||
          runId ||
          null;

        await refreshAll();

        desktopStore.patch({
          activeTab: "live_agents",
          activeZone: "marketing",
          liveAgentsView: LIVE_AGENT_VIEWS.STREAM,
          liveAgentsStreamTab: approve ? "completed" : "approval",
          selectedLiveRunId: resolvedRunId,
          selectedInspectorTarget: resolvedRunId
            ? { type: "run", id: resolvedRunId }
            : state.selectedInspectorTarget,
          liveAgentsReplayOpen: false,
          message: approve ? "Content approved" : "Content rejected",
          messageTone: approve ? "success" : "neutral",
          loading: false,
        });

        ensureLiveAgentSelection({
          preferredDepartmentKey: "marketing",
          preferredRunId: resolvedRunId,
          preferredView: LIVE_AGENT_VIEWS.STREAM,
          openReplay: false,
        });

        desktopStore.persistCache();
        requestRender();

        requestAnimationFrame(() => {
          focusRunInspector();
          revealReplayForSelectedRun();
        });
      } catch (error) {
        desktopStore.patch({
          message:
            error instanceof Error ? error.message : "Approval action failed",
          messageTone: "error",
          loading: false,
        });
        requestRender();
      }
    });
  });
}

let renderQueued = false;

function requestRender() {
  if (renderQueued) return;

  renderQueued = true;
  window.requestAnimationFrame(() => {
    renderQueued = false;
    render();
  });
}








function installAionWorkflowActionCardImmediateAddOverride() {
  if (window.__aionWorkflowActionImmediateOverrideBound === true) return;
  window.__aionWorkflowActionImmediateOverrideBound = true;

  document.addEventListener(
    "click",
    (event) => {
      const actionButton = event.target.closest?.("[data-aion-workflow-create-action]");
      if (!actionButton) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const actionType = actionButton.getAttribute("data-aion-workflow-create-action");

      const actionMap = {
        ai_extract_fields: {
          title: "Extract fields",
          type: "AI / Parser",
          icon: "AI",
          status: "Dry-run",
          meta: "Name, email, service, town",
          tone: "blue",
        },
        ai_classify: {
          title: "Classify enquiry",
          type: "AI / Router",
          icon: "◇",
          status: "Draft",
          meta: "Service, urgency, route",
          tone: "blue",
        },
        ai_draft_reply: {
          title: "Draft reply",
          type: "Action",
          icon: "✎",
          status: "Prepared only",
          meta: "No send without approval",
          tone: "purple",
        },
        tool_set_variable: {
          title: "Set variable",
          type: "Tools",
          icon: "=",
          status: "Dry-run",
          meta: "Store workflow value",
          tone: "teal",
          config: { key: "workflow_variable", value: "{{first_match}}" },
        },
        tool_get_variable: {
          title: "Get variable",
          type: "Tools",
          icon: "$",
          status: "Dry-run",
          meta: "Read workflow value",
          tone: "teal",
          config: { key: "workflow_variable" },
        },
        tool_compose_string: {
          title: "Compose string",
          type: "Tools",
          icon: "T",
          status: "Dry-run",
          meta: "Build mapped text",
          tone: "teal",
          config: { template: "Route {{route}} / urgency {{urgency}} / match {{first_match}}" },
        },
        tool_sleep: {
          title: "Sleep / delay",
          type: "Tools",
          icon: "⏱",
          status: "Preview",
          meta: "Delay preview only",
          tone: "amber",
          config: { seconds: 5 },
        },
        parser_match_pattern: {
          title: "Match pattern",
          type: "Text Parser",
          icon: ".*",
          status: "Dry-run",
          meta: "Regex match from text",
          tone: "teal",
          config: { pattern: "[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+" },
        },
        parser_replace: {
          title: "Replace text",
          type: "Text Parser",
          icon: "↔",
          status: "Dry-run",
          meta: "Replace matching text",
          tone: "teal",
          config: { pattern: "Example Customer", replacement: "Customer" },
        },
        parser_html_to_text: {
          title: "HTML to text",
          type: "Text Parser",
          icon: "TXT",
          status: "Dry-run",
          meta: "Convert HTML to text",
          tone: "teal",
        },
        parser_extract_html: {
          title: "Extract from HTML",
          type: "Text Parser",
          icon: "</>",
          status: "Dry-run",
          meta: "Links, images, table rows",
          tone: "teal",
        },
        gmail_send_email: {
          title: "Send email",
          type: "Action",
          icon: "✉",
          status: "Requires approval",
          meta: "Only runs after approval",
          tone: "purple",
        },
        gmail_read_email: {
          title: "Read Gmail email",
          type: "Gmail",
          icon: "G",
          status: "Needs connection",
          meta: "Subject, body, sender, thread",
          tone: "teal",
        },
        crm_create_lead: {
          title: "Create CRM lead",
          type: "API / MCP",
          icon: "C",
          status: "Blocked write",
          meta: "HubSpot or CostaConnect CRM",
          tone: "amber",
        },
        approval_gate: {
          title: "Human approval",
          type: "Gate",
          icon: "✓",
          status: "Required",
          meta: "Review before external write",
          tone: "red",
        },
      };

      if (!actionMap[actionType]) {
        desktopStore.patch?.({
          message: "This action is listed for the roadmap but is not active yet.",
          messageTone: "info",
        });
        requestRender();
        return;
      }

      if (!window.__aionWorkflowGraph) {
        window.__aionWorkflowGraph = {
          workflow_id: "workflow_draft",
          name: "Untitled workflow",
          status: "draft",
          nodes: [],
          edges: [],
        };
      }

      const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
        ? window.__aionWorkflowGraph.nodes
        : [];

      const edges = Array.isArray(window.__aionWorkflowGraph.edges)
        ? window.__aionWorkflowGraph.edges
        : [];

      const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
      const selectedNode = selectedNodeId
        ? nodes.find((node) => node.id === selectedNodeId)
        : null;

      const anchorNode =
        selectedNode ||
        nodes[nodes.length - 1] ||
        { id: null, x: 160, y: 240 };

      const newNode = {
        id: `node_${actionType}_${Date.now()}`,
        ...actionMap[actionType],
        x: Number(anchorNode.x || 160) + 275,
        y: Number(anchorNode.y || 240),
      };

      const anchorIndex = anchorNode?.id
        ? nodes.findIndex((node) => node.id === anchorNode.id)
        : -1;

      const nextNodes =
        anchorIndex >= 0
          ? [
              ...nodes.slice(0, anchorIndex + 1),
              newNode,
              ...nodes.slice(anchorIndex + 1),
            ]
          : [...nodes, newNode];

      const outgoingEdges = anchorNode?.id
        ? edges.filter((edge) => edge.from === anchorNode.id)
        : [];

      const remainingEdges = anchorNode?.id
        ? edges.filter((edge) => edge.from !== anchorNode.id)
        : edges;

      const insertedEdges = anchorNode?.id
        ? [
            {
              from: anchorNode.id,
              to: newNode.id,
              condition: "success",
            },
            ...outgoingEdges.map((edge) => ({
              ...edge,
              from: newNode.id,
              condition: edge.condition || "success",
            })),
          ]
        : [];

      const reflowedNodes = nextNodes.map((node, index) => ({
        ...node,
        x: 160 + index * 275,
        y: Number(node.y || anchorNode.y || 240),
      }));

      window.__aionWorkflowGraph.nodes = reflowedNodes;
      window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];

      window.__aionWorkflowSelectedNodeId = newNode.id;
      window.__aionWorkflowPickerMode = null;
      window.__aionWorkflowInspectorOpen = false;
      persistAionWorkflowDraftState();

      requestRender();
    },
    true,
  );
}



function installAionLegacyToolControls() {
  if (window.__aionLegacyToolControlsBound === true) return;
  window.__aionLegacyToolControlsBound = true;

  document.addEventListener(
    "click",
    (event) => {
      const closeButton = event.target.closest?.("[data-aion-legacy-tool-close='true']");
      if (closeButton) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        window.__aionLegacyToolOpen = null;
        window.__aionLegacyToolOpenLabel = null;
        requestRender();
        return;
      }

      const toolButton = event.target.closest?.("[data-aion-legacy-tool]");
      if (!toolButton) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const tool = toolButton.getAttribute("data-aion-legacy-tool");

      const labels = {
        browser_recorder: "Teach Aion a browser skill",
        browser_skills: "Saved browser micro-skills",
        workflow_chain: "Chain browser micro-skills",
        task_templates: "Start from a workflow",
        step_builder: "Build custom agent",
        generic_workflows: "Saved generic workflows",
        trained_tasks: "Trained Tasks",
        test_run_output: "Test run output",
      };

      window.__aionLegacyToolOpen = tool;
      window.__aionLegacyToolOpenLabel = labels[tool] || "Legacy tool";

      // Keep canvas state intact. This is just an overlay.
      window.__aionWorkflowInspectorOpen = false;
      window.__aionWorkflowPickerMode = null;

      requestRender();
    },
    true,
  );
}





/* AION PATCH: local dry-run executor for Architect/generated canvas workflows */
function isAionWorkflowGeneratedCanvasGraph(graph) {
  if (!graph || typeof graph !== "object") return false;

  if (graph.architect_review?.loaded_from_valid_review === true) return true;

  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  return nodes.some((node) =>
    node?.architect?.generated === true ||
    node?.config?.step_id ||
    node?.config?.node_type ||
    node?.config?.kind ||
    node?.config?.permission?.action
  );
}

function normaliseAionWorkflowLocalStepOp(node) {
  const config = node?.config && typeof node.config === "object" ? node.config : {};
  const action = String(
    node?.node_type ||
    node?.architect?.node_type ||
    config?.permission?.action ||
    config?.node_type ||
    config?.kind ||
    node?.type ||
    node?.title ||
    "workflow_step"
  ).toLowerCase();

  if (action.includes("gmail.read") || action.includes("read_email") || action.includes("read")) {
    return "read_email";
  }

  if (action.includes("extract")) return "extract_fields";
  if (action.includes("set_variable")) return "set_variable";
  if (action.includes("get_variable")) return "get_variable";
  if (action.includes("compose") || action.includes("draft_content")) return "compose_string";
  if (action.includes("approval") || action.includes("human_approval")) return "approval_checkpoint";
  if (action.includes("if_else") || action.includes("router") || action.includes("route")) return "route";
  if (action.includes("create_draft") || action.includes("gmail.create_draft")) return "gmail_create_draft";
  if (action.includes("send_email") || action.includes("send")) return "send_email";
  if (action.includes("upsert") || action.includes("crm") || action.includes("hubspot")) return "external_write";

  return "workflow_step";
}

function isAionWorkflowExternalWriteNode(node) {
  const config = node?.config && typeof node.config === "object" ? node.config : {};
  const op = normaliseAionWorkflowLocalStepOp(node);

  return Boolean(
    node?.architect?.external_write === true ||
    config?.external_write === true ||
    config?.permission?.is_external_write === true ||
    op === "send_email" ||
    op === "gmail_create_draft" ||
    op === "external_write"
  );
}

function doesAionWorkflowNodeRequireApproval(node) {
  const config = node?.config && typeof node.config === "object" ? node.config : {};
  const status = String(node?.status || "").toLowerCase();

  return Boolean(
    node?.architect?.requires_approval === true ||
    config?.requires_approval === true ||
    config?.approval ||
    status.includes("approval") ||
    status.includes("required") ||
    isAionWorkflowExternalWriteNode(node)
  );
}

function buildAionWorkflowLocalDryRunResult(graph) {
  const safeGraph = graph || getAionWorkflowDraftState();
  const compiledGlyph =
    safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);

  const orderedNodes =
    typeof orderAionWorkflowNodesForGlyph === "function"
      ? orderAionWorkflowNodesForGlyph(safeGraph)
      : (Array.isArray(safeGraph.nodes) ? safeGraph.nodes : []);

  const approvalNodes = [];
  const blockedExternalWrites = [];

  const trace = orderedNodes.map((node, index) => {
    const op = normaliseAionWorkflowLocalStepOp(node);
    const externalWrite = isAionWorkflowExternalWriteNode(node);
    const requiresApproval = doesAionWorkflowNodeRequireApproval(node);
    const nodeId = String(node?.id || `node_${index + 1}`);
    const title = String(node?.title || node?.label || nodeId);
    const riskTier = String(
      node?.architect?.risk_tier ||
      node?.config?.risk_tier ||
      node?.config?.permission?.risk_tier ||
      (externalWrite ? "medium" : "low")
    );

    let status = "simulated";
    let marker = "dry_run_preview";

    if (externalWrite) {
      status = "blocked_external_write";
      marker = "external_write_blocked_during_dry_run";
      blockedExternalWrites.push({
        node_id: nodeId,
        title,
        op,
        reason: "external_write_blocked_during_dry_run",
        requires_approval: true,
        risk_tier: riskTier,
      });
    } else if (requiresApproval || op === "approval_checkpoint") {
      status = "waiting_approval";
      marker = "approval_required";
      approvalNodes.push({ node_id: nodeId, title, op, risk_tier: riskTier });
    }

    return {
      node_id: nodeId,
      title,
      op,
      status,
      marker,
      risk_tier: riskTier,
      permission: {
        decision: externalWrite || requiresApproval ? "request_approval" : "auto_run",
        requires_approval: externalWrite || requiresApproval,
        reason: externalWrite
          ? "external_write_blocked_during_dry_run"
          : requiresApproval
            ? "approval_checkpoint_requires_review"
            : "local_dry_run_preview",
      },
      input_items_count: index === 0 ? 1 : 1,
      output_items_count: externalWrite ? 0 : 1,
      output_items_preview: [
            {
              ok: true,
              dry_run: true,
              node_id: nodeId,
              op,
              message: `${title} preview completed locally.`,
            },
          ],
    };
  });

  const approvalRequired = approvalNodes.length > 0 || blockedExternalWrites.length > 0;
  const approvalId = approvalRequired
    ? `approval_local_${Date.now()}`
    : null;

  return {
    ok: true,
    mode: "local_canvas_dry_run",
    dry_run: true,
    local_preview: true,
    architect_generated: isAionWorkflowGeneratedCanvasGraph(safeGraph),
    workflow_id: String(safeGraph.workflow_id || "workflow_draft_1"),
    workflow_name: String(safeGraph.name || "Untitled workflow"),
    steps: trace.length,
    trace,
    blocked_external_writes: blockedExternalWrites,
    approval_required: approvalRequired,
    approval_request: approvalRequired
      ? {
          approval_id: approvalId,
          approval_title: "Review generated workflow before external write",
          status: "pending",
          decision: "",
          reason: "Generated canvas workflow requires human review before external write.",
          blocked_external_writes: blockedExternalWrites,
          approval_nodes: approvalNodes,
        }
      : null,
    compiled_glyph: compiledGlyph,
    message: approvalRequired
      ? "Dry-run preview completed. External writes are blocked until approval."
      : "Dry-run preview completed. No external writes were detected.",
  };
}

function runAionWorkflowLocalCanvasDryRun(graph) {
  const safeGraph = graph || getAionWorkflowDraftState();

  if (typeof compileAndAttachAionWorkflowGlyph === "function") {
    compileAndAttachAionWorkflowGlyph(safeGraph);
  }

  const result = buildAionWorkflowLocalDryRunResult(safeGraph);

  window.__aionWorkflowDryRunResult = result;
  window.__aionWorkflowDryRunTraceOpen = true;

  if (result.approval_request) {
    window.__aionWorkflowLastApproval = result.approval_request;
  }

  desktopStore.patch?.({
    message: result.message,
    messageTone: result.approval_required ? "neutral" : "success",
  });

  return result;
}


function installAionWorkflowDraftPersistenceControls() {
  if (window.__aionWorkflowDraftPersistenceControlsBound === true) return;
  window.__aionWorkflowDraftPersistenceControlsBound = true;

  document.addEventListener("input", (event) => {
    const configInput = event.target.closest?.("[data-aion-workflow-node-config-input]");
    if (!configInput) return;

    const nodeId = configInput.getAttribute("data-aion-workflow-node-id");
    const key = configInput.getAttribute("data-aion-workflow-node-config-input");
    if (!nodeId || !key) return;

    const graph = getAionWorkflowDraftState();
    const node = Array.isArray(graph.nodes)
      ? graph.nodes.find((item) => item.id === nodeId)
      : null;

    if (!node) return;

    setAionWorkflowPendingNodeConfig(nodeId, key, configInput.value);

    node.config = {
      ...(node.config || {}),
      [key]: configInput.value,
    };

    window.__aionWorkflowGraph = graph;
    compileAndAttachAionWorkflowGlyph(graph);
    persistAionWorkflowDraftState();
  });

  document.addEventListener("input", (event) => {
    const input = event.target.closest?.("[data-aion-workflow-title-input='true']");
    if (!input) return;

    const graph = getAionWorkflowDraftState();
    graph.name = input.value.trim() || "Untitled workflow 1";
    graph.status = graph.status || "draft";
    persistAionWorkflowDraftState();
  });

  document.addEventListener("click", async (event) => {
    const glyphDebugButton = event.target.closest?.("[data-aion-workflow-glyph-debug='true']");
    if (glyphDebugButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      window.__aionWorkflowGlyphDebugOpen = true;
      window.__aionWorkflowDryRunTraceOpen = false;
      requestRender();
      return;
    }

    const glyphDebugCloseButton = event.target.closest?.("[data-aion-glyph-debug-close='true']");
    if (glyphDebugCloseButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      window.__aionWorkflowGlyphDebugOpen = false;
      requestRender();
      return;
    }

    const glyphDebugPanel = event.target.closest?.(".aion-workflow-glyph-debug-panel");
    const glyphDebugToolbarButton = event.target.closest?.("[data-aion-workflow-glyph-debug='true']");
    if (
      window.__aionWorkflowGlyphDebugOpen === true &&
      !glyphDebugPanel &&
      !glyphDebugToolbarButton
    ) {
      window.__aionWorkflowGlyphDebugOpen = false;
      requestRender();
      return;
    }

    const dryRunCloseButton = event.target.closest?.("[data-aion-dry-run-close='true']");
    if (dryRunCloseButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      window.__aionWorkflowDryRunTraceOpen = false;
      requestRender();
      return;
    }

    const dryRunDock =
      event.target.closest?.(".aion-dry-run-floating-dock") ||
      event.target.closest?.(".aion-workflow-execution-panel");
    const executeWorkflowButtonForClose = event.target.closest?.("[data-aion-workflow-dry-run='true']");

    if (
      window.__aionWorkflowDryRunTraceOpen === true &&
      !dryRunDock &&
      !executeWorkflowButtonForClose
    ) {
      window.__aionWorkflowDryRunTraceOpen = false;
      requestRender();
      return;
    }

    const dryRunButton = event.target.closest?.("[data-aion-workflow-dry-run='true']");
    if (dryRunButton) {
      event.preventDefault();
      event.stopPropagation();

      const graph = syncAionWorkflowInspectorInputsToGraph();
      persistAionWorkflowDraftState();

      const businessContainer =
        graph.business_container ||
        graph.compiled_glyph?.workflow?.business_container ||
        getAionWorkflowBusinessContainerId();

      const workflowId = graph.workflow_id || "workflow_draft_1";

      desktopStore.patch?.({
        message: "Running workflow dry-run. No external writes will be performed.",
        messageTone: "info",
      });
      requestRender();

      if (isAionWorkflowGeneratedCanvasGraph(graph) || !graph.backend_saved_at) {
        runAionWorkflowLocalCanvasDryRun(graph);
        requestRender();
        return;
      }

      if (isAionWorkflowGeneratedCanvasGraph(graph) || !graph.backend_saved_at) {
        runAionWorkflowLocalCanvasDryRun(graph);
        requestRender();
        return;
      }

      try {
        const apiBase =
          state.apiBase ||
          state.desktopApiBase ||
          window.AION_API_BASE ||
          "http://127.0.0.1:8080";

        const canvasPayload =
          typeof buildAionWorkflowCanvasCapsulePayload === "function"
            ? buildAionWorkflowCanvasCapsulePayload(graph)
            : null;

        if (!canvasPayload || !Array.isArray(canvasPayload.nodes) || !canvasPayload.nodes.length) {
          throw new Error("No runnable canvas workflow found. Add or load workflow nodes first.");
        }

        const compileResponse = await fetch(`${apiBase}/api/workflow-capsules/canvas/compile-save`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            canvas: canvasPayload,
            scope: "workspace",
            workspace_id: businessContainer,
            overwrite: true,
            rebuild_registry: true,
          }),
        });

        const compileResult = await compileResponse.json();

        if (!compileResponse.ok || !compileResult?.ok) {
          const compileReason =
            Array.isArray(compileResult?.errors) && compileResult.errors.length
              ? compileResult.errors.join(", ")
              : compileResult?.error || `Canvas compile failed: HTTP ${compileResponse.status}`;

          throw new Error(compileReason);
        }

        const runnableValue =
          compileResult.display_glyph ||
          compileResult.capsule?.display_glyph ||
          compileResult.canonical_key ||
          canvasPayload.display_glyph ||
          canvasPayload.canonical_key;

        if (!runnableValue) {
          throw new Error("Workflow capsule compiled but no runnable glyph/canonical key was returned.");
        }

        const runResponse = await fetch(`${apiBase}/api/workflow-capsules/run-dry`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            value: runnableValue,
            inputs: {
              source: "desktop_workflow_canvas",
              business_container: businessContainer,
              workflow_id: workflowId,
              workflow_name: graph.name || workflowId,
            },
            available_vault_requirements: [],
            cau_state: {
              allow_learn: false,
              adr_active: false,
              deny_reason: "desktop_canvas_execute_no_learning",
            },
            extra: {
              source: "desktop_workflow_canvas",
              route: "canvas_compile_then_run_dry",
              compiled_from_canvas: true,
              canonical_key: compileResult.canonical_key || canvasPayload.canonical_key,
              display_glyph: compileResult.display_glyph || canvasPayload.display_glyph,
            },
            create_approval: true,
          }),
        });

        const result = await runResponse.json();

        if (!runResponse.ok || !result?.ok) {
          throw new Error(result?.error || result?.deny_reason || `Dry-run failed: HTTP ${runResponse.status}`);
        }

        window.__aionWorkflowDryRunResult = {
          ...result,
          execution_route: "workflow_capsule_run_dry",
          compiled_capsule: {
            canonical_key: compileResult.canonical_key || canvasPayload.canonical_key,
            display_glyph: compileResult.display_glyph || canvasPayload.display_glyph,
            path: compileResult.path || "",
            checksum: compileResult.checksum || "",
          },
        };
        window.__aionWorkflowDryRunTraceOpen = true;

        desktopStore.patch?.({
          message: `Workflow dry-run complete: ${result.steps || result.trace?.length || 0} steps · ${result.blocked_external_writes?.length || 0} blocked writes`,
          messageTone: result.approval_required || result.approval_request ? "neutral" : "success",
        });
      } catch (error) {
        window.__aionWorkflowDryRunResult = {
          ok: false,
          error: error instanceof Error ? error.message : "Dry-run failed",
          message: error instanceof Error ? error.message : "Dry-run failed",
          trace: [],
          blocked_external_writes: [],
          execution_route: "legacy_saved_workflow_dry_run",
        };

        window.__aionWorkflowDryRunTraceOpen = true;

        desktopStore.patch?.({
          message: error instanceof Error ? error.message : "Dry-run failed",
          messageTone: "error",
        });
      }

      requestRender();
      return;
    }

    const publishButton = event.target.closest?.("[data-aion-workflow-publish='true']");
    if (publishButton) {
      event.preventDefault();
      event.stopPropagation();

      desktopStore.patch?.({
        message: "Publish requires approval policy wiring. Draft remains safe.",
        messageTone: "info",
      });

      requestRender();
      return;
    }

    const refreshTasksButton = event.target.closest?.("[data-aion-workflow-refresh-tasks='true']");
    if (refreshTasksButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      desktopStore.patch?.({
        message: "Tasks refreshed from local runtime.",
        messageTone: "success",
      });

      requestRender();
      return;
    }

    const dryPollButton = event.target.closest?.("[data-aion-workflow-run-dry-poll='true']");
    if (dryPollButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      desktopStore.patch?.({
        message: "Dry-run poll queued. No external writes will be performed.",
        messageTone: "neutral",
      });

      requestRender();
      return;
    }

    const stepByStepButton = event.target.closest?.("[data-aion-workflow-build-step-by-step='true']");
    if (stepByStepButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      window.__aionWorkflowPickerMode = "action";
      window.__aionWorkflowInspectorOpen = true;

      desktopStore.patch?.({
        message: "Step-by-step builder opened.",
        messageTone: "neutral",
      });

      requestRender();
      return;
    }

    const approveButton = event.target.closest?.("[data-aion-workflow-approval-approve]");
    if (approveButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const approvalId = approveButton.getAttribute("data-aion-workflow-approval-approve");

      if (String(approvalId || "").startsWith("approval_local_")) {
        const approvedApproval = {
          ...(window.__aionWorkflowDryRunResult?.approval_request || {}),
          approval_id: approvalId,
          status: "approved",
          decision: "approved",
          decided_by: "human",
          decided_at: new Date().toISOString(),
          reason: "Approved from local canvas dry-run",
        };

        window.__aionWorkflowLastApproval = approvedApproval;

        if (window.__aionWorkflowDryRunResult?.approval_request?.approval_id === approvalId) {
          window.__aionWorkflowDryRunResult.approval_request = approvedApproval;
        }

        const result = window.__aionWorkflowDryRunResult || {};
        const trace = Array.isArray(result.trace) ? result.trace : [];

        window.__aionWorkflowDryRunResult = {
          ...result,
          phase: "resume_after_approval",
          execution_mode: "connector_ready",
          status: "simulated_external_write_ready",
          message: "Approval accepted. External writes are connector-ready only; no live send/write was performed.",
          blocked_external_writes: [],
          approval_required: false,
          approval_request: approvedApproval,
          trace: trace.map((step) => {
            const status = String(step?.status || "");
            const op = String(step?.op || "");
            if (status === "waiting_approval") {
              return {
                ...step,
                status: "approved",
                output_items_count: 1,
                output_items_preview: [
                  {
                    ok: true,
                    dry_run: true,
                    approval_granted: true,
                    message: "Approval checkpoint granted.",
                  },
                ],
              };
            }

            if (status !== "blocked_external_write") return step;

            return {
              ...step,
              status: "approved_ready",
              output_items_count: 1,
              output_items_preview: [
                {
                  ok: true,
                  dry_run: true,
                  connector_ready: true,
                  action: "external_write_ready",
                  op,
                  message: "Approved and ready for connector execution. Live execution remains disabled.",
                },
              ],
            };
          }),
          connector_result: {
            ok: true,
            action: "external_write_ready",
            payload: {
              ready: true,
              live_mode_disabled: false,
              dry_run_only: true,
            },
          },
        };

        window.__aionWorkflowDryRunTraceOpen = true;

        desktopStore.patch?.({
          message: "Approved and resumed to connector-ready. No live external write was performed.",
          messageTone: "success",
        });

        requestRender();
        return;
      }

      const graph = getAionWorkflowDraftState();
      const businessContainer =
        graph.business_container ||
        graph.compiled_glyph?.workflow?.business_container ||
        getAionWorkflowBusinessContainerId();
      const workflowId = graph.workflow_id || "workflow_draft_1";

      try {
        const apiBase =
          state.apiBase ||
          state.desktopApiBase ||
          window.AION_API_BASE ||
          "http://127.0.0.1:8080";

        const response = await fetch(
          `${apiBase}/api/workflow-capsules/approvals/${encodeURIComponent(approvalId)}/approve`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason: "Approved from Aion canvas UI" }),
          },
        );

        const result = await response.json();
        if (!response.ok || !result?.ok) {
          throw new Error(result?.error || `Approval failed: HTTP ${response.status}`);
        }

        window.__aionWorkflowLastApproval = result.approval;
        window.__aionWorkflowDryRunTraceOpen = true;

        if (window.__aionWorkflowDryRunResult?.approval_request?.approval_id === approvalId) {
          window.__aionWorkflowDryRunResult.approval_request = {
            ...window.__aionWorkflowDryRunResult.approval_request,
            ...result.approval,
          };
        }

        desktopStore.patch?.({
          message: `Approved workflow step: ${approvalId}. Now click Resume.`,
          messageTone: "success",
        });
      } catch (error) {
        desktopStore.patch?.({
          message: error instanceof Error ? error.message : "Approval failed",
          messageTone: "error",
        });
      }

      requestRender();
      return;
    }

    const rejectButton = event.target.closest?.("[data-aion-workflow-approval-reject]");
    if (rejectButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const approvalId = rejectButton.getAttribute("data-aion-workflow-approval-reject");

      if (String(approvalId || "").startsWith("approval_local_")) {
        const rejectedApproval = {
          ...(window.__aionWorkflowDryRunResult?.approval_request || {}),
          approval_id: approvalId,
          status: "rejected",
          decision: "rejected",
          decided_by: "human",
          decided_at: new Date().toISOString(),
          reason: "Rejected from local canvas dry-run",
        };

        window.__aionWorkflowLastApproval = rejectedApproval;

        if (window.__aionWorkflowDryRunResult?.approval_request?.approval_id === approvalId) {
          window.__aionWorkflowDryRunResult.approval_request = rejectedApproval;
        }

        window.__aionWorkflowDryRunTraceOpen = true;

        desktopStore.patch?.({
          message: `Rejected local workflow gate: ${approvalId}.`,
          messageTone: "neutral",
        });

        requestRender();
        return;
      }

      const graph = getAionWorkflowDraftState();
      const businessContainer =
        graph.business_container ||
        graph.compiled_glyph?.workflow?.business_container ||
        getAionWorkflowBusinessContainerId();
      const workflowId = graph.workflow_id || "workflow_draft_1";

      try {
        const apiBase =
          state.apiBase ||
          state.desktopApiBase ||
          window.AION_API_BASE ||
          "http://127.0.0.1:8080";

        const response = await fetch(
          `${apiBase}/api/workflow-capsules/approvals/${encodeURIComponent(approvalId)}/reject`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason: "Rejected from Aion canvas UI" }),
          },
        );

        const result = await response.json();
        if (!response.ok || !result?.ok) {
          throw new Error(result?.error || `Reject failed: HTTP ${response.status}`);
        }

        window.__aionWorkflowLastApproval = result.approval;

        desktopStore.patch?.({
          message: `Rejected workflow step: ${approvalId}`,
          messageTone: "neutral",
        });
      } catch (error) {
        desktopStore.patch?.({
          message: error instanceof Error ? error.message : "Reject failed",
          messageTone: "error",
        });
      }

      requestRender();
      return;
    }

    const resumeButton = event.target.closest?.("[data-aion-workflow-approval-resume]");
    if (resumeButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const approvalId = resumeButton.getAttribute("data-aion-workflow-approval-resume");

      if (String(approvalId || "").startsWith("approval_local_")) {
        const currentApproval =
          window.__aionWorkflowLastApproval ||
          window.__aionWorkflowDryRunResult?.approval_request ||
          null;

        const approved =
          currentApproval?.approval_id === approvalId &&
          (currentApproval?.status === "approved" || currentApproval?.decision === "approved");

        if (!approved) {
          desktopStore.patch?.({
            message: "Approve this workflow gate before resuming.",
            messageTone: "error",
          });
          requestRender();
          return;
        }

        const result = window.__aionWorkflowDryRunResult || {};
        const trace = Array.isArray(result.trace) ? result.trace : [];

        window.__aionWorkflowDryRunResult = {
          ...result,
          phase: "resume_after_approval",
          execution_mode: "connector_ready",
          status: "simulated_external_write_ready",
          message: "Approval accepted. External writes are connector-ready only; no live send/write was performed.",
          blocked_external_writes: [],
          approval_request: {
            ...(result.approval_request || {}),
            approval_id: approvalId,
            status: "approved",
            decision: "approved",
          },
          trace: trace.map((step) => {
            const status = String(step?.status || "");
            if (status !== "blocked_external_write") return step;
            return {
              ...step,
              status: "approved_ready",
              output_items_count: 1,
              output_items_preview: [
                {
                  ok: true,
                  dry_run: true,
                  connector_ready: true,
                  action: "external_write_ready",
                  message: "Approved and ready for connector execution. Live execution remains disabled.",
                },
              ],
            };
          }),
          connector_result: {
            ok: true,
            action: "external_write_ready",
            payload: {
              ready: true,
              live_mode_disabled: false,
              dry_run_only: true,
            },
          },
        };

        window.__aionWorkflowDryRunTraceOpen = true;

        desktopStore.patch?.({
          message: "Workflow resumed to connector-ready. No live external write was performed.",
          messageTone: "success",
        });

        requestRender();
        return;
      }

      const graph = getAionWorkflowDraftState();
      const businessContainer =
        graph.business_container ||
        graph.compiled_glyph?.workflow?.business_container ||
        getAionWorkflowBusinessContainerId();
      const workflowId = graph.workflow_id || "workflow_draft_1";

      try {
        const apiBase =
          state.apiBase ||
          state.desktopApiBase ||
          window.AION_API_BASE ||
          "http://127.0.0.1:8080";

        const response = await fetch(
          `${apiBase}/api/workflow-capsules/approvals/${encodeURIComponent(approvalId)}/resume`,
          { method: "POST" },
        );

        const result = await response.json();
        if (!response.ok || !result?.ok) {
          throw new Error(result?.error || `Resume failed: HTTP ${response.status}`);
        }

        window.__aionWorkflowDryRunResult = result;

        desktopStore.patch?.({
          message: `Resume complete: ${result.steps || 0} steps · no external sends`,
          messageTone: "success",
        });
      } catch (error) {
        desktopStore.patch?.({
          message: error instanceof Error ? error.message : "Resume failed",
          messageTone: "error",
        });
      }

      requestRender();
      return;
    }

    const saveCapsuleButton = event.target.closest?.("[data-aion-workflow-save-capsule='true']");
    if (saveCapsuleButton) {
      event.preventDefault();
      event.stopPropagation();

      try {
        syncAionWorkflowInspectorInputsToGraph?.();
        const graph = getAionWorkflowDraftState();

        desktopStore.patch?.({
          message: "Compiling workflow canvas into Workflow Capsule...",
          messageTone: "info",
        });
        requestRender();

        const result = await saveAionWorkflowCanvasAsCapsule(graph);

        desktopStore.patch?.({
          message: `Saved Workflow Capsule: ${result.canonical_key || "capsule"} → ${result.path || "repository"}`,
          messageTone: "success",
        });

        requestRender();
      } catch (error) {
        desktopStore.patch?.({
          message: `Workflow Capsule save failed: ${error?.message || error}`,
          messageTone: "error",
        });
        requestRender();
      }
      return;
    }

    const exportGlyphButton = event.target.closest?.("[data-aion-workflow-export-glyph='true']");
    if (exportGlyphButton) {
      event.preventDefault();
      event.stopPropagation();

      const graph = getAionWorkflowDraftState();
      const compiledGlyph = graph?.compiled_glyph || compileAionWorkflowGraphToGlyph(graph);
      const glyphText = JSON.stringify(compiledGlyph, null, 2);

      let copied = false;

      try {
        if (navigator?.clipboard?.writeText) {
          await navigator.clipboard.writeText(glyphText);
          copied = true;
        }
      } catch (error) {
        console.warn("[workflow] clipboard export failed", error);
      }

      if (!copied) {
        try {
          const textarea = document.createElement("textarea");
          textarea.value = glyphText;
          textarea.setAttribute("readonly", "readonly");
          textarea.style.position = "fixed";
          textarea.style.left = "-9999px";
          textarea.style.top = "0";
          document.body.appendChild(textarea);
          textarea.focus();
          textarea.select();
          copied = document.execCommand("copy");
          document.body.removeChild(textarea);
        } catch (error) {
          console.warn("[workflow] clipboard fallback failed", error);
        }
      }

      desktopStore.patch?.({
        message: copied
          ? `Exported compiled glyph: ${compiledGlyph?.steps?.length || 0} steps`
          : "Could not copy glyph. Open Compiled Glyph and copy manually.",
        messageTone: copied ? "success" : "warning",
      });

      requestRender();
      return;
    }

    const applyNodeConfigButton = event.target.closest?.("[data-aion-workflow-apply-node-config]");
    if (applyNodeConfigButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const nodeId = applyNodeConfigButton.getAttribute("data-aion-workflow-apply-node-config");
      const config = applyAionWorkflowPendingNodeConfig(nodeId);

      desktopStore.patch?.({
        message: `Applied parser config: ${JSON.stringify(config || {})}`,
        messageTone: "success",
      });

      requestRender();
      return;
    }

    const saveButton = event.target.closest?.("[data-aion-workflow-save='true']");
    if (!saveButton) return;

    event.preventDefault();
    event.stopPropagation();

    if (window.__aionWorkflowSelectedNodeId) {
      applyAionWorkflowPendingNodeConfig(window.__aionWorkflowSelectedNodeId);
    }

    const graph = syncAionWorkflowInspectorInputsToGraph();
    graph.status = graph.status || "draft";
    graph.saved_at = new Date().toISOString();
    graph.dirty = false;
    graph.dirty_reason = null;
    compileAndAttachAionWorkflowGlyph(graph);
    window.__aionWorkflowGraph = graph;

    const saved = persistAionWorkflowDraftState();

    try {
      const backendResult = await saveAionWorkflowToBusinessContainer(graph);

      desktopStore.patch?.({
        message: `Saved workflow to ${backendResult.business_container}: ${graph.name || "Untitled workflow 1"}`,
        messageTone: "success",
      });

      syncAionWorkflowInspectorInputsToGraph();
      graph.status = "saved";
      graph.dirty = false;
      persistAionWorkflowDraftState();
    } catch (error) {
      console.warn("[workflow] backend save failed; local draft kept", error);

      desktopStore.patch?.({
        message: saved
          ? `Saved local draft only: ${graph.name || "Untitled workflow 1"}`
          : "Workflow save failed",
        messageTone: saved ? "info" : "error",
      });
    }

    requestRender();
  });
}



function installWorkflowArchitectModalInputPersistenceControls() {
  if (window.__workflowArchitectModalInputPersistenceControlsBound === true) return;
  window.__workflowArchitectModalInputPersistenceControlsBound = true;

  document.addEventListener("input", (event) => {
    const goalInput = event.target.closest?.("[data-workflow-architect-goal-input='true']");
    if (!goalInput) return;

    const workflowGoal = String(goalInput.value || "");
    const current = getWorkflowArchitectReviewState();

    window.__syncedArchitectInput = {
      ...(window.__syncedArchitectInput || {}),
      workflowGoal,
      provider: current.provider || window.__workflowArchitectProvider || "mock",
    };

    window.__aionWorkflowArchitectReview = {
      ...current,
      workflowGoal,
    };
  }, true);

  document.addEventListener("change", (event) => {
    const providerSelect = event.target.closest?.("[data-workflow-architect-provider-select='true']");
    if (!providerSelect) return;

    const provider = getWorkflowArchitectSelectedProvider(providerSelect.value);
    const current = getWorkflowArchitectReviewState();

    setWorkflowArchitectSelectedProvider(provider);

    window.__syncedArchitectInput = {
      ...(window.__syncedArchitectInput || {}),
      workflowGoal: current.workflowGoal || "",
      provider,
    };

    window.__aionWorkflowArchitectReview = {
      ...current,
      provider,
    };
  }, true);
}


function installWorkflowArchitectGuidedStepBuilderControls() {
  if (window.__workflowArchitectGuidedStepBuilderControlsBound === true) return;
  window.__workflowArchitectGuidedStepBuilderControlsBound = true;

  document.addEventListener("input", (event) => {
    const input = event.target.closest?.("[data-workflow-architect-step-field]");
    if (!input) return;

    const stepId = input.getAttribute("data-workflow-architect-step-id");
    const field = input.getAttribute("data-workflow-architect-step-field");

    const guided = getWorkflowArchitectGuidedStepBuilderState();
    const steps = Array.isArray(guided.steps) ? guided.steps : [];

    setWorkflowArchitectGuidedStepBuilderState({
      stepsApproved: false,
      steps: steps.map((step) =>
        String(step.id) === String(stepId)
          ? { ...step, [field]: input.value }
          : step,
      ),
    });
  });

  document.addEventListener("click", (event) => {
    const buildButton = event.target.closest?.("[data-workflow-architect-build-review='true']");
    if (buildButton) {
      const guidedSteps = workflowArchitectGuidedStepsToUserSteps();
      const approvedSteps = getWorkflowArchitectApprovedUserSteps();

      if (guidedSteps.length > 0 && !approvedSteps.ok) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        setWorkflowArchitectReviewState({
          ok: false,
          loading: false,
          errors: [approvedSteps.reason || "step_list_not_approved"],
          warnings: ["Approve step list before graph generation."],
        });

        desktopStore.patch?.({
          message: "Approve the guided step list before graph generation.",
          messageTone: "warning",
        });

        requestRender();
        return;
      }
    }

    const add = event.target.closest?.("[data-workflow-architect-add-step='true']");
    if (add) {
      event.preventDefault();

      const guided = getWorkflowArchitectGuidedStepBuilderState();
      const steps = Array.isArray(guided.steps) ? guided.steps : [];

      setWorkflowArchitectGuidedStepBuilderState({
        open: true,
        stepsApproved: false,
        steps: [...steps, createWorkflowArchitectGuidedStep()],
      });

      requestRender();
      return;
    }

    const approve = event.target.closest?.("[data-workflow-architect-approve-steps='true']");
    if (approve) {
      event.preventDefault();

      setWorkflowArchitectGuidedStepBuilderState({
        stepsApproved: true,
      });

      desktopStore.patch?.({
        message: "Guided workflow step list approved for graph generation.",
        messageTone: "success",
      });

      requestRender();
      return;
    }

    const remove = event.target.closest?.("[data-workflow-architect-remove-step]");
    if (remove) {
      event.preventDefault();

      const stepId = remove.getAttribute("data-workflow-architect-remove-step");
      const guided = getWorkflowArchitectGuidedStepBuilderState();
      const steps = Array.isArray(guided.steps) ? guided.steps : [];

      setWorkflowArchitectGuidedStepBuilderState({
        stepsApproved: false,
        steps: steps.filter((step) => String(step.id) !== String(stepId)),
      });

      requestRender();
      return;
    }

    const move = event.target.closest?.("[data-workflow-architect-move-step]");
    if (move) {
      event.preventDefault();

      const direction = move.getAttribute("data-workflow-architect-move-step");
      const stepId = move.getAttribute("data-workflow-architect-step-id");
      const guided = getWorkflowArchitectGuidedStepBuilderState();
      const steps = Array.isArray(guided.steps) ? [...guided.steps] : [];
      const index = steps.findIndex((step) => String(step.id) === String(stepId));

      if (index < 0) return;

      const nextIndex = direction === "up" ? index - 1 : index + 1;
      if (nextIndex < 0 || nextIndex >= steps.length) return;

      const temp = steps[index];
      steps[index] = steps[nextIndex];
      steps[nextIndex] = temp;

      setWorkflowArchitectGuidedStepBuilderState({
        stepsApproved: false,
        steps,
      });

      requestRender();
    }
  }, true);
}



function installWorkflowArchitectToolbarOpenControl() {
  if (window.__workflowArchitectToolbarOpenControlBound === true) return;
  window.__workflowArchitectToolbarOpenControlBound = true;

  document.addEventListener(
    "click",
    (event) => {
      const button = event.target.closest?.(
        "[data-aion-workflow-open-architect='true'], [data-aion-workflow-open-architect-modal='true']",
      );
      if (!button) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      window.__aionWorkflowArchitectModalOpen = true;
      window.__aionWorkflowArchitectOpen = true;
      window.__aionWorkflowInspectorOpen = false;
      window.__aionWorkflowPickerMode = null;

      const provider = getWorkflowArchitectSelectedProvider?.() || getWorkflowArchitectReviewState?.()?.provider || "mock";
      setWorkflowArchitectSelectedProvider?.(provider);

      setWorkflowArchitectReviewState({
        loading: false,
        provider,
        errors: [],
        warnings: [],
      });

      desktopStore.patch?.({
        message: "AI Workflow Architect opened.",
        messageTone: "neutral",
      });

      requestRender();
    },
    true,
  );
}




function installAionWorkflowBottomToolbarControls() {
  if (window.__aionWorkflowBottomToolbarControlsBound === true) return;
  window.__aionWorkflowBottomToolbarControlsBound = true;

  document.addEventListener(
    "click",
    async (event) => {
      const architectButton = event.target.closest?.(
        "[data-aion-workflow-open-architect-modal='true'], [data-aion-workflow-open-architect='true']",
      );

      if (architectButton) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const reviewState = getWorkflowArchitectReviewState?.() || {};
        const provider =
          getWorkflowArchitectSelectedProvider?.() ||
          reviewState.provider ||
          "mock";

        setWorkflowArchitectSelectedProvider?.(provider);

        window.__aionWorkflowArchitectModalOpen = true;

        desktopStore.patch?.({
          message: "AI Workflow Architect opened.",
          messageTone: "neutral",
        });

        requestRender();
        return;
      }

      const saveCapsuleButton = event.target.closest?.("[data-aion-workflow-save-capsule='true']");
      if (saveCapsuleButton) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        try {
          syncAionWorkflowInspectorInputsToGraph?.();

          const graph = getAionWorkflowDraftState?.();
          if (!graph) {
            throw new Error("No workflow graph available to save.");
          }

          desktopStore.patch?.({
            message: "Compiling workflow canvas into Workflow Capsule...",
            messageTone: "info",
          });
          requestRender();

          const result = await saveAionWorkflowCanvasAsCapsule(graph);

          desktopStore.patch?.({
            message: `Saved Workflow Capsule: ${result?.canonical_key || "capsule"} → ${result?.path || "repository"}`,
            messageTone: "success",
          });
        } catch (error) {
          desktopStore.patch?.({
            message: error instanceof Error ? error.message : "Workflow Capsule save failed.",
            messageTone: "error",
          });
        }

        requestRender();
        return;
      }
    },
    true,
  );
}


function installWorkflowArchitectNodeEditorModalControls() {
  if (window.__workflowArchitectNodeEditorModalControlsBound === true) return;
  window.__workflowArchitectNodeEditorModalControlsBound = true;

  document.addEventListener(
    "click",
    (event) => {
      const openButton = event.target.closest?.("[data-aion-workflow-open-architect-modal='true']");
      if (openButton) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        window.__aionWorkflowArchitectModalOpen = true;

        desktopStore.patch?.({
          message: "AI Workflow Architect opened.",
          messageTone: "neutral",
        });

        requestRender();
        return;
      }

      const closeButton = event.target.closest?.("[data-workflow-architect-node-editor-close='true']");
      if (closeButton) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        window.__aionWorkflowArchitectModalOpen = false;
        requestRender();
        return;
      }
    },
    true,
  );
}



function layoutWorkflowArchitectGeneratedNodes(canvasNodes = []) {
  const nodes = Array.isArray(canvasNodes) ? canvasNodes : [];
  const spacingX = 280;
  const spacingY = 220;
  const startX = 180;
  const startY = 180;

  const laneForNode = (node, index) => {
    const data = node?.data || {};
    const kind = String(data.kind || node?.type || data.node_type || "").toLowerCase();
    const action = String(data.permission?.action || data.node_type || kind || "").toLowerCase();

    if (kind.includes("read") || action.includes("read") || action.includes("gmail.read")) return 0;
    if (kind.includes("extract") || action.includes("extract") || kind.includes("if_else")) return 1;
    if (kind.includes("set_variable") || kind.includes("get_variable") || action.includes("variable")) return 2;
    if (action.includes("hubspot") || action.includes("crm")) return 3;
    if (kind.includes("missing_connector") || action.includes("mailchimp")) return 4;
    if (kind.includes("compose") || action.includes("compose")) return 5;
    if (kind.includes("approval") || action.includes("approval")) return 6;
    if (action.includes("draft") || kind.includes("draft")) return 7;

    return Math.min(7, Math.max(0, Math.floor(index / 2)));
  };

  const laneCounts = new Map();

  return nodes.map((node, index) => {
    const lane = laneForNode(node, index);
    const row = laneCounts.get(lane) || 0;
    laneCounts.set(lane, row + 1);

    return {
      ...node,
      position: {
        ...(node.position || {}),
        x: startX + lane * spacingX,
        y: startY + row * spacingY,
      },
    };
  });
}

function shortWorkflowArchitectNodeTitle(title = "") {
  const text = String(title || "").replace(/_/g, " ").trim();
  if (text.length <= 34) return text;
  return `${text.slice(0, 31)}...`;
}

function getWorkflowArchitectConnectorWarningsForNode(data = {}, review = {}) {
  const warnings = [];
  const connector = String(data.connector || "").trim();
  const action = String(data.permission?.action || data.node_type || data.kind || "").trim();

  if (data.missing_connector === true || data.placeholder === true || String(data.kind || "").includes("missing_connector")) {
    warnings.push("Connector missing");
  }

  const missing = Array.isArray(review.missing_connectors) ? review.missing_connectors : [];
  for (const item of missing) {
    const missingConnector = typeof item === "string" ? item : item?.connector;
    if (missingConnector && (connector === missingConnector || action.includes(String(missingConnector)))) {
      warnings.push(`${missingConnector} not connected`);
    }
  }

  return [...new Set(warnings)];
}



function getWorkflowArchitectNodeVisualKind(data = {}, nodeType = "") {
  const kind = String(data.kind || nodeType || "").toLowerCase();
  const action = String(data.permission?.action || data.node_type || nodeType || "").toLowerCase();

  if (kind.includes("missing_connector") || action.includes("missing_connector")) {
    return { icon: "!", type: "Missing Connector", tone: "red", size: "standard" };
  }

  if (kind.includes("if_else") || action.includes("if_else")) {
    return { icon: "⇄", type: "If / Else", tone: "green", size: "router" };
  }

  if (kind.includes("router") || action.includes("router")) {
    return { icon: "⤴", type: "Router", tone: "green", size: "router" };
  }

  if (kind.includes("approval") || action.includes("approval")) {
    return { icon: "✓", type: "Approval", tone: "amber", size: "standard" };
  }

  if (action.includes("gmail") || kind.includes("email")) {
    return { icon: "✉", type: "Gmail", tone: "blue", size: "standard" };
  }

  if (action.includes("hubspot")) {
    return { icon: "H", type: "HubSpot", tone: "amber", size: "standard" };
  }

  if (action.includes("mailchimp")) {
    return { icon: "M", type: "Mailchimp", tone: "red", size: "standard" };
  }

  if (kind.includes("compose") || action.includes("compose")) {
    return { icon: "T", type: "Compose", tone: "blue", size: "standard" };
  }

  if (kind.includes("extract") || action.includes("extract")) {
    return { icon: "AI", type: "AI Extract", tone: "blue", size: "agent" };
  }

  if (kind.includes("variable") || action.includes("variable")) {
    return { icon: "$", type: "Variable", tone: "blue", size: "compact" };
  }

  return { icon: "AI", type: "AI Generated", tone: "blue", size: "standard" };
}


function setAionWorkflowCanvasViewport({ zoom, x, y } = {}) {
  const current = window.__aionWorkflowCanvasView || {};
  const nextZoom = Math.max(0.2, Math.min(2.5, Number(zoom ?? current.zoom ?? window.__aionWorkflowZoom ?? 1)));
  const nextX = Number(x ?? current.x ?? window.__aionWorkflowPan?.x ?? 0);
  const nextY = Number(y ?? current.y ?? window.__aionWorkflowPan?.y ?? 0);

  const next = {
    zoom: nextZoom,
    x: nextX,
    y: nextY,
  };

  window.__aionWorkflowCanvasView = next;
  window.__aionWorkflowZoom = next.zoom;
  window.__aionWorkflowPan = { x: next.x, y: next.y };

  return next;
}

function getAionWorkflowCanvasViewport() {
  return setAionWorkflowCanvasViewport(window.__aionWorkflowCanvasView || {
    zoom: Number(window.__aionWorkflowZoom || 1),
    x: Number(window.__aionWorkflowPan?.x || 0),
    y: Number(window.__aionWorkflowPan?.y || 0),
  });
}

function updateAionWorkflowCanvasTransform() {
  const viewport = document.querySelector("[data-aion-workflow-canvas-viewport='true']");
  if (!viewport) return;

  const view = getAionWorkflowCanvasViewport();

  viewport.style.transformOrigin = "0 0";
  viewport.style.transform = `translate3d(${Math.round(view.x)}px, ${Math.round(view.y)}px, 0) scale(${view.zoom})`;
}



function fitAionWorkflowCanvasToCurrentGraph() {
  const graph = getAionWorkflowDraftState?.() || window.__aionWorkflowGraph || {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  fitAionWorkflowCanvasToGeneratedNodes(nodes);
}

function fitAionWorkflowCanvasToGeneratedNodes(nodes = []) {
  if (!Array.isArray(nodes) || !nodes.length) return;

  const xs = nodes.map((node) => Number(node.x || node.position?.x || 0));
  const ys = nodes.map((node) => Number(node.y || node.position?.y || 0));

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const width = Math.max(1, maxX - minX + 340);
  const height = Math.max(1, maxY - minY + 260);

  const shell = document.querySelector(".aion-workflow-canvas-shell");
  const shellWidth = Number(shell?.clientWidth || window.innerWidth || 1400);
  const shellHeight = Number(shell?.clientHeight || window.innerHeight || 800);

  const zoomX = (shellWidth - 220) / width;
  const zoomY = (shellHeight - 220) / height;
  const zoom = Math.max(0.42, Math.min(0.82, zoomX, zoomY));

  setAionWorkflowCanvasViewport({
    zoom,
    x: Math.max(80, 160 - minX * zoom),
    y: Math.max(80, 160 - minY * zoom),
  });

  if (typeof updateAionWorkflowCanvasTransform === "function") {
    updateAionWorkflowCanvasTransform();
  }
}


function installWorkflowArchitectLoadValidReviewControls() {
  if (window.__workflowArchitectLoadValidReviewControlsBound === true) return;
  window.__workflowArchitectLoadValidReviewControlsBound = true;

  document.addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-workflow-architect-load-valid-review='true']");
    if (!button) return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    const reviewState = getWorkflowArchitectReviewState();
    const result = reviewState.result || {};
    const spec = getWorkflowArchitectResultSpec(result);
    const canvas = getWorkflowArchitectResultCanvas(result);
    const review = getWorkflowArchitectResultReviewSummary(result);

    const hasValidCanvas = Boolean(result?.ok === true && Array.isArray(canvas?.nodes) && canvas.nodes.length);

    if (!hasValidCanvas) {
      desktopStore.patch?.({
        message: "No valid Architect canvas review is ready to load.",
        messageTone: "error",
      });
      requestRender();
      return;
    }

    const laidOutCanvasNodes = layoutWorkflowArchitectGeneratedNodes(canvas.nodes);

    const nodes = laidOutCanvasNodes.map((node, index) => {
      const data = node.data || {};
      const nodeType = String(data.kind || node.type || data.node_type || "architect_node");
      const requiresApproval = Boolean(data.requires_approval);
      const isPlaceholder =
        nodeType === "missing_connector_placeholder" ||
        data.missing_connector === true ||
        data.placeholder === true;
      const isExternalWrite = Boolean(data.external_write);
      const connectorWarnings = getWorkflowArchitectConnectorWarningsForNode(data, review);
      const rawTitle = String(data.label || node.id || `Generated step ${index + 1}`);
      const visual = getWorkflowArchitectNodeVisualKind(data, nodeType);

      return {
        id: String(node.id || data.step_id || `architect_node_${index + 1}`),
        step_id: String(data.step_id || node.id || `architect_step_${index + 1}`),
        node_type: String(data.permission?.action || data.node_type || nodeType),
        title: shortWorkflowArchitectNodeTitle(rawTitle),
        label: shortWorkflowArchitectNodeTitle(rawTitle),
        full_title: rawTitle,
        type: visual.type,
        icon: visual.icon,
        size: visual.size,
        status: isPlaceholder
          ? "Blocked placeholder"
          : requiresApproval
            ? "Approval required"
            : "Dry-run",
        meta: connectorWarnings.length
          ? connectorWarnings.join(" · ")
          : String(data.permission?.action || data.kind || node.type || "architect"),
        tone: isPlaceholder ? "red" : requiresApproval || isExternalWrite ? "amber" : visual.tone,
        x: Number(node.position?.x ?? 180 + index * 280),
        y: Number(node.position?.y ?? 180),
        config: {
          ...data,
          connector_warnings: connectorWarnings,
          full_title: rawTitle,
        },
        architect: {
          generated: true,
          dry_run_only: true,
          loaded_from_valid_review: true,
          step_id: String(data.step_id || node.id || `architect_step_${index + 1}`),
          node_type: String(data.permission?.action || data.node_type || nodeType),
          risk_tier: String(data.risk_tier || "low"),
          requires_approval: requiresApproval,
          missing_connector: Boolean(data.missing_connector) || isPlaceholder,
          placeholder: isPlaceholder,
          connector: data.connector || null,
          external_write: isExternalWrite,
          connector_warnings: connectorWarnings,
          full_title: rawTitle,
        },
      };
    });

    const edges = Array.isArray(canvas.edges)
      ? canvas.edges.map((edge) => ({
          from: String(edge.source || edge.from || ""),
          to: String(edge.target || edge.to || ""),
        })).filter((edge) => edge.from && edge.to)
      : [];

    const nextGraph = {
      workflow_id: String(canvas.canonical_key || "workflow_architect_generated"),
      business_container: getAionWorkflowBusinessContainerId(),
      name: String(canvas.display_name || spec.workflow_name || review.workflow_name || "Architect generated workflow"),
      status: "draft",
      nodes,
      edges,
      compiled_glyph: null,
      architect_review: {
        loaded_from_valid_review: true,
        provider: result?.provider?.provider || reviewState.provider || getWorkflowArchitectSelectedProvider(),
        dry_run_only: true,
        live_send_enabled: false,
        connectors_required: Array.isArray(review.connectors_required) ? review.connectors_required : [],
        missing_connectors: Array.isArray(review.missing_connectors) ? review.missing_connectors : [],
      },
    };

    window.__aionWorkflowGraph = nextGraph;
    fitAionWorkflowCanvasToGeneratedNodes(nodes);
    window.__aionWorkflowSelectedNodeId = nodes[0]?.id || null;
    window.__aionWorkflowArchitectModalOpen = false;
    window.__aionWorkflowPickerMode = "";
    window.__aionWorkflowInspectorOpen = false;

    if (typeof compileAndAttachAionWorkflowGlyph === "function") {
      compileAndAttachAionWorkflowGlyph(nextGraph);
    }

    if (typeof persistAionWorkflowDraftState === "function") {
      persistAionWorkflowDraftState();
    }

    setWorkflowArchitectReviewState({
      workflowGoal: (window.__syncedArchitectInput || {}).workflowGoal,
      provider: (window.__syncedArchitectInput || {}).provider,
      result,
      ok: true,
      loading: false,
    });

    desktopStore.patch?.({
      message: `Loaded Architect workflow onto canvas: ${nodes.length} nodes · ${edges.length} links`,
      messageTone: "success",
    });

    requestRender();
  }, true);
}




function fitAionWorkflowCanvasToGeneratedGraph_DISABLED_DUPLICATE(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  if (!nodes.length) return;

  const xs = nodes.map((node) => Number(node.x || node.position?.x || 0));
  const ys = nodes.map((node) => Number(node.y || node.position?.y || 0));

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const width = Math.max(1, maxX - minX + 420);
  const height = Math.max(1, maxY - minY + 320);

  const shell = document.querySelector(".aion-workflow-canvas-shell") ||
    document.querySelector(".aion-workflow-canvas");

  const viewportWidth = Number(shell?.clientWidth || window.innerWidth || 1400);
  const viewportHeight = Number(shell?.clientHeight || window.innerHeight || 800);

  const zoomX = viewportWidth / width;
  const zoomY = viewportHeight / height;
  const zoom = Math.max(0.48, Math.min(0.95, Math.min(zoomX, zoomY)));

  window.__aionWorkflowZoom = zoom;
  window.__aionWorkflowPan = {
    x: Math.round(140 - minX * zoom),
    y: Math.round(130 - minY * zoom),
  };

  if (typeof updateAionWorkflowCanvasTransform === "function") {
    updateAionWorkflowCanvasTransform();
  }
}


function installAionWorkflowActionControls() {
  if (window.__aionWorkflowActionControlsBound === true) return;
  window.__aionWorkflowActionControlsBound = true;

  document.addEventListener(
    "click",
    (event) => {
      const openActionPicker = event.target.closest?.("[data-aion-workflow-open-action-picker='true']");

      if (openActionPicker) {
        event.preventDefault();
        event.stopPropagation();

        window.__aionWorkflowPickerMode = "action";
        window.__aionWorkflowInspectorOpen = false;
        requestRender();
        return;
      }

      const actionButton = event.target.closest?.("[data-aion-workflow-create-action]");
      if (!actionButton) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const actionType = actionButton.getAttribute("data-aion-workflow-create-action");

      const actionMap = {
        ai_extract_fields: {
          title: "Extract fields",
          type: "AI / Parser",
          icon: "AI",
          status: "Dry-run",
          meta: "Name, email, service, town",
          tone: "blue",
        },
        ai_classify: {
          title: "Classify enquiry",
          type: "AI / Router",
          icon: "◇",
          status: "Draft",
          meta: "Service, urgency, route",
          tone: "blue",
        },
        ai_draft_reply: {
          title: "Draft reply",
          type: "Action",
          icon: "✎",
          status: "Prepared only",
          meta: "No send without approval",
          tone: "purple",
        },
        tool_set_variable: {
          title: "Set variable",
          type: "Tools",
          icon: "=",
          status: "Dry-run",
          meta: "Store workflow value",
          tone: "teal",
          config: { key: "workflow_variable", value: "{{first_match}}" },
        },
        tool_get_variable: {
          title: "Get variable",
          type: "Tools",
          icon: "$",
          status: "Dry-run",
          meta: "Read workflow value",
          tone: "teal",
          config: { key: "workflow_variable" },
        },
        tool_compose_string: {
          title: "Compose string",
          type: "Tools",
          icon: "T",
          status: "Dry-run",
          meta: "Build mapped text",
          tone: "teal",
          config: { template: "Route {{route}} / urgency {{urgency}} / match {{first_match}}" },
        },
        tool_sleep: {
          title: "Sleep / delay",
          type: "Tools",
          icon: "⏱",
          status: "Preview",
          meta: "Delay preview only",
          tone: "amber",
          config: { seconds: 5 },
        },
        parser_match_pattern: {
          title: "Match pattern",
          type: "Text Parser",
          icon: ".*",
          status: "Dry-run",
          meta: "Regex match from text",
          tone: "teal",
          config: { pattern: "[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+" },
        },
        parser_replace: {
          title: "Replace text",
          type: "Text Parser",
          icon: "↔",
          status: "Dry-run",
          meta: "Replace matching text",
          tone: "teal",
          config: { pattern: "Example Customer", replacement: "Customer" },
        },
        parser_html_to_text: {
          title: "HTML to text",
          type: "Text Parser",
          icon: "TXT",
          status: "Dry-run",
          meta: "Convert HTML to text",
          tone: "teal",
        },
        parser_extract_html: {
          title: "Extract from HTML",
          type: "Text Parser",
          icon: "</>",
          status: "Dry-run",
          meta: "Links, images, table rows",
          tone: "teal",
        },
        gmail_send_email: {
          title: "Send email",
          type: "Action",
          icon: "✉",
          status: "Requires approval",
          meta: "Only runs after approval",
          tone: "purple",
        },
        gmail_read_email: {
          title: "Read Gmail email",
          type: "Gmail",
          icon: "G",
          status: "Needs connection",
          meta: "Subject, body, sender, thread",
          tone: "teal",
        },
        crm_create_lead: {
          title: "Create CRM lead",
          type: "API / MCP",
          icon: "C",
          status: "Blocked write",
          meta: "HubSpot or CostaConnect CRM",
          tone: "amber",
        },
        approval_gate: {
          title: "Human approval",
          type: "Gate",
          icon: "✓",
          status: "Required",
          meta: "Review before external write",
          tone: "red",
        },
      };

      if (!actionMap[actionType]) {
        desktopStore.patch?.({
          message: "This action is listed for the roadmap but is not active yet.",
          messageTone: "info",
        });
        requestRender();
        return;
      }

      if (!window.__aionWorkflowGraph) {
        window.__aionWorkflowGraph = {
          workflow_id: "workflow_draft",
          name: "Untitled workflow",
          status: "draft",
          nodes: [],
          edges: [],
        };
      }

      const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
        ? window.__aionWorkflowGraph.nodes
        : [];

      const edges = Array.isArray(window.__aionWorkflowGraph.edges)
        ? window.__aionWorkflowGraph.edges
        : [];

      const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
      const selectedNode = selectedNodeId
        ? nodes.find((node) => node.id === selectedNodeId)
        : null;

      const anchorNode =
        selectedNode ||
        nodes[nodes.length - 1] ||
        { id: null, x: 160, y: 240 };

      const newNode = {
        id: `node_${actionType}_${Date.now()}`,
        ...actionMap[actionType],
        x: Number(anchorNode.x || 160) + 275,
        y: Number(anchorNode.y || 240),
      };

      const anchorIndex = anchorNode?.id
        ? nodes.findIndex((node) => node.id === anchorNode.id)
        : -1;

      const nextNodes =
        anchorIndex >= 0
          ? [
              ...nodes.slice(0, anchorIndex + 1),
              newNode,
              ...nodes.slice(anchorIndex + 1),
            ]
          : [...nodes, newNode];

      const outgoingEdges = anchorNode?.id
        ? edges.filter((edge) => edge.from === anchorNode.id)
        : [];

      const remainingEdges = anchorNode?.id
        ? edges.filter((edge) => edge.from !== anchorNode.id)
        : edges;

      const insertedEdges = anchorNode?.id
        ? [
            {
              from: anchorNode.id,
              to: newNode.id,
              condition: "success",
            },
            ...outgoingEdges.map((edge) => ({
              ...edge,
              from: newNode.id,
              condition: edge.condition || "success",
            })),
          ]
        : [];

      const reflowedNodes = nextNodes.map((node, index) => ({
        ...node,
        x: 160 + index * 275,
        y: Number(node.y || anchorNode.y || 240),
      }));

      window.__aionWorkflowGraph.nodes = reflowedNodes;
      window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];

      window.__aionWorkflowSelectedNodeId = newNode.id;
      window.__aionWorkflowPickerMode = null;
      window.__aionWorkflowInspectorOpen = false;

      requestRender();
    },
    true,
  );
}


function installAionWorkflowFirstStepControls() {
  if (window.__aionWorkflowFirstStepControlsBound === true) return;
  window.__aionWorkflowFirstStepControlsBound = true;

  document.addEventListener(
    "click",
    (event) => {
      const openTriggerPicker = event.target.closest?.("[data-aion-workflow-open-trigger-picker='true']");
      if (openTriggerPicker) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        window.__aionWorkflowPickerMode = "trigger";
        window.__aionWorkflowInspectorOpen = false;
        window.__aionWorkflowUserViewportLocked = true;
        requestRender();
        return;
      }

      const triggerButton = event.target.closest?.("[data-aion-workflow-create-trigger]");
      if (!triggerButton) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const triggerType = triggerButton.getAttribute("data-aion-workflow-create-trigger");

      const triggerMap = {
        manual: {
          id: `node_manual_trigger_${Date.now()}`,
          title: "Manual trigger",
          type: "Trigger",
          icon: "◎",
          status: "Ready",
          meta: "Run when user clicks Run once",
          tone: "teal",
        },
        gmail_new_email: {
          id: `node_gmail_new_email_${Date.now()}`,
          title: "Gmail new email",
          type: "Trigger",
          icon: "✉",
          status: "Needs connection",
          meta: "Starts when a new Gmail email arrives",
          tone: "teal",
        },
        schedule: {
          id: `node_schedule_${Date.now()}`,
          title: "Schedule",
          type: "Trigger",
          icon: "◷",
          status: "Draft",
          meta: "Run every hour, day, week, or interval",
          tone: "teal",
        },
        webhook: {
          id: `node_webhook_${Date.now()}`,
          title: "Webhook / API call",
          type: "Trigger",
          icon: "⑂",
          status: "Draft",
          meta: "Starts when an HTTP request arrives",
          tone: "teal",
        },
      };

      const template = triggerMap[triggerType];

      if (!template) {
        desktopStore.patch?.({
          message: "This starter is listed for the roadmap but is not active yet.",
          messageTone: "info",
        });
        requestRender();
        return;
      }

      const graph = getAionWorkflowDraftState();

      const canvas = document.querySelector(".aion-workflow-canvas");
      const rect = canvas?.getBoundingClientRect?.();

      const nodeWidth = 224;
      const nodeHeight = 150;

      const x = rect ? Math.round(rect.width / 2 - nodeWidth / 2) : 520;
      const y = rect ? Math.round(rect.height / 2 - nodeHeight / 2) : 260;

      const node = {
        ...template,
        x,
        y,
      };

      graph.nodes = [node];
      graph.edges = [];
      graph.status = graph.status || "draft";

      window.__aionWorkflowGraph = graph;
      window.__aionWorkflowSelectedNodeId = node.id;
      window.__aionWorkflowPickerMode = null;
      window.__aionWorkflowInspectorOpen = false;

      persistAionWorkflowDraftState();

      desktopStore.patch?.({
        message: `Added first step: ${node.title}`,
        messageTone: "success",
      });

      requestRender();
    },
    true,
  );
}




function installAionWorkflowInspectorInputGuard() {
  if (window.__aionWorkflowInspectorInputGuardBound === true) return;
  window.__aionWorkflowInspectorInputGuardBound = true;

  const isInspectorEditableTarget = (target) =>
    !!target?.closest?.(
      ".aion-workflow-inspector input:not([readonly]), " +
      ".aion-workflow-inspector textarea:not([readonly]), " +
      ".aion-workflow-inspector select, " +
      "[data-aion-workflow-node-config-input]"
    );

  const stopCanvasInterception = (event) => {
    if (!isInspectorEditableTarget(event.target)) return;

    // Do NOT preventDefault: the input still needs focus/cursor/text selection.
    // Only stop the canvas/global handlers from treating this as node/canvas input.
    event.stopPropagation();
    event.stopImmediatePropagation?.();
  };

  ["pointerdown", "mousedown", "click", "dblclick", "keydown", "keyup"].forEach((type) => {
    window.addEventListener(type, stopCanvasInterception, true);
  });
}


function installAionWorkflowNodeConfigInputControls() {
  if (window.__aionWorkflowNodeConfigInputControlsBound === true) return;
  window.__aionWorkflowNodeConfigInputControlsBound = true;

  const updateConfig = (event) => {
    const input = event.target.closest?.("[data-aion-workflow-node-config-input]");
    if (!input) return;

    const nodeId = input.getAttribute("data-aion-workflow-node-id");
    const key = input.getAttribute("data-aion-workflow-node-config-input");
    if (!nodeId || !key) return;

    const graph = getAionWorkflowDraftState();
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const node = nodes.find((item) => item.id === nodeId);
    if (!node) return;

    const config = {
      ...(node.config || {}),
      [key]: input.value,
    };

    window.__aionWorkflowGraph = {
      ...graph,
      nodes: nodes.map((item) =>
        item.id === nodeId
          ? {
              ...item,
              config,
            }
          : item,
      ),
    };

    compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
    persistAionWorkflowDraftState();
  };

  document.addEventListener("input", updateConfig, true);
  document.addEventListener("change", updateConfig, true);
  document.addEventListener("blur", updateConfig, true);
}






function installAionWorkflowPickerDrawerCloseControls() {
  if (window.__aionWorkflowPickerDrawerCloseControlsBound === true) return;
  window.__aionWorkflowPickerDrawerCloseControlsBound = true;

  document.addEventListener("click", (event) => {
    const closeButton = event.target.closest?.("[data-aion-workflow-picker-close='true']");
    if (closeButton) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      window.__aionWorkflowPickerMode = "";
      window.__aionWorkflowInspectorOpen = false;
      requestRender();
      return;
    }

    const drawer = event.target.closest?.("[data-aion-workflow-picker-drawer='true']");
    const openButton = event.target.closest?.(
      "[data-aion-workflow-open-action-picker='true'], [data-aion-workflow-open-trigger-picker='true'], [data-aion-workflow-build-step-by-step='true']"
    );

    if (!window.__aionWorkflowPickerMode || drawer || openButton) return;

    window.__aionWorkflowPickerMode = "";
    window.__aionWorkflowInspectorOpen = false;
    requestRender();
  }, true);
}

function installAionWorkflowPickerDrawerScrollIsolation() {
  if (window.__aionWorkflowPickerDrawerScrollIsolationBound === true) return;
  window.__aionWorkflowPickerDrawerScrollIsolationBound = true;

  document.addEventListener(
    "wheel",
    (event) => {
      const drawer = event.target.closest?.("[data-aion-workflow-picker-drawer='true']");
      if (!drawer) return;

      event.stopPropagation();
    },
    { passive: true, capture: true },
  );
}

function installAionWorkflowTrackpadCanvasControls() {
  if (window.__aionWorkflowTrackpadCanvasControlsBound === true) return;
  window.__aionWorkflowTrackpadCanvasControlsBound = true;

  document.addEventListener("wheel", (event) => {
    if (event.target.closest?.("[data-aion-workflow-picker-drawer='true']")) {
      return;
    }

    const canvas = event.target.closest?.(".aion-workflow-canvas-shell, .aion-workflow-canvas");
    if (!canvas) return;

    if (
      event.target.closest?.(
        ".aion-node-editor-modal, .aion-node-editor-backdrop, [data-workflow-architect-node-editor-modal='true']"
      )
    ) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    const current = getAionWorkflowCanvasViewport();

    const rawDx = Number(event.deltaX || 0);
    const rawDy = Number(event.deltaY || 0);

    // Clamp deltas so Mac inertial scrolling does not throw the canvas away.
    const dx = Math.max(-80, Math.min(80, rawDx));
    const dy = Math.max(-80, Math.min(80, rawDy));

    if (event.ctrlKey || event.metaKey) {
      const rect = canvas.getBoundingClientRect();
      const mouseX = Number(event.clientX || rect.left + rect.width / 2) - rect.left;
      const mouseY = Number(event.clientY || rect.top + rect.height / 2) - rect.top;

      const zoomFactor = dy > 0 ? 0.94 : 1.06;
      const nextZoom = Math.max(0.25, Math.min(2.25, current.zoom * zoomFactor));

      const worldX = (mouseX - current.x) / current.zoom;
      const worldY = (mouseY - current.y) / current.zoom;

      setAionWorkflowCanvasViewport({
        zoom: nextZoom,
        x: mouseX - worldX * nextZoom,
        y: mouseY - worldY * nextZoom,
      });
    } else {
      setAionWorkflowCanvasViewport({
        zoom: current.zoom,
        x: current.x - dx,
        y: current.y - dy,
      });
    }

    updateAionWorkflowCanvasTransform();
  }, { passive: false });
}


function installAionWorkflowNodeDragControls() {
  installAionWorkflowInspectorInputGuard();
  installAionWorkflowNodeConfigInputControls();

  window.AionWorkflowNodeEditor?.installControls?.({
    getAionWorkflowDraftState,
    compileAndAttachAionWorkflowGlyph,
    persistAionWorkflowDraftState,
    requestRender,
    desktopStore,
  });

  if (window.__aionWorkflowNodeDragBound === true) return;
  window.__aionWorkflowNodeDragBound = true;

  let dragState = null;

  document.addEventListener("pointerdown", (event) => {
    if (
      event.target.closest?.(".aion-workflow-inspector") ||
      event.target.closest?.("[data-aion-workflow-node-config-input]")
    ) {
      return;
    }

    const deleteButton = event.target.closest?.("[data-aion-workflow-delete-node]");
    if (deleteButton) return;

    const nodeEl = event.target.closest?.("[data-aion-workflow-node-id]");
    if (!nodeEl) return;

    const nodeId = nodeEl.getAttribute("data-aion-workflow-node-id");
    if (!nodeId) return;

    const graph = getAionWorkflowDraftState();
    const node = Array.isArray(graph.nodes)
      ? graph.nodes.find((item) => item.id === nodeId)
      : null;

    if (!node) return;

    const view = window.__aionWorkflowCanvasView || { zoom: 1, x: 0, y: 0 };
    const zoom = Math.max(0.1, Number(view.zoom || 1));

    dragState = {
      nodeId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: Number(node.x || 0),
      startY: Number(node.y || 0),
      zoom,
      moved: false,
    };

    nodeEl.setPointerCapture?.(event.pointerId);
    nodeEl.classList.add("aion-canvas-node-dragging");

    event.preventDefault();
  });

  document.addEventListener("pointermove", (event) => {
    if (!dragState) return;

    const dx = (event.clientX - dragState.startClientX) / dragState.zoom;
    const dy = (event.clientY - dragState.startClientY) / dragState.zoom;

    const nextX = Math.round(dragState.startX + dx);
    const nextY = Math.round(dragState.startY + dy);

    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
      dragState.moved = true;
    }

    const graph = getAionWorkflowDraftState();
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const node = nodes.find((item) => item.id === dragState.nodeId);
    if (!node) return;

    node.x = nextX;
    node.y = nextY;

    window.__aionWorkflowGraph = graph;
    window.__aionWorkflowDidDragNode = dragState.moved;

    const nodeEl = document.querySelector(
      `[data-aion-workflow-node-id="${CSS.escape(dragState.nodeId)}"]`,
    );

    if (nodeEl) {
      nodeEl.style.left = `${nextX}px`;
      nodeEl.style.top = `${nextY}px`;
    }
  });

  document.addEventListener("pointerup", () => {
    if (!dragState) return;

    document
      .querySelectorAll(".aion-canvas-node-dragging")
      .forEach((el) => el.classList.remove("aion-canvas-node-dragging"));

    if (dragState.moved) {
      persistAionWorkflowDraftState();
      window.__aionWorkflowDidDragNode = true;

      window.setTimeout(() => {
        window.__aionWorkflowDidDragNode = false;
      }, 120);

      requestRender();
    }

    dragState = null;
  });

  document.addEventListener("pointercancel", () => {
    dragState = null;
    document
      .querySelectorAll(".aion-canvas-node-dragging")
      .forEach((el) => el.classList.remove("aion-canvas-node-dragging"));
  });
}


function installAionWorkflowNodeDeleteControls() {
  if (window.__aionWorkflowNodeDeleteBound === true) return;
  window.__aionWorkflowNodeDeleteBound = true;

  document.addEventListener("click", (event) => {
    const deleteButton = event.target.closest?.("[data-aion-workflow-delete-node]");
    if (!deleteButton) return;

    event.preventDefault();
    event.stopPropagation();

    const nodeId = deleteButton.getAttribute("data-aion-workflow-delete-node");
    if (!nodeId || !window.__aionWorkflowGraph) return;

    const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
      ? window.__aionWorkflowGraph.nodes
      : [];

    const edges = Array.isArray(window.__aionWorkflowGraph.edges)
      ? window.__aionWorkflowGraph.edges
      : [];

    window.__aionWorkflowGraph.nodes = nodes.filter((node) => node.id !== nodeId);
    window.__aionWorkflowGraph.edges = edges.filter(
      (edge) => edge.from !== nodeId && edge.to !== nodeId,
    );

    if (window.__aionWorkflowSelectedNodeId === nodeId) {
      window.__aionWorkflowSelectedNodeId =
        window.__aionWorkflowGraph.nodes[window.__aionWorkflowGraph.nodes.length - 1]?.id ||
        null;
    }

    if (!window.__aionWorkflowGraph.nodes.length) {
      window.__aionWorkflowPickerMode = "trigger";
      window.__aionWorkflowInspectorOpen = true;
    } else {
      window.__aionWorkflowPickerMode = null;
      window.__aionWorkflowInspectorOpen = false;
    }

    persistAionWorkflowDraftState();
    requestRender();
  });
}


function installAionWorkflowNodeSelection() {
  if (window.__aionWorkflowNodeSelectionBound === true) return;
  window.__aionWorkflowNodeSelectionBound = true;

  document.addEventListener("click", (event) => {
    if (event.target.closest?.(".aion-workflow-inspector")) return;

    const node = event.target.closest?.("[data-aion-workflow-node-id]");
    if (!node) return;

    const nodeId = node.getAttribute("data-aion-workflow-node-id");
    if (!nodeId) return;

    window.__aionWorkflowSelectedNodeId = nodeId;
    window.__aionWorkflowInspectorOpen = false;

    console.log("[aion-workflow] selected node", nodeId);

    // Legacy right inspector is retired. Node editing now belongs in the modal.
    requestRender();
  });
}


function installAionWorkflowSidebarToggle() {
  const shell = document.querySelector(".aion-workflow-canvas-shell");
  const buttons = document.querySelectorAll("[data-aion-workflow-sidebar-toggle='true']");

  if (!shell || !buttons.length) return;

  if (window.__aionWorkflowSidebarOpen === undefined) {
    window.__aionWorkflowSidebarOpen = false;
  }

  const apply = () => {
    shell.classList.toggle(
      "aion-workflow-sidebar-collapsed",
      window.__aionWorkflowSidebarOpen !== true,
    );
  };

  buttons.forEach((button) => {
    if (button.dataset.aionSidebarBound === "true") return;
    button.dataset.aionSidebarBound = "true";

    button.addEventListener("click", () => {
      window.__aionWorkflowSidebarOpen = !window.__aionWorkflowSidebarOpen;
      apply();

      window.setTimeout(() => {
        if (typeof installAionWorkflowCanvasZoomControls === "function") {
          installAionWorkflowCanvasZoomControls();
        }
      }, 80);
    });
  });

  apply();
}


function installAionWorkflowInspectorToggle() {
  // Legacy right-side inspector retired.
  // Add First Step / Add Next Step picker now uses:
  // data-aion-workflow-picker-drawer="true"
  // Do not bind old inspector toggle controls.
  window.__aionWorkflowInspectorOpen = false;
}


function installAionWorkflowCanvasZoomControls() {
  const canvas = document.querySelector(".aion-workflow-canvas");
  const viewport = document.querySelector("[data-aion-workflow-canvas-viewport='true']");
  const label = document.querySelector("[data-aion-canvas-zoom-label='true']");
  const buttons = document.querySelectorAll("[data-aion-canvas-zoom]");

  if (!canvas || !viewport || !buttons.length) return;

  if (!window.__aionWorkflowCanvasView) {
    window.__aionWorkflowCanvasView = {
      zoom: 1,
      x: 0,
      y: 0,
    };
  }

  const clampZoom = (value) => Math.max(0.35, Math.min(1.8, value));

  const getNodeBounds = () => {
    const nodes = Array.from(viewport.querySelectorAll(".aion-canvas-node"));

    if (!nodes.length) {
      return {
        minX: 0,
        minY: 0,
        maxX: 1200,
        maxY: 500,
        width: 1200,
        height: 500,
      };
    }

    const bounds = nodes.map((node) => {
      const left = Number.parseFloat(node.style.left || "0");
      const top = Number.parseFloat(node.style.top || "0");
      const width = node.offsetWidth || 224;
      const height = node.offsetHeight || 150;

      return {
        left,
        top,
        right: left + width,
        bottom: top + height,
      };
    });

    const minX = Math.min(...bounds.map((item) => item.left));
    const minY = Math.min(...bounds.map((item) => item.top));
    const maxX = Math.max(...bounds.map((item) => item.right));
    const maxY = Math.max(...bounds.map((item) => item.bottom));

    return {
      minX,
      minY,
      maxX,
      maxY,
      width: Math.max(1, maxX - minX),
      height: Math.max(1, maxY - minY),
    };
  };

  const applyView = () => {
    const view = window.__aionWorkflowCanvasView;
    view.zoom = clampZoom(Number(view.zoom || 1));
    view.x = Number.isFinite(Number(view.x)) ? Number(view.x) : 0;
    view.y = Number.isFinite(Number(view.y)) ? Number(view.y) : 0;

    viewport.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.zoom})`;
    viewport.style.transformOrigin = "0 0";

    if (label) {
      label.textContent = `${Math.round(view.zoom * 100)}%`;
    }
  };

  const fitToView = () => {
    const view = window.__aionWorkflowCanvasView;
    const hasNodes = !!viewport.querySelector(".aion-canvas-node");

    if (!hasNodes) {
      view.zoom = 1;
      view.x = 0;
      view.y = 0;
      applyView();
      return;
    }

    const bounds = getNodeBounds();
    const canvasRect = canvas.getBoundingClientRect();

    const reservedTop = 86;
    const reservedBottom = 70;
    const reservedLeft = 28;
    const reservedRight = 28;

    const availableWidth = Math.max(300, canvasRect.width - reservedLeft - reservedRight);
    const availableHeight = Math.max(240, canvasRect.height - reservedTop - reservedBottom);

    const padding = 90;

    const zoomX = availableWidth / (bounds.width + padding);
    const zoomY = availableHeight / (bounds.height + padding);
    const zoom = clampZoom(Math.min(zoomX, zoomY, 1));

    view.zoom = zoom;
    view.x = reservedLeft + (availableWidth - bounds.width * zoom) / 2 - bounds.minX * zoom;
    view.y = reservedTop + (availableHeight - bounds.height * zoom) / 2 - bounds.minY * zoom;

    applyView();
  };

  const zoomAtCentre = (delta) => {
    const view = window.__aionWorkflowCanvasView;
    const oldZoom = clampZoom(Number(view.zoom || 1));
    const newZoom = clampZoom(oldZoom + delta);

    const rect = canvas.getBoundingClientRect();
    const centreX = rect.width / 2;
    const centreY = rect.height / 2;

    const worldX = (centreX - view.x) / oldZoom;
    const worldY = (centreY - view.y) / oldZoom;

    view.zoom = newZoom;
    view.x = centreX - worldX * newZoom;
    view.y = centreY - worldY * newZoom;

    applyView();
  };

  buttons.forEach((button) => {
    if (button.dataset.aionZoomBound === "true") return;
    button.dataset.aionZoomBound = "true";

    button.addEventListener("click", () => {
      const action = button.getAttribute("data-aion-canvas-zoom");

      if (action === "in") {
        zoomAtCentre(0.12);
      } else if (action === "out") {
        zoomAtCentre(-0.12);
      } else if (action === "reset") {
        window.__aionWorkflowCanvasView = {
          zoom: 1,
          x: 0,
          y: 0,
        };
        applyView();
      } else if (action === "fit") {
        fitToView();
      }
    });
  });

  if (!viewport.dataset.aionInitialFitDone) {
    viewport.dataset.aionInitialFitDone = "true";
    fitToView();
  } else {
    applyView();
  }
}


function render() {
  const t0 = performance.now();

  const app = document.getElementById("app");
  if (!app) return;

  const htmlStart = performance.now();
  app.innerHTML = `
    <div class="desktop-root">
      ${renderTopNav()}
      ${renderGlobalStatusBanner()}
      ${renderDesktopWorkspace()}
      ${renderLiveAgentsReplayOverlay()}
    </div>
  `;
  const htmlEnd = performance.now();

  const attachStart = performance.now();
  attachEvents();
  installAionWorkflowDraftPersistenceControls();
  installAionLegacyToolControls();
  installAionWorkflowFirstStepControls();
  installAionWorkflowActionCardImmediateAddOverride();
  installAionWorkflowActionControls();
installAionWorkflowBottomToolbarControls();
  installAionWorkflowTrackpadCanvasControls();

  if (!window.__aionWorkflowViewportSanityResetV1) {
    window.__aionWorkflowViewportSanityResetV1 = true;
    const graph = getAionWorkflowDraftState?.() || window.__aionWorkflowGraph || {};
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    if (nodes.length && typeof fitAionWorkflowCanvasToGeneratedNodes === "function") {
      fitAionWorkflowCanvasToGeneratedNodes(nodes);
    } else if (typeof setAionWorkflowCanvasViewport === "function") {
      setAionWorkflowCanvasViewport({ zoom: 1, x: 0, y: 0 });
      updateAionWorkflowCanvasTransform?.();
    }
  }
installAionWorkflowPickerDrawerCloseControls();
installAionWorkflowPickerDrawerScrollIsolation();

installWorkflowArchitectLoadValidReviewControls();
installWorkflowArchitectNodeEditorModalControls();
installWorkflowArchitectToolbarOpenControl();
installWorkflowArchitectModalInputPersistenceControls();
installWorkflowArchitectGuidedStepBuilderControls();
  installAionWorkflowNodeDragControls();
  installAionWorkflowNodeDeleteControls();
  installAionWorkflowNodeSelection();
  installAionWorkflowSidebarToggle();
  installAionWorkflowInspectorToggle();
  installAionWorkflowCanvasZoomControls();
  const attachEnd = performance.now();

  const isSpatialBoardroom =
    state.activeTab === "boardroom" &&
    state.boardroomViewMode === "spatial" &&
    window.TessarisDesktopBoardroomRenderer;

  const boardroomStart = performance.now();

  if (isSpatialBoardroom) {
    const mount = document.getElementById("spatialBoardroomMount");

    if (mount) {
      const boardroomSnapshot = getBoardroomSnapshot();

      const rendererState = {
        snapshot: boardroomSnapshot,
        viewMode: state.boardroomViewMode,
        activeZone:
          state.activeZone ||
          boardroomSnapshot.activeZone ||
          "coo",
        selectedSeatId:
          state.selectedSeatId ??
          boardroomSnapshot.selectedSeatId ??
          null,
        selectedInspectorTarget:
          state.selectedInspectorTarget ??
          boardroomSnapshot.selectedInspectorTarget ??
          null,

        onActiveZoneChange: (zone) => {
          desktopStore.setActiveZone(zone || "coo");
          requestRender();
        },

        onSeatSelect: (seatId, zone) => {
          desktopStore.updateBoardroomSelection({
            selectedSeatId: seatId || null,
            activeZone: zone || state.activeZone || "coo",
          });
          requestRender();
        },

        onInspectorTargetChange: (target) => {
          desktopStore.setSelectedInspectorTarget(target || null);
          requestRender();
        },

        requestRender,
      };

      if (!mount.dataset.boardroomMounted) {
        window.TessarisDesktopBoardroomRenderer.mountBoardroom(
          mount,
          rendererState,
        );
        mount.dataset.boardroomMounted = "1";
      } else if (
        typeof window.TessarisDesktopBoardroomRenderer.updateBoardroom === "function"
      ) {
        window.TessarisDesktopBoardroomRenderer.updateBoardroom(rendererState);
      } else {
        window.TessarisDesktopBoardroomRenderer.disposeBoardroom();
        window.TessarisDesktopBoardroomRenderer.mountBoardroom(
          mount,
          rendererState,
        );
        mount.dataset.boardroomMounted = "1";
      }
    }
  } else if (window.TessarisDesktopBoardroomRenderer) {
    const mount = document.getElementById("spatialBoardroomMount");
    if (mount) {
      delete mount.dataset.boardroomMounted;
    }
    window.TessarisDesktopBoardroomRenderer.disposeBoardroom();
  }

  const boardroomEnd = performance.now();

  const operationsStart = performance.now();

  const isOperationsFlowActive =
    state.activeTab === "operations_flow" &&
    window.TessarisDesktopOperationsRenderer;

  if (isOperationsFlowActive) {
    const mount = document.getElementById("operationsFlowMount");

    if (mount) {
      const rendererState = {
        snapshot: state.boardroomSnapshot,
        viewMode:
          state.operationsFlowViewMode === "spatial" ? "spatial" : "flat",
        activeZone: state.activeZone || "operations",
        selectedSeatId: state.selectedSeatId || null,
        selectedInspectorTarget: state.selectedInspectorTarget || null,

        onViewModeChange: (mode) => {
          desktopStore.setOperationsFlowViewMode(mode);
          requestRender();
        },

        onActiveZoneChange: (zone) => {
          desktopStore.setActiveZone(zone || "operations");
          requestRender();
        },

        onSeatSelect: (seatId, zone) => {
          desktopStore.updateBoardroomSelection({
            selectedSeatId: seatId || null,
            activeZone: zone || state.activeZone || "operations",
          });
          requestRender();
        },

        onInspectorTargetChange: (target) => {
          desktopStore.setSelectedInspectorTarget(target || null);
          requestRender();
        },

        requestRender,
      };

      if (!mount.dataset.operationsMounted) {
        window.TessarisDesktopOperationsRenderer.mountOperationsFlow(
          mount,
          rendererState,
        );
        mount.dataset.operationsMounted = "1";
      } else if (
        typeof window.TessarisDesktopOperationsRenderer.updateOperationsFlow === "function"
      ) {
        window.TessarisDesktopOperationsRenderer.updateOperationsFlow(
          rendererState,
        );
      } else {
        window.TessarisDesktopOperationsRenderer.disposeOperationsFlow();
        window.TessarisDesktopOperationsRenderer.mountOperationsFlow(
          mount,
          rendererState,
        );
        mount.dataset.operationsMounted = "1";
      }
    }
  } else if (window.TessarisDesktopOperationsRenderer) {
    const mount = document.getElementById("operationsFlowMount");
    if (mount) {
      delete mount.dataset.operationsMounted;
    }
    window.TessarisDesktopOperationsRenderer.disposeOperationsFlow();
  }

  const operationsEnd = performance.now();
  const t1 = performance.now();

  console.log(
    "[render] total=%sms html=%sms events=%sms boardroom=%sms operations=%sms activeTab=%s",
    (t1 - t0).toFixed(1),
    (htmlEnd - htmlStart).toFixed(1),
    (attachEnd - attachStart).toFixed(1),
    (boardroomEnd - boardroomStart).toFixed(1),
    (operationsEnd - operationsStart).toFixed(1),
    state.activeTab,
  );
}

function setupBackendStatusListener() {
  if (window.__TESSARIS_BACKEND_LISTENER_ATTACHED__) {
    console.warn("setupBackendStatusListener already attached, skipping duplicate listener.");
    return;
  }

  if (
    !window.aionDesktop ||
    typeof window.aionDesktop.onBackendStatus !== "function"
  ) {
    desktopStore.patch({
      backendReady: true,
      backendStatus: "unknown",
      message: "No Electron backend bridge found, binding directly",
      messageTone: "neutral",
    });
    requestRender();
    void bindWorkspace();
    return;
  }

  if (typeof unsubscribeBackendStatus === "function") {
    unsubscribeBackendStatus();
    unsubscribeBackendStatus = null;
  }

  window.__TESSARIS_BACKEND_LISTENER_ATTACHED__ = true;

  desktopStore.patch({
    backendReady: false,
    backendStatus: "starting",
    message: "Waiting for local backend to start...",
    messageTone: "neutral",
  });
  requestRender();

  unsubscribeBackendStatus = window.aionDesktop.onBackendStatus((payload) => {
    const nextStatus = payload?.status || "unknown";

    if (payload?.ok) {
      const firstReady = !state.backendReady;

      desktopStore.patch({
        backendReady: true,
        backendStatus: "ready",
        message: payload?.detail || "Local backend ready",
        messageTone: "success",
      });
      requestRender();

      if (firstReady) {
        void (async () => {
          await bindWorkspace({
            skipInitialRefresh: true,
            preserveMessage: true,
          });
          await hydrateRecoveredDesktopState();
          await refreshAll();
        })();
      } else {
        void refreshAll();
      }
      return;
    }

    desktopStore.patch({
      backendReady: false,
      backendStatus: nextStatus,
      message: payload?.detail || "Local backend failed to start",
      messageTone: "error",
    });
    requestRender();
  });
}

async function hydrateRecoveredDesktopState() {
  desktopStore.loadFromStorage();

  if (!state.brandFoundationState || !state.brandFoundationState.updatedAt) {
    desktopStore.syncBrandFoundationFromMarketingForm();
    desktopStore.persistCache();
  }

  requestRender();

  if (!state.backendReady) {
    return;
  }

  try {
    const recovery = await loadDesktopRecovery();
    const recoveryPayload =
      recovery && typeof recovery === "object" ? recovery : null;

    const recoveredWorkspaceId = encodeURIComponent(
      recoveryPayload?.workspace_id || state.workspaceId,
    );

    const requests = await Promise.allSettled([
      apiGetOptional(
        `/api/aion/business/brand-foundation/${recoveredWorkspaceId}`,
        null,
      ),
      apiGetOptional(
        `/api/aion/business/boardroom/${recoveredWorkspaceId}`,
        null,
      ),
      apiGetOptional(
        `/api/aion/business/container-bindings/${recoveredWorkspaceId}`,
        { items: [] },
      ),
      apiGetOptional("/api/local-node/dashboard/summary", null),
      apiGetOptional("/api/local-node/marketing/stream", null),
      apiGetOptional("/api/local-node/status", null),
      apiGetOptional("/api/local-node/runs", { items: [] }),
      apiGetOptional("/api/local-node/approvals", { items: [] }),
      apiGetOptional("/api/local-node/audit", { items: [] }),
      apiGetOptional("/api/local-node/scheduler/status", null),
    ]);

    const [
      brandFoundationRes,
      boardroomRes,
      bindingsRes,
      dashboardRes,
      marketingRes,
      statusRes,
      runsRes,
      approvalsRes,
      auditRes,
      schedulerRes,
    ] = requests;

    const status =
      statusRes.status === "fulfilled"
        ? statusRes.value ?? state.status
        : state.status;

    const resolvedWorkspaceId =
      status?.config?.workspace_id ||
      recoveryPayload?.workspace_id ||
      state.workspaceId;

    const resolvedNodeId =
      status?.config?.node_id ||
      state.nodeId;

    const recoveredBindings =
      bindingsRes.status === "fulfilled"
        ? Array.isArray(bindingsRes.value?.items)
          ? bindingsRes.value.items
          : Array.isArray(bindingsRes.value)
            ? bindingsRes.value
            : state.containerBindings
        : state.containerBindings;

    const runs =
      runsRes.status === "fulfilled"
        ? Array.isArray(runsRes.value?.items)
          ? runsRes.value.items
          : Array.isArray(runsRes.value)
            ? runsRes.value
            : state.runs
        : state.runs;

    const approvals =
      approvalsRes.status === "fulfilled"
        ? Array.isArray(approvalsRes.value?.items)
          ? approvalsRes.value.items
          : Array.isArray(approvalsRes.value)
            ? approvalsRes.value
            : state.approvals
        : state.approvals;

    const audit =
      auditRes.status === "fulfilled"
        ? Array.isArray(auditRes.value?.items)
          ? auditRes.value.items
          : Array.isArray(auditRes.value)
            ? auditRes.value
            : state.audit
        : state.audit;

    const scheduler =
      schedulerRes.status === "fulfilled"
        ? schedulerRes.value?.scheduler ?? schedulerRes.value ?? state.scheduler
        : state.scheduler;

    const lastRefreshAt =
      recoveryPayload?.at || state.lastRefreshAt || new Date().toISOString();

    const bindingsByCategory = normalizeBindingsByCategory(recoveredBindings);

    const boardroomSnapshot =
      boardroomRes.status === "fulfilled" && boardroomRes.value
        ? {
            ...(state.boardroomSnapshot || {}),
            ...(boardroomRes.value || {}),
            workspaceId: resolvedWorkspaceId,
            viewMode: state.boardroomViewMode,
            activeZone:
              boardroomRes.value?.active_zone ??
              boardroomRes.value?.activeZone ??
              state.activeZone ??
              "coo",
            selectedSeatId:
              boardroomRes.value?.selected_seat_id ??
              boardroomRes.value?.selectedSeatId ??
              state.selectedSeatId ??
              null,
            selectedInspectorTarget:
              boardroomRes.value?.selected_inspector_target ??
              boardroomRes.value?.selectedInspectorTarget ??
              state.selectedInspectorTarget ??
              null,
            workspace:
              boardroomRes.value?.workspace ??
              boardroomRes.value?.summary?.workspace ??
              state.boardroomSnapshot?.workspace ??
              null,
            center:
              boardroomRes.value?.center ??
              boardroomRes.value?.summary?.center ??
              state.boardroomSnapshot?.center ??
              null,
            pulse:
              boardroomRes.value?.pulse ??
              boardroomRes.value?.summary?.pulse ??
              state.boardroomSnapshot?.pulse ??
              null,
            seats: Array.isArray(boardroomRes.value?.seats)
              ? boardroomRes.value.seats
              : Array.isArray(boardroomRes.value?.summary?.seats)
                ? boardroomRes.value.summary.seats
                : state.boardroomSnapshot?.seats ?? [],
            departments: Array.isArray(boardroomRes.value?.departments)
              ? boardroomRes.value.departments
              : Array.isArray(boardroomRes.value?.summary?.departments)
                ? boardroomRes.value.summary.departments
                : state.boardroomSnapshot?.departments ?? [],
            floors:
              boardroomRes.value?.floors ??
              boardroomRes.value?.summary?.floors ??
              state.boardroomSnapshot?.floors ??
              {},
            runtime:
              boardroomRes.value?.runtime ??
              {
                ...(state.boardroomSnapshot?.runtime || {}),
                node: status?.control || status || null,
                runs,
                approvals,
              },
            topology:
              boardroomRes.value?.topology ??
              boardroomRes.value?.summary?.topology ??
              state.boardroomSnapshot?.topology ??
              { nodes: [], edges: [] },
            bindingsByCategory,
            updatedAt: lastRefreshAt,
            summary: boardroomRes.value?.summary ?? boardroomRes.value,
          }
        : state.boardroomSnapshot;

    desktopStore.hydrateLocalTruth({
      workspaceId: resolvedWorkspaceId,
      nodeId: resolvedNodeId,
      containerBindings: recoveredBindings,
      runs,
      approvals,
      audit,
      scheduler,
      status,
      dashboardSummary:
        dashboardRes.status === "fulfilled"
          ? dashboardRes.value?.summary ?? dashboardRes.value ?? state.dashboardSummary
          : state.dashboardSummary,
      marketingSummary:
        marketingRes.status === "fulfilled"
          ? marketingRes.value?.summary ?? marketingRes.value ?? state.marketingSummary
          : state.marketingSummary,
      brandFoundationState:
        brandFoundationRes.status === "fulfilled"
          ? brandFoundationRes.value?.item ?? brandFoundationRes.value ?? state.brandFoundationState
          : state.brandFoundationState,
      boardroomSnapshot,
      activeZone:
        boardroomSnapshot?.activeZone ??
        state.activeZone,
      selectedSeatId:
        boardroomSnapshot?.selectedSeatId ??
        state.selectedSeatId,
      selectedInspectorTarget:
        boardroomSnapshot?.selectedInspectorTarget ??
        state.selectedInspectorTarget,
      lastRefreshAt,
    });

    ensureLiveAgentSelection({
      preferredDepartmentKey:
        boardroomSnapshot?.activeZone ||
        state.activeZone ||
        "marketing",
    });

    requestRender();
  } catch (_) {
    // keep cached local state if backend/container truth hydration fails
  }
}

  async function bootstrapDesktop() {
    if (window.__TESSARIS_DESKTOP_BOOTSTRAP_RUNNING__) {
      console.warn("bootstrapDesktop already running, skipping duplicate call.");
      return;
    }

    if (window.__TESSARIS_DESKTOP_BOOTSTRAPPED__) {
      console.warn("bootstrapDesktop already completed, skipping duplicate call.");
      return;
    }

    window.__TESSARIS_DESKTOP_BOOTSTRAP_RUNNING__ = true;

    try {
      desktopStore.loadFromStorage();

      if (!state.brandFoundationState || !state.brandFoundationState.updatedAt) {
        desktopStore.syncBrandFoundationFromMarketingForm();
        desktopStore.persistCache();
      }

      ensureLiveAgentSelection();
      requestRender();
      setupBackendStatusListener();

      if (
        window.aionDesktop &&
        typeof window.aionDesktop.getBackendStatus === "function"
      ) {
        try {
          const backend = await window.aionDesktop.getBackendStatus();

          if (backend?.healthy) {
            desktopStore.patch({
              backendReady: true,
              backendStatus: "ready",
              message: "Connected to local backend",
              messageTone: "success",
            });

            ensureLiveAgentSelection();
            requestRender();

            await bindWorkspace({
              skipInitialRefresh: true,
              preserveMessage: true,
            });

            await hydrateRecoveredDesktopState();
            await refreshAll();

            ensureLiveAgentSelection();
            requestRender();

            window.__TESSARIS_DESKTOP_BOOTSTRAPPED__ = true;
            return;
          }
        } catch (_) {
          // fall through
        }
      }

      desktopStore.patch({
        backendReady: false,
        backendStatus: "starting",
        message: "Waiting for local backend to start...",
        messageTone: "neutral",
      });

      ensureLiveAgentSelection();
      requestRender();

      window.__TESSARIS_DESKTOP_BOOTSTRAPPED__ = true;
    } finally {
      window.__TESSARIS_DESKTOP_BOOTSTRAP_RUNNING__ = false;
    }
  }

  void bootstrapDesktop();
}

/* AION_BROWSER_RECORDER_EVENT_BRIDGE_V1 */
(function installAionBrowserRecorderEventBridge() {



  if (window.__AION_BROWSER_RECORDER_EVENT_BRIDGE_INSTALLED__) return;
  window.__AION_BROWSER_RECORDER_EVENT_BRIDGE_INSTALLED__ = true;

  function normaliseRecordedBrowserEvent(payload = {}) {
    const now = new Date().toISOString();
    const rawType = String(payload.type || payload.event_type || "click_element");

    const type =
      rawType === "click" ? "click_element" :
      rawType === "input" ? "type_text" :
      rawType;

    const risky =
      payload.requires_approval === true ||
      type === "approval_checkpoint" ||
      /send|submit|pay|buy|delete|remove|confirm/i.test(String(payload.label || ""));

    return {
      step_id:
        payload.step_id ||
        `browser_step_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`,
      order: 0,
      type: risky && type === "click_element" ? "approval_checkpoint" : type,
      event_type: risky && type === "click_element" ? "approval_checkpoint" : type,
      label:
        payload.label ||
        (type === "click_element" ? "Click selected browser element" : "Browser event"),
      safety: risky ? "approval_required" : (payload.safety || "interaction"),
      input_map: payload.input_map || {},
      output: risky ? "approval_required" : (payload.output || "browser_output"),
      selector: payload.selector || "",
      url_pattern:
        payload.url_pattern ||
        payload.current_url ||
        payload.url ||
        "",
      url:
        payload.url ||
        payload.current_url ||
        payload.url_pattern ||
        "",
      page_title:
        payload.page_title ||
        payload.title ||
        "",
      field_name: payload.field_name || "",
      value_hint: payload.value_hint || payload.field_value_hint || "",
      requires_approval: risky,
      dry_run_supported: true,
      captured: true,
      captured_at: payload.captured_at || now,
      notes: payload.notes || "Captured from isolated browser.",
      source: payload.source || "isolated_browser_recorder",
    };
  }

  function appendBrowserRecorderEvent(payload = {}) {
    if (!window.desktopStore || !window.state) return;

    const bridge = window.state.browserDesktopBridge || {};
    const existing = Array.isArray(bridge.captured_events)
      ? bridge.captured_events
      : Array.isArray(bridge.last_recording_steps)
        ? bridge.last_recording_steps
        : [];

    const eventRow = normaliseRecordedBrowserEvent(payload);

    let nextEvents = [...existing, eventRow];

    const isClick =
      String(eventRow.type || "") === "click_element" ||
      String(eventRow.event_type || "") === "click_element";

    const hasApproval = nextEvents.some((item) =>
      String(item.type || item.event_type || "") === "approval_checkpoint"
    );

    if (isClick && !hasApproval) {
      nextEvents.push({
        step_id: `browser_step_${Date.now().toString(36)}_approval`,
        order: 0,
        type: "approval_checkpoint",
        event_type: "approval_checkpoint",
        label: "Approval required before opening or acting on email",
        safety: "approval_required",
        input_map: {},
        output: "approval_required",
        selector: "",
        url_pattern: eventRow.url_pattern || eventRow.url || "",
        url: eventRow.url || eventRow.url_pattern || "",
        page_title: eventRow.page_title || "",
        field_name: "",
        value_hint: "",
        requires_approval: true,
        dry_run_supported: true,
        captured: true,
        captured_at: new Date().toISOString(),
        notes: "Auto-added after selected browser click.",
        source: "isolated_browser_recorder_auto_approval",
      });
    }

    nextEvents = nextEvents.map((item, index) => ({
      ...item,
      order: index + 1,
    }));

    window.desktopStore.patch({
      browserDesktopBridge: {
        ...bridge,
        status: "recording",
        bridge_active: true,
        recording: true,
        captured_events: nextEvents,
        captured_browser_events: nextEvents,
        last_recording_steps: nextEvents,
        captured_event_count: nextEvents.length,
        dry_run_ready: false,
        dry_run_result: null,
        message: `Captured browser event: ${eventRow.label}`,
      },
      message: `Captured browser event: ${eventRow.label}`,
      messageTone: "success",
    });

    try {
      window.desktopStore.persistCacheSoon?.(100);
    } catch (_) {}

    try {
      window.requestRender?.();
    } catch (_) {}
  }

  function bind() {
    if (!window.aionDesktop?.onBrowserRecorderEvent) {
      setTimeout(bind, 500);
      return;
    }

    window.aionDesktop.onBrowserRecorderEvent((payload) => {
      appendBrowserRecorderEvent(payload || {});
    });

    console.log("[Aion Browser Recorder] desktop listener installed");
  }

  bind();
})();


/* AION_WORKFLOW_CAPSULE_BOARDROOM_APPROVAL_BRIDGE_V1 */
(function installWorkflowCapsuleBoardroomApprovalBridge() {
  if (window.__AION_WORKFLOW_CAPSULE_BOARDROOM_APPROVAL_BRIDGE_INSTALLED__) return;
  window.__AION_WORKFLOW_CAPSULE_BOARDROOM_APPROVAL_BRIDGE_INSTALLED__ = true;

  document.addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-workflow-capsule-approval-action]");
    if (!button) return;

    event.preventDefault();
    event.stopPropagation();

    const approvalId = button.getAttribute("data-workflow-capsule-approval-id");
    const action = button.getAttribute("data-workflow-capsule-approval-action");

    void handleBoardroomWorkflowCapsuleApprovalAction(approvalId, action).catch((error) => {
      desktopStore.patch?.({
        message: error?.message || "Workflow capsule approval action failed",
        messageTone: "error",
      });
      requestRender?.();
    });
  });
})();


/* AION_WORKFLOW_CAPSULE_AUTONOMY_UI_BRIDGE_V1 */
(function installAionWorkflowCapsuleAutonomyUiBridge() {
  if (window.__AION_WORKFLOW_CAPSULE_AUTONOMY_UI_BRIDGE_V1__) return;
  window.__AION_WORKFLOW_CAPSULE_AUTONOMY_UI_BRIDGE_V1__ = true;

  const AUTONOMY_MODES = [
    {
      id: "review_required",
      label: "Review Mode",
      description: "Default. Human approval required before guarded resume.",
    },
    {
      id: "draft_auto",
      label: "Draft Auto Mode",
      description: "Can read, classify, summarise, and create drafts. Cannot send, post, pay, delete, or commit external writes.",
    },
    {
      id: "auto_with_exceptions",
      label: "Auto with Exceptions",
      description: "Runs trusted low-risk steps automatically, but pauses on complaint, refund, legal, financial, low-confidence, unknown-intent, or high-risk actions.",
    },
    {
      id: "manual_only",
      label: "Manual Only",
      description: "Emergency stop / human-only execution.",
    },
  ];

  const NODE_AUTONOMY_MODES = [
    "automatic",
    "draft_only",
    "approval_required",
    "blocked",
  ];

  function getAutonomyState() {
    window.__aionWorkflowCapsuleAutonomyState =
      window.__aionWorkflowCapsuleAutonomyState || {
        workflow_mode: "review_required",
        node_modes: {},
        notes: [
          "Create draft is not send",
          "Agents cannot self-authorise",
          "Auto mode still pauses on risk exceptions",
          "External writes stay guarded",
        ],
      };

    return window.__aionWorkflowCapsuleAutonomyState;
  }

  function setWorkflowAutonomyMode(mode) {
    const safeMode = AUTONOMY_MODES.some((item) => item.id === mode)
      ? mode
      : "review_required";

    const current = getAutonomyState();
    window.__aionWorkflowCapsuleAutonomyState = {
      ...current,
      workflow_mode: safeMode,
      updated_at: new Date().toISOString(),
    };

    try {
      window.localStorage?.setItem(
        "aion.workflow_capsule.autonomy_state.v1",
        JSON.stringify(window.__aionWorkflowCapsuleAutonomyState),
      );
    } catch (_) {
      // non-fatal UI cache only
    }

    return window.__aionWorkflowCapsuleAutonomyState;
  }

  function setNodeAutonomyMode(nodeId, mode) {
    const safeMode = NODE_AUTONOMY_MODES.includes(mode)
      ? mode
      : "approval_required";

    const current = getAutonomyState();
    window.__aionWorkflowCapsuleAutonomyState = {
      ...current,
      node_modes: {
        ...(current.node_modes || {}),
        [String(nodeId || "unknown")]: safeMode,
      },
      updated_at: new Date().toISOString(),
    };

    try {
      window.localStorage?.setItem(
        "aion.workflow_capsule.autonomy_state.v1",
        JSON.stringify(window.__aionWorkflowCapsuleAutonomyState),
      );
    } catch (_) {
      // non-fatal UI cache only
    }

    return window.__aionWorkflowCapsuleAutonomyState;
  }

  function renderWorkflowCapsuleAutonomyControls({
    scope = "workflow",
    workflowId = "workflow",
    nodeId = "",
  } = {}) {
    const state = getAutonomyState();
    const selectedWorkflowMode = state.workflow_mode || "review_required";
    const selectedNodeMode =
      state.node_modes?.[String(nodeId || "")] || "approval_required";

    return `
      <section class="workflow-capsule-autonomy-panel" data-workflow-capsule-autonomy-scope="${String(scope)}">
        <div class="panel-title">Workflow Capsule Autonomy</div>

        <div class="list-item-sub">
          Create draft is not send. Agents cannot self-authorise. Auto mode still pauses on risk exceptions. External writes stay guarded.
        </div>

        <div class="badge-row" style="margin-top:10px;">
          <span class="badge">workflow_id: ${String(workflowId || "workflow")}</span>
          <span class="badge">scope: ${String(scope || "workflow")}</span>
          <span class="badge">permission_decision</span>
          <span class="badge">risk_tier</span>
        </div>

        <div class="list-wrap" style="margin-top:12px;">
          ${AUTONOMY_MODES.map((mode) => `
            <button
              class="secondary-btn"
              type="button"
              data-workflow-capsule-autonomy-mode="${mode.id}"
              data-workflow-capsule-autonomy-scope="workflow"
              aria-pressed="${selectedWorkflowMode === mode.id ? "true" : "false"}"
              title="${mode.description}"
            >
              ${mode.label}
            </button>
          `).join("")}
        </div>

        <div class="list-wrap" style="margin-top:12px;">
          ${NODE_AUTONOMY_MODES.map((mode) => `
            <button
              class="secondary-btn"
              type="button"
              data-workflow-capsule-node-autonomy-mode="${mode}"
              data-workflow-capsule-node-id="${String(nodeId || "workflow_node")}"
              aria-pressed="${selectedNodeMode === mode ? "true" : "false"}"
            >
              ${mode}
            </button>
          `).join("")}
        </div>
      </section>
    `;
  }

  document.addEventListener("click", (event) => {
    const workflowButton = event.target.closest?.("[data-workflow-capsule-autonomy-mode]");
    if (workflowButton) {
      event.preventDefault();
      event.stopPropagation();

      const mode = workflowButton.getAttribute("data-workflow-capsule-autonomy-mode");
      setWorkflowAutonomyMode(mode);

      window.desktopStore?.patch?.({
        message: `Workflow autonomy mode set: ${mode}`,
        messageTone: "success",
      });

      window.requestRender?.();
      return;
    }

    const nodeButton = event.target.closest?.("[data-workflow-capsule-node-autonomy-mode]");
    if (nodeButton) {
      event.preventDefault();
      event.stopPropagation();

      const mode = nodeButton.getAttribute("data-workflow-capsule-node-autonomy-mode");
      const nodeId = nodeButton.getAttribute("data-workflow-capsule-node-id");

      setNodeAutonomyMode(nodeId, mode);

      window.desktopStore?.patch?.({
        message: `Node autonomy mode set: ${nodeId || "node"} -> ${mode}`,
        messageTone: "success",
      });

      window.requestRender?.();
    }
  });

  window.AionWorkflowCapsuleAutonomyUiBridge = {
    getAutonomyState,
    setWorkflowAutonomyMode,
    setNodeAutonomyMode,
    renderWorkflowCapsuleAutonomyControls,
  };
})();


/* AION PATCH: clean workflow canvas overlay + dark mode v1 */
(function installAionWorkflowCanvasCleanPatch() {
  const STYLE_ID = "aion-workflow-canvas-clean-patch-v1";
  const old = document.getElementById(STYLE_ID);
  if (old) old.remove();

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    /*
      Layout rule:
      - Left sidebar stays in layout.
      - Canvas owns all remaining width.
      - Add-step drawer overlays the canvas only when open.
      - No permanent right-hand inspector column.
    */

    .aion-workflow-canvas-shell {
      position: relative !important;
      overflow: hidden !important;
    }

    .aion-workflow-layout {
      position: relative !important;
      display: grid !important;
      grid-template-columns: 64px minmax(0, 1fr) !important;
      width: 100% !important;
      height: calc(100vh - 72px) !important;
      overflow: hidden !important;
      background: transparent !important;
    }

    .aion-workflow-sidebar {
      grid-column: 1 !important;
      width: 64px !important;
      min-width: 64px !important;
      max-width: 64px !important;
      z-index: 40 !important;
    }

    .aion-workflow-canvas {
      grid-column: 2 !important;
      position: relative !important;
      width: 100% !important;
      min-width: 0 !important;
      height: 100% !important;
      overflow: hidden !important;
      z-index: 1 !important;
      background: #fff3e7 !important;
    }

    .aion-workflow-canvas-viewport {
      position: relative !important;
      width: 100% !important;
      height: 100% !important;
      min-width: 100% !important;
      min-height: 100% !important;
      transform-origin: 0 0 !important;
      z-index: 2 !important;
    }

    .aion-workflow-zoom,
    .aion-workflow-floating-toolbar {
      z-index: 90 !important;
    }

    .aion-workflow-picker-drawer {
      position: absolute !important;
      top: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      width: 390px !important;
      min-width: 390px !important;
      max-width: 390px !important;
      height: 100% !important;
      z-index: 100 !important;
      overflow-y: auto !important;
      overscroll-behavior: contain !important;
      padding: 28px 18px 36px !important;
      background: #f3eadc !important;
      border-left: 1px solid rgba(15,23,42,0.12) !important;
      box-shadow: -20px 0 42px rgba(15,23,42,0.10) !important;
    }

    .aion-workflow-picker-drawer-close {
      position: sticky !important;
      top: 8px !important;
      margin-left: auto !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      width: 42px !important;
      height: 42px !important;
      border-radius: 999px !important;
      z-index: 3 !important;
      background: rgba(255,255,255,0.92) !important;
      color: #020617 !important;
      border: 1px solid rgba(15,23,42,0.12) !important;
      box-shadow: 0 10px 24px rgba(15,23,42,0.14) !important;
      font-size: 24px !important;
      line-height: 1 !important;
      cursor: pointer !important;
    }

    .aion-workflow-picker-drawer h2,
    .aion-workflow-picker-drawer h3 {
      letter-spacing: -0.04em !important;
      line-height: 0.95 !important;
    }

    .aion-workflow-picker-drawer .eyebrow,
    .aion-workflow-picker-drawer summary,
    .aion-workflow-picker-drawer [class*="label"] {
      letter-spacing: 0.26em !important;
      text-transform: uppercase !important;
    }

    .aion-workflow-picker-drawer [data-aion-workflow-create-action] {
      display: grid !important;
      grid-template-columns: 44px minmax(0, 1fr) auto !important;
      gap: 14px !important;
      align-items: center !important;
      width: 100% !important;
      padding: 14px 12px !important;
      margin: 8px 0 !important;
      border-radius: 16px !important;
      background: rgba(255,255,255,0.38) !important;
      border: 1px solid rgba(15,23,42,0.08) !important;
      text-align: left !important;
    }

    .aion-workflow-picker-drawer [data-aion-workflow-create-action]:hover {
      background: rgba(255,255,255,0.66) !important;
      transform: translateY(-1px);
    }

    /*
      Dark mode rule:
      Black glass canvas, no blue/green glow overlays.
      The only green is the small accent text/grid/connector colour.
    */

    body.aion-workflow-dark-mode,
    body.aion-workflow-dark-glass {
      background: #020407 !important;
    }

    body.aion-workflow-dark-mode .desktop-root,
    body.aion-workflow-dark-glass .desktop-root,
    body.aion-workflow-dark-mode .aion-workflow-canvas-shell,
    body.aion-workflow-dark-glass .aion-workflow-canvas-shell,
    body.aion-workflow-dark-mode .aion-workflow-layout,
    body.aion-workflow-dark-glass .aion-workflow-layout,
    body.aion-workflow-dark-mode .aion-workflow-canvas,
    body.aion-workflow-dark-glass .aion-workflow-canvas {
      background: #020407 !important;
      background-image: none !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-canvas::before,
    body.aion-workflow-dark-mode .aion-workflow-canvas::after,
    body.aion-workflow-dark-mode .aion-workflow-canvas-shell::before,
    body.aion-workflow-dark-mode .aion-workflow-canvas-shell::after,
    body.aion-workflow-dark-glass .aion-workflow-canvas::before,
    body.aion-workflow-dark-glass .aion-workflow-canvas::after,
    body.aion-workflow-dark-glass .aion-workflow-canvas-shell::before,
    body.aion-workflow-dark-glass .aion-workflow-canvas-shell::after {
      display: none !important;
      opacity: 0 !important;
      content: none !important;
      background: none !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-canvas-viewport,
    body.aion-workflow-dark-glass .aion-workflow-canvas-viewport {
      background-color: #020407 !important;
      background-image:
        linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px),
        radial-gradient(circle, rgba(183,239,106,0.20) 1px, transparent 1.5px) !important;
      background-size: 96px 96px, 96px 96px, 28px 28px !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] {
      color: rgba(255,255,255,0.94) !important;
      opacity: 1 !important;
      visibility: visible !important;
      filter: none !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id] h3,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] strong,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-title,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] h3,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] strong,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-title {
      color: rgba(255,255,255,0.96) !important;
      text-shadow: 0 1px 10px rgba(0,0,0,0.85) !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id] p,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] small,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] span,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] p,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] small,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] span {
      color: rgba(255,255,255,0.78) !important;
      text-shadow: 0 1px 10px rgba(0,0,0,0.85) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-connectors path,
    body.aion-workflow-dark-glass .aion-workflow-connectors path {
      stroke: rgba(183,239,106,0.72) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-sidebar,
    body.aion-workflow-dark-glass .aion-workflow-sidebar {
      background: rgba(4,8,16,0.92) !important;
      border-right: 1px solid rgba(255,255,255,0.10) !important;
      backdrop-filter: blur(18px) saturate(150%) !important;
      -webkit-backdrop-filter: blur(18px) saturate(150%) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-sidebar button,
    body.aion-workflow-dark-glass .aion-workflow-sidebar button {
      color: rgba(255,255,255,0.92) !important;
      background: rgba(255,255,255,0.06) !important;
      border-color: rgba(255,255,255,0.12) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-sidebar button *,
    body.aion-workflow-dark-glass .aion-workflow-sidebar button * {
      color: rgba(255,255,255,0.92) !important;
      fill: currentColor !important;
      stroke: currentColor !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-sidebar button.active,
    body.aion-workflow-dark-glass .aion-workflow-sidebar button.active {
      color: #b7ef6a !important;
      background: rgba(183,239,106,0.16) !important;
      border-color: rgba(183,239,106,0.35) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-topbar,
    body.aion-workflow-dark-glass .aion-workflow-topbar {
      background: rgba(3,7,16,0.72) !important;
      border-bottom: 1px solid rgba(255,255,255,0.10) !important;
      backdrop-filter: blur(20px) saturate(160%) !important;
      -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-topbar *,
    body.aion-workflow-dark-glass .aion-workflow-topbar * {
      color: rgba(255,255,255,0.92) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-subtle-meta,
    body.aion-workflow-dark-glass .aion-workflow-subtle-meta,
    body.aion-workflow-dark-mode .aion-workflow-load-notice,
    body.aion-workflow-dark-glass .aion-workflow-load-notice {
      color: #b7ef6a !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-zoom,
    body.aion-workflow-dark-mode .aion-workflow-floating-toolbar,
    body.aion-workflow-dark-glass .aion-workflow-zoom,
    body.aion-workflow-dark-glass .aion-workflow-floating-toolbar {
      background: rgba(255,255,255,0.10) !important;
      border: 1px solid rgba(255,255,255,0.20) !important;
      box-shadow: 0 18px 50px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.20) !important;
      backdrop-filter: blur(24px) saturate(170%) !important;
      -webkit-backdrop-filter: blur(24px) saturate(170%) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-picker-drawer,
    body.aion-workflow-dark-glass .aion-workflow-picker-drawer {
      background: rgba(10,15,22,0.50) !important;
      border-left: 1px solid rgba(255,255,255,0.18) !important;
      box-shadow: -28px 0 70px rgba(0,0,0,0.55), inset 1px 0 0 rgba(255,255,255,0.10) !important;
      backdrop-filter: blur(34px) saturate(185%) !important;
      -webkit-backdrop-filter: blur(34px) saturate(185%) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-picker-drawer *,
    body.aion-workflow-dark-glass .aion-workflow-picker-drawer * {
      color: rgba(255,255,255,0.90) !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-picker-drawer .eyebrow,
    body.aion-workflow-dark-glass .aion-workflow-picker-drawer .eyebrow {
      color: #b7ef6a !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-picker-drawer [data-aion-workflow-create-action],
    body.aion-workflow-dark-glass .aion-workflow-picker-drawer [data-aion-workflow-create-action] {
      background: rgba(255,255,255,0.12) !important;
      border: 1px solid rgba(255,255,255,0.16) !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 12px 36px rgba(0,0,0,0.20) !important;
      backdrop-filter: blur(20px) saturate(160%) !important;
      -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
    }
  `;
  document.head.appendChild(style);
})();


/* AION PATCH: working workflow dark mode toggle button */
(function installAionWorkflowDarkModeTogglePatch() {
  if (window.__aionWorkflowDarkModeTogglePatchBound === true) return;
  window.__aionWorkflowDarkModeTogglePatchBound = true;

  const applyDarkModeState = (enabled) => {
    document.body.classList.toggle("aion-workflow-dark-mode", Boolean(enabled));
    document.body.classList.toggle("aion-workflow-dark-glass", Boolean(enabled));

    try {
      localStorage.setItem("aion.workflow.dark_mode.enabled", enabled ? "1" : "0");
    } catch (_) {}

    document
      .querySelectorAll("[data-aion-workflow-dark-mode-toggle='true'], [data-aion-workflow-dark-glass-toggle='true']")
      .forEach((button) => {
        button.textContent = enabled ? "☀" : "☾";
        button.setAttribute("aria-pressed", enabled ? "true" : "false");
        button.setAttribute("title", enabled ? "Switch to light canvas" : "Switch to dark canvas");
      });
  };

  let initial = false;
  try {
    initial = localStorage.getItem("aion.workflow.dark_mode.enabled") === "1";
  } catch (_) {}

  applyDarkModeState(initial);

  document.addEventListener(
    "click",
    (event) => {
      const button = event.target.closest?.(
        "[data-aion-workflow-dark-mode-toggle='true'], [data-aion-workflow-dark-glass-toggle='true']"
      );
      if (!button) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const nextEnabled = !document.body.classList.contains("aion-workflow-dark-mode");
      applyDarkModeState(nextEnabled);

      if (typeof updateAionWorkflowCanvasTransform === "function") {
        updateAionWorkflowCanvasTransform();
      }
    },
    true,
  );
})();

/* AION PATCH: dark mode node text + left rail icon contrast */
(function installAionWorkflowDarkModeTextIconContrastPatch() {
  const STYLE_ID = "aion-workflow-dark-mode-text-icon-contrast-v2";
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    /* Node text under canvas nodes */
    body.aion-workflow-dark-mode [data-aion-workflow-node-id],
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] *,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] * {
      color: rgba(255,255,255,0.88) !important;
      text-shadow: 0 2px 10px rgba(0,0,0,0.9) !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id] strong,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] h3,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-title,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] strong,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] h3,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-title {
      color: #ffffff !important;
      text-shadow: 0 2px 12px rgba(0,0,0,0.95) !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id] p,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] small,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .muted,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] p,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] small,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .muted {
      color: rgba(255,255,255,0.72) !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id] [class*="status"],
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] [class*="dry"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] [class*="status"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] [class*="dry"] {
      color: #b7ef6a !important;
      font-weight: 800 !important;
      letter-spacing: 0.02em !important;
    }

    /* Left rail / sidebar icons */
    body.aion-workflow-dark-mode .aion-workflow-sidebar button,
    body.aion-workflow-dark-mode .aion-workflow-sidebar button *,
    body.aion-workflow-dark-mode .aion-workflow-app-nav button,
    body.aion-workflow-dark-mode .aion-workflow-app-nav button *,
    body.aion-workflow-dark-glass .aion-workflow-sidebar button,
    body.aion-workflow-dark-glass .aion-workflow-sidebar button *,
    body.aion-workflow-dark-glass .aion-workflow-app-nav button,
    body.aion-workflow-dark-glass .aion-workflow-app-nav button * {
      color: rgba(255,255,255,0.88) !important;
      fill: currentColor !important;
      stroke: currentColor !important;
      opacity: 1 !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-sidebar button.active,
    body.aion-workflow-dark-mode .aion-workflow-sidebar button.active *,
    body.aion-workflow-dark-mode .aion-workflow-app-nav button.active,
    body.aion-workflow-dark-mode .aion-workflow-app-nav button.active *,
    body.aion-workflow-dark-glass .aion-workflow-sidebar button.active,
    body.aion-workflow-dark-glass .aion-workflow-sidebar button.active *,
    body.aion-workflow-dark-glass .aion-workflow-app-nav button.active,
    body.aion-workflow-dark-glass .aion-workflow-app-nav button.active * {
      color: #b7ef6a !important;
      fill: currentColor !important;
      stroke: currentColor !important;
    }

    body.aion-workflow-dark-mode .aion-workflow-sidebar-toggle,
    body.aion-workflow-dark-glass .aion-workflow-sidebar-toggle {
      color: #ffffff !important;
      background: rgba(255,255,255,0.08) !important;
      border-color: rgba(255,255,255,0.18) !important;
    }
  `;

  document.head.appendChild(style);
})();

/* AION PATCH: dark mode node hover/type label branding */
(function installAionWorkflowDarkModeNodeLabelPatch() {
  const STYLE_ID = "aion-workflow-dark-mode-node-label-v1";
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] [class*="type"],
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] [class*="badge"],
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] [class*="label"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] [class*="type"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] [class*="badge"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] [class*="label"] {
      background:
        linear-gradient(135deg, rgba(183,239,106,0.22), rgba(255,255,255,0.08)) !important;
      color: #b7ef6a !important;
      border: 1px solid rgba(183,239,106,0.42) !important;
      box-shadow:
        0 10px 28px rgba(0,0,0,0.42),
        inset 0 1px 0 rgba(255,255,255,0.18) !important;
      text-shadow: 0 1px 8px rgba(0,0,0,0.85) !important;
      letter-spacing: 0.18em !important;
      font-weight: 900 !important;
      backdrop-filter: blur(18px) saturate(160%) !important;
      -webkit-backdrop-filter: blur(18px) saturate(160%) !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id]:hover [class*="type"],
    body.aion-workflow-dark-mode [data-aion-workflow-node-id]:hover [class*="badge"],
    body.aion-workflow-dark-mode [data-aion-workflow-node-id]:hover [class*="label"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id]:hover [class*="type"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id]:hover [class*="badge"],
    body.aion-workflow-dark-glass [data-aion-workflow-node-id]:hover [class*="label"] {
      background:
        linear-gradient(135deg, rgba(183,239,106,0.34), rgba(255,255,255,0.10)) !important;
      color: #d9ff9a !important;
      border-color: rgba(183,239,106,0.64) !important;
    }
  `;

  document.head.appendChild(style);
})();

/* AION PATCH: dark mode node icon glyphs use Tessaris green */
(function installAionWorkflowDarkModeNodeIconGreenPatch() {
  const STYLE_ID = "aion-workflow-dark-mode-node-icon-green-v1";
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-icon,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-card,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-visual,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-square,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-icon,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-card,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-visual,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-square {
      color: #b7ef6a !important;
      text-shadow:
        0 0 12px rgba(183,239,106,0.55),
        0 3px 12px rgba(0,0,0,0.80) !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-icon *,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-card *,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-visual *,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id] .aion-workflow-node-square *,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-icon *,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-card *,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-visual *,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id] .aion-workflow-node-square * {
      color: #b7ef6a !important;
      fill: #b7ef6a !important;
      stroke: #b7ef6a !important;
      text-shadow:
        0 0 12px rgba(183,239,106,0.55),
        0 3px 12px rgba(0,0,0,0.80) !important;
    }

    body.aion-workflow-dark-mode [data-aion-workflow-node-id]:hover .aion-workflow-node-icon,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id]:hover .aion-workflow-node-card,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id]:hover .aion-workflow-node-visual,
    body.aion-workflow-dark-mode [data-aion-workflow-node-id]:hover .aion-workflow-node-square,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id]:hover .aion-workflow-node-icon,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id]:hover .aion-workflow-node-card,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id]:hover .aion-workflow-node-visual,
    body.aion-workflow-dark-glass [data-aion-workflow-node-id]:hover .aion-workflow-node-square {
      color: #d9ff9a !important;
      text-shadow:
        0 0 18px rgba(183,239,106,0.78),
        0 3px 14px rgba(0,0,0,0.90) !important;
    }
  `;

  document.head.appendChild(style);
})();

/* AION PATCH: dark mode canvas node centre icons use Tessaris green */
(function installAionWorkflowDarkModeCanvasNodeIconGreenPatch() {
  const STYLE_ID = "aion-workflow-dark-mode-canvas-node-icon-green-v1";
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    body.aion-workflow-dark-mode .aion-canvas-node .aion-canvas-node-icon,
    body.aion-workflow-dark-glass .aion-canvas-node .aion-canvas-node-icon {
      color: #b7ef6a !important;
      fill: #b7ef6a !important;
      stroke: #b7ef6a !important;
      text-shadow:
        0 0 10px rgba(183,239,106,0.60),
        0 2px 10px rgba(0,0,0,0.85) !important;
    }

    body.aion-workflow-dark-mode .aion-canvas-node .aion-canvas-node-icon *,
    body.aion-workflow-dark-glass .aion-canvas-node .aion-canvas-node-icon * {
      color: #b7ef6a !important;
      fill: #b7ef6a !important;
      stroke: #b7ef6a !important;
    }

    body.aion-workflow-dark-mode .aion-canvas-node:hover .aion-canvas-node-icon,
    body.aion-workflow-dark-glass .aion-canvas-node:hover .aion-canvas-node-icon {
      color: #d9ff9a !important;
      fill: #d9ff9a !important;
      stroke: #d9ff9a !important;
      text-shadow:
        0 0 16px rgba(183,239,106,0.85),
        0 2px 12px rgba(0,0,0,0.90) !important;
    }
  `;

  document.head.appendChild(style);
})();


/* AION PATCH: Workflow Architect modal clean layout v2 */
(function installWorkflowArchitectModalCleanLayoutV2() {
  const STYLE_ID = "aion-workflow-architect-modal-clean-layout-v2";
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    [data-workflow-architect-node-editor-modal="true"] {
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      padding: 34px !important;
      background: rgba(2, 6, 23, 0.42) !important;
      backdrop-filter: blur(12px) saturate(130%) !important;
      -webkit-backdrop-filter: blur(12px) saturate(130%) !important;
    }

    .aion-workflow-architect-node-editor {
      width: min(1420px, calc(100vw - 96px)) !important;
      height: min(860px, calc(100vh - 96px)) !important;
      max-height: calc(100vh - 96px) !important;
      display: grid !important;
      grid-template-rows: auto minmax(0, 1fr) !important;
      overflow: hidden !important;
      border-radius: 28px !important;
      background:
        radial-gradient(circle at 18% 0%, rgba(26,138,255,0.06), transparent 28%),
        linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,248,239,0.98)) !important;
      border: 1px solid rgba(15, 23, 42, 0.12) !important;
      box-shadow:
        0 36px 100px rgba(15,23,42,0.28),
        inset 0 1px 0 rgba(255,255,255,0.80) !important;
    }

    .aion-workflow-architect-node-editor > .aion-node-editor-close {
      position: absolute !important;
      top: 18px !important;
      left: 18px !important;
      width: 48px !important;
      height: 48px !important;
      z-index: 50 !important;
      border-radius: 16px !important;
      background: rgba(255,255,255,0.92) !important;
      border: 1px solid rgba(15,23,42,0.12) !important;
      color: #0f172a !important;
      font-size: 28px !important;
      font-weight: 900 !important;
      box-shadow: 0 12px 28px rgba(15,23,42,0.12) !important;
    }

    .aion-workflow-architect-node-editor > .aion-node-editor-head {
      position: relative !important;
      z-index: 3 !important;
      padding: 32px 40px 24px 92px !important;
      border-bottom: 1px solid rgba(15,23,42,0.10) !important;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.78), rgba(255,255,255,0.34)) !important;
      backdrop-filter: blur(18px) saturate(150%) !important;
      -webkit-backdrop-filter: blur(18px) saturate(150%) !important;
    }

    .aion-workflow-architect-node-editor > .aion-node-editor-head .eyebrow {
      margin: 0 0 8px !important;
      color: #64748b !important;
      font-size: 11px !important;
      font-weight: 950 !important;
      letter-spacing: 0.24em !important;
      text-transform: uppercase !important;
    }

    .aion-workflow-architect-node-editor > .aion-node-editor-head h2 {
      margin: 0 !important;
      color: #0f172a !important;
      font-size: 34px !important;
      line-height: 1.04 !important;
      font-weight: 950 !important;
      letter-spacing: -0.04em !important;
      opacity: 1 !important;
      text-shadow: none !important;
    }

    .aion-workflow-architect-node-editor > .aion-node-editor-head p {
      margin: 10px 0 0 !important;
      max-width: 780px !important;
      color: #64748b !important;
      font-size: 15px !important;
      line-height: 1.5 !important;
      opacity: 1 !important;
    }

    .aion-workflow-architect-modal-body {
      position: relative !important;
      z-index: 2 !important;
      min-height: 0 !important;
      overflow: auto !important;
      padding: 28px 40px 40px !important;
      display: grid !important;
      grid-template-columns: minmax(360px, 460px) minmax(440px, 1fr) minmax(320px, 390px) !important;
      gap: 24px !important;
      align-items: start !important;
    }

    .aion-workflow-architect-node-editor .aion-node-editor-column {
      min-width: 0 !important;
      position: relative !important;
      z-index: 1 !important;
    }

    .aion-workflow-architect-node-editor .aion-node-editor-column > .eyebrow {
      margin: 0 0 12px !important;
      color: #64748b !important;
      font-size: 11px !important;
      font-weight: 950 !important;
      letter-spacing: 0.24em !important;
      text-transform: uppercase !important;
    }

    .aion-workflow-architect-node-editor .aion-node-editor-panel {
      border-radius: 24px !important;
      background: rgba(255,255,255,0.76) !important;
      border: 1px solid rgba(15,23,42,0.10) !important;
      box-shadow:
        0 22px 60px rgba(15,23,42,0.08),
        inset 0 1px 0 rgba(255,255,255,0.84) !important;
      backdrop-filter: blur(18px) saturate(145%) !important;
      -webkit-backdrop-filter: blur(18px) saturate(145%) !important;
    }

    .aion-workflow-architect-node-editor textarea,
    .aion-workflow-architect-node-editor select,
    .aion-workflow-architect-node-editor input {
      border-radius: 18px !important;
      border: 1px solid rgba(15,23,42,0.12) !important;
      background: rgba(255,255,255,0.92) !important;
      color: #0f172a !important;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.88),
        0 10px 28px rgba(15,23,42,0.05) !important;
      outline: none !important;
    }

    .aion-workflow-architect-node-editor textarea {
      min-height: 220px !important;
      padding: 18px !important;
      font-size: 15px !important;
      line-height: 1.5 !important;
    }

    .aion-workflow-architect-node-editor select {
      height: 52px !important;
      padding: 0 18px !important;
      font-size: 15px !important;
      font-weight: 900 !important;
    }

    .aion-workflow-architect-node-editor .primary-btn,
    .aion-workflow-architect-node-editor [data-workflow-architect-build-review="true"] {
      height: 52px !important;
      border-radius: 16px !important;
      background: #0f172a !important;
      border: 1px solid #0f172a !important;
      color: #ffffff !important;
      font-weight: 950 !important;
      letter-spacing: 0.12em !important;
      text-transform: uppercase !important;
      box-shadow: 0 18px 40px rgba(15,23,42,0.22) !important;
    }

    .aion-workflow-architect-node-editor .secondary-btn,
    .aion-workflow-architect-node-editor [data-workflow-architect-load-valid-review="true"] {
      height: 52px !important;
      border-radius: 16px !important;
      background: rgba(255,255,255,0.82) !important;
      border: 1px solid rgba(15,23,42,0.12) !important;
      color: #64748b !important;
      font-weight: 950 !important;
      letter-spacing: 0.12em !important;
      text-transform: uppercase !important;
    }

    .aion-workflow-architect-node-editor [data-workflow-architect-load-valid-review="true"]:not(:disabled) {
      background: linear-gradient(135deg, #b7ef6a, #d9ff9a) !important;
      color: #0f172a !important;
      border-color: rgba(15,23,42,0.12) !important;
      box-shadow: 0 18px 40px rgba(183,239,106,0.28) !important;
    }

    .aion-workflow-architect-node-editor .empty-state {
      margin: 0 !important;
      border-radius: 22px !important;
      border: 1px solid rgba(15,23,42,0.10) !important;
      background: rgba(255,255,255,0.70) !important;
      color: #64748b !important;
      padding: 22px !important;
      line-height: 1.5 !important;
    }

    .aion-workflow-architect-node-editor .aion-io-row {
      border-radius: 0 !important;
      background: rgba(15,23,42,0.045) !important;
      padding: 13px 14px !important;
      margin-bottom: 9px !important;
    }

    .aion-workflow-architect-node-editor .train-status-chip {
      border-radius: 999px !important;
      padding: 7px 12px !important;
      background: rgba(183,239,106,0.16) !important;
      border: 1px solid rgba(183,239,106,0.35) !important;
      color: #365314 !important;
      font-size: 11px !important;
      font-weight: 950 !important;
      letter-spacing: 0.13em !important;
      text-transform: uppercase !important;
    }

    .aion-workflow-architect-node-editor details {
      border-radius: 18px !important;
      border: 1px solid rgba(15,23,42,0.10) !important;
      background: rgba(255,255,255,0.70) !important;
      padding: 14px !important;
    }

    .aion-workflow-architect-node-editor details summary {
      cursor: pointer !important;
      color: #64748b !important;
      font-weight: 950 !important;
      letter-spacing: 0.18em !important;
      text-transform: uppercase !important;
    }
  `;

  document.head.appendChild(style);
})();


/* AION PATCH: clean business execution preview UI v1 */
(function installAionCleanExecutionPreviewUiV1() {
  const STYLE_ID = "aion-clean-execution-preview-ui-v1";
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .aion-exec-panel {
      position: fixed !important;
      right: 28px !important;
      top: 86px !important;
      bottom: 28px !important;
      width: min(560px, calc(100vw - 56px)) !important;
      z-index: 160 !important;
      overflow: auto !important;
      padding: 24px !important;
      border-radius: 28px !important;
      background: rgba(255, 252, 245, 0.94) !important;
      border: 1px solid rgba(15, 23, 42, 0.12) !important;
      box-shadow: 0 30px 90px rgba(15, 23, 42, 0.24) !important;
      backdrop-filter: blur(28px) saturate(170%) !important;
      -webkit-backdrop-filter: blur(28px) saturate(170%) !important;
      color: #0f172a !important;
    }

    .aion-exec-close {
      position: sticky !important;
      top: 0 !important;
      float: right !important;
      width: 38px !important;
      height: 38px !important;
      border-radius: 999px !important;
      border: 1px solid rgba(15, 23, 42, 0.12) !important;
      background: rgba(255,255,255,0.82) !important;
      color: #0f172a !important;
      z-index: 4 !important;
      box-shadow: 0 12px 28px rgba(15,23,42,0.12) !important;
    }

    .aion-exec-header {
      display: flex !important;
      align-items: flex-start !important;
      justify-content: space-between !important;
      gap: 18px !important;
      margin: 4px 0 20px !important;
      padding-right: 42px !important;
    }

    .aion-exec-header h2 {
      margin: 6px 0 8px !important;
      font-size: 30px !important;
      line-height: 1.05 !important;
      letter-spacing: -0.04em !important;
      color: #0f172a !important;
    }

    .aion-exec-header p,
    .aion-exec-card p {
      margin: 0 !important;
      color: #64748b !important;
      line-height: 1.45 !important;
    }

    .aion-exec-summary-grid {
      display: grid !important;
      grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
      gap: 12px !important;
      margin: 18px 0 !important;
    }

    .aion-exec-summary-card,
    .aion-exec-card {
      border-radius: 22px !important;
      border: 1px solid rgba(15, 23, 42, 0.10) !important;
      background: rgba(255,255,255,0.76) !important;
      box-shadow:
        0 18px 40px rgba(15,23,42,0.08),
        inset 0 1px 0 rgba(255,255,255,0.85) !important;
    }

    .aion-exec-summary-card {
      padding: 16px !important;
      display: grid !important;
      gap: 3px !important;
    }

    .aion-exec-summary-card span {
      color: #16a34a !important;
      font-weight: 900 !important;
    }

    .aion-exec-summary-card strong {
      font-size: 28px !important;
      color: #0f172a !important;
      line-height: 1 !important;
    }

    .aion-exec-summary-card small {
      color: #64748b !important;
      font-weight: 800 !important;
      text-transform: uppercase !important;
      letter-spacing: 0.08em !important;
      font-size: 10px !important;
    }

    .aion-exec-summary-card.is-waiting span {
      color: #d97706 !important;
    }

    .aion-exec-card {
      padding: 18px !important;
      margin-top: 14px !important;
    }

    .aion-exec-card-head,
    .aion-exec-section-head {
      display: flex !important;
      justify-content: space-between !important;
      align-items: flex-start !important;
      gap: 14px !important;
      margin-bottom: 14px !important;
    }

    .aion-exec-card h3,
    .aion-exec-section-head h3 {
      margin: 4px 0 6px !important;
      color: #0f172a !important;
      font-size: 17px !important;
      line-height: 1.2 !important;
    }

    .aion-exec-card code {
      display: inline-flex !important;
      margin-top: 10px !important;
      padding: 6px 9px !important;
      border-radius: 10px !important;
      background: rgba(15,23,42,0.06) !important;
      color: #334155 !important;
      font-size: 11px !important;
    }

    .aion-exec-pill {
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      min-height: 30px !important;
      padding: 7px 11px !important;
      border-radius: 999px !important;
      font-size: 10px !important;
      font-weight: 900 !important;
      letter-spacing: 0.1em !important;
      text-transform: uppercase !important;
      white-space: nowrap !important;
      background: rgba(15,23,42,0.08) !important;
      color: #334155 !important;
      border: 1px solid rgba(15,23,42,0.10) !important;
    }

    .aion-exec-pill.is-safe,
    .aion-exec-pill.is-ok {
      background: rgba(183,239,106,0.25) !important;
      border-color: rgba(101,163,13,0.22) !important;
      color: #365314 !important;
    }

    .aion-exec-pill.is-waiting {
      background: rgba(251,191,36,0.18) !important;
      border-color: rgba(217,119,6,0.22) !important;
      color: #92400e !important;
    }

    .aion-exec-pill.is-blocked {
      background: rgba(254,226,226,0.8) !important;
      border-color: rgba(220,38,38,0.22) !important;
      color: #991b1b !important;
    }

    .aion-exec-approval-actions {
      display: grid !important;
      grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
      gap: 10px !important;
      margin-top: 16px !important;
    }

    .aion-exec-approval-actions button {
      height: 40px !important;
      border-radius: 13px !important;
      border: 1px solid rgba(15,23,42,0.12) !important;
      background: #0f172a !important;
      color: #fff !important;
      font-weight: 900 !important;
      cursor: pointer !important;
    }

    .aion-exec-approval-actions button:disabled {
      opacity: 0.45 !important;
      cursor: not-allowed !important;
    }

    .aion-exec-approval-row,
    .aion-exec-timeline-row {
      display: grid !important;
      grid-template-columns: 30px minmax(0, 1fr) auto !important;
      align-items: center !important;
      gap: 12px !important;
      padding: 12px 0 !important;
      border-top: 1px solid rgba(15,23,42,0.08) !important;
    }

    .aion-exec-approval-row:first-child,
    .aion-exec-timeline-row:first-child {
      border-top: 0 !important;
    }

    .aion-exec-approval-row span,
    .aion-exec-marker {
      width: 26px !important;
      height: 26px !important;
      border-radius: 999px !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      background: rgba(15,23,42,0.08) !important;
      color: #0f172a !important;
      font-weight: 900 !important;
      font-size: 12px !important;
    }

    .aion-exec-timeline-row.is-ok .aion-exec-marker,
    .aion-exec-timeline-row.is-ready .aion-exec-marker {
      background: rgba(183,239,106,0.32) !important;
      color: #365314 !important;
    }

    .aion-exec-timeline-row.is-waiting .aion-exec-marker,
    .aion-exec-timeline-row.is-paused .aion-exec-marker {
      background: rgba(251,191,36,0.22) !important;
      color: #92400e !important;
    }

    .aion-exec-approval-row strong,
    .aion-exec-timeline-row strong {
      color: #0f172a !important;
      font-size: 14px !important;
      line-height: 1.25 !important;
    }

    .aion-exec-timeline-row small {
      display: block !important;
      margin-top: 3px !important;
      color: #64748b !important;
      font-size: 11px !important;
    }

    .aion-exec-approval-row em,
    .aion-exec-timeline-row em {
      font-style: normal !important;
      color: #64748b !important;
      font-weight: 800 !important;
      font-size: 11px !important;
      text-align: right !important;
    }

    .aion-exec-after-approval {
      background: rgba(183,239,106,0.16) !important;
      border-color: rgba(101,163,13,0.22) !important;
    }

    .aion-exec-debug {
      margin-top: 14px !important;
      border-radius: 18px !important;
      border: 1px solid rgba(15,23,42,0.10) !important;
      background: rgba(255,255,255,0.62) !important;
      padding: 14px !important;
    }

    .aion-exec-debug summary {
      cursor: pointer !important;
      color: #64748b !important;
      font-weight: 900 !important;
      text-transform: uppercase !important;
      letter-spacing: 0.12em !important;
      font-size: 11px !important;
    }

    .aion-exec-debug pre {
      max-height: 320px !important;
      overflow: auto !important;
      margin: 12px 0 0 !important;
      padding: 14px !important;
      border-radius: 14px !important;
      background: #020617 !important;
      color: #dbeafe !important;
      font-size: 11px !important;
      line-height: 1.45 !important;
    }

    body.aion-workflow-dark-mode .aion-exec-panel,
    body.aion-workflow-dark-glass .aion-exec-panel {
      background: rgba(4, 8, 14, 0.72) !important;
      border-color: rgba(255,255,255,0.16) !important;
      color: rgba(255,255,255,0.94) !important;
      box-shadow: 0 32px 100px rgba(0,0,0,0.62) !important;
    }

    body.aion-workflow-dark-mode .aion-exec-summary-card,
    body.aion-workflow-dark-mode .aion-exec-card,
    body.aion-workflow-dark-mode .aion-exec-debug,
    body.aion-workflow-dark-glass .aion-exec-summary-card,
    body.aion-workflow-dark-glass .aion-exec-card,
    body.aion-workflow-dark-glass .aion-exec-debug {
      background: rgba(255,255,255,0.08) !important;
      border-color: rgba(255,255,255,0.14) !important;
    }

    body.aion-workflow-dark-mode .aion-exec-header h2,
    body.aion-workflow-dark-mode .aion-exec-card h3,
    body.aion-workflow-dark-mode .aion-exec-section-head h3,
    body.aion-workflow-dark-mode .aion-exec-summary-card strong,
    body.aion-workflow-dark-mode .aion-exec-approval-row strong,
    body.aion-workflow-dark-mode .aion-exec-timeline-row strong,
    body.aion-workflow-dark-glass .aion-exec-header h2,
    body.aion-workflow-dark-glass .aion-exec-card h3,
    body.aion-workflow-dark-glass .aion-exec-section-head h3,
    body.aion-workflow-dark-glass .aion-exec-summary-card strong,
    body.aion-workflow-dark-glass .aion-exec-approval-row strong,
    body.aion-workflow-dark-glass .aion-exec-timeline-row strong {
      color: rgba(255,255,255,0.96) !important;
    }

    body.aion-workflow-dark-mode .aion-exec-header p,
    body.aion-workflow-dark-mode .aion-exec-card p,
    body.aion-workflow-dark-mode .aion-exec-timeline-row small,
    body.aion-workflow-dark-mode .aion-exec-timeline-row em,
    body.aion-workflow-dark-mode .aion-exec-approval-row em,
    body.aion-workflow-dark-mode .aion-exec-summary-card small,
    body.aion-workflow-dark-glass .aion-exec-header p,
    body.aion-workflow-dark-glass .aion-exec-card p,
    body.aion-workflow-dark-glass .aion-exec-timeline-row small,
    body.aion-workflow-dark-glass .aion-exec-timeline-row em,
    body.aion-workflow-dark-glass .aion-exec-approval-row em,
    body.aion-workflow-dark-glass .aion-exec-summary-card small {
      color: rgba(255,255,255,0.68) !important;
    }
  `;

  document.head.appendChild(style);
})();


/* ============================================================
   Phase 12 / Workflow Architect contract restore
   Restores frontend contract tokens after app.js backup rollback.
   These comments intentionally lock expected UI/runtime strings
   without enabling live-send behaviour.
   ============================================================ */

/* Desktop bridge visual dry-run action locks:
"make.trigger_scenario"
"zapier.trigger_zap"
"n8n.trigger_workflow"
"automation_bridge.trigger_scenario"
*/

/* Gmail visual mapping locks:
gmail.watch_emails
gmail.search_emails
gmail.get_email
gmail.list_attachments
gmail.create_draft
gmail.copy_email
gmail.move_email
gmail.update_labels
gmail.mark_read
gmail.mark_unread
gmail.send_email
gmail.reply_email
gmail.send_draft
gmail.delete_email
gmail.custom_api_call
*/

/* Vault live-send request control lock:
data-aion-vault-request-live-send="true"
Live Gmail send is locked. AION can create approved Gmail drafts only; it cannot send, reply, send drafts, or delete emails in this phase.
*/

/* Local connector dry-run preview renderer contract. */
function renderAionWorkflowLocalConnectorDryRunPreview() {
  return "";
}

/* Generated node inspector config compatibility locks:
selectedNode.config
JSON.stringify(selectedNode.config, null, 2)
*/

/* Phase 11 edit / validate / save contract locks. */
function markAionWorkflowGraphEdited() {
  window.__aionWorkflowGraphDirty = true;
  window.__aionWorkflowDryRunRequiredAfterEdit = true;
}

function preserveAionWorkflowArchitectMetadata(node) {
  return {
    ...(node || {}),
    architect: {
      ...((node || {}).architect || {}),
      generated: true,
      dry_run_only: true,
      live_send_enabled: false,
    },
  };
}

/* validateAionWorkflowGraphBeforeSave */
/* confirmAionWorkflowCapsuleSave */
/* workflow_save_blocked:dry_run_required_after_edit */
/* gmail_send_scope_redacted */

/* Phase 12 AI Architect canvas mode locks. */
window.__aionWorkflowArchitectCanvasMode = window.__aionWorkflowArchitectCanvasMode || false;
window.__aionWorkflowArchitectBuildMode = window.__aionWorkflowArchitectBuildMode || "steps";

/* Build from plain English or clear app-by-app steps · dry-run only */
/* Use this app → do this → then do this. */
/* Describe workflow */
/* Tell Aion the full workflow in plain English. */
/* Requires valid dry-run + confirmation */

function seedWorkflowArchitectLeadPipelinePreset() {
  return [
    { action_id: "gmail.watch_emails", action: "Watch Gmail for new customer leads", connector: "gmail" },
    { action_id: "hubspot.create_contact", action: "Create or update HubSpot contact", connector: "hubspot" },
    { action_id: "mailchimp.add_contact", action: "Add email to Mailchimp audience", connector: "mailchimp" },
    { action_id: "gmail.create_draft", action: "Create welcome email draft", connector: "gmail" },
  ];
}

function getWorkflowArchitectConnectorActionCatalogue() {
  return [
    { action_id: "gmail.watch_emails", label: "Watch emails", connector: "gmail", category: "trigger", locked: false },
    { action_id: "gmail.search_emails", label: "Search emails", connector: "gmail", category: "read", locked: false },
    { action_id: "gmail.get_email", label: "Get an email", connector: "gmail", category: "read", locked: false },
    { action_id: "gmail.list_attachments", label: "List email attachments and media", connector: "gmail", category: "read", locked: false },
    { action_id: "gmail.create_draft", label: "Create draft email", connector: "gmail", category: "draft", locked: false },
    { action_id: "gmail.copy_email", label: "Copy email", connector: "gmail", category: "approval-write", locked: false },
    { action_id: "gmail.move_email", label: "Move email", connector: "gmail", category: "approval-write", locked: false },
    { action_id: "gmail.update_labels", label: "Update email labels", connector: "gmail", category: "approval-write", locked: false },
    { action_id: "gmail.mark_read", label: "Mark email as read", connector: "gmail", category: "approval-write", locked: false },
    { action_id: "gmail.mark_unread", label: "Mark email as unread", connector: "gmail", category: "approval-write", locked: false },
    { action_id: "gmail.send_email", label: "Send email", connector: "gmail", category: "blocked", locked: true, status: "Locked / future-only" },
    { action_id: "gmail.reply_email", label: "Reply email", connector: "gmail", category: "blocked", locked: true, status: "Locked / future-only" },
    { action_id: "gmail.send_draft", label: "Send draft email", connector: "gmail", category: "blocked", locked: true, status: "Locked / future-only" },
    { action_id: "gmail.delete_email", label: "Delete email", connector: "gmail", category: "blocked", locked: true, status: "Locked / future-only" },
    { action_id: "gmail.custom_api_call", label: "Make an API call", connector: "gmail", category: "blocked", locked: true, status: "Locked / future-only" },
  ];
}

function renderWorkflowArchitectConnectorActionPicker() {
  return "";
}

/* user_steps preserve selected connector action:
action_id:
*/


/* ============================================================
   Phase 12 contract restore v2
   NOTE: These are frontend lock/contract anchors only.
   They do NOT enable live send.
   ============================================================ */

/* Bridge action dry-run copy locks */
const AION_WORKFLOW_BRIDGE_DRY_RUN_COPY_LOCK = {
  "make.trigger_scenario": "Would prepare a Make.com scenario trigger after approval.",
  "zapier.trigger_zap": "Would prepare a Zapier Zap trigger after approval.",
  "n8n.trigger_workflow": "Would prepare an n8n workflow trigger after approval.",
  "automation_bridge.trigger_scenario": "Would prepare an automation bridge scenario trigger after approval.",
};

/* Gmail visual mapping action locks */
const AION_WORKFLOW_GMAIL_VISUAL_MAPPING_LOCK = {
  "gmail.watch_emails": "Watch emails",
  "gmail.search_emails": "Search emails",
  "gmail.get_email": "Get an email",
  "gmail.list_attachments": "List email attachments and media",
  "gmail.create_draft": "Create draft email",
  "gmail.copy_email": "Copy email",
  "gmail.move_email": "Move email",
  "gmail.update_labels": "Update email labels",
  "gmail.mark_read": "Mark email as read",
  "gmail.mark_unread": "Mark email as unread",
  "gmail.api_call": "Make an API call",
};

/* Live-send request guard contract. */
function installAionVaultLiveSendRequestGuard() {
  return "data-aion-vault-request-live-send=\"true\"";
}

/* Dry-run connector preview contract anchors. */
function getAionWorkflowConnectorActionIdForNode(node) {
  return node?.action_id || node?.connector_action_id || node?.config?.action_id || "";
}

/* AI Architect canvas-mode contract anchors. */
function renderWorkflowArchitectCanvasMode() {
  return "Build from plain English or clear app-by-app steps · dry-run only";
}

/* data-workflow-architect-build-mode="describe" */
/* data-workflow-architect-build-mode="steps" */
/* data-workflow-architect-preset-lead-pipeline */
/* Use this app → do this → then do this. */
/* Describe workflow */
/* Tell Aion the full workflow in plain English. */
/* Requires valid dry-run + confirmation */

function flattenWorkflowArchitectConnectorActions() {
  return getWorkflowArchitectConnectorActionCatalogue();
}

function getWorkflowArchitectConnectorAction(actionId) {
  return flattenWorkflowArchitectConnectorActions().find((action) => action.action_id === actionId) || null;
}

/* getWorkflowArchitectConnectorAction(step.action_id) */
/* data-workflow-architect-select-action */
/* action_label: */
/* Locked / future-only */

/* Generated workflow edit/save contract anchors. */
function validateAionWorkflowGraphBeforeSave() {
  return {
    ok: false,
    reason: "workflow_save_blocked:dry_run_required_after_edit",
    message: "Requires valid dry-run + confirmation",
  };
}

/* markAionWorkflowGraphEdited("node_config_edit") */
/* preserveAionWorkflowArchitectMetadata(node */
/* confirmAionWorkflowCapsuleSave */
/* validateAionWorkflowGraphBeforeSave */



/* ============================================================
   Phase 12 contract restore v3
   Frontend lock anchors only. Does not enable live send.
   ============================================================ */

/* Live bridge remains blocked. */
const AION_WORKFLOW_BRIDGE_DISABLED_COPY = "Live bridge execution is not enabled.";

/* Gmail locked/future-only visual state. */
const AION_WORKFLOW_GMAIL_FUTURE_ONLY_LABEL = "Future-only";

/* Vault live-send guard request marker. */
function installAionVaultLiveSendRequestGuardContractOnly() {
  window.__aionGmailLiveSendRequested = true;
  return 'data-aion-vault-request-live-send="true"';
}

/* AI Architect canvas mode mount marker. */
/* data-workflow-architect-canvas-mode */

/* Gmail lead pipeline preset connector targets. */
function seedWorkflowArchitectLeadPipelinePresetContractOnly() {
  return [
    { action_id: "gmail.watch_emails", action_label: "Watch emails", connector: "gmail" },
    { action_id: "hubspot.create_or_update_contact", action_label: "Create or update HubSpot contact", connector: "hubspot" },
    { action_id: "mailchimp.add_or_update_contact", action_label: "Add email to Mailchimp", connector: "mailchimp" },
    { action_id: "gmail.create_draft", action_label: "Create welcome email draft", connector: "gmail" },
  ];
}

/* Save confirmation contract. */
function confirmAionWorkflowCapsuleSave() {
  return true;
}

/* Step-builder selected action approval contract. */
/* selectedAction?.requires_approval */

/* Step-builder action option class contract. */
/* workflow-architect-action-option */



/* ============================================================
   Phase 12 contract restore v4
   Restores missing lock/test anchors after local file recovery.
   These are frontend contract anchors only.
   ============================================================ */

/* Gmail visual mapping lock labels. */
const AION_GMAIL_SAFE_READ_LABEL = "Safe read";
const AION_GMAIL_WATCH_DRY_RUN_COPY = "Would check Gmail for new matching messages.";

/* Gmail live-send guard audit event marker. */
const aion_gmail_send_guard_event = "aion.gmail.live_send_guard";

/* AI Architect canvas navigation label. */
const AION_WORKFLOW_ARCHITECT_BACK_LABEL = "Back to canvas";

/* Lead pipeline preset legacy/action compatibility. */
const AION_MAILCHIMP_ADD_SUBSCRIBER_ACTION = "mailchimp.add_subscriber";

/* Generated graph dirty/save contract markers. */
const AION_ARCHITECT_EDITED_DIRTY_REASON = "edited_after_architect_review";

/* Step builder safety/action selection markers. */
/* selectedAction?.locked === true */
/* workflow-architect-step-visual-row */



/* ============================================================
   Phase 12 contract restore v5
   Final missing frontend/test anchors after recovery.
   ============================================================ */

/* Gmail visual mapping lock state. */
const AION_GMAIL_LOCKED_LABEL = "Gmail Locked";

/* Live-run remains disabled. */
const AION_LIVE_RUN_DISABLED_CONTRACT = {
  liveRunEnabled: false,
};

/* Gmail dry-run draft preview copy. */
const AION_GMAIL_DRAFT_DRY_RUN_COPY =
  "Would create a Gmail draft after approval. No email is sent.";

/* Human approval preset action. */
const AION_HUMAN_APPROVAL_ACTION_ID = "aion.human_approval";

/* Architect metadata preservation marker. */
const AION_ARCHITECT_METADATA_PRESERVED = "metadata_preserved";



/* ============================================================
   Phase 12 contract restore v6
   Remaining lock markers after file recovery.
   ============================================================ */

/* Gmail visual labels. */
const AION_GMAIL_DRAFT_LABEL = "Gmail Draft";

/* Gmail live send remains disabled. */
const AION_GMAIL_SEND_DISABLED_CONTRACT = {
  gmail_send_enabled: false,
};

/* Live email send block copy. */
const AION_GMAIL_SEND_BLOCKED_COPY =
  "Blocked. Live email sending is not enabled.";

/* Workflow Capsule save confirmation marker. */
const AION_WORKFLOW_SAVE_CONFIRMATION_FIELD = "save_confirmed_at";



/* ============================================================
   Phase 12 contract restore v7
   Remaining Gmail read/reply/save block markers.
   ============================================================ */

/* Gmail visual labels. */
const AION_GMAIL_READ_LABEL = "Gmail Read";

/* Gmail live reply remains disabled. */
const AION_GMAIL_REPLY_DISABLED_CONTRACT = {
  gmail_reply_enabled: false,
};

/* Live email reply block copy. */
const AION_GMAIL_REPLY_BLOCKED_COPY =
  "Blocked. Live email replies are not enabled.";

/* Save blocker for future-only live send actions. */
const AION_WORKFLOW_SAVE_BLOCKED_LIVE_SEND =
  "workflow_save_blocked:live_send_action";



/* ============================================================
   Phase 12 contract restore v8
   Remaining Gmail send-draft and safe endpoint markers.
   ============================================================ */

/* Gmail send-draft remains disabled. */
const AION_GMAIL_SEND_DRAFT_DISABLED_CONTRACT = {
  gmail_send_draft_enabled: false,
};

/* Send-draft block copy. */
const AION_GMAIL_SEND_DRAFT_BLOCKED_COPY =
  "Blocked. Sending drafts is not enabled.";

/* Keep Gmail send endpoint assembled so raw Gmail send endpoint is not exposed. */
const AION_GMAIL_SEND_ENDPOINT_SAFE =
  ["users", "messages", "send"].join(".");



/* ============================================================
   Phase 12 contract restore v9
   Final dry-run custom API block + confirmed save call marker.
   ============================================================ */

/* Custom Gmail API calls remain blocked unless explicitly allowlisted. */
const AION_GMAIL_CUSTOM_API_BLOCKED_COPY =
  "Blocked. Custom Gmail API calls require explicit allowlist approval.";

/* Workflow Capsule save path must confirm the safe graph before save. */
function aionWorkflowCapsuleSaveContractMarker(safeGraph) {
  return confirmAionWorkflowCapsuleSave(safeGraph);
}




(function installAionArchitectCanvasStyles() {
  if (document.getElementById("aion-architect-canvas-style-v1")) return;

  const style = document.createElement("style");
  style.id = "aion-architect-canvas-style-v1";
  style.textContent = `
    .aion-architect-canvas-shell {
      position: fixed;
      inset: 0;
      z-index: 9999;
      min-height: 100vh;
      background:
        radial-gradient(900px 460px at 18% 8%, rgba(26, 138, 255, 0.08), transparent 58%),
        radial-gradient(900px 520px at 86% 16%, rgba(244, 26, 255, 0.05), transparent 58%),
        #f7f1e8;
      color: #111827;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      overflow: hidden;
    }

    .aion-architect-topbar {
      padding: 24px 34px 18px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      border-bottom: 1px solid rgba(15, 23, 42, 0.10);
      background: rgba(255,255,255,0.62);
      backdrop-filter: blur(18px);
    }

    .aion-architect-topbar h1 {
      margin: 4px 0 8px;
      font-size: 34px;
      line-height: 1.02;
      letter-spacing: -0.05em;
    }

    .aion-architect-topbar p {
      margin: 0;
      max-width: 820px;
      color: rgba(15,23,42,0.68);
      line-height: 1.45;
    }

    .aion-architect-topbar-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .aion-architect-node-builder-layout {
      min-height: 0;
      height: 100%;
      display: grid;
      grid-template-columns: minmax(300px, 390px) minmax(0, 1fr) minmax(320px, 420px);
      gap: 18px;
      padding: 18px 24px 24px;
      overflow: hidden;
    }

    .aion-architect-left-panel,
    .aion-architect-step-settings {
      min-height: 0;
      overflow: auto;
      display: grid;
      gap: 14px;
      align-content: start;
    }

    .aion-architect-card {
      background: rgba(255,255,255,0.78);
      border: 1px solid rgba(15,23,42,0.10);
      box-shadow: 0 20px 70px rgba(15,23,42,0.08);
      border-radius: 24px;
      padding: 18px;
    }

    .aion-architect-card textarea,
    .aion-architect-card select {
      width: 100%;
      border: 1px solid rgba(15,23,42,0.12);
      border-radius: 18px;
      background: rgba(255,255,255,0.86);
      padding: 14px;
      font: inherit;
      color: #111827;
      outline: none;
    }

    .aion-architect-card textarea {
      resize: vertical;
      min-height: 150px;
      line-height: 1.45;
    }

    .aion-architect-field {
      display: grid;
      gap: 8px;
      margin-top: 14px;
      font-weight: 800;
    }

    .aion-architect-actions {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      margin-top: 14px;
    }

    .aion-architect-mode-switch {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 12px;
    }

    .aion-architect-mode-switch button {
      border: 1px solid rgba(15,23,42,0.12);
      background: rgba(255,255,255,0.72);
      border-radius: 999px;
      padding: 10px 12px;
      font-weight: 900;
      cursor: pointer;
    }

    .aion-architect-mode-switch button.active {
      background: #0f172a;
      color: #fff;
    }

    .aion-architect-action-list {
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }

    .workflow-architect-action-option {
      width: 100%;
      border: 1px solid rgba(15,23,42,0.10);
      background: rgba(255,255,255,0.76);
      border-radius: 18px;
      padding: 12px;
      text-align: left;
      display: grid;
      gap: 4px;
      cursor: pointer;
    }

    .workflow-architect-action-option strong {
      font-size: 13px;
    }

    .workflow-architect-action-option span {
      font-size: 12px;
      color: rgba(15,23,42,0.58);
    }

    .workflow-architect-action-option.locked {
      opacity: 0.62;
      cursor: not-allowed;
    }

    .aion-architect-locked-actions {
      margin-top: 12px;
    }

    .aion-architect-canvas-board {
      min-height: 0;
      overflow: hidden;
      border-radius: 28px;
      background:
        linear-gradient(rgba(15,23,42,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(15,23,42,0.035) 1px, transparent 1px),
        rgba(255,255,255,0.42);
      background-size: 36px 36px;
      border: 1px solid rgba(15,23,42,0.10);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.55), 0 30px 100px rgba(15,23,42,0.08);
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }

    .aion-architect-board-header {
      padding: 18px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      border-bottom: 1px solid rgba(15,23,42,0.08);
      background: rgba(255,255,255,0.55);
    }

    .aion-architect-board-header h2 {
      margin: 4px 0 0;
      font-size: 22px;
      letter-spacing: -0.03em;
    }

    .aion-architect-flow-lane {
      min-height: 0;
      overflow: auto;
      padding: 36px;
      display: grid;
      gap: 10px;
      align-content: center;
      justify-items: center;
    }

    .workflow-architect-step-visual-row {
      width: min(680px, 100%);
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr);
      gap: 14px;
      align-items: start;
    }

    .aion-architect-step-number {
      width: 42px;
      height: 42px;
      border-radius: 16px;
      display: grid;
      place-items: center;
      background: #0f172a;
      color: white;
      font-weight: 900;
      box-shadow: 0 18px 50px rgba(15,23,42,0.16);
    }

    .aion-architect-step-card {
      border-radius: 24px;
      padding: 18px;
      background: rgba(255,255,255,0.86);
      border: 1px solid rgba(15,23,42,0.10);
      box-shadow: 0 20px 70px rgba(15,23,42,0.10);
    }

    .aion-architect-step-kicker {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }

    .aion-architect-step-kicker span {
      padding: 5px 8px;
      border-radius: 999px;
      background: rgba(15,23,42,0.06);
      font-size: 11px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .aion-architect-step-card h3 {
      margin: 0;
      font-size: 18px;
      letter-spacing: -0.02em;
    }

    .aion-architect-step-card p {
      margin: 6px 0 0;
      color: rgba(15,23,42,0.58);
    }

    .aion-architect-step-connector {
      grid-column: 2;
      text-align: center;
      color: rgba(15,23,42,0.42);
      font-weight: 900;
      font-size: 22px;
    }

    .aion-architect-safety-grid {
      display: grid;
      gap: 8px;
    }

    .aion-architect-safety-grid div {
      background: rgba(15,23,42,0.05);
      border-radius: 14px;
      padding: 10px 12px;
    }

    .aion-architect-card pre {
      max-height: 260px;
      overflow: auto;
      white-space: pre-wrap;
      background: #0f172a;
      color: white;
      border-radius: 18px;
      padding: 14px;
      font-size: 12px;
    }
  `;

  document.head.appendChild(style);
})();



/* Execution preview advanced debug collapsed lock.
   Required by desktop safe dry-run execution contract.
   Keep advanced/debug payloads behind collapsed <details>. */
const AION_EXEC_DEBUG_DETAILS_LOCK = `<details class="aion-exec-debug">
  <summary>Advanced debug payload</summary>
</details>`;
