(function installAionBoardroomSeatConversation(global) {
  "use strict";

  if (global.AionBoardroomSeatConversation) return;

  const API_BASE = "http://127.0.0.1:8080";
  const DEPARTMENTS = new Set(["marketing", "sales", "finance", "operations", "support", "hr"]);
  const session = {
    seat: null,
    messages: [],
    recording: null,
    stream: null,
    chunks: [],
    busy: false,
  };

  const departmentCopy = {
    marketing: {
      title: "Marketing Agent",
      greeting: "Hello Kevin. I’m your Marketing agent. Would you like a campaign and conversion update, or do you want me to prepare a marketing task?",
      suggestions: ["Give me a marketing update", "What is converting today?", "Prepare a new campaign task"],
    },
    sales: {
      title: "Sales Agent",
      greeting: "Hello Kevin. I’m your Sales agent. Would you like a pipeline update, or do you want me to prepare a quote, follow-up or customer task?",
      suggestions: ["Give me today’s sales update", "Prepare a customer quote", "Show me enquiries needing action"],
    },
    finance: {
      title: "Finance Agent",
      greeting: "Hello Kevin. I’m your Finance agent. Would you like a cash and invoice update, or do you want me to prepare a finance task for approval?",
      suggestions: ["Give me a finance update", "Show overdue invoices", "Prepare an invoice follow-up"],
    },
    operations: {
      title: "Operations Agent",
      greeting: "Hello Kevin. I’m your Operations agent. Would you like a rundown of today’s work across the business, or do you want me to coordinate a task?",
      suggestions: ["Give me today’s business rundown", "What needs attention now?", "Prepare an operations task"],
    },
    support: {
      title: "Support Agent",
      greeting: "Hello Kevin. I’m your Support agent. Would you like an update on open customer issues, or do you want me to prepare a response or escalation?",
      suggestions: ["Give me a support update", "Show urgent customer issues", "Prepare a customer response"],
    },
    hr: {
      title: "People Agent",
      greeting: "Hello Kevin. I’m your People agent. Would you like a workforce and capacity update, or do you want me to prepare a people task?",
      suggestions: ["Give me a workforce update", "Show capacity risks", "Prepare a people task"],
    },
  };

  const seatVoices = {
    marketing: "Samantha",
    sales: "Daniel",
    finance: "Moira",
    operations: "Rishi",
    support: "Karen",
    hr: "Tessa",
    aion: "Samantha",
    ceo: "Daniel",
    openai: "Daniel",
    gemini: "Karen",
    gemma: "Moira",
  };

  function clean(value) {
    return String(value == null ? "" : value).trim();
  }

  function escapeHtml(value) {
    return clean(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function seatKey() {
    return clean(session.seat?.key || session.seat?.providerId).toLowerCase();
  }

  function isExecutive() {
    return clean(session.seat?.teamMode).toLowerCase() === "executive" || DEPARTMENTS.has(seatKey());
  }

  function seatProfile(seat) {
    const key = clean(seat?.key || seat?.providerId).toLowerCase();
    if (DEPARTMENTS.has(key)) return departmentCopy[key];
    const label = clean(seat?.label) || (key === "aion" ? "AION" : "Board Adviser");
    return {
      title: label,
      greeting: key === "ceo"
        ? "Hello Kevin. This is the Chair’s seat. What would you like the Board to review, challenge or turn into a decision?"
        : `Hello Kevin. You’re speaking with ${label}. What would you like me to review, challenge or advise you on?`,
      suggestions: ["Review the business now", "Challenge the current plan", "What should I do next?"],
    };
  }

  function storageKey() {
    return `tessaris.boardroom.conversation.${clean(session.seat?.teamMode)}.${seatKey()}`;
  }

  function loadHistory() {
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey()) || "[]");
      session.messages = Array.isArray(parsed) ? parsed.slice(-30) : [];
    } catch {
      session.messages = [];
    }
  }

  function saveHistory() {
    try { localStorage.setItem(storageKey(), JSON.stringify(session.messages.slice(-30))); } catch {}
  }

  async function speak(text) {
    const line = clean(text).slice(0, 650);
    if (!line) return;
    try {
      if (typeof global.aionDesktop?.playSystemVoice === "function") {
        await global.aionDesktop.playSystemVoice({
          text: line,
          voice: seatVoices[seatKey()] || "Samantha",
          rate: 190,
        });
        return;
      }
      if (typeof global.aionDesktop?.playLocalVoice === "function") {
        await global.aionDesktop.playLocalVoice({ text: line, voice: "af_heart" });
      }
    } catch (error) {
      console.warn("[AION] Boardroom seat voice unavailable", error);
    }
  }

  function stopRecordingTracks() {
    try { session.stream?.getTracks?.().forEach((track) => track.stop()); } catch {}
    session.stream = null;
  }

  function render() {
    const old = document.getElementById("aionBoardroomSeatConversation");
    if (old) old.remove();
    if (!session.seat) return;

    const profile = seatProfile(session.seat);
    const overlay = document.createElement("section");
    overlay.id = "aionBoardroomSeatConversation";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.innerHTML = `
      <style>
        #aionBoardroomSeatConversation{position:fixed;inset:0;z-index:100000;background:rgba(15,42,67,.25);display:flex;justify-content:flex-end;font-family:Inter,system-ui,-apple-system,sans-serif}
        #aionBoardroomSeatConversation .absc-panel{width:min(520px,94vw);height:100%;background:#fff;border-left:1px solid #b8d9e7;box-shadow:-18px 0 48px rgba(15,42,67,.18);display:flex;flex-direction:column}
        #aionBoardroomSeatConversation .absc-head{padding:22px 22px 17px;border-bottom:1px solid #d9ebf2;background:#f5fbfd}
        #aionBoardroomSeatConversation .absc-kicker{font-size:11px;font-weight:900;letter-spacing:.2em;color:#0f766e;text-transform:uppercase}
        #aionBoardroomSeatConversation h2{margin:7px 0 3px;font-size:26px;color:#102a43}
        #aionBoardroomSeatConversation .absc-sub{color:#58748a;font-size:13px}
        #aionBoardroomSeatConversation .absc-close{position:absolute;right:18px;top:16px;border:1px solid #aacddd;background:#fff;width:38px;height:38px;font-size:20px;cursor:pointer}
        #aionBoardroomSeatConversation .absc-boundary{margin:12px 22px 0;padding:10px 12px;border-left:4px solid #f59e0b;background:#fff8e6;color:#6b4b00;font-size:12px;line-height:1.45}
        #aionBoardroomSeatConversation .absc-messages{flex:1;overflow:auto;padding:18px 22px;display:flex;flex-direction:column;gap:12px}
        #aionBoardroomSeatConversation .absc-msg{max-width:88%;padding:12px 14px;border:1px solid #cfe3ec;color:#29465b;line-height:1.48;white-space:pre-wrap}
        #aionBoardroomSeatConversation .absc-msg.user{align-self:flex-end;background:#eaf6fb;border-color:#90c7dc}
        #aionBoardroomSeatConversation .absc-msg.assistant{align-self:flex-start;background:#fff}
        #aionBoardroomSeatConversation .absc-engine{display:block;margin-top:8px;font-size:10px;font-weight:850;letter-spacing:.08em;text-transform:uppercase;color:#6b8798}
        #aionBoardroomSeatConversation .absc-suggestions{padding:0 22px 12px;display:flex;gap:8px;flex-wrap:wrap}
        #aionBoardroomSeatConversation .absc-suggestion{border:1px solid #93bfd0;background:#f6fbfd;color:#29465b;padding:8px 10px;font-weight:750;cursor:pointer}
        #aionBoardroomSeatConversation .absc-compose{border-top:1px solid #d9ebf2;padding:14px 22px 20px;background:#f8fcfd}
        #aionBoardroomSeatConversation textarea{width:100%;min-height:84px;box-sizing:border-box;border:1px solid #8fb8c8;padding:12px;font:inherit;color:#102a43;resize:vertical;background:#fff}
        #aionBoardroomSeatConversation .absc-actions{display:flex;gap:9px;margin-top:10px}
        #aionBoardroomSeatConversation button{font-family:inherit}
        #aionBoardroomSeatConversation .absc-send{flex:1;border:1px solid #0f6f86;background:#0f6f86;color:#fff;padding:12px;font-weight:900;letter-spacing:.06em;cursor:pointer}
        #aionBoardroomSeatConversation .absc-mic{border:1px solid #8fb8c8;background:#fff;color:#29465b;padding:12px 16px;font-weight:850;cursor:pointer}
        #aionBoardroomSeatConversation .absc-mic.recording{background:#fff1f2;border-color:#fb7185;color:#9f1239}
        #aionBoardroomSeatConversation button:disabled{opacity:.55;cursor:wait}
      </style>
      <div class="absc-panel">
        <button class="absc-close" type="button" aria-label="Close">×</button>
        <header class="absc-head">
          <div class="absc-kicker">${isExecutive() ? "Executive team conversation" : "Board adviser conversation"}</div>
          <h2>${escapeHtml(profile.title)}</h2>
          <div class="absc-sub">${escapeHtml(session.seat.role || (isExecutive() ? "Department-specific AION agent" : "Connected Board member"))} · live business context</div>
        </header>
        <div class="absc-boundary"><strong>Governed action:</strong> advice and drafts can be created here. Messages, invoices, payments, bookings, adverts and other external actions still require the business’s configured approval.</div>
        <div class="absc-messages">
          ${session.messages.map((item) => `<div class="absc-msg ${item.role === "user" ? "user" : "assistant"}">${escapeHtml(item.text)}${item.provider ? `<span class="absc-engine">AION reasoning route · ${escapeHtml(item.provider)}</span>` : ""}</div>`).join("")}
          ${session.busy ? '<div class="absc-msg assistant">Checking the live business context…</div>' : ""}
        </div>
        <div class="absc-suggestions">
          ${profile.suggestions.map((text) => `<button type="button" class="absc-suggestion" data-suggestion="${escapeHtml(text)}">${escapeHtml(text)}</button>`).join("")}
        </div>
        <div class="absc-compose">
          <textarea aria-label="Talk to this agent" placeholder="Ask for an update or describe the task you want prepared…"></textarea>
          <div class="absc-actions">
            <button type="button" class="absc-mic ${session.recording ? "recording" : ""}">${session.recording ? "Stop & transcribe" : "Speak"}</button>
            <button type="button" class="absc-send" ${session.busy ? "disabled" : ""}>${session.busy ? "Working…" : "Send"}</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    const messagePane = overlay.querySelector(".absc-messages");
    if (messagePane) messagePane.scrollTop = messagePane.scrollHeight;
    overlay.querySelector(".absc-close")?.addEventListener("click", close);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
    overlay.querySelectorAll("[data-suggestion]").forEach((button) => {
      button.addEventListener("click", () => send(button.getAttribute("data-suggestion")));
    });
    const textarea = overlay.querySelector("textarea");
    overlay.querySelector(".absc-send")?.addEventListener("click", () => send(textarea?.value));
    textarea?.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") send(textarea.value);
    });
    overlay.querySelector(".absc-mic")?.addEventListener("click", toggleRecording);
  }

  function currentContextPacket() {
    try {
      if (typeof global.buildAionBoardroomSessionPacket === "function") {
        const packet = global.buildAionBoardroomSessionPacket("seat_conversation") || {};
        return {
          business_map_snapshot: packet.business_map_snapshot || null,
          business_map_confirmation: packet.business_map_confirmation || null,
          canonical_context_envelope: packet.canonical_context_envelope || null,
          department_intelligence_packet: packet.department_intelligence_packet || {},
          business_context_lines: Array.isArray(packet.business_context_packet?.lines) ? packet.business_context_packet.lines : [],
          department_context_lines: Array.isArray(packet.department_context_packet?.lines) ? packet.department_context_packet.lines : [],
        };
      }
    } catch (error) {
      console.warn("[AION] Could not assemble full seat context", error);
    }
    return { boardroom_snapshot: session.seat?.snapshot || {} };
  }

  async function connectedProviderIds() {
    try {
      const response = await fetch(`${API_BASE}/api/boardroom/providers/status`);
      const payload = await response.json();
      return (Array.isArray(payload?.providers) ? payload.providers : [])
        .filter((provider) => provider?.connected === true)
        .map((provider) => clean(provider.id))
        .filter(Boolean);
    } catch {
      return [];
    }
  }

  async function chooseProviderCandidates() {
    const key = seatKey();
    const connected = await connectedProviderIds();
    if (!isExecutive() && !["ceo", "aion"].includes(key)) {
      return connected.includes(key) ? [key] : [];
    }
    let selected = [];
    try {
      if (typeof global.getAionLiveSelectedBoardroomProviderIdsV2 === "function") {
        selected = global.getAionLiveSelectedBoardroomProviderIdsV2();
      }
    } catch {}
    return Array.from(new Set([
      ...selected.filter((id) => connected.includes(id)),
      ...connected,
    ])).filter(Boolean);
  }

  function friendlyProviderFailure(reason, providerId) {
    const raw = clean(reason);
    if (/429|rate.?limit|quota/i.test(raw)) {
      return `${providerId || "The selected provider"} is temporarily rate-limited`;
    }
    if (/credit|billing|insufficient/i.test(raw)) {
      return `${providerId || "The selected provider"} has no available API credit`;
    }
    return raw || `${providerId || "The selected provider"} did not return an answer`;
  }

  function structuredReply(response) {
    const structured = response?.structured || {};
    const position = clean(structured.position || response?.content);
    const recommendations = Array.isArray(structured.recommendations) ? structured.recommendations.slice(0, 3) : [];
    const missing = Array.isArray(structured.missing_inputs) ? structured.missing_inputs.slice(0, 2) : [];
    return [
      position,
      recommendations.length ? `Next steps:\n${recommendations.map((line) => `• ${line}`).join("\n")}` : "",
      missing.length ? `I still need:\n${missing.map((line) => `• ${line}`).join("\n")}` : "",
    ].filter(Boolean).join("\n\n");
  }

  async function send(value) {
    const userText = clean(value);
    if (!userText || session.busy) return;
    session.messages.push({ role: "user", text: userText, at: new Date().toISOString() });
    session.busy = true;
    saveHistory();
    render();

    try {
      const providerCandidates = await chooseProviderCandidates();
      if (!providerCandidates.length) throw new Error("No connected Board intelligence provider is available. Connect one in Settings, then try again.");
      const key = seatKey();
      const profile = seatProfile(session.seat);
      const history = session.messages.slice(-10).map((item) => ({ role: item.role, text: item.text }));
      const objective = isExecutive()
        ? `Act as the Tessaris ${profile.title} for this business. Answer the founder's latest message conversationally and specifically from verified live context: ${userText}. If this requests an external action, do not claim it happened. Explain the exact draft or task you can prepare and the approval needed. Keep position to at most four spoken sentences; put up to three concrete actions in recommendations.`
        : `The founder is speaking directly to ${profile.title}. Respond as this selected provider, using verified live business context: ${userText}. Do not claim an external action happened. Keep position to at most four spoken sentences; put up to three concrete actions in recommendations.`;
      let providerResponse = null;
      let providerId = "";
      const providerFailures = [];
      for (const candidate of providerCandidates) {
        const response = await fetch(`${API_BASE}/api/boardroom/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({
            business_id: "home-fixed",
            session_type: isExecutive() ? `executive_${key}_conversation` : `board_${key}_conversation`,
            requested_providers: [candidate],
            objective,
            context_packet: {
              ...currentContextPacket(),
              selected_seat: { key, label: profile.title, team_mode: session.seat.teamMode },
              conversation_history: history,
              approval_boundary: "Prepare or advise only. No external action without configured authority and approval.",
            },
            founder_feedback: { latest_message: userText },
          }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          providerFailures.push(friendlyProviderFailure(payload?.detail || payload?.error || `HTTP ${response.status}`, candidate));
          continue;
        }
        providerResponse = (Array.isArray(payload?.responses) ? payload.responses : []).find((item) => item?.status === "succeeded") || null;
        if (providerResponse) {
          providerId = candidate;
          break;
        }
        const reason = (payload?.responses || []).map((item) => item?.reason).filter(Boolean).join(", ");
        providerFailures.push(friendlyProviderFailure(reason, candidate));
      }
      if (!providerResponse) {
        throw new Error(providerFailures.join("; ") || "The selected intelligence provider did not return an answer.");
      }
      const reply = structuredReply(providerResponse);
      session.messages.push({ role: "assistant", text: reply, provider: providerId, at: new Date().toISOString() });
      session.busy = false;
      saveHistory();
      render();
      void speak(clean(providerResponse?.structured?.position || reply));
    } catch (error) {
      session.messages.push({ role: "assistant", text: `I couldn’t complete that live context check: ${clean(error?.message || error)}`, at: new Date().toISOString() });
      session.busy = false;
      saveHistory();
      render();
    }
  }

  async function toggleRecording() {
    if (session.recording?.state && session.recording.state !== "inactive") {
      session.recording.stop();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") return;
    try {
      const permission = await global.aionDesktop?.requestMicrophonePermission?.();
      if (permission && permission.granted !== true) throw new Error("Microphone permission was not granted.");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported?.("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      session.stream = stream;
      session.recording = recorder;
      session.chunks = [];
      recorder.ondataavailable = (event) => { if (event.data?.size) session.chunks.push(event.data); };
      recorder.onstop = async () => {
        stopRecordingTracks();
        const chunks = session.chunks.splice(0);
        session.recording = null;
        render();
        if (!chunks.length) return;
        try {
          const form = new FormData();
          form.append("file", new Blob(chunks, { type: mimeType }), `boardroom-seat-${Date.now()}.webm`);
          const response = await fetch(`${API_BASE}/api/aion/voice/stt`, { method: "POST", body: form });
          const payload = await response.json();
          if (!response.ok || !clean(payload?.text)) throw new Error(payload?.message || payload?.error || "No speech was recognised.");
          await send(payload.text);
        } catch (error) {
          session.messages.push({ role: "assistant", text: `Voice transcription failed: ${clean(error?.message || error)}` });
          saveHistory();
          render();
        }
      };
      recorder.start();
      render();
    } catch (error) {
      session.messages.push({ role: "assistant", text: `Microphone unavailable: ${clean(error?.message || error)}` });
      render();
    }
  }

  function open(seat = {}) {
    session.seat = { ...seat };
    loadHistory();
    const profile = seatProfile(seat);
    if (!session.messages.length) {
      session.messages.push({ role: "assistant", text: profile.greeting, at: new Date().toISOString() });
      saveHistory();
    }
    render();
    void speak(profile.greeting);
  }

  function close() {
    stopRecordingTracks();
    session.recording = null;
    session.seat = null;
    document.getElementById("aionBoardroomSeatConversation")?.remove();
  }

  global.AionBoardroomSeatConversation = { open, close, send };
})(window);
