# Tessaris Finance Receipt Vision and Expense Policy

**Implemented:** 9 August 2026  
**Status:** Operational suggestion workflow; human confirmation and approval remain mandatory

## Outcome

The Finance Inbox can now read receipt images and PDFs, prefill visible accounting facts, check arithmetic, suggest a business expense category, surface uncertainty and route missing business context to the reviewer. It does not post to Xero or another accounting provider and it does not infer tax deductibility.

## Processing flow

1. The original upload is stored immutably and bound to its SHA-256 content hash.
2. Supported JPG, JPEG, PNG, WEBP, HEIC and PDF documents are sent to the configured vision provider.
3. The provider returns a constrained structured record containing merchant, date, currency, net, tax, tip, total, receipt number, payment evidence, line items, visible category signals and field-level confidence.
4. Tessaris normalises the fields and independently checks `net + tax + tip = total` within a two-cent tolerance.
5. The deterministic expense-policy layer applies learned supplier mappings and business-configured limits.
6. A human reviews the protected original beside the suggestions, supplies missing business context and confirms the accounting fields.
7. Existing HR authority rules select the approval route.
8. Approval creates only a provider-neutral accounting draft. External writes remain disabled.

## Meaning is separated from vision

The document reader answers only what is visible. A restaurant receipt can show food, drink and a total, but it cannot prove who attended or why the meal was a business cost. A fuel receipt cannot prove which vehicle or journey was involved, whether the fuel was wholly business use, or whether the business reimburses actual fuel or mileage.

The policy layer therefore requires:

- meals and hospitality: business purpose and attendees;
- alcohol: justification or the amount to exclude;
- fuel: vehicle, business journey and reclaim basis;
- mixed purchases: the business/personal split;
- possible personal purchases: exclusion or explicit business justification.

These questions must be answered before an ambiguous document can move to approval.

## Business policy configuration

The Finance Inbox now exposes an **Expense rules** view with optional fields for:

- policy currency;
- meal receipt limit;
- daily meal allowance;
- mileage rate.

These are company policy settings, not statutory tax rules. No legal allowance or tax treatment is hard-coded. Later country-specific tax adapters can assess a confirmed transaction against the applicable jurisdiction without changing the intake contract.

## Learning

When a reviewer confirms a supplier and allocation, Tessaris stores a normalised supplier mapping. The next document from the same supplier can reuse the confirmed category, account code, account name and tax code as a high-confidence suggestion. A reviewer can still override it. This creates useful automation from governed experience without allowing the model to self-authorise accounting treatment.

## Provider-neutral reader implementation

AION owns the receipt task, evidence rules, output schema, arithmetic checks, expense-policy assessment, authority route and approval gate. The selected LLM is an interchangeable perceptual worker; it is not allowed to redefine the accounting contract.

Eight receipt-capable routes now implement that contract, with a ninth mainstream provider registered for non-vision work:

- Gemini multimodal `generateContent` with inline image/PDF bytes and a response JSON schema;
- OpenAI Responses API with Base64 image input or PDF file input and strict Structured Outputs;
- Claude Messages vision/PDF input with structured outputs;
- Grok Responses vision input with strict structured outputs and response storage disabled;
- Kimi K3 through the Moonshot OpenAI-compatible multimodal chat API, followed by Tessaris schema validation;
- local Gemma through Ollama vision and JSON-schema output, without sending the source off the Mac.
- Meta AI through the OpenAI-compatible Meta Model API Responses route using multimodal Muse Spark and strict schema output;
- Mistral AI through its multimodal Chat Completions route with JSON output and Tessaris schema validation;
- DeepSeek is present in the main provider vault for text/reasoning work, but remains disabled in the receipt-reader selector because its official API currently exposes JSON output without a verified image-input contract.

The business saves its chosen reader under `expense_policy.receipt_reader_provider`. The Finance UI displays every provider, its selected model and whether it is connected and receipt-capable. `auto` tries only configured cloud readers in a fixed order. Selecting a named provider is strict: if Claude is selected and Claude is unavailable, the read fails closed and does not quietly send the document to Grok, Gemini or another company.

The Vault provider panel now includes working save, refresh and removal controls for OpenAI, Claude, Gemini, Grok, Kimi, Gemma, Meta, Mistral and DeepSeek. Adding a provider changes only credentials and model selection; no Finance workflow code needs to be redesigned.

## Boardroom membership is independent of receipt vision

Provider connection, Boardroom membership and receipt-reading eligibility are three separate states:

