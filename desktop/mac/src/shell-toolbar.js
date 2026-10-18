(() => {
  if (window.__tessarisShellToolbarInstalled) return;
  window.__tessarisShellToolbarInstalled = true;

  const toolbar = document.querySelector("[data-tessaris-window-toolbar='true']");
  if (!toolbar) return;

  const teamStrip = toolbar.querySelector("[data-tessaris-window-team-strip='true']");
  const modelSelect = toolbar.querySelector("[data-tessaris-active-model]");
  let teamSyncFrame = 0;
  let activeModelSelection = null;

  const activeWorkspaceId = () => String(
    window.desktopStore?.state?.workspaceId ||
    window.AionBusinessContainerClient?.resolveBusinessId?.() ||
    "home-fixed"
  );

  const modelOverrideKey = () => `tessaris.active-model.v1:${activeWorkspaceId()}`;

  const publishActiveModel = (selection) => {
    activeModelSelection = selection || null;
    window.__tessarisActiveModelSelection = activeModelSelection;
    if (activeModelSelection?.provider_id && typeof window.setAionChatSelectedEngineV1 === "function") {
      window.setAionChatSelectedEngineV1(activeModelSelection.provider_id);
    }
    window.dispatchEvent(new CustomEvent("tessaris-active-model-changed", { detail: activeModelSelection }));
  };

  window.getTessarisActiveModelSelection = () => activeModelSelection ? { ...activeModelSelection } : null;

  const refreshModelSwitcher = async () => {
    if (!modelSelect) return;
    const workspaceId = activeWorkspaceId();
    try {
      const response = await fetch(`http://127.0.0.1:8080/api/boardroom/providers/status?workspace_id=${encodeURIComponent(workspaceId)}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`provider_status_${response.status}`);
      const payload = await response.json();
      const models = Array.isArray(payload?.providers)
        ? payload.providers.filter((item) => item?.connected === true || (item?.id === "local_model" && item?.installed === true))
        : [];
      let override = null;
      try { override = JSON.parse(window.sessionStorage.getItem(modelOverrideKey()) || "null"); } catch {}
      const lead = payload?.lead_model || null;
      const wantedProvider = String(override?.provider_id || lead?.provider_id || "");
      const selected = models.find((item) => String(item.id) === wantedProvider) || null;
      const options = [];
      if (!lead?.provider_id) {
        const placeholder = Object.assign(document.createElement("option"), {
          value: "",
          textContent: "Choose a model",
          disabled: true,
        });
        options.push(placeholder);
      } else if (!selected && !override) {
        options.push(Object.assign(document.createElement("option"), {
          value: "",
          textContent: "Default model unavailable",
        }));
      }
      options.push(...models.map((item) => {
              const option = document.createElement("option");
              const providerLabel = String(item.label || item.id || "AI model");
              const modelLabel = String(item.model || "").trim();
              const displayLabel = modelLabel && !providerLabel.toLowerCase().includes(modelLabel.toLowerCase())
                ? `${providerLabel} · ${modelLabel}`
                : providerLabel;
              option.value = String(item.id || "");
              const availability = item.connected === true ? "" : " · Available — select to start";
              option.textContent = `${item.is_lead ? "★ " : ""}${displayLabel}${availability}`;
              option.dataset.modelId = String(item.model || "");
              option.dataset.displayLabel = displayLabel;
              option.dataset.isLead = item.is_lead ? "true" : "false";
              option.dataset.connected = item.connected === true ? "true" : "false";
              option.dataset.workspaceSelected = item.id !== "local_model" || item.workspace_selected === true ? "true" : "false";
              return option;
            }));
      if (!options.length) options.push(Object.assign(document.createElement("option"), { value: "", textContent: "No live models" }));
      modelSelect.replaceChildren(...options);
      modelSelect.value = selected?.id || "";
      // The toolbar is always available for a temporary live-model choice.
      // Connections remains the only surface that persists the workspace lead.
      modelSelect.disabled = models.length === 0;
      publishActiveModel(selected ? {
        workspace_id: workspaceId,
        provider_id: String(selected.id),
        model_id: String(selected.model || ""),
        label: String(selected.label || selected.model || selected.id),
        source: override ? "toolbar_session_override" : "connections_lead",
      } : null);
    } catch (_) {
      modelSelect.replaceChildren(Object.assign(document.createElement("option"), { value: "", textContent: "Models unavailable" }));
      modelSelect.disabled = true;
      publishActiveModel(null);
    }
  };

  window.refreshTessarisModelSwitcher = refreshModelSwitcher;
  window.addEventListener("tessaris-lead-model-changed", () => void refreshModelSwitcher());
  modelSelect?.addEventListener("focus", () => void refreshModelSwitcher(), { once: true });

  modelSelect?.addEventListener("change", async () => {
    const option = modelSelect.options[modelSelect.selectedIndex];
    const selection = {
      workspace_id: activeWorkspaceId(),
      provider_id: String(modelSelect.value || ""),
      model_id: String(option?.dataset?.modelId || ""),
      label: String(option?.dataset?.displayLabel || option?.textContent || modelSelect.value || "").replace(/^★\s*/, ""),
      source: "toolbar_session_override",
    };
    if (selection.provider_id === "local_model" && option?.dataset?.workspaceSelected !== "true") {
      const originalLabel = option.textContent;
      modelSelect.disabled = true;
      option.textContent = `${selection.label} · Starting…`;
      try {
        const response = await fetch("http://127.0.0.1:8080/api/vault/local-models/select", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-Aion-Vault-Intent": "select-local-model-v1",
          },
          body: JSON.stringify({ workspace_id: selection.workspace_id, model_id: selection.model_id }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(String(body?.detail || "The local model could not be started."));
        option.dataset.workspaceSelected = "true";
        option.dataset.connected = "true";
        option.textContent = selection.label;
      } catch (error) {
        option.textContent = `${originalLabel} · Start failed`;
        modelSelect.title = String(error?.message || error);
        modelSelect.disabled = false;
        return;
      }
      modelSelect.disabled = false;
    }
    const returnsToDefault = option?.dataset?.isLead === "true";
    try {
      if (returnsToDefault) window.sessionStorage.removeItem(modelOverrideKey());
      else window.sessionStorage.setItem(modelOverrideKey(), JSON.stringify(selection));
    } catch {}
    publishActiveModel({ ...selection, source: returnsToDefault ? "connections_lead" : "toolbar_session_override" });
  });

  const syncTeamHeader = () => {
    teamSyncFrame = 0;
    // Keep the native title bar intentionally quiet. Board, executive-team and
    // department navigation belongs to the workspace below it, where it has
    // enough room for readable labels and accessible hover help.
    teamStrip?.replaceChildren();
  };

  const scheduleTeamHeaderSync = () => {
    if (teamSyncFrame) return;
    teamSyncFrame = window.requestAnimationFrame(syncTeamHeader);
  };

  if (document.body) {
    new MutationObserver(scheduleTeamHeaderSync).observe(document.body, {
      childList: true,
      subtree: true,
    });
  }
  scheduleTeamHeaderSync();

  const pilotControl = toolbar.querySelector("[data-tessaris-pilot-control='true']");
  const pilotDashboardLaunch = pilotControl?.querySelector("[data-tessaris-pilot-dashboard-launch='true']");
  const pilotToggle = pilotControl?.querySelector("[data-tessaris-pilot-toggle='true']");
  const pilotPanel = pilotControl?.querySelector("[data-tessaris-pilot-panel='true']");
  const pilotMessage = pilotControl?.querySelector("[data-tessaris-pilot-message]");
  const pilotRetry = pilotControl?.querySelector("[data-tessaris-pilot-action='retry']");
  const microphoneButton = pilotControl?.querySelector("[data-tessaris-pilot-action='toggle-microphone']");
  let pilotStatus = null;
  let pilotBusy = false;

  const setPilotStatusRow = (selector, value, fallbackState, fallbackLabel) => {
    const row = pilotControl?.querySelector(selector);
    if (!row) return;
    row.dataset.state = value?.state || fallbackState;
    const label = row.querySelector("span");
    if (label) label.textContent = value?.label || fallbackLabel;
    if (value?.detail) row.title = value.detail;
    else row.removeAttribute("title");
  };

  const applyPilotStatus = (status) => {
    pilotStatus = status || null;
    setPilotStatusRow(
      "[data-tessaris-pilot-service-status]",
      status?.service,
      "unavailable",
      "Pilot unavailable",
    );
    setPilotStatusRow(
      "[data-tessaris-pilot-microphone-status]",
      status?.microphone,
      "off",
      "Microphone off",
    );
    setPilotStatusRow(
      "[data-tessaris-pilot-tv-status]",
      status?.tv,
      "unavailable",
      "TV unavailable",
    );
    if (microphoneButton) {
      microphoneButton.textContent = status?.microphone?.state === "listening"
        ? "Turn microphone off"
        : "Turn microphone on";
    }
    pilotDashboardLaunch?.setAttribute("data-state", status?.service?.state || "unavailable");
    if (pilotMessage && status?.message && !pilotBusy) pilotMessage.textContent = status.message;
    if (pilotRetry && status?.ok) pilotRetry.hidden = true;
  };

  const refreshPilotStatus = async ({ quiet = false } = {}) => {
    if (!window.aionDesktop?.getPilotStatus) return;
    if (!quiet && pilotMessage) pilotMessage.textContent = "Checking the local Pilot service…";
    try {
      applyPilotStatus(await window.aionDesktop.getPilotStatus());
    } catch (error) {
      applyPilotStatus(null);
      if (pilotMessage) pilotMessage.textContent = error?.message || "Pilot status could not be checked.";
    }
  };

  const setPilotBusy = (busy, message = "") => {
    pilotBusy = busy;
    pilotControl?.querySelectorAll("[data-tessaris-pilot-action]").forEach((button) => {
      button.disabled = busy;
    });
    pilotControl?.classList.toggle("is-busy", busy);
    if (message && pilotMessage) pilotMessage.textContent = message;
  };

  const showPilotFailure = (message, { retry = false } = {}) => {
    if (pilotMessage) pilotMessage.textContent = message || "Pilot could not start. Check the local service and try again.";
    if (pilotRetry) pilotRetry.hidden = !retry;
  };

  const runPilotAction = async (action) => {
    if (pilotBusy || !window.aionDesktop) return;
    const opensDashboard = action === "open-dashboard" || action === "retry";
    const serviceAction = action === "toggle-microphone"
      ? (pilotStatus?.microphone?.state === "listening" ? "microphone-off" : "microphone-on")
      : action;
    const busyMessages = {
      "open-dashboard": "Starting Pilot if needed, then opening the dashboard…",
      retry: "Retrying the local Pilot service…",
      "microphone-on": "Asking Pilot to turn the microphone on…",
      "microphone-off": "Turning the Pilot microphone off…",
      "reconnect-tv": "Checking and reconnecting the television…",
      "open-games": "Opening Games on the confirmed television…",
      "open-ai-tv": "Opening AI TV on the confirmed television…",
    };
    setPilotBusy(true, busyMessages[serviceAction] || "Contacting Pilot…");
    if (pilotRetry) pilotRetry.hidden = true;
    try {
      const response = opensDashboard
        ? await window.aionDesktop.openPilotDashboard()
        : await window.aionDesktop.runPilotControl(serviceAction);
      if (!response?.ok) throw new Error(response?.message || "Pilot could not complete that action.");
      applyPilotStatus(response.status);
      if (pilotMessage) {
        pilotMessage.textContent = opensDashboard
          ? "Pilot Dashboard is open. This control will reuse it next time."
          : "Pilot confirmed the requested control.";
      }
      if (serviceAction === "microphone-on") {
        window.setTimeout(() => void refreshPilotStatus({ quiet: true }), 1400);
      }
    } catch (error) {
      showPilotFailure(
        error?.message || "Pilot could not complete that action. Please try again.",
        { retry: opensDashboard },
      );
      await refreshPilotStatus({ quiet: true });
      if (pilotMessage && error?.message) pilotMessage.textContent = error.message;
      if (pilotRetry) {
        pilotRetry.hidden = !(opensDashboard || pilotStatus?.service?.state !== "online");
      }
    } finally {
      setPilotBusy(false);
    }
  };

  pilotToggle?.addEventListener("click", (event) => {
    event.stopPropagation();
    const opening = Boolean(pilotPanel?.hidden);
    if (pilotPanel) pilotPanel.hidden = !opening;
    pilotToggle.setAttribute("aria-expanded", String(opening));
    if (opening) void refreshPilotStatus();
  });
  pilotControl?.querySelector("[data-tessaris-pilot-close='true']")?.addEventListener("click", () => {
    if (pilotPanel) pilotPanel.hidden = true;
    pilotToggle?.setAttribute("aria-expanded", "false");
  });
  pilotControl?.addEventListener("click", (event) => {
    const actionButton = event.target.closest?.("[data-tessaris-pilot-action]");
    if (!actionButton) return;
    event.stopPropagation();
    const action = actionButton.getAttribute("data-tessaris-pilot-action") || "";
    if (action === "open-dashboard" && pilotPanel) {
      pilotPanel.hidden = false;
      pilotToggle?.setAttribute("aria-expanded", "true");
    }
    void runPilotAction(action);
  });
  document.addEventListener("click", (event) => {
    if (!pilotPanel || pilotPanel.hidden || pilotControl?.contains(event.target)) return;
    pilotPanel.hidden = true;
    pilotToggle?.setAttribute("aria-expanded", "false");
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !pilotPanel || pilotPanel.hidden) return;
    pilotPanel.hidden = true;
    pilotToggle?.setAttribute("aria-expanded", "false");
    pilotToggle?.focus();
  });
  void refreshPilotStatus({ quiet: true });
  window.setInterval(() => void refreshPilotStatus({ quiet: true }), 8000);

  toolbar.addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-tessaris-shell-action]");
    if (!button) return;

    const action = button.getAttribute("data-tessaris-shell-action");
    if (action === "back") {
      window.history.back();
      return;
    }
    if (action === "forward") {
      window.history.forward();
      return;
    }
    if (action === "reload") {
      window.location.reload();
      return;
    }
    if (action === "sidebar") {
      document
        .querySelector("[data-aion-workflow-sidebar-toggle='true']")
        ?.click();
    }
  });
})();
