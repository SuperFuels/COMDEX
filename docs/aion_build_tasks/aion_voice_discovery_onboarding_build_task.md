# AION Build Task — Voice Discovery Onboarding + Conversational Business Twin Setup

## Objective

Build a Voice Discovery Onboarding capability for AION so the first business setup experience feels like a natural conversation with the AI Boardroom, not a form-filling chore.

The user should be able to start onboarding by speaking naturally:

> Sit down with the AI Boardroom and explain your business.

AION should listen, ask intelligent follow-up questions through department function heads, extract structured Business Twin data, identify gaps, confirm the summary with the user, and write the result into the same ledgers and persistence systems used by manual forms.

Manual setup must remain available as the structured fallback and correction surface.

---

## Core Product Principle

Voice discovery is not a separate chat feature.

It is a natural capture layer over the same structured onboarding system.

The voice session must write into:

- Business Twin
- Department Intelligence Ledger
- Boardroom readiness status
- Discovery backlog
- Function/department discovery records
- Evidence and provenance records
- Goal Loop candidate records where relevant

Startup flow:

Startup
→ I have a business
→ Choose onboarding style
→ Start with a conversation / Fill in manually / Upload or connect data
→ Voice discovery session
→ AION extracts Business Twin fields
→ Department heads ask follow-up questions
→ User confirms summary
→ Finance-first / Live Agents / Boardroom unlock

The recommended first option should be:

Start with a conversation — Recommended

---

## Provider Principle

Do not hard-code ElevenLabs.

AION should support provider abstraction:

- speech-to-text provider
- text-to-speech provider
- LLM extraction provider
- conversation reasoning provider

Out of the box, AION may use a managed platform voice provider key, but it must be usage-limited.

Customers should not need an ElevenLabs account for the default experience.

Provider behaviour:

- AION default managed voice profile
- usage caps per session
- retry limits
- text-only fallback
- optional customer-owned provider key later
- Vault/settings provider status later
- no raw audio storage by default

---

## Phase 1 — Code Discovery / Audit

Before building, locate the current startup, onboarding, Business Twin, Live Agents and Boardroom routes.

Required audit:

- startup screen code
- “I have a business” route handler
- Business Twin setup overlay
- manual form setup fields
- website scan/import logic
- Business Twin persistence keys
- Department Intelligence Ledger helpers
- Discovery Question Inbox/backlog
- Boardroom readiness status
- Finance-first routing
- Live Agents department tabs
- provider council / LLM call path
- Vault provider key storage
- existing voice/audio code
- frontend render loop

---

## Phase 2 — Voice Discovery Data Contract

Create a stable `voice_discovery_session` contract.

Required fields:

- session_id
- business_id
- workspace_id
- mode
- status
- current_stage
- transcript
- transcript_chunks
- speaker_turns
- extracted_facts
- department_questions
- answered_questions
- unanswered_questions
- confidence_by_field
- business_twin_draft
- department_ledger_patch
- boardroom_readiness_patch
- discovery_backlog_patch
- confirmation_summary
- user_confirmed
- consent
- cost_controls
- created_at
- updated_at

Draft facts must remain separate from confirmed facts.

---

## Phase 3 — Startup Choice

Add three onboarding paths after “I have a business”:

1. Start with a conversation — Recommended
2. Fill in manually
3. Upload / connect data

Manual setup remains the structured edit/correction surface.

---

## Phase 4 — Voice Capture Layer

Frontend states:

- idle
- permission_requested
- listening
- paused
- transcribing
- thinking
- asking_followup
- summary_ready
- awaiting_confirmation
- confirmed
- failed

Build:

- mic permission
- recording state
- start/pause/stop controls
- typed fallback
- live transcript
- transcript chunk persistence
- session recovery
- discard session
- continue later

---

## Phase 5 — Speech-to-Text Adapter

Provider-abstract STT contract.

Do not hard-code one provider.

Support:

- browser/dev mock STT
- cloud STT later
- local Whisper later
- manual transcript correction
- confidence if available
- transcript-first persistence
- raw audio optional only

---

## Phase 6 — Text-to-Speech Adapter

Provider-abstract TTS contract.

Support:

- AION host voice
- department voice profiles later
- mute / text-only mode
- replay last question
- captions
- provider fallback
- AION-managed default key with usage caps

---

## Phase 7 — Discovery Conversation Controller

Guided discovery meeting, not generic free chat.

Rules:

- ask one question at a time
- extract after each answer
- detect missing fields
- route to department heads
- avoid asking answered questions
- allow skip / I don’t know / connect data instead
- stop when minimum readiness is reached
- produce confirmation summary

Opening question:

Tell me what your business does, who your customers are, and what you want help with first.

---

## Phase 8 — Extraction into Business Twin Schema

Extract:

- business name
- business type
- products/services
- region/service area
- customer type
- primary goal
- pricing model
- costs
- capacity
- lead sources
- operational constraints
- support/customer issues
- finance gaps
- confidence by field
- unanswered questions
- suggested connectors/uploads

Every extracted fact needs source transcript reference and confidence.

---

## Phase 9 — Department Head Discovery

Finance:
pricing, margins, costs, cash, budget, accounting tools.

Sales:
lead sources, follow-up, quote process, conversion, CRM.

Operations:
capacity, delivery process, bottlenecks, scheduling, resources.

Marketing:
target customer, offer, channels, current campaigns, brand/message.

Support:
complaints, objections, reviews, repeat questions, feedback loops.

---

## Phase 10 — Confirmation Summary