1. A provider is **connected** when its credential or verified local runtime exists.
2. A connected provider becomes a **Boardroom member** only when the user enables its Boardroom checkbox.
3. A provider appears as a **receipt reader** only when Tessaris has a verified image-input transport for that provider/model family.

All nine mainstream providers can serve as Boardroom members. The live Boardroom router now contains real call paths for OpenAI, Claude, Gemini, Grok, Kimi, Meta, Mistral, DeepSeek and local Gemma; the former Claude/Grok placeholder boundary has been removed. Missing providers fail visibly and never produce simulated opinions.

DeepSeek therefore remains useful as a technical and cost-focused Boardroom adviser while the Finance UI states that receipt reconciliation is unavailable for it. This is a capability warning, not a provider-wide rejection. If DeepSeek later exposes a documented image-input model, only its receipt transport/capability record needs to change.

Local Gemma is not selected for the Boardroom by default because its installed model consumes substantial memory. The user may opt it in explicitly. This prevents an ordinary Boardroom run from unexpectedly loading the high-memory local model.

Every response is validated against the same nested JSON Schema after transport-level structured output. Missing fields, invalid enumerations, malformed line items and out-of-range confidence values are rejected. Provider and model identity, latency, usage metadata, external-transfer status and the no-storage request are recorded with the suggestion.

Local Gemma is deliberately explicit-only. The installed `gemma4:e2b` model advertises vision but loads approximately 7.7 GB on this Mac. It is shown with a high-memory warning and is excluded from automatic fallback so receipt processing cannot unexpectedly destabilise Tessaris or the AION background services.

Tessaris requests no provider-side response storage where the provider exposes that control. The UI explicitly tells the user which reader will receive the image or PDF. The protected local original remains unchanged.

## API additions

- `POST /api/aion/business/finance-inbox/{workspace_id}/documents/{document_id}/extract`
- `PUT /api/aion/business/finance-inbox/{workspace_id}/expense-policy`

`GET /api/aion/business/finance-inbox/{workspace_id}` also returns public reader readiness metadata; API keys are never returned. The extraction request may specify `provider`, while the saved business policy supplies the normal default.

The extraction endpoint mutates only the suggestion record. On provider or schema failure it records a fail-closed extraction status and preserves the original for manual review.

## Evidence

- The Claude, Grok, Kimi, Gemma, Meta and Mistral transport/contract suite passes, including fail-closed malformed-output coverage, DeepSeek receipt-vision rejection and explicit-provider no-fallback coverage.
- 33 focused Boardroom-provider, receipt-reader, Finance service/API and UI-lock tests passed after the main-suite expansion.
- JavaScript syntax and Python compilation checks passed.
- A live Gemini 2.5 Flash read of a synthetic trade receipt correctly returned:
  - supplier: `FERRETERIA SOL`;
  - date: `2026-08-09`;
  - net: `EUR 50.00`;
  - tax: `EUR 10.50`;
  - total: `EUR 60.50`;
  - primary category: `materials`;
  - category confidence: `0.90`;
  - uncertainties: none.
- A non-receipt screenshot was correctly classified as `other` with no invented supplier and an uncertainty marker.
- The OpenAI request path reached the API correctly, but that configured OpenAI account currently has no remaining credits. Gemini is therefore the working live route.
- Claude, Grok and Kimi are implemented but could not be live-billed because no corresponding keys are connected. They remain visibly unavailable until connected rather than returning simulated success.
- Local Gemma's vision capability was confirmed. A live full-schema attempt loaded roughly 7.7 GB, so it was unloaded and retained as an explicit high-memory option instead of being placed in automatic fallback.
- A live, non-simulated Gemini Boardroom smoke call succeeded through the expanded Boardroom router after installation.

## Current honest boundary

This is high-quality pre-accounting automation, not autonomous bookkeeping. A person still confirms the evidence and business purpose, and an authorised person still approves the resulting draft. Automatic posting, jurisdiction-specific tax validation, duplicate transaction matching and accounting-provider reconciliation remain later controlled stages.

## Main implementation files

- `backend/modules/aion_business/runtime/finance_receipt_vision.py`
- `backend/modules/aion_business/runtime/finance_expense_policy.py`
- `backend/modules/aion_business/runtime/finance_inbox_service.py`
- `backend/modules/aion_business/api/finance_inbox_api.py`
- `desktop/mac/src/aion_finance_inbox_workspace.js`
- `backend/tests/test_finance_inbox_service.py`
- `backend/tests/test_finance_receipt_vision.py`
- `backend/tests/workflow_capsules/test_aion_finance_inbox_ui_lock.py`
