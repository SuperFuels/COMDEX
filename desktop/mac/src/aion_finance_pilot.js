(function installAionFinancePilot(global) {
  'use strict';

  const STORAGE_KEY = 'aion.financePilot.discoveryState.v1';
  const MODEL_KEY = 'aion.financePilot.businessFinancialModel.v1';
  const BOARDROOM_PACKET_KEY = 'aion.businessTwin.financePacket.v1';
  const FINANCE_STT_ENDPOINT = 'http://127.0.0.1:8080/api/aion/voice/stt';
  const FINANCE_VOICE_VERSION = 'aion.finance.voice.v3';
  let volatileState = null;
  const schema = global.AionFinanceDiscoverySchema;
  if (!schema) return;

  const voiceRuntime = {
    status: 'idle',
    recorder: null,
    stream: null,
    chunks: [],
    error: null,
    autoAttemptQuestionId: null,
  };

  const now = () => new Date().toISOString();
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));

  function ensureVisualStyles() {
    const id = 'aion-finance-pilot-visual-system-v1';
    document.getElementById(id)?.remove();
    const style = document.createElement('style');
    style.id = id;
    style.textContent = `
      html body [data-aion-finance-workspace="true"] {
        background:#ffffff !important;
      }
      html body [data-aion-finance-workspace="true"] p {
        color:#cbd5e1 !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting],
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence] {
        appearance:none !important;
        -webkit-appearance:none !important;
        background:#07111f !important;
        background-image:linear-gradient(145deg,rgba(14,165,233,.08),transparent 58%) !important;
        border:1px solid rgba(56,189,248,.42) !important;
        color:#f8fafc !important;
        box-shadow:inset 3px 0 0 rgba(14,165,233,.42) !important;
        transition:border-color 140ms ease,background 140ms ease,transform 140ms ease !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting]:hover,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence]:hover {
        background:#0b1b2d !important;
        border-color:#38bdf8 !important;
        transform:translateY(-1px) !important;
      }
      html body [data-aion-finance-workspace="true"] [aria-pressed="true"] {
        background:#06281f !important;
        background-image:linear-gradient(145deg,rgba(34,197,94,.18),transparent 62%) !important;
        border:2px solid #4ade80 !important;
        box-shadow:inset 3px 0 0 #22c55e,0 0 0 1px rgba(34,197,94,.16) !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting] strong,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence] strong {
        color:#f8fafc !important;
      }
      html body [data-aion-finance-workspace="true"] [aria-pressed="true"] strong {
        color:#86efac !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting] span,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence] span {
        color:#94a3b8 !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-continue],
      html body [data-aion-finance-workspace="true"] [data-aion-finance-finalise] {
        background:#22c55e !important;
        background-image:linear-gradient(135deg,#4ade80,#22c55e) !important;
        color:#052e16 !important;
        border:1px solid #86efac !important;
        box-shadow:0 8px 24px rgba(34,197,94,.18) !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting-select],
      html body [data-aion-finance-workspace="true"] [data-aion-finance-file-category] {
        appearance:none !important;
        background:#07111f !important;
        color:#e2e8f0 !important;
        border:1px solid #38bdf8 !important;
        border-radius:0 !important;
        box-shadow:inset 3px 0 0 rgba(14,165,233,.55) !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-xero-sync] {
        background:linear-gradient(135deg,#4ade80,#22c55e) !important;
        color:#052e16 !important;
        border:1px solid #86efac !important;
        border-radius:0 !important;
        box-shadow:0 7px 20px rgba(34,197,94,.2) !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-xero-disconnect] {
        background:#07111f !important;
        color:#fca5a5 !important;
        border:1px solid #ef4444 !important;
        border-radius:0 !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accept-artifact],
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accept-all-artifacts] {
        appearance:none !important;
        -webkit-appearance:none !important;
        background:linear-gradient(135deg,#4ade80,#22c55e) !important;
        color:#052e16 !important;
        -webkit-text-fill-color:#052e16 !important;
        border:1px solid #86efac !important;
        opacity:1 !important;
        cursor:pointer !important;
        box-shadow:0 7px 20px rgba(34,197,94,.2) !important;
        font-weight:900 !important;
      }
      html body section[data-aion-finance-workspace="true"] [data-aion-finance-fact-value] {
        color:#f8fafc !important;
        -webkit-text-fill-color:#f8fafc !important;
        opacity:1 !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-fact-review] span {
        color:#cbd5e1 !important;
      }
      html body [data-aion-finance-workspace="true"]>section{
        background:#ffffff !important;color:#102a43 !important;border:1px solid #cbd9e6 !important;
        border-left:5px solid #0ea5e9 !important;box-shadow:none !important;
      }
      html body [data-aion-finance-workspace="true"] p,
      html body [data-aion-finance-workspace="true"] span{color:#52667a !important}
      html body [data-aion-finance-workspace="true"] strong{color:#102a43 !important}
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting],
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence]{
        background:#ffffff !important;background-image:none !important;color:#102a43 !important;
        border:1px solid #cbd9e6 !important;box-shadow:inset 4px 0 0 #0284c7 !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting]:hover,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence]:hover{background:#edf8fc !important}
      html body [data-aion-finance-workspace="true"] [aria-pressed="true"]{
        background:#f0fdf7 !important;background-image:none !important;border:2px solid #15803d !important;
        box-shadow:inset 4px 0 0 #15803d !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting] strong,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence] strong,
      html body [data-aion-finance-workspace="true"] [aria-pressed="true"] strong{color:#102a43 !important}
      html body [data-aion-finance-workspace="true"] input,
      html body [data-aion-finance-workspace="true"] select,
      html body [data-aion-finance-workspace="true"] textarea{
        background:#ffffff !important;color:#102a43 !important;-webkit-text-fill-color:#102a43 !important;
        border:1px solid #b7c8d6 !important;box-shadow:none !important;
      }
      html body section[data-aion-finance-workspace="true"] [data-aion-finance-fact-value]{color:#102a43 !important;-webkit-text-fill-color:#102a43 !important}
      html body [data-aion-finance-workspace="true"] [data-aion-finance-fact-review] span{color:#52667a !important}
    `;
    document.head.appendChild(style);
  }

  window.setTimeout(ensureVisualStyles, 0);

  function initialState() {
    return {
      schema_version: schema.version,
      status: 'data_sources',
      accounting_platforms: [],
      other_accounting_platform: '',
      evidence_sources: [],
      source_records: [],
      integration_connections: {},
      connector_policy: 'read_only_discovery',
      question_index: 0,
      answers: {},
      transcript: [],
      operational_transcript: [],
      created_at: now(),
      updated_at: now(),
      completed_at: null,
    };
  }

  function load() {
    if (volatileState && typeof volatileState === 'object') return migrateSchema({ ...initialState(), ...volatileState });
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      return value && typeof value === 'object' ? migrateSchema({ ...initialState(), ...value }) : initialState();
    } catch { return initialState(); }
  }

  function migrateSchema(value) {
    if (!value || value.schema_version === schema.version || value.status === 'complete') return value;
    value.schema_version = schema.version;
    const firstUnanswered = schema.questions.findIndex((question) => !String(value.answers?.[question.id] || '').trim());
    value.question_index = firstUnanswered < 0 ? schema.questions.length : firstUnanswered;
    if (value.status !== 'data_sources') value.status = firstUnanswered < 0 ? 'review' : 'discovery';
    value.voice_last_spoken_question_id = null;
    value.voice_last_spoken_version = null;
    return value;
  }

  function compactStateForLocalStorage(value) {
    return {
      ...value,
      source_records: (value.source_records || []).map((item) => ({
        ...item,
        analysis_result: item.analysis_result ? {
          status: item.analysis_result.status,
          artifact_id: item.analysis_result.artifact_id,
          candidate_facts: item.analysis_result.candidate_facts || [],
          warnings: item.analysis_result.warnings || [],
        } : null,
      })),
    };
  }

  function persistStateLocally(value) {
    volatileState = value;
    const serialised = JSON.stringify(value);
    try {
      localStorage.setItem(STORAGE_KEY, serialised);
      return true;
    } catch (error) {
      if (error?.name !== 'QuotaExceededError') throw error;
      const compact = JSON.stringify(compactStateForLocalStorage(value));
      try {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.setItem(STORAGE_KEY, compact);
        console.warn('[AION] Finance state compacted because local storage was full; canonical evidence remains in the Business Container.');
        return true;
      } catch (compactError) {
        console.warn('[AION] Finance state is using the in-memory and backend-authoritative copies because local storage is full.', compactError);
        return false;
      }
    }
  }

  function save(next) {
    const value = { ...next, updated_at: now() };
    persistStateLocally(value);
    global.AionBusinessContainerClient?.syncFinanceState?.(value);
    return value;
  }

  function toggle(list, value) {
    const set = new Set(Array.isArray(list) ? list : []);
    if (set.has(value)) set.delete(value); else set.add(value);
    return [...set];
  }

  function buildBusinessFinancialModel(state) {
    const calculated = global.AionFinanceModelBuilder?.build?.(state) || {};
    // Canonical artifact bytes and extracted facts already live in the Business
    // Container.  Keeping them in this browser handoff duplicated large workbook
    // analyses and could exhaust localStorage during finalisation.
    const sourceRecords = (state.source_records || []).map((item) => ({
      id: item.id,
      name: item.name,
      size: item.size,
      mime_type: item.mime_type,
      type_label: item.type_label,
      category: item.category,
      status: item.status,
      canonical_record: item.canonical_record || null,
      file_cabinet_pointer: item.file_cabinet_pointer || null,
      analysis: item.analysis ? {
        status: item.analysis.status,
        candidate_fact_count: item.analysis.candidate_fact_count,
        accepted_fact_ids: item.analysis.accepted_fact_ids || [],
      } : null,
    }));
    const model = {
      schema_version: 'aion.business_financial_model.v1',
      status: 'draft_for_board_review',
      source_discovery: {
        accounting_platforms: state.accounting_platforms,
        other_accounting_platform: state.other_accounting_platform,
        evidence_sources: state.evidence_sources,
        source_records: sourceRecords,
        connector_policy: state.connector_policy,
      },
      discovery_answers: state.answers,
      ...calculated,
      evidence_quality: 'user_supplied_unverified',
      boardroom_handoff: {
        ready: true,
        requested_outputs: ['financial_baseline', 'margin_model', 'cash_risk', 'cost_opportunities', 'finance_actions'],
      },
      created_at: now(),
      updated_at: now(),
    };
    let localModelStored = true;
    try {
      localStorage.setItem(MODEL_KEY, JSON.stringify(model));
    } catch (error) {
      localModelStored = false;
      console.warn('[AION] Finance model local cache unavailable; canonical Business Container remains authoritative.', error);
    }
    let foundationPacket = null;
    try { foundationPacket = JSON.parse(localStorage.getItem('aion.businessTwin.foundationPacket.v1') || 'null'); } catch {}
    const boardroomPacket = {
      schema_version: 'aion.business_twin.finance_packet.v1',
      department: 'finance',
      status: 'ready_for_boardroom_review',
      foundation_packet_ref: foundationPacket?.packet_id || foundationPacket?.business_id || null,
      financial_model: model,
      permissions: {
        discovery_read: true,
        external_writes: false,
        payments: false,
        filings: false,
        approval_required: true,
      },
      created_at: now(),
    };
    try {
      localStorage.setItem(BOARDROOM_PACKET_KEY, JSON.stringify(boardroomPacket));
    } catch (error) {
      console.warn('[AION] Finance Boardroom packet local cache unavailable; canonical Business Container remains authoritative.', error);
    }
    return { ...model, local_cache_stored: localModelStored };
  }

  function refresh() {
    const root = document.querySelector('[data-aion-finance-workspace="true"]');
    if (root) root.outerHTML = render();
    window.setTimeout(maybeSpeakCurrentFinanceQuestion, 60);
  }

  function persistWithoutContainerSync(state) {
    persistStateLocally({ ...state, updated_at: now() });
  }

  async function speakFinanceText(text, { force = false } = {}) {
    const clean = String(text || '').trim();
    if (!clean || typeof global.aionDesktop?.playLocalVoice !== 'function') return { ok: false, reason: 'local_voice_unavailable' };
    const state = load();
    const question = schema.questions[state.question_index];
    if (!force && question && state.voice_last_spoken_question_id === question.id && state.voice_last_spoken_version === FINANCE_VOICE_VERSION) return { ok: true, skipped: true };
    voiceRuntime.status = 'speaking';
    voiceRuntime.error = null;
    refresh();
    try {
      const result = await global.aionDesktop.playLocalVoice({ text: clean, voice: 'af_heart' });
      if (!result?.ok) throw new Error(result?.error || 'Desktop voice playback failed');
      if (question) {
        const latest = load();
        latest.voice_last_spoken_question_id = question.id;
        latest.voice_last_spoken_version = FINANCE_VOICE_VERSION;
        persistWithoutContainerSync(latest);
      }
      voiceRuntime.status = 'idle';
      refresh();
      return result;
    } catch (error) {
      voiceRuntime.status = 'idle';
      voiceRuntime.error = String(error?.message || error);
      refresh();
      return { ok: false, error: voiceRuntime.error };
    }
  }

  function maybeSpeakCurrentFinanceQuestion() {
    const state = load();
    if (state.status !== 'discovery' || voiceRuntime.status !== 'idle') return;
    const question = schema.questions[state.question_index];
    if (!question || voiceRuntime.autoAttemptQuestionId === question.id || (state.voice_last_spoken_question_id === question.id && state.voice_last_spoken_version === FINANCE_VOICE_VERSION)) return;
    voiceRuntime.autoAttemptQuestionId = question.id;
    speakFinanceText(question.prompt);
  }

  function advanceFinanceDiscovery(answer, source = 'typed') {
    const clean = String(answer || '').trim();
    if (!clean) return false;
    const state = load();
    const question = schema.questions[state.question_index];
    if (!question) return false;
    state.answers[question.id] = clean;
    state.transcript.push({ question_id: question.id, prompt: question.prompt, answer: clean, source, captured_at: now() });
    const allAnswered = schema.questions.every((item) => String(state.answers[item.id] || '').trim());
    const nextUnanswered = schema.questions.findIndex((item, index) => index > state.question_index && !String(state.answers[item.id] || '').trim());
    const firstUnanswered = nextUnanswered >= 0 ? nextUnanswered : schema.questions.findIndex((item) => !String(state.answers[item.id] || '').trim());
    state.question_index = firstUnanswered < 0 ? schema.questions.length : firstUnanswered;
    state.status = allAnswered ? 'review' : 'discovery';
    voiceRuntime.autoAttemptQuestionId = null;
    save(state);
    refresh();
    return true;
  }

  function stopFinanceVoiceTracks() {
    try { voiceRuntime.stream?.getTracks?.().forEach((track) => track.stop()); } catch {}
    voiceRuntime.stream = null;
  }

  async function startFinanceVoiceAnswer() {
    if (voiceRuntime.status === 'recording') return stopFinanceVoiceAnswer();
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      voiceRuntime.error = 'Microphone capture is unavailable. Type the answer instead.';
      refresh();
      return;
    }
    try {
      global.stopAionO21ELiveMicTranscriptCapture?.();
      voiceRuntime.status = 'requesting_microphone';
      voiceRuntime.error = null;
      refresh();
      const permission = await global.aionDesktop?.requestMicrophonePermission?.();
      if (permission && permission.granted !== true) throw new Error(`Microphone permission is ${permission.status || 'unavailable'}`);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferred = MediaRecorder.isTypeSupported?.('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType: preferred });
      voiceRuntime.stream = stream;
      voiceRuntime.recorder = recorder;
      voiceRuntime.chunks = [];
      recorder.ondataavailable = (event) => { if (event.data?.size) voiceRuntime.chunks.push(event.data); };
      recorder.onerror = (event) => {
        voiceRuntime.status = 'idle';
        voiceRuntime.error = String(event?.error?.message || 'Microphone recording failed');
        stopFinanceVoiceTracks();
        refresh();
      };
      recorder.onstop = async () => {
        stopFinanceVoiceTracks();
        const chunks = [...voiceRuntime.chunks];
        voiceRuntime.chunks = [];
        if (!chunks.length) {
          voiceRuntime.status = 'idle';
          voiceRuntime.error = 'No speech was captured. Try again or type the answer.';
          refresh();
          return;
        }
        voiceRuntime.status = 'transcribing';
        refresh();
        try {
          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
          const form = new FormData();
          form.append('file', blob, `finance-answer-${Date.now()}.webm`);
          const response = await fetch(FINANCE_STT_ENDPOINT, { method: 'POST', body: form });
          const payload = await response.json();
          const transcript = String(payload?.text || '').trim();
          if (!response.ok || payload?.ok === false || !transcript) throw new Error(payload?.message || payload?.reason || 'No transcript returned');
          voiceRuntime.status = 'idle';
          voiceRuntime.error = null;
          advanceFinanceDiscovery(transcript, 'local_voice');
        } catch (error) {
          voiceRuntime.status = 'idle';
          voiceRuntime.error = `Voice transcription failed: ${String(error?.message || error)}. Type the answer instead.`;
          refresh();
        }
      };
      recorder.start();
      voiceRuntime.status = 'recording';
      refresh();
    } catch (error) {
      stopFinanceVoiceTracks();
      voiceRuntime.status = 'idle';
      voiceRuntime.error = String(error?.message || error);
      refresh();
    }
  }

  function stopFinanceVoiceAnswer() {
    if (voiceRuntime.recorder?.state && voiceRuntime.recorder.state !== 'inactive') voiceRuntime.recorder.stop();
    voiceRuntime.recorder = null;
  }

  async function reconcileFinanceArtifacts() {
    try {
      const result = await global.AionBusinessContainerClient?.listFinanceArtifacts?.();
      const serverArtifacts = Array.isArray(result?.artifacts) ? result.artifacts : [];
      if (!serverArtifacts.length) return;
      const state = load();
      let changed = false;
      state.source_records = (state.source_records || []).map((item) => {
        const match = serverArtifacts.find((serverItem) => {
          const record = serverItem.record || {};
          return record.artifact_id === item.canonical_record?.artifact_id
            || (record.target?.artifact_name === item.name && Number(record.byte_size || 0) === Number(item.size || 0));
        });
        if (!match) return item;
        changed = true;
        const analysis = match.analysis || null;
        return {
          ...item,
          status: 'committed_to_business_container',
          local_path_stored: true,
          content_stored: true,
          canonical_record: match.record,
          analysis: analysis ? {
            ...(match.record?.analysis || {}),
            status: analysis.status,
            candidate_fact_count: (analysis.candidate_facts || []).length,
          } : match.record?.analysis,
          analysis_result: analysis || item.analysis_result,
          analysis_error: null,
          error: null,
        };
      });
      if (changed) {
        applyEvidenceAnswers(state);
        save(state);
        refresh();
      }
    } catch (error) {
      console.warn('[AION] Finance artifact reconciliation deferred', error);
    }
  }

  async function acceptAllReviewedFinanceArtifacts() {
    const state = load();
    const review = evidenceReviewState(state);
    const targets = review.needsAcceptance;
    if (!targets.length) return;
    try {
      voiceRuntime.status = 'accepting_evidence';
      refresh();
      const results = await Promise.all(targets.map(async (record) => {
        const artifactId = record.canonical_record?.artifact_id;
        const factIds = (record.analysis_result?.candidate_facts || []).map((item) => item.fact_id).filter(Boolean);
        return { artifactId, result: await global.AionBusinessContainerClient.acceptFinanceArtifactFacts(artifactId, factIds) };
      }));
      const latest = load();
      latest.source_records = latest.source_records.map((item) => {
        const accepted = results.find((entry) => entry.artifactId === item.canonical_record?.artifact_id);
        if (!accepted) return item;
        return {
          ...item,
          status: 'committed_to_business_container',
          analysis: {
            ...(item.analysis || {}),
            status: 'accepted_into_finance_model',
            accepted_fact_ids: accepted.result.accepted_fact_ids || [],
          },
          file_cabinet_pointer: accepted.result.file_cabinet_pointer,
          analysis_error: null,
          error: null,
        };
      });
      voiceRuntime.status = 'idle';
      voiceRuntime.error = null;
      applyEvidenceAnswers(latest);
      save(latest);
      refresh();
    } catch (error) {
      voiceRuntime.status = 'idle';
      voiceRuntime.error = `Evidence acceptance failed: ${String(error?.message || error)}`;
      refresh();
    }
  }

  function storeXeroConnection(connection, extras = {}) {
    const state = load();
    state.integration_connections = state.integration_connections || {};
    state.integration_connections.xero = { ...(connection || {}), ...extras };
    save(state); refresh();
  }

  async function refreshXeroStatus() {
    try {
      const result = await global.AionBusinessContainerClient?.getXeroStatus?.();
      if (result?.connection) storeXeroConnection(result.connection);
    } catch (error) {
      storeXeroConnection(xeroConnection(load()), { last_error: String(error) });
    }
  }

  async function startXeroConnection() {
    try {
      const result = await global.AionBusinessContainerClient?.connectXero?.();
      if (!result?.ok) {
        storeXeroConnection(result?.connection || xeroConnection(load()), {
          config_message: result?.message || 'Xero connection is not configured.',
          redirect_uri: result?.redirect_uri || null,
        });
        return;
      }
      storeXeroConnection(result.connection || {}, { status: 'awaiting_authorisation' });
      if (result.connect_url) {
        const opened = await global.aionDesktop?.openExternalUrl?.(result.connect_url);
        if (!opened?.ok) window.open(result.connect_url, '_blank', 'noopener,noreferrer');
      }
    } catch (error) {
      storeXeroConnection(xeroConnection(load()), { last_error: String(error) });
    }
  }

  async function syncXeroNow() {
    storeXeroConnection(xeroConnection(load()), { last_sync_status: 'syncing', last_error: null });
    try {
      const result = await global.AionBusinessContainerClient?.syncXero?.();
      storeXeroConnection(result?.connection || {}, { last_sync_status: 'complete' });
    } catch (error) {
      storeXeroConnection(xeroConnection(load()), { last_sync_status: 'failed', last_error: String(error) });
    }
  }

  function card(item, selected, attr) {
    return `<button type="button" ${attr}="${esc(item.id)}" aria-pressed="${selected}" style="text-align:left;padding:14px;border:${selected ? '2px solid #22c55e' : '1px solid rgba(125,211,252,.4)'};background:${selected ? 'rgba(20,83,45,.48)' : 'rgba(8,47,73,.42)'};color:#e2e8f0;cursor:pointer;min-height:92px"><strong style="display:block;color:${selected ? '#86efac' : '#7dd3fc'};font-size:14px">${esc(item.label)}</strong><span style="display:block;margin-top:7px;color:#cbd5e1;font-size:12px;line-height:1.4">${esc(item.description)}</span></button>`;
  }

  function xeroConnection(state) {
    return state.integration_connections?.xero || {
      status: 'not_connected', connected: false, configured: false,
      available_tenants: [], last_sync_status: 'never_synced', sync_summary: {},
    };
  }

  function evidenceReviewState(state) {
    const records = Array.isArray(state.source_records) ? state.source_records : [];
    const pending = records.filter((item) => item.status === 'upload_pending' || item.status === 'analysing');
    const failed = records.filter((item) => item.analysis?.status !== 'accepted_into_finance_model' && (item.status === 'upload_failed' || item.analysis_error));
    const needsAnalysis = records.filter((item) => item.status === 'committed_to_business_container' && !item.analysis?.status);
    const needsAcceptance = records.filter((item) => item.analysis?.status === 'analysed_requires_review' && Number(item.analysis?.candidate_fact_count || item.analysis_result?.candidate_facts?.length || 0) > 0);
    return { records, pending, failed, needsAnalysis, needsAcceptance, ready: pending.length === 0 && failed.length === 0 && needsAnalysis.length === 0 && needsAcceptance.length === 0 };
  }

  function applyEvidenceAnswers(state) {
    const analyses = (state.source_records || []).filter((item) => item.analysis?.status === 'accepted_into_finance_model').map((item) => item.analysis_result).filter(Boolean);
    const tables = analyses.flatMap((analysis) => analysis.tables || []);
    const table = (...names) => tables.find((item) => names.includes(String(item.source || '').toLowerCase()));
    const monthlyData = table('monthly_data', 'monthly_p&l_data');
    if (!monthlyData) return state;
    const total = (column) => {
      const reported = monthlyData.reported_totals?.[column];
      return Number.isFinite(Number(reported)) ? Number(reported) : Number(monthlyData.numeric_columns?.[column]?.sum || 0);
    };
    const values = tables.flatMap((item) => (item.sample_rows || []).flatMap((row) => Object.values(row || {}))).map((value) => String(value || '').trim());
    const currency = values.find((value) => /^(EUR|€|euro|euros)$/i.test(value)) || (values.some((value) => /EUR|€/i.test(value)) ? 'EUR' : '');
    const revenue = total('net_sales') || total('revenue');
    const jobs = total('jobs');
    const directCosts = total('total_direct_costs') || total('costs');
    const operatingExpenses = total('operating_expenses') || total('overheads');
    const closingCash = total('ending_cash');
    const monthlyValues = (monthlyData.sample_rows || [])
      .filter((row) => !/\b(total|closing)\b/i.test(String(row.month || Object.values(row || {})[0] || '')))
      .map((row) => Number(row.net_sales || row.revenue || 0))
      .filter((value) => value > 0);
    const euro = (value) => `€${Math.round(value).toLocaleString('en-GB')}`;
    const derived = {};
    if (currency) derived.currency = `${currency} (€), detected from accepted finance evidence`;
    if (revenue) derived.revenue_monthly = `${euro(revenue / 12)} average monthly revenue (${euro(revenue)} FY2025 total), extracted from accepted records`;
    if (jobs) derived.sales_volume = `${Math.round(jobs / 12)} completed jobs per average month (${Math.round(jobs)} FY2025 total), extracted from accepted records`;
    if (monthlyValues.length > 1) derived.revenue_pattern = `Monthly and mildly seasonal; recorded net sales range from ${euro(Math.min(...monthlyValues))} to ${euro(Math.max(...monthlyValues))}`;
    if (directCosts) {
      derived.direct_costs = `Recorded direct delivery costs total ${euro(directCosts)} for FY2025, including materials, subcontractors and job vehicle costs`;
      derived.direct_cost_monthly = `${euro(directCosts / 12)} average monthly direct delivery cost, extracted from accepted records`;
    }
    if (operatingExpenses) {
      derived.fixed_costs = `Recorded operating expenses total ${euro(operatingExpenses)} for FY2025; source schedules include owner salary, administration, marketing and fixed overhead`;
      derived.fixed_cost_monthly = `${euro(operatingExpenses / 12)} average monthly operating expense, extracted from accepted records`;
    }
    if (closingCash) derived.cash_position = `${euro(closingCash)} closing cash recorded at 31 December 2025; minimum operating buffer still requires confirmation`;
    state.answers = { ...derived, ...(state.answers || {}) };
    state.evidence_prefilled_fields = Object.keys(derived);
    const firstUnanswered = schema.questions.findIndex((question) => !String(state.answers[question.id] || '').trim());
    state.question_index = firstUnanswered < 0 ? schema.questions.length : firstUnanswered;
    return state;
  }

  function renderXeroConnection(state) {
    if (!state.accounting_platforms.includes('xero')) return '';
    const connection = xeroConnection(state);
    const connected = connection.connected === true || connection.status === 'connected';
    const reauthorisationRequired = connected && connection.reauthorisation_required === true;
    const missingScopes = Array.isArray(connection.missing_scopes) ? connection.missing_scopes : [];
    const awaiting = connection.status === 'awaiting_authorisation';
    const tenants = Array.isArray(connection.available_tenants) ? connection.available_tenants : [];
    const tenantSelect = connection.status === 'tenant_selection_required' && tenants.length
      ? `<div style="display:flex;gap:8px;align-items:center;margin-top:10px"><select data-aion-xero-tenant style="flex:1;background:#07111f;color:#bae6fd;border:1px solid #38bdf8;padding:9px">${tenants.map((tenant) => `<option value="${esc(tenant.tenant_id)}">${esc(tenant.tenant_name || tenant.tenant_id)}</option>`).join('')}</select><button type="button" data-aion-xero-select-tenant style="padding:9px 12px">Use organisation</button></div>`
      : '';
    const summary = connection.sync_summary || {};
    return `<section data-aion-xero-connection style="margin-top:12px;border:1px solid ${connected ? '#22c55e' : 'rgba(56,189,248,.42)'};background:#07111f;padding:13px 14px">
      <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start">
        <div>
          <div style="color:${connected ? '#86efac' : '#7dd3fc'};font-weight:900">&gt; Xero · ${esc(String(connection.status || 'not_connected').replaceAll('_', ' '))}</div>
          <div style="color:#94a3b8;font-size:12px;margin-top:5px">Credentials remain in macOS Keychain. Sync is read-only; every Xero bill write requires a separately approved exact payload and provider read-back verification.</div>
          ${connection.tenant_name ? `<div style="color:#e2e8f0;margin-top:6px">Organisation: ${esc(connection.tenant_name)}</div>` : ''}
          ${connection.last_sync_at ? `<div style="color:#94a3b8;margin-top:4px">Last sync: ${esc(connection.last_sync_at)} · ${Number(summary.account_count || 0)} accounts · ${Number(summary.invoice_count || 0)} invoices · ${Number((summary.reports_received || []).length)} reports</div>` : ''}
          ${connection.last_error ? `<div style="color:#fca5a5;margin-top:6px">${esc(connection.last_error)}</div>` : ''}
          ${connection.config_message ? `<div style="color:#facc15;margin-top:6px">${esc(connection.config_message)}</div>` : ''}
          ${reauthorisationRequired ? `<div style="color:#facc15;margin-top:7px"><strong>Reauthorisation required.</strong> Xero must approve the granular invoice, payment, bank-transaction, journal, attachment and contact permissions used by the controlled accounting workflow.${missingScopes.length ? `<br><small>Missing: ${esc(missingScopes.join(', '))}</small>` : ''}</div>` : ''}
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end">
          ${connected ? `${reauthorisationRequired ? '<button type="button" data-aion-xero-connect style="padding:9px 12px;background:#facc15;color:#422006;border:1px solid #fde68a;font-weight:900">Reauthorise Xero</button>' : ''}<button type="button" data-aion-xero-sync style="padding:9px 12px;background:#22c55e;color:#052e16;border:1px solid #86efac;font-weight:900">Sync Xero now</button><button type="button" data-aion-xero-disconnect style="padding:9px 12px;background:transparent;color:#fca5a5;border:1px solid #ef4444">Disconnect</button>` : `<button type="button" data-aion-xero-connect style="padding:9px 12px;background:#22c55e;color:#052e16;border:1px solid #86efac;font-weight:900">${awaiting ? 'Restart connection' : 'Connect Xero'}</button>${awaiting ? '<button type="button" data-aion-xero-status style="padding:9px 12px">Check connection</button>' : ''}`}
        </div>
      </div>
      ${tenantSelect}
    </section>`;
  }

  function renderAccountingConnection(state) {
    const platformId = state.accounting_platforms[0] || '';
    if (!platformId) return '';
    if (platformId === 'xero') return renderXeroConnection(state);
    const platform = schema.accountingPlatforms.find((item) => item.id === platformId);
    if (!platform) return '';
    const noConnector = platformId === 'none';
    const label = platformId === 'other' && state.other_accounting_platform
      ? state.other_accounting_platform
      : platform.label;
    return `<section data-aion-accounting-connection style="margin-top:12px;border:1px solid rgba(56,189,248,.42);background:#07111f;padding:13px 14px">
      <div style="display:flex;justify-content:space-between;gap:16px;align-items:center">
        <div>
          <div style="color:#7dd3fc;font-weight:900">&gt; ${esc(label)} · ${noConnector ? 'records only' : 'not connected'}</div>
          <div style="color:#94a3b8;font-size:12px;margin-top:5px">${noConnector ? 'Finance will use uploaded records and user-confirmed estimates.' : 'This source is recorded for Finance setup. Its live read-only connector has not been installed yet.'}</div>
        </div>
        ${noConnector ? '' : '<div style="padding:9px 12px;background:#0b1b2d;color:#94a3b8;border:1px solid rgba(56,189,248,.35);font-weight:800">Connector unavailable</div>'}
      </div>
    </section>`;
  }

  function packageHeader(state) {
    const label = state.status === 'complete' ? 'Financial model ready for Boardroom review' : 'Finance discovery and evidence capture in progress';
    return `<section style="border:2px solid #f59e0b;background:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:14px"><div><div style="color:#0f766e;font-size:11px;letter-spacing:.28em;text-transform:uppercase;font-weight:900">Boardroom Package</div><div style="font-size:20px;font-weight:900;color:#0f172a;margin-top:6px">Finance assignment package</div><div style="font-size:13px;font-weight:650;color:#475569;margin-top:6px">${esc(label)} · read-only discovery · approval gated</div></div><button type="button" data-aion-finance-package style="padding:12px 18px;background:#fff;border:1px solid rgba(15,23,42,.22);font-size:11px;letter-spacing:.18em;text-transform:uppercase;font-weight:900">Open Package</button></section>`;
  }

  function renderSources(state) {
    const selectedPlatform = state.accounting_platforms[0] || '';
    const platforms = schema.accountingPlatforms.map((item) => `<option value="${esc(item.id)}" ${selectedPlatform === item.id ? 'selected' : ''}>${esc(item.label)} — ${esc(item.description)}</option>`).join('');
    const evidence = schema.evidenceSources.map((x) => card(x, state.evidence_sources.includes(x.id), 'data-aion-finance-evidence')).join('');
    const other = state.accounting_platforms.includes('other') ? `<label style="display:block;margin-top:12px;color:#bae6fd">Other accounting software<input data-aion-finance-other value="${esc(state.other_accounting_platform)}" placeholder="Enter software name" style="display:block;width:100%;box-sizing:border-box;margin-top:7px;padding:10px;background:#e2e8f0;color:#0f172a;border:0"></label>` : '';
    const files = state.source_records.length
      ? state.source_records.map((file) => {
          const artifactId = file.canonical_record?.artifact_id || '';
          const analysed = file.analysis?.status;
          const candidateCount = Number(file.analysis?.candidate_fact_count || file.analysis_result?.candidate_facts?.length || 0);
          const candidateFacts = Array.isArray(file.analysis_result?.candidate_facts) ? file.analysis_result.candidate_facts : [];
          const factsAccepted = analysed === 'accepted_into_finance_model';
          const factReview = candidateFacts.length ? `<details data-aion-finance-fact-review style="margin-top:8px;border-top:1px solid rgba(56,189,248,.18);padding-top:8px"><summary style="color:${factsAccepted ? '#86efac' : '#facc15'};cursor:pointer">${factsAccepted ? 'Accepted' : 'Review'} ${candidateFacts.length} extracted financial facts${factsAccepted ? '' : ' before acceptance'}</summary><div style="display:grid;grid-template-columns:repeat(2,minmax(240px,1fr));gap:5px 16px;margin-top:9px">${candidateFacts.map((fact) => {
            const label = String(fact.source_column || fact.field || 'fact').replaceAll('_', ' ');
            const numeric = Number(fact.value);
            const value = Number.isFinite(numeric) ? numeric.toLocaleString('en-GB', { maximumFractionDigits: 2 }) : String(fact.value ?? '');
            return `<div style="display:flex;justify-content:space-between;gap:10px;color:#cbd5e1"><span>${esc(label)}</span><strong data-aion-finance-fact-value style="color:#f8fafc!important">${esc(value)}</strong></div>`;
          }).join('')}</div><div style="color:#94a3b8;font-size:11px;margin-top:8px">Source workbook values · reporting currency confirmed separately · acceptance records provenance and does not change the source file.</div></details>` : '';
          const actions = file.status === 'committed_to_business_container' && artifactId && !analysed
            ? `<button type="button" data-aion-finance-analyse-artifact="${esc(artifactId)}" style="background:transparent;color:#7dd3fc;border:1px solid #38bdf8;padding:5px 8px">Analyse</button>`
            : analysed === 'analysed_requires_review' && candidateCount > 0
              ? `<button type="button" data-aion-finance-accept-artifact="${esc(artifactId)}" style="background:#22c55e;color:#052e16;border:1px solid #86efac;padding:5px 8px">Accept ${candidateCount} extracted fact${candidateCount === 1 ? '' : 's'}</button>`
              : analysed ? `<span style="color:#94a3b8">${esc(String(analysed).replaceAll('_', ' '))}</span>` : '';
          return `<div style="padding:8px 9px;border-top:1px solid rgba(56,189,248,.18)"><div style="display:flex;justify-content:space-between;gap:12px;align-items:center"><span style="color:#e2e8f0">${esc(file.name)}</span><span style="display:flex;gap:9px;align-items:center;color:${file.status === 'committed_to_business_container' ? '#86efac' : file.status === 'upload_failed' ? '#fca5a5' : '#facc15'}">${esc(file.type_label)} · ${esc(file.status || 'upload pending')} ${actions}</span></div>${factReview}</div>`;
        }).join('')
      : '<div style="color:#64748b;padding:8px 0">No local finance files staged.</div>';
    const review = evidenceReviewState(state);
    const blockedMessage = review.pending.length ? `${review.pending.length} file upload${review.pending.length === 1 ? '' : 's'} still completing` : review.needsAnalysis.length ? `Analyse ${review.needsAnalysis.length} committed file${review.needsAnalysis.length === 1 ? '' : 's'} before continuing` : review.needsAcceptance.length ? `Review and accept extracted facts from ${review.needsAcceptance.length} file${review.needsAcceptance.length === 1 ? '' : 's'}` : review.failed.length ? 'Resolve failed uploads before continuing' : '';
    const continueLabel = review.ready ? 'Save sources & begin discovery' : blockedMessage;
    const footerAction = review.needsAcceptance.length
      ? `<button type="button" data-aion-finance-accept-all-artifacts style="padding:11px 18px;letter-spacing:.08em;text-transform:uppercase">Accept reviewed facts from ${review.needsAcceptance.length} file${review.needsAcceptance.length === 1 ? '' : 's'}</button>`
      : `<button type="button" data-aion-finance-continue ${review.ready ? '' : 'disabled aria-disabled="true"'} style="padding:11px 18px;background:${review.ready ? '#22c55e' : '#334155'};color:${review.ready ? '#052e16' : '#cbd5e1'};border:1px solid ${review.ready ? '#86efac' : '#64748b'};font-weight:900;letter-spacing:.08em;text-transform:uppercase;cursor:${review.ready ? 'pointer' : 'not-allowed'}">${esc(continueLabel)}</button>`;
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Setup · Existing Data Discovery</div><p style="color:#cbd5e1;line-height:1.55;max-width:900px">First, tell the Finance Pilot where the financial truth currently lives. Selecting a source records it for setup; a connection remains read-only and cannot change accounting data.</p><div style="color:#facc15;margin:18px 0 10px;font-weight:800">&gt; Accounting software</div><select data-aion-finance-accounting-select style="display:block;width:100%;padding:12px 14px;font:inherit"><option value="">Select accounting software…</option>${platforms}</select>${other}${renderAccountingConnection(state)}<div style="color:#facc15;margin:22px 0 10px;font-weight:800">&gt; Other records available to Finance</div><div style="display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px">${evidence}</div><div style="margin-top:18px;border:1px solid rgba(56,189,248,.34);background:#07111f;padding:12px"><div style="display:flex;justify-content:space-between;align-items:center;gap:14px"><div><div style="color:#7dd3fc;font-weight:900">&gt; Add files to the Finance Business Container</div><div style="color:#94a3b8;margin-top:4px;font-size:12px">Original bytes, hash and receipt are stored first. Analysis and accepting extracted values are separate, visible actions.</div></div><div style="display:flex;gap:8px;align-items:center"><select data-aion-finance-file-category style="padding:8px"><option value="spreadsheets">Spreadsheets</option><option value="bank-statements">Bank Statements</option><option value="invoices-receipts">Invoices & Receipts</option><option value="management-accounts">Management Accounts</option><option value="vat-tax">VAT & Tax</option><option value="payroll">Payroll</option><option value="payment-processors">Payment Processors</option><option value="crm-sales">CRM & Sales</option></select><label style="padding:8px 12px;border:1px solid #38bdf8;color:#bae6fd;cursor:pointer">Choose files<input data-aion-finance-files type="file" multiple accept=".csv,.xlsx,.xls,.pdf,.ofx,.qif,.xml,.json" style="display:none"></label></div></div><div style="margin-top:8px">${files}</div></div><div style="display:flex;justify-content:flex-end;margin-top:22px">${footerAction}</div>`;
  }

  function renderDiscovery(state) {
    const review = evidenceReviewState(state);
    if (!review.ready) return `<div style="color:#facc15;font-weight:900;letter-spacing:.18em;text-transform:uppercase">&gt; Finance Evidence Review Required</div><div style="margin-top:18px;border:1px solid #f59e0b;background:rgba(120,53,15,.22);padding:16px;line-height:1.6"><div>&gt; The uploaded files are safely stored, but their extracted facts have not yet been accepted into the canonical Finance model.</div><div style="color:#cbd5e1;margin-top:8px">&gt; Pending uploads: ${review.pending.length} · awaiting analysis: ${review.needsAnalysis.length} · awaiting acceptance: ${review.needsAcceptance.length}</div><button type="button" data-aion-finance-review-evidence style="margin-top:14px;padding:10px 14px;background:#facc15;color:#422006;border:1px solid #fde68a;font-weight:900">Return to evidence review</button></div>`;
    const question = schema.questions[state.question_index];
    if (!question) return renderReview(state);
    const history = state.transcript.slice(-4).map((turn) => `<div style="margin:7px 0"><span style="color:#94a3b8">&gt; You:</span> ${esc(turn.answer)}</div>`).join('');
    const answeredCount = schema.questions.filter((item) => String(state.answers[item.id] || '').trim()).length;
    const prefilled = Number(state.evidence_prefilled_fields?.length || 0);
    const voiceLabel = voiceRuntime.status === 'recording' ? 'Stop & transcribe' : voiceRuntime.status === 'transcribing' ? 'Transcribing…' : voiceRuntime.status === 'requesting_microphone' ? 'Opening microphone…' : 'Reply by voice';
    const voiceDisabled = ['transcribing', 'requesting_microphone', 'speaking'].includes(voiceRuntime.status);
    const sourceCount = state.accounting_platforms.length + (state.source_records || []).filter((item) => item.status === 'committed_to_business_container').length;
    const speakingStatus = voiceRuntime.status === 'speaking' ? '<span style="color:#86efac;font-size:12px">AION is asking the question automatically…</span>' : '';
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Pilot · Financial Discovery</div><div style="margin-top:16px;border:1px solid rgba(14,165,233,.55);background:rgba(8,47,73,.55);padding:14px 16px;line-height:1.55"><div style="color:#7dd3fc;font-weight:900;text-transform:uppercase;letter-spacing:.16em">&gt; Discovery Question Inbox</div><div>&gt; Answered: ${answeredCount} / ${schema.questions.length}</div><div>&gt; Evidence-derived answers: ${prefilled} · remaining questions only request missing context</div><div>&gt; Connected and accepted sources: ${sourceCount}</div><br><div style="display:flex;justify-content:space-between;gap:14px;align-items:center"><div style="color:#bae6fd">&gt; Current question: ${esc(question.prompt)}</div><button type="button" data-aion-finance-hear-question style="flex:0 0 auto;background:transparent;color:#7dd3fc;border:1px solid #38bdf8;padding:7px 10px">Hear again</button></div></div><div style="margin-top:16px;line-height:1.55">${history}<div style="color:#86efac;margin-top:12px">&gt; Finance Pilot: ${esc(question.prompt)}</div></div><div style="position:absolute;left:18px;right:18px;bottom:18px"><div style="display:flex;gap:10px;align-items:center;margin-bottom:9px"><button type="button" data-aion-finance-voice-answer ${voiceDisabled ? 'disabled aria-disabled="true"' : ''} style="padding:9px 14px;background:${voiceRuntime.status === 'recording' ? '#f59e0b' : '#22c55e'};color:#052e16;border:1px solid ${voiceRuntime.status === 'recording' ? '#fcd34d' : '#86efac'};font-weight:900">${esc(voiceLabel)}</button>${speakingStatus}<span style="color:#94a3b8;font-size:12px">Local Whisper transcription · typed answers remain available</span>${voiceRuntime.error ? `<span style="color:#fca5a5;font-size:12px">${esc(voiceRuntime.error)}</span>` : ''}</div><div style="display:flex;gap:10px;align-items:center"><span>&gt;</span><input data-aion-finance-answer placeholder="Type an answer, or use Reply by voice..." style="flex:1;padding:9px;background:#e2e8f0;color:#0f172a;border:0"><button type="button" data-aion-finance-answer-send style="padding:9px 15px;font-weight:900;text-transform:uppercase">Send</button></div></div>`;
  }

  function renderReview(state) {
    const rows = schema.questions.map((q, index) => `<div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;padding:9px 0;border-bottom:1px solid rgba(148,163,184,.2)"><div><div style="color:#7dd3fc">${esc(q.prompt)}</div><div style="color:#e2e8f0;margin-top:4px">${esc(state.answers[q.id] || 'Not answered')}</div></div><button type="button" data-aion-finance-edit-answer="${index}" style="align-self:center;background:transparent;color:#7dd3fc;border:1px solid rgba(56,189,248,.5);padding:6px 9px">Edit</button></div>`).join('');
    const finalisation = state.finalisation || {};
    const message = finalisation.status === 'failed'
      ? `<div role="alert" style="margin-top:12px;padding:10px;border:1px solid #ef4444;color:#fecaca">Financial model could not be finalised: ${esc(finalisation.error || 'Unknown error')}. Your discovery answers remain saved; retry when the local backend is available.</div>`
      : finalisation.status === 'building'
        ? '<div style="margin-top:12px;color:#bae6fd">Building the canonical model and confirming the Business Container receipt…</div>'
        : '';
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Discovery · Review</div><p style="color:#cbd5e1">Review the captured baseline. Finalising creates the first Business Financial Model for the Boardroom; it does not authorise payments or external changes.</p><div style="max-height:380px;overflow:auto">${rows}</div>${message}<div style="display:flex;justify-content:space-between;margin-top:18px"><button data-aion-finance-back style="padding:10px 16px" ${finalisation.status === 'building' ? 'disabled' : ''}>Back</button><button data-aion-finance-finalise style="padding:10px 16px;background:#22c55e;color:#052e16;border:0;font-weight:900" ${finalisation.status === 'building' ? 'disabled aria-busy="true"' : ''}>${finalisation.status === 'building' ? 'Building Financial Model…' : 'Build Financial Model'}</button></div>`;
  }

  function renderComplete(state) {
    const turns = (state.operational_transcript || []).slice(-12).map((turn) => `<div style="margin:10px 0"><div style="color:#94a3b8">&gt; You: ${esc(turn.user_text)}</div><div style="color:#86efac;margin-top:5px">&gt; Finance Pilot: ${esc(turn.response)}</div></div>`).join('');
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Pilot · Operational Stream</div><div style="margin-top:18px;border:1px solid rgba(34,197,94,.55);background:rgba(20,83,45,.32);padding:12px;line-height:1.5;color:#bbf7d0">&gt; Canonical financial baseline captured · Boardroom context ready · external actions approval gated.</div><p style="color:#cbd5e1;line-height:1.6">Ask for a finance update, margins, cash, fixed costs or cost-reduction analysis. Answers are grounded in the canonical Business Financial Model and label unverified inputs.</p><div style="height:330px;overflow:auto;padding-bottom:12px">${turns || '<div style="color:#64748b">&gt; No operational Finance questions yet.</div>'}</div><div style="position:absolute;left:18px;right:18px;bottom:18px;display:flex;gap:10px"><span>&gt;</span><input data-aion-finance-operational-answer placeholder="Ask the Finance Pilot..." style="flex:1;padding:9px;background:#e2e8f0;color:#0f172a;border:0"><button data-aion-finance-operational-send style="padding:9px 15px;font-weight:900">Send</button></div>`;
  }

  function render() {
    const state = load();
    if (state.status === 'complete' && typeof global.renderAionDepartmentPilotRuntime === 'function') {
      return global.renderAionDepartmentPilotRuntime('finance');
    }
    if (state.status === 'discovery') window.setTimeout(maybeSpeakCurrentFinanceQuestion, 100);
    const body = state.status === 'data_sources' ? renderSources(state) : state.status === 'discovery' ? renderDiscovery(state) : state.status === 'review' ? renderReview(state) : renderComplete(state);
    return `<section class="panel large-panel" data-aion-finance-workspace="true" style="padding:16px;border:1px solid rgba(15,23,42,.14)">${packageHeader(state)}<section style="position:relative;background:#0f172a;color:#cbd5e1;min-height:590px;padding:18px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;box-shadow:inset 4px 0 0 #0284c7">${body}</section></section>`;
  }

  document.addEventListener('click', (event) => {
    const accounting = event.target.closest?.('[data-aion-finance-accounting]');
    const evidence = event.target.closest?.('[data-aion-finance-evidence]');
    const action = event.target.closest?.('[data-aion-finance-continue],[data-aion-finance-review-evidence],[data-aion-finance-answer-send],[data-aion-finance-voice-answer],[data-aion-finance-hear-question],[data-aion-finance-operational-send],[data-aion-finance-back],[data-aion-finance-finalise],[data-aion-finance-package],[data-aion-finance-edit-answer],[data-aion-xero-connect],[data-aion-xero-status],[data-aion-xero-sync],[data-aion-xero-select-tenant],[data-aion-xero-disconnect],[data-aion-finance-analyse-artifact],[data-aion-finance-accept-artifact],[data-aion-finance-accept-all-artifacts]');
    if (!accounting && !evidence && !action) return;
    event.preventDefault();
    let state = load();
    if (accounting) {
      const id = accounting.dataset.aionFinanceAccounting;
      let values = toggle(state.accounting_platforms, id);
      if (id === 'none' && values.includes('none')) values = ['none'];
      else if (id !== 'none') values = values.filter((x) => x !== 'none');
      state.accounting_platforms = values;
    } else if (evidence) {
      state.evidence_sources = toggle(state.evidence_sources, evidence.dataset.aionFinanceEvidence);
    } else if (action.matches('[data-aion-xero-connect]')) {
      startXeroConnection(); return;
    } else if (action.matches('[data-aion-xero-status]')) {
      refreshXeroStatus(); return;
    } else if (action.matches('[data-aion-xero-sync]')) {
      syncXeroNow(); return;
    } else if (action.matches('[data-aion-xero-select-tenant]')) {
      const tenantId = document.querySelector('[data-aion-xero-tenant]')?.value || '';
      global.AionBusinessContainerClient?.selectXeroTenant?.(tenantId)
        .then((result) => storeXeroConnection(result.connection || {}))
        .catch((error) => storeXeroConnection(xeroConnection(load()), { last_error: String(error) }));
      return;
    } else if (action.matches('[data-aion-xero-disconnect]')) {
      global.AionBusinessContainerClient?.disconnectXero?.()
        .then((result) => storeXeroConnection(result.connection || {}))
        .catch((error) => storeXeroConnection(xeroConnection(load()), { last_error: String(error) }));
      return;
    } else if (action.matches('[data-aion-finance-analyse-artifact]')) {
      const artifactId = action.dataset.aionFinanceAnalyseArtifact;
      action.disabled = true;
      global.AionBusinessContainerClient?.analyseFinanceArtifact?.(artifactId)
        .then((result) => {
          const latest = load();
          latest.source_records = latest.source_records.map((item) => item.canonical_record?.artifact_id === artifactId ? {
            ...item,
            analysis: result.analysis_ref,
            analysis_result: result.analysis,
            file_cabinet_pointer: result.file_cabinet_pointer,
          } : item);
          applyEvidenceAnswers(latest);
          save(latest); refresh();
        })
        .catch((error) => {
          const latest = load();
          latest.source_records = latest.source_records.map((item) => item.canonical_record?.artifact_id === artifactId ? { ...item, analysis_error: String(error) } : item);
          save(latest); refresh();
        });
      return;
    } else if (action.matches('[data-aion-finance-accept-artifact]')) {
      const artifactId = action.dataset.aionFinanceAcceptArtifact;
      const record = state.source_records.find((item) => item.canonical_record?.artifact_id === artifactId);
      const factIds = (record?.analysis_result?.candidate_facts || []).map((item) => item.fact_id).filter(Boolean);
      action.disabled = true;
      global.AionBusinessContainerClient?.acceptFinanceArtifactFacts?.(artifactId, factIds)
        .then((result) => {
          const latest = load();
          latest.source_records = latest.source_records.map((item) => item.canonical_record?.artifact_id === artifactId ? {
            ...item,
            status: 'committed_to_business_container',
            analysis: { ...(item.analysis || {}), status: 'accepted_into_finance_model', accepted_fact_ids: result.accepted_fact_ids || [] },
            file_cabinet_pointer: result.file_cabinet_pointer,
            analysis_error: null,
            error: null,
          } : item);
          applyEvidenceAnswers(latest);
          save(latest); refresh();
        })
        .catch((error) => {
          const latest = load();
          latest.source_records = latest.source_records.map((item) => item.canonical_record?.artifact_id === artifactId ? { ...item, analysis_error: String(error) } : item);
          save(latest); refresh();
        });
      return;
    } else if (action.matches('[data-aion-finance-accept-all-artifacts]')) {
      acceptAllReviewedFinanceArtifacts();
      return;
    } else if (action.matches('[data-aion-finance-review-evidence]')) {
      state.status = 'data_sources';
      save(state); refresh();
      reconcileFinanceArtifacts();
      return;
    } else if (action.matches('[data-aion-finance-continue]')) {
      const review = evidenceReviewState(state);
      if (!review.ready) {
        state.status = 'data_sources';
      } else {
        applyEvidenceAnswers(state);
        const allAnswered = schema.questions.every((item) => String(state.answers[item.id] || '').trim());
        state.status = allAnswered ? 'review' : 'discovery';
        if (state.status === 'discovery') {
          state.voice_last_spoken_question_id = null;
          state.voice_last_spoken_version = null;
          voiceRuntime.autoAttemptQuestionId = null;
        }
      }
    } else if (action.matches('[data-aion-finance-answer-send]')) {
      const input = document.querySelector('[data-aion-finance-answer]');
      const answer = String(input?.value || '').trim();
      if (!answer) return;
      advanceFinanceDiscovery(answer, 'typed');
      return;
    } else if (action.matches('[data-aion-finance-voice-answer]')) {
      startFinanceVoiceAnswer();
      return;
    } else if (action.matches('[data-aion-finance-hear-question]')) {
      const question = schema.questions[state.question_index];
      if (question) {
        voiceRuntime.autoAttemptQuestionId = null;
        speakFinanceText(question.prompt, { force: true });
      }
      return;
    } else if (action.matches('[data-aion-finance-back]')) {
      state.status = 'discovery';
      state.question_index = Math.max(0, schema.questions.length - 1);
    } else if (action.matches('[data-aion-finance-edit-answer]')) {
      state.status = 'discovery';
      state.question_index = Number(action.dataset.aionFinanceEditAnswer || 0);
    } else if (action.matches('[data-aion-finance-finalise]')) {
      action.disabled = true;
      state.finalisation = { status: 'building', started_at: now(), error: null };
      persistWithoutContainerSync(state);
      refresh();
      (async () => {
        try {
          const latest = load();
          latest.status = 'complete';
          latest.completed_at = now();
          const model = buildBusinessFinancialModel(latest);
          const sync = await global.AionBusinessContainerClient?.syncFinanceStateNow?.(latest);
          if (!sync?.ok) throw new Error(sync?.reason || 'Canonical Finance Business Container receipt was not returned');
          const completion = await global.AionBusinessContainerClient?.completeFinanceFoundation?.();
          if (!completion?.ok) throw new Error('Financial statements and operating model were not completed');
          latest.finalisation = {
            status: 'complete',
            completed_at: latest.completed_at,
            business_id: sync.business_id,
            finance_model_receipt: sync.finance_model || null,
            local_cache_stored: model.local_cache_stored !== false,
            statements_ready: true,
            operating_model_created: completion.operating_model_created === true,
          };
          save(latest);
          global.AionBusinessTwinOrchestrator?.completeFinancePilot?.({
            completed_at: latest.completed_at,
            model_key: MODEL_KEY,
            business_id: sync.business_id,
            finance_model_receipt: sync.finance_model || null,
            approval_gated: true,
          });
          refresh();
        } catch (error) {
          const latest = load();
          latest.status = 'review';
          latest.finalisation = { status: 'failed', failed_at: now(), error: String(error?.message || error) };
          persistWithoutContainerSync(latest);
          refresh();
        }
      })();
      return;
    } else if (action.matches('[data-aion-finance-operational-send]')) {
      const input = document.querySelector('[data-aion-finance-operational-answer]');
      const userText = String(input?.value || '').trim();
      if (!userText) return;
      action.disabled = true;
      global.AionBusinessContainerClient?.askFinanceAgent?.(userText).then((result) => {
        const latest = load(); latest.operational_transcript = latest.operational_transcript || [];
        latest.operational_transcript.push(result.turn); save(latest); refresh();
      }).catch((error) => {
        const latest = load(); latest.operational_transcript = latest.operational_transcript || [];
        latest.operational_transcript.push({ user_text: userText, response: `Finance service unavailable: ${String(error)}`, created_at: now() }); save(latest); refresh();
      });
      return;
    } else if (action.matches('[data-aion-finance-package]')) {
      const model = localStorage.getItem(MODEL_KEY);
      alert(model ? 'Finance package is ready in the Business Financial Model.' : 'Finance discovery must be completed before this package is ready.');
      return;
    }
    save(state); refresh();
    if (accounting?.dataset.aionFinanceAccounting === 'xero' && state.accounting_platforms.includes('xero')) {
      window.setTimeout(refreshXeroStatus, 0);
    }
  }, true);

  document.addEventListener('change', (event) => {
    if (event.target.matches?.('[data-aion-finance-accounting-select]')) {
      const state = load();
      const selected = String(event.target.value || '');
      state.accounting_platforms = selected ? [selected] : [];
      if (selected !== 'other') state.other_accounting_platform = '';
      save(state); refresh();
      if (selected === 'xero') window.setTimeout(refreshXeroStatus, 0);
      return;
    }
    if (event.target.matches?.('[data-aion-finance-other]')) {
      const state = load(); state.other_accounting_platform = String(event.target.value || '').trim(); save(state); return;
    }
    if (event.target.matches?.('[data-aion-finance-files]')) {
      const state = load();
      const category = String(document.querySelector('[data-aion-finance-file-category]')?.value || 'spreadsheets');
      const existing = new Set(state.source_records.map((item) => `${item.name}:${item.size}`));
      const uploads = [];
      Array.from(event.target.files || []).forEach((file) => {
        const signature = `${file.name}:${file.size}`;
        if (existing.has(signature)) return;
        const item = {
          id: `finance_source_${Date.now()}_${Math.random().toString(16).slice(2)}`,
          name: file.name,
          size: file.size,
          mime_type: file.type || 'application/octet-stream',
          type_label: (file.name.split('.').pop() || 'file').toUpperCase(),
          category,
          status: 'upload_pending',
          local_path_stored: false,
          content_stored: false,
          selected_at: now(),
        };
        state.source_records.push(item);
        uploads.push({ file, itemId: item.id });
      });
      save(state); refresh();
      uploads.forEach(({ file, itemId }) => {
        global.AionBusinessContainerClient?.uploadFinanceArtifact?.(file, category)
          .then((result) => {
            const latest = load();
            latest.source_records = latest.source_records.map((item) => item.id === itemId ? {
              ...item,
              status: 'committed_to_business_container',
              local_path_stored: true,
              content_stored: true,
              canonical_record: result.record,
              file_cabinet_pointer: result.file_cabinet_pointer,
            } : item);
            save(latest); refresh();
          })
          .catch((error) => {
            const latest = load();
            latest.source_records = latest.source_records.map((item) => item.id === itemId ? { ...item, status: 'upload_failed', error: String(error) } : item);
            save(latest); refresh();
          });
      });
    }
  }, true);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.matches?.('[data-aion-finance-answer]')) {
      event.preventDefault(); document.querySelector('[data-aion-finance-answer-send]')?.click();
    }
    if (event.key === 'Enter' && event.target.matches?.('[data-aion-finance-operational-answer]')) {
      event.preventDefault(); document.querySelector('[data-aion-finance-operational-send]')?.click();
    }
  }, true);

  window.setTimeout(() => {
    if (load().accounting_platforms.includes('xero')) refreshXeroStatus();
    if ((load().source_records || []).length) reconcileFinanceArtifacts();
    maybeSpeakCurrentFinanceQuestion();
  }, 1200);

  global.AionFinancePilot = { load, save, render, buildBusinessFinancialModel, refreshXeroStatus, reset: () => { localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(MODEL_KEY); localStorage.removeItem(BOARDROOM_PACKET_KEY); refresh(); } };
})(window);