Before confirmed ledger writes:

- show extracted facts
- show confidence
- show known gaps
- show department readiness
- show recommended route
- allow voice confirmation
- allow typed correction
- allow manual editing
- allow upload/connect instead

Confirmation options:

- Yes, that’s right
- Change something
- Ask me more
- I’ll fill missing parts manually
- Connect data instead

---

## Phase 11 — Ledger Writes

Confirmed voice discovery writes to:

- Business Twin
- Department Intelligence Ledger
- Boardroom readiness status
- Discovery backlog
- Business container
- Department sub-containers
- Transcript evidence record
- Extraction provenance record
- Confirmation receipt

Voice onboarding and manual onboarding must converge into the same Business Twin schema.

---

## Phase 12 — Finance-First Route

After confirmation:

- if pricing/cost/margin/cash missing → Finance
- if finance sufficient but delivery capacity missing → Operations
- if core discovery sufficient → limited Boardroom unlock
- manual and upload/connect paths remain available

---

## Phase 13 — Boardroom Readiness Integration

Readiness states:

- not_started
- conversation_started
- draft_ready
- confirmed_partial
- finance_required
- operations_required
- department_discovery_required
- boardroom_limited
- boardroom_ready

Boardroom shows:

- what AION knows
- what AION does not know
- departments ready
- departments blocked
- next best question
- useful uploads/connectors

---

## Phase 14 — Safety, Privacy and Consent

Voice onboarding rules:

- ask mic permission only when needed
- visible recording indicator
- pause/stop/delete
- transcript storage by default
- raw audio storage disabled by default
- user can delete transcript/session
- no live messages
- no bookings
- no payments
- no invoices
- no external actions
- extracted facts remain draft until confirmed

---

## Phase 15 — Session Orchestration

Turn state:

- aion_speaking
- user_speaking
- thinking
- waiting
- interrupted

Support:

- user interruption / barge-in
- long silence detection
- gentle prompt after silence
- skip / come back / I don’t know
- department context per question
- question resolution tracking

---

## Phase 16 — Streaming vs Batch Transcription

First implementation can use batch typed/dev transcript.

Design for future streaming:

- partial transcript
- final transcript
- corrected transcript
- discarded transcript
- partial transcript never becomes confirmed fact

---

## Phase 17 — Schema Guard

Validation rules:

- validate against Business Twin schema
- unknown fields go to extra_notes
- direct statements separate from inferences
- draft facts separate from confirmed facts
- source transcript reference required
- schema_version required

---

## Phase 18 — Multilingual Support

Priority:

- English
- Spanish
- mixed English/Spanish

Preserve:

- original transcript
- translated transcript if used
- language metadata
- user wording

---

## Phase 19 — Error Recovery

Fallback modes:

- voice_full
- voice_without_tts
- text_only
- upload_or_connect
- manual_form
- session_recovery

Provider failure must not crash onboarding.

---

## Phase 20 — Cost and Rate Limits

Controls:

- max_session_minutes: 20
- max_followup_questions: 12
- max_questions_per_department: 3
- max_retries_per_provider: 2
- extract_after_each_turn: true
- extract_while_streaming: false
- provider timeout
- usage metering
- AION-managed key limit

---

## Phase 21 — Backend API Contracts

Suggested routes:

- POST /api/aion/voice-discovery/session/start
- POST /api/aion/voice-discovery/session/{session_id}/audio
- POST /api/aion/voice-discovery/session/{session_id}/transcript
- POST /api/aion/voice-discovery/session/{session_id}/extract
- POST /api/aion/voice-discovery/session/{session_id}/next-question
- POST /api/aion/voice-discovery/session/{session_id}/confirm
- POST /api/aion/voice-discovery/session/{session_id}/discard
- GET  /api/aion/voice-discovery/session/{session_id}

---

## Phase 22 — Voice-to-Goal-Loop Handoff

Capture goals during onboarding.

Store goal candidates as draft Boardroom goals.

Example:

{
  "goal_candidate_id": "goal_candidate_001",
  "source": "voice_discovery",
  "title": "Get more qualified leads",
  "department_dependencies": ["marketing", "sales", "finance", "operations"],
  "status": "draft",
  "ready_for_boardroom_review": true
}

---

## Tests / Locks

Add tests for:

- startup shows Start with a conversation
- manual setup remains
- upload/connect remains
- session object created
- transcript chunks persist
- extraction maps into Business Twin schema
- department questions generated from missing fields
- confirmation writes to Business Twin
- correction updates extracted facts
- discovery backlog created
- Department Intelligence Ledger patched
- Boardroom readiness updated
- Finance-first routing works
- provider unavailable does not crash
- text-only fallback works
- raw audio not stored by default
- no ElevenLabs hard dependency
- no hard-coded Home Fixed data
- no stale costa-conexion default
- no live external actions
- node --check desktop/mac/src/app.js
- python -m py_compile backend/main.py

---

## Definition of Done

Complete when:

- user can choose Start with a conversation
- AION can capture spoken or typed onboarding input
- transcript is persisted safely
- structured Business Twin fields are extracted
- department heads ask targeted follow-up questions
- AION produces confirmation summary
- user confirms or corrects
- confirmed data writes into Business Twin
- Department Intelligence Ledger updates
- Discovery backlog updates
- Boardroom readiness updates
- user routes to Finance-first, Live Agents or limited Boardroom
- manual forms remain available
- upload/connect remains available
- provider failures do not crash onboarding
- no live external actions occur
- system remains generic for any business
