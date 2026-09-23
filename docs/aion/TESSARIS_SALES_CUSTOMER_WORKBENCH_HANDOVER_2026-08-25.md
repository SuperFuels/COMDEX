# Tessaris Sales Customer Workbench — Continuation Handover

**Prepared:** 25 August 2026  
**Repository:** `/Users/kevinrobinson/dev/COMDEX`  
**Status:** implementation deliberately stopped; requested customer workbench is **not complete**

## 1. User objective

Turn the existing full-page Sales customer record into a practical customer/job workspace. The customer is already selected, so every note, job, quote, variation and invoice add-on must remain attached to that customer without asking the user to choose the lead again.

The intended workflow is generic enough for different businesses, while supporting a service/trade business particularly well:

1. Open a customer or lead from Sales.
2. Add an internal note or verified job update.
3. Create a new job, quote, quote variation/add-on, or invoice add-on.
4. Build a private cost breakdown using labour, materials and external charges.
5. Produce customer-facing quote wording that excludes private costs and margin.
6. Save the record into the same durable customer work feed.
7. Later, approve and send the exact quote/email through a connected provider.

## 2. Required user-facing capabilities

The customer page needs one integrated commercial workbench with these modes:

- Internal note
- New job / project
- New quote
- Quote variation or add-on
- Invoice add-on

For notes:

- Title
- Internal note/details
- Recorded by
- Save to customer feed

For jobs, quotes and add-ons:

- Read-only selected customer identity
- Internal reference or job number
- Job/quote title
- Scope of work
- Internal notes
- Repeatable cost lines
- Terms and payment schedule
- Generated customer-facing wording
- Private totals and margin calculation
- Save draft to the customer work feed

Cost-line categories must include:

- Labour
- Materials
- Parking
- Congestion charge
- ULEZ or equivalent local charge
- Supplier/subcontractor
- Scaffolding
- Skip/waste
- Other

Each line should support:

- Description
- Quantity
- Internal unit cost
- Customer unit price
- Optional person selection for labour, populated from the existing People records

Calculated totals:

- Internal cost total
- Customer net total
- VAT/tax percentage
- VAT/tax amount
- Customer gross total
- Gross profit
- Gross margin percentage

The customer-facing preview must contain only customer-safe fields: scope, charge lines, net, tax, gross and terms. It must not expose internal costs, labour cost rates or margin.

## 3. Current implementation state

Primary frontend file:

`desktop/mac/src/aion_sales_revenue_workspace.js`

Current verified facts about the file:

- `customerWorkspace()` already renders the selected customer as a full-page record.
- `markup()` returns `customerWorkspace()` when `state.panel === 'detail'`.
- The customer page already contains:
  - Back to Sales
  - Save customer record acknowledgement
  - Customer identity and enquiry
  - Qualification summary
  - Campaign/consent summary
  - Customer work feed
  - Existing actions such as Qualify, Log conversation and Prepare production call
- The old `work_event` side panel still exists for a generic lifecycle update.
- The lower global commercial-work form still asks the user to choose a lead. It is not the requested customer-specific workbench.
- No customer-specific notes/jobs/quotes/add-ons workbench has been implemented in this interrupted run.
- No source files were edited during the interrupted run before this handover was written.

Relevant code locations at handover time:

- `customerWorkspace()` begins near line 161.
- `panel()` and `work_event` are near lines 173–206.
- `markup()` and `render()` are near lines 221–251.
- `post()` is near lines 281–286 and currently closes the active panel after success.
- Click routing begins near line 289.
- Existing work-feed submission begins near line 405.
- Styles begin near line 433.

## 4. Existing durable write route

The existing customer work-feed endpoint is the correct initial persistence route:

`POST /api/aion/sales/{workspace_id}/opportunities/{opportunity_id}/work-feed/events`

Existing payload shape:

```json
{
  "kind": "...",
  "title": "...",
  "summary": "...",
  "details": {},
  "lifecycle_stage": "...",
  "source": "sales",
  "provider": "tessaris",
  "source_reference": "...",
  "attachments": [],
  "action": {
    "status": "draft",
    "external_action_performed": false
  },
  "recorded_by_person_id": "..."
}
```

The new workbench should store its structured record inside `details`, for example:

```json
{
  "commercial_record": {
    "mode": "new_quote",
    "reference": "Q-001",
    "scope": "...",
    "internal_note": "...",
    "lines": [],
    "totals": {},
    "terms": "..."
  },
  "customer_facing": {
    "wording": "...",
    "lines": [],
    "net": 0,
    "tax_rate": 0,
    "tax": 0,
    "gross": 0,
    "terms": "..."
  }
}
```

Every initial save must remain `external_action_performed: false`. Sending, invoicing, payment collection or third-party writes remain separate exact-approval operations.

## 5. Implementation plan — resume in this order

### Step A — add structured draft state

Extend the state object with a customer/opportunity-keyed commercial draft store, for example:

```js
commercialDrafts: {}
```

The draft must survive the application's periodic render/load cycle while the user is typing.

### Step B — add workbench helpers

Add helpers before `customerWorkspace()` for:

- Default draft creation
- Draft lookup by opportunity ID
- Repeatable-line creation/removal
- Reading form values back into structured state
- Currency-safe numeric conversion
- Totals calculation
- Customer-facing quote wording generation
- Workbench HTML rendering

Do not hard-code roofing, CarbonCore, HomeFixed or a single industry into the general component.

### Step C — mount the workbench on the customer page

Render it inside `customerWorkspace()` after the customer work feed/actions. It must remain on the full customer page and must not open as a right-hand sidebar.

### Step D — wire interactions

Add click handling before generic `data-srw-panel` routing for:

- Change workbench mode
- Add cost line
- Remove cost line
- Generate/update customer wording
- Reset/cancel current draft

Use input/change handlers to preserve the structured draft and update calculated totals without wiping focused fields.

### Step E — submit without leaving the customer record

Handle `data-srw-form="commercial"` before the generic `work_event` branch.

On successful save:

1. POST to the existing work-feed endpoint.
2. Clear only that customer's completed draft.
3. Reload Sales data.
4. Restore `state.selectedId`.
5. Restore `state.panel = 'detail'`.
6. Show a clear success message on the customer page.

Do not use the existing generic `post()` helper unchanged because it sets `state.panel = null`, which returns the user to Sales.

### Step F — style the workbench

Add styles to the existing injected stylesheet for:

- Mode selector
- Workbench form
- Repeatable cost rows
- Private totals
- Customer-facing preview
- Responsive single-column fallback

Match the current light-blue, white, grey and black Tessaris design.

## 6. Non-negotiable behavioural requirements

- Periodic Sales refreshes must not clear partially entered workbench fields.
- Opening the customer page must not ask the user to select the same customer again.
- A quote variation must append to the current customer history rather than overwrite the original quote.
- Internal notes and costs must never appear in customer-facing output.
- Saving a draft must not imply that an email, invoice or payment action occurred.
- Each saved event must retain actor, source, lifecycle stage and timestamp from the backend receipt.
- No hard-coded responses or industry-specific assumptions.
- All external actions remain governed independently.

## 7. Tests to add or update

Primary UI behavioural test:

`backend/tests/workflow_capsules/test_aion_sales_revenue_workspace_ui.py`

Minimum assertions:

- Full-page customer workspace remains present.
- Workbench modes are rendered.
- Customer selection is implicit from `state.selectedId`.
- Repeatable cost lines are supported.
- Labour/person selector uses existing actor/person records.
- Totals include net, tax, gross, cost, profit and margin.
- Customer-facing preview omits internal costs.
- Workbench submits to `/work-feed/events`.
- Successful submit restores `state.panel = 'detail'`.
- `external_action_performed` is false.
- Draft state is preserved through render/load cycles.

Also run JavaScript syntax validation against the edited file.

## 8. Verification and release sequence

After implementation:

1. Run JavaScript syntax validation.
2. Run the targeted Sales workspace behavioural tests.
3. Run any broader desktop tests affected by the shared sticky header or Sales mounting lifecycle.
4. Build/package the desktop app using the repository's existing release process.
5. Verify the installed Tessaris bundle hash.
6. Relaunch Tessaris.
7. Manually verify:
   - Open Sales.
   - Open a customer.
   - Create an internal note.
   - Create a quote with labour, materials and an external charge.
   - Confirm totals update.
   - Save it.
   - Confirm the customer page remains open.
   - Confirm the saved record appears in the customer feed.
   - Confirm private cost/margin data is absent from the customer wording.

## 9. Claim boundary

At the time of this handover, only the full-page customer record is present. The requested integrated notes/jobs/quotes/add-ons workbench is not implemented, tested, packaged or installed. Do not report this feature complete until the verification sequence above passes against the installed Tessaris application.

