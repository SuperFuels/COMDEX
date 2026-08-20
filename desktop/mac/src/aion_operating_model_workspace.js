(function installAionOperatingModelWorkspace(global) {
  'use strict';

  const STORAGE_KEY = 'aion.businessOperatingModel.draft.v1';
  const TABS = [
    ['offerings', 'Offerings'], ['workforce', 'Workforce & capacity'], ['jobs', 'Jobs & quotes'],
    ['stock', 'Stock'], ['procurement', 'Procurement'], ['finance', 'Finance'], ['summary', 'Summary'],
  ];
  const state = {
    loaded: false, loading: false, saving: false, error: '', savedAt: '', activeTab: 'offerings', people: [],
    model: {
      model_status: 'draft', setup_mode: 'simple', currency: 'EUR', revision: 0,
      offerings: [], pricing_rules: [], payment_terms: [], customer_terms: [], labour_resources: [],
      jobs: [], job_labour_assignments: [], job_cost_items: [], job_economics: [],
      overheads: [], debt_commitments: [], financial_targets: [], production_lines: [],
      bills_of_materials: [], inventory_items: [], suppliers: [], procurement_queue: [],
      unit_economics: [], inventory_metrics: {}, capacity_model: {}, provenance: {}, source_refs: [],
    },
  };

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const list = (key) => Array.isArray(state.model[key]) ? state.model[key] : (state.model[key] = []);
  const money = (value) => new Intl.NumberFormat('en-GB', { style: 'currency', currency: state.model.currency || 'EUR', maximumFractionDigits: 2 }).format(Number(value || 0));
  const localId = (prefix) => `${prefix}.draft.${Date.now().toString(36)}.${Math.random().toString(36).slice(2,7)}`;

  function ensureRelationshipIds() {
    [['offerings','offering'],['labour_resources','labour'],['jobs','job']].forEach(([key,prefix]) => {
      list(key).forEach((row) => { if (!row.id) row.id = localId(prefix); });
    });
  }

  function persistDraft() { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.model)); } catch {} }
  function rerender() { if (typeof global.requestRender === 'function') global.requestRender(); }

  let conversationPersistTimer = null;

  function conversationFacts() {
    const provenance = state.model.provenance && typeof state.model.provenance === 'object'
      ? state.model.provenance
      : (state.model.provenance = {});
    return Array.isArray(provenance.conversation_facts)
      ? provenance.conversation_facts
      : (provenance.conversation_facts = []);
  }

  function upsertFinancialTarget(id, name, value, unit) {
    if (value == null || value === '' || !Number.isFinite(Number(value))) return;
    const targets = list('financial_targets');
    const current = targets.find((row) => row.id === id || row.source_fact_id === id);
    const next = {
      id,
      source_fact_id: id,
      name,
      target_value: Number(value),
      unit,
      source: 'department_pilot_conversation',
      status: 'owner_supplied_unverified',
    };
    if (current) Object.assign(current, next);
    else targets.push(next);
  }

  function applyStructuredConversationFact(fact) {
    const extracted = fact.extracted && typeof fact.extracted === 'object' ? fact.extracted : {};
    const capacity = state.model.capacity_model && typeof state.model.capacity_model === 'object'
      ? state.model.capacity_model
      : (state.model.capacity_model = {});

    if (fact.field === 'engineer_planning_rate' || fact.field === 'workforce_capacity_and_costs') {
      capacity.engineer_planning_rate = {
        ...extracted,
        source_fact_id: fact.id,
        status: 'owner_supplied_unverified',
        updated_at: fact.updated_at,
      };
    }
    if (fact.field === 'average_job_cost_by_service') {
      capacity.average_job_cost_by_service = { ...extracted, raw: fact.answer, source_fact_id: fact.id };
    }
    if (fact.field === 'weekly_delivery_capacity') {
      capacity.weekly_delivery_capacity = { raw: fact.answer, source_fact_id: fact.id };
    }
    if (fact.field === 'target_gross_margin') {
      upsertFinancialTarget(fact.id, 'Target gross margin', extracted.percent, '%');
    }
    if (fact.field === 'minimum_profitable_job_value') {
      upsertFinancialTarget(fact.id, 'Minimum profitable job value', extracted.primary_amount, extracted.currency || state.model.currency || 'EUR');
    }
    if (fact.field === 'campaign_spend_limit' || fact.field === 'financial_limit') {
      upsertFinancialTarget(fact.id, fact.field === 'campaign_spend_limit' ? 'Campaign spend limit' : 'Financial limit', extracted.primary_amount, extracted.currency || state.model.currency || 'EUR');
    }
  }

  async function persistConversationFactsToBackend() {
    try {
      if (!global.AionBusinessContainerClient?.saveOperatingModel) return;
      const facts = [...conversationFacts()];
      const expected = Number(state.model.revision || 0) || null;
      const result = await global.AionBusinessContainerClient.saveOperatingModel(state.model, expected);
      if (result?.payload) {
        state.model = {
          ...state.model,
          ...result.payload,
          provenance: {
            ...(state.model.provenance || {}),
            ...(result.payload.provenance || {}),
            conversation_facts: facts,
          },
        };
      }
      state.savedAt = new Date().toLocaleTimeString();
      persistDraft();
      global.dispatchEvent(new CustomEvent('aion:operating-model-conversation-fact-saved', { detail: { count: facts.length } }));
    } catch (error) {
      state.error = `Conversation fact is saved locally; Business Container sync is pending: ${String(error?.message || error)}`;
      persistDraft();
    }
  }

  function applyConversationFact(fact, options = {}) {
    const clean = fact && typeof fact === 'object' ? { ...fact } : null;
    if (!clean?.id || !clean.answer) return null;
    if (options.dryRun === true) return clean;

    const facts = conversationFacts();
    const index = facts.findIndex((item) => item.id === clean.id);
    if (index >= 0) facts[index] = clean;
    else facts.push(clean);
    applyStructuredConversationFact(clean);
    persistDraft();

    if (options.persistBackend !== false) {
      if (conversationPersistTimer) clearTimeout(conversationPersistTimer);
      conversationPersistTimer = setTimeout(persistConversationFactsToBackend, 650);
    }
    return clean;
  }

  async function load() {
    if (state.loading || state.loaded) return;
    state.loading = true;
    try {
      const result = await global.AionBusinessContainerClient?.getOperatingModel?.();
      if (result?.payload) state.model = { ...state.model, ...result.payload };
      try {
        const businessId = global.AionBusinessContainerClient?.resolveBusinessId?.();
        const response = await fetch(`http://127.0.0.1:8080/api/aion/business/organisation/${encodeURIComponent(businessId)}`);
        const organisation = response.ok ? await response.json() : null;
        state.people = (organisation?.model?.people || []).filter((person) => person.status === 'active');
      } catch { state.people = []; }
      ensureRelationshipIds();
    } catch (error) {
      if (!String(error).includes('404')) state.error = String(error?.message || error);
      try {
        const draft = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
        if (draft) state.model = { ...state.model, ...draft };
      } catch {}
    } finally {
      state.loading = false; state.loaded = true; rerender();
    }
  }

  async function save() {
    state.saving = true; state.error = ''; rerender();
    try {
      const expected = Number(state.model.revision || 0) || null;
      const result = await global.AionBusinessContainerClient.saveOperatingModel(state.model, expected);
      state.model = { ...state.model, ...(result.payload || {}) };
      // A saved operating model is a Finance input, not an isolated catalogue.
      // Rebuild the source-backed Finance package so its unit economics and the
      // Boardroom projection reflect the owner's latest approved assumptions.
      try {
        const completion = await global.AionBusinessContainerClient.completeFinanceFoundation?.();
        if (completion?.operating_model) {
          state.model = { ...state.model, ...completion.operating_model };
        }
      } catch (completionError) {
        // The operating-model save remains valid if Finance discovery has not
        // been completed yet. Its next Finance finalisation will perform this.
        console.warn('Finance completion deferred after operating-model save', completionError);
      }
      state.savedAt = new Date().toLocaleTimeString();
      persistDraft();
      global.dispatchEvent(new CustomEvent('aion:operating-model-saved', { detail: result }));
    } catch (error) {
      state.error = String(error?.message || error);
      persistDraft();
    } finally { state.saving = false; rerender(); }
  }

  async function importSpreadsheet(file, category) {
    if (!file) return;
    state.saving = true; state.error = ''; rerender();
    try {
      const result = await global.AionBusinessContainerClient.importOperatingModelSpreadsheet(file, category);
      state.model = { ...state.model, ...(result.payload || {}) };
      state.savedAt = `${result.import?.imported_row_count || 0} ${category === 'offerings' ? 'offerings' : 'stock items'} imported`;
      persistDraft();
    } catch (error) { state.error = String(error?.message || error); }
    finally { state.saving = false; rerender(); }
  }

  function option(values, selected) {
    return values.map(([value, label]) => `<option value="${esc(value)}" ${String(value) === String(selected) ? 'selected' : ''}>${esc(label)}</option>`).join('');
  }

  function input(listName, index, field, value, type = 'text', placeholder = '') {
    return `<input class="om-input" type="${type}" data-om-list="${listName}" data-om-index="${index}" data-om-field="${field}" value="${esc(value)}" placeholder="${esc(placeholder)}">`;
  }

  function select(listName, index, field, value, values) {
    return `<select class="om-input" data-om-list="${listName}" data-om-index="${index}" data-om-field="${field}">${option(values, value)}</select>`;
  }

  function personSelect(listName, index, field, value) {
    const options = state.people.map((person) => {
      const costing = person.workforce_costing || {};
      const hourly = Number(costing.effective_hourly_cost);
      const daily = Number(costing.effective_daily_cost || (hourly * Number(costing.hours_per_day || 8)));
      const costingLabel = Number.isFinite(hourly) && hourly > 0
        ? ` · ${money(hourly)}/hour · ${money(daily)}/day`
        : ' · costing incomplete';
      return [person.id, `${person.name}${costingLabel}`];
    });
    return select(listName, index, field, value, [['','Select a person from HR'], ...options]);
  }

  function planningRateFromHR(row, basis = row?.cost_basis) {
    const person = state.people.find((candidate) => String(candidate.id) === String(row?.person_id));
    const costing = person?.workforce_costing || {};
    const hourly = Number(costing.effective_hourly_cost);
    if (!Number.isFinite(hourly) || hourly < 0) return null;
    if (basis === 'daily') {
      const daily = Number(costing.effective_daily_cost);
      return Number.isFinite(daily) ? daily : hourly * Number(costing.hours_per_day || 8);
    }
    if (basis === 'monthly') {
      return hourly * Number(costing.productive_hours_month || row?.available_hours_month || 160);
    }
    if (basis === 'per_job') return null;
    return hourly;
  }

  function syncLabourPlanningRate(row, reason) {
    const person = state.people.find((candidate) => String(candidate.id) === String(row?.person_id));
    if (person) row.person_name = person.name || row.person_name || '';
    const calculated = planningRateFromHR(row, row.cost_basis || 'hourly');
    if (calculated == null) return false;
    row.cost_rate = Number(calculated.toFixed(2));
    row.rate_source = 'hr_effective_cost';
    row.rate_sync_reason = reason;
    return true;
  }

  function relationSelect(listName, index, field, value, rows, placeholder) {
    return select(listName, index, field, value, [['', placeholder], ...rows.map((row) => [row.id, row.name || row.person_name || row.id])]);
  }

  function remove(listName, index) { return `<button class="om-remove" type="button" data-om-remove="${listName}" data-om-index="${index}" title="Remove row">×</button>`; }
  function empty(message) { return `<div class="om-empty">${esc(message)}</div>`; }

  function renderedConversationFacts(...sections) {
    const wanted = new Set(sections.flat().filter(Boolean));
    const rows = conversationFacts().filter((fact) => wanted.has(fact.target_section));
    if (!rows.length) return '';
    return `<section class="om-conversation-facts"><div class="om-conversation-facts-title">Captured by your AION agents</div>${rows.map((fact) => `<article><div><strong>${esc(fact.target_label || fact.field)}</strong><span>${esc(String(fact.question || ''))}</span></div><p>${esc(fact.answer)}</p><small>Owner supplied · available to the Boardroom · verify before external action</small></article>`).join('')}</section>`;
  }

  function offerings() {
    const rows = list('offerings');
    const advanced = state.model.setup_mode === 'advanced';
    return `${renderedConversationFacts('offerings')}
      <div class="om-section-head"><div><h3>Products, services and rate card</h3><p>Add one day rate or build a full product catalogue. Use + for each additional line.</p></div><div class="om-actions"><label class="om-import">Import CSV/XLSX<input type="file" accept=".csv,.xlsx" data-om-import="offerings"></label><button class="om-add" data-om-add="offerings">+ Add offering</button></div></div>
      ${rows.length ? `<div class="om-table-wrap"><table><thead><tr><th>Name</th><th>Type</th><th>Charge basis</th><th>Rate</th><th>Unit</th><th>Expected monthly volume</th>${advanced ? '<th>Material/unit</th><th>Labour/unit</th><th>Other direct/unit</th>' : ''}<th></th></tr></thead><tbody>
      ${rows.map((row, i) => `<tr><td>${input('offerings', i, 'name', row.name, 'text', 'Plumber day rate')}</td><td>${select('offerings', i, 'offering_type', row.offering_type || 'service', [['service','Service'],['product','Product'],['subscription','Subscription'],['rental','Rental'],['experience','Experience'],['other','Other']])}</td><td>${select('offerings', i, 'pricing_basis', row.pricing_basis || 'day_rate', [['hourly','Hourly'],['day_rate','Day rate'],['fixed','One-off / fixed'],['per_unit','Per unit'],['subscription','Subscription'],['tiered','Tiered volume'],['quote','Quoted'],['cost_plus','Cost plus']])}</td><td>${input('offerings', i, 'price', row.price, 'number', '0')}</td><td>${input('offerings', i, 'unit', row.unit || 'day', 'text', 'day')}</td><td>${input('offerings', i, 'expected_monthly_volume', row.expected_monthly_volume, 'number', '0')}</td>${advanced ? `<td>${input('offerings', i, 'material_cost_per_unit', row.material_cost_per_unit, 'number')}</td><td>${input('offerings', i, 'labour_cost_per_unit', row.labour_cost_per_unit, 'number')}</td><td>${input('offerings', i, 'other_direct_cost_per_unit', row.other_direct_cost_per_unit, 'number')}</td>` : ''}<td>${remove('offerings', i)}</td></tr>`).join('')}
      </tbody></table></div>` : empty('Start with a service, product, subscription or day rate.')}
      <div class="om-note">Customer-specific prices and payment terms can be added below Finance inputs. Large catalogues can be imported in the next connector stage without changing this model.</div>`;
  }

  function workforce() {
    const labour = list('labour_resources'); const lines = list('production_lines'); const bom = list('bills_of_materials');
    return `${renderedConversationFacts('workforce')}
      <div class="om-section-head"><div><h3>Workforce and direct labour</h3><p>Select real people from HR. Confidential pay, employment burden, leave and contractor rates stay owned by HR; this workspace receives an effective planning cost.</p></div><button class="om-add" data-om-add="labour_resources">+ Assign person</button></div>
      ${!state.people.length ? `<div class="om-route-note"><strong>Complete HR first</strong><p>Add employees, owners and contractors plus their confidential workforce costing, then return here.</p><button class="om-secondary" data-om-open-workspace="hr">Open HR people & costing</button></div>` : ''}
      ${labour.length ? `<div class="om-table-wrap"><table><thead><tr><th>Person from HR</th><th>Cost basis</th><th>Editable planning rate (${esc(state.model.currency || 'EUR')})</th><th>Available hours/month</th><th></th></tr></thead><tbody>${labour.map((r,i)=>`<tr><td>${personSelect('labour_resources',i,'person_id',r.person_id)}</td><td>${select('labour_resources',i,'cost_basis',r.cost_basis||'hourly',[['hourly','Hourly'],['daily','Daily'],['monthly','Monthly'],['per_job','Per job']])}</td><td><div class="om-rate-editor">${input('labour_resources',i,'cost_rate',r.cost_rate,'number','0.00')}<small>${r.rate_source === 'manual_planning_override' ? 'Planning override' : 'Synced from HR costing'}</small></div></td><td>${input('labour_resources',i,'available_hours_month',r.available_hours_month,'number')}</td><td>${remove('labour_resources',i)}</td></tr>`).join('')}</tbody></table></div><div class="om-note">Changing Hourly, Daily or Monthly recalculates the planning rate from HR. You may override the planning rate here; confidential pay in HR is never changed.</div>` : empty('Assign people only after they exist in HR. Never retype a person or confidential pay rate here.')}
      <div class="om-section-head"><div><h3>Production lines or delivery units</h3><p>Optional for factories, kitchens, workshops, crews or service teams.</p></div><button class="om-add" data-om-add="production_lines">+ Add line</button></div>
      ${lines.length ? `<div class="om-table-wrap"><table><thead><tr><th>Line / unit</th><th>Output unit</th><th>Capacity per day</th><th>Operating days/month</th><th>Constraint</th><th></th></tr></thead><tbody>${lines.map((r,i)=>`<tr><td>${input('production_lines',i,'name',r.name,'text','Cake line 1')}</td><td>${input('production_lines',i,'output_unit',r.output_unit,'text','cakes')}</td><td>${input('production_lines',i,'capacity_per_day',r.capacity_per_day,'number')}</td><td>${input('production_lines',i,'operating_days_month',r.operating_days_month,'number')}</td><td>${input('production_lines',i,'constraint',r.constraint,'text','oven capacity')}</td><td>${remove('production_lines',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('A sole trader can leave this empty; factories and production businesses can model each line.')}
      <div class="om-section-head"><div><h3>Materials used per product or job</h3><p>A lightweight bill of materials that links inputs to an offering.</p></div><button class="om-add" data-om-add="bills_of_materials">+ Add material</button></div>
      ${bom.length ? `<div class="om-table-wrap"><table><thead><tr><th>Offering ID / name</th><th>Material</th><th>Quantity per unit</th><th>Unit</th><th>Unit cost</th><th>Waste %</th><th></th></tr></thead><tbody>${bom.map((r,i)=>`<tr><td>${input('bills_of_materials',i,'offering_id',r.offering_id)}</td><td>${input('bills_of_materials',i,'material_name',r.material_name,'text','Flour')}</td><td>${input('bills_of_materials',i,'quantity_per_unit',r.quantity_per_unit,'number')}</td><td>${input('bills_of_materials',i,'unit',r.unit,'text','kg')}</td><td>${input('bills_of_materials',i,'unit_cost',r.unit_cost,'number')}</td><td>${input('bills_of_materials',i,'waste_percent',r.waste_percent,'number')}</td><td>${remove('bills_of_materials',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Add materials when a product or job consumes stock.')}`;
  }

  function jobs() {
    const jobs = list('jobs'); const assignments = list('job_labour_assignments'); const costs = list('job_cost_items'); const economics = list('job_economics');
    return `${renderedConversationFacts('jobs')}
      <div class="om-section-head"><div><h3>Quoted jobs and project economics</h3><p>Use this for variable work that cannot honestly be reduced to one standard unit cost. Start with an estimate, then track the accepted quote, live delivery and final actual result.</p></div><button class="om-add" data-om-add="jobs">+ Add job / quote</button></div>
      ${jobs.length ? `<div class="om-table-wrap"><table><thead><tr><th>Job / quote</th><th>Linked offering</th><th>Status</th><th>Estimated revenue</th><th>Actual revenue</th><th>Customer / reference</th><th></th></tr></thead><tbody>${jobs.map((r,i)=>`<tr><td>${input('jobs',i,'name',r.name,'text','Customer project or order')}</td><td>${relationSelect('jobs',i,'offering_id',r.offering_id,list('offerings'),'Optional offering')}</td><td>${select('jobs',i,'status',r.status||'estimate',[['estimate','Estimate'],['quote_draft','Quote draft'],['quote_sent','Quote sent'],['quote_accepted','Quote accepted'],['in_progress','Live job'],['completed','Completed'],['cancelled','Cancelled']])}</td><td>${input('jobs',i,'estimated_revenue',r.estimated_revenue,'number')}</td><td>${input('jobs',i,'actual_revenue',r.actual_revenue,'number')}</td><td>${input('jobs',i,'customer_reference',r.customer_reference,'text','Customer / order / project')}</td><td>${remove('jobs',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Add a job when price, labour or materials vary by customer, order, project or production batch.')}

      <div class="om-section-head"><div><h3>People assigned to jobs</h3><p>Estimate hours or days before accepting work, then record actual time. Rates come from the HR-linked workforce above.</p></div><button class="om-add" data-om-add="job_labour_assignments">+ Assign labour</button></div>
      ${assignments.length ? `<div class="om-table-wrap"><table><thead><tr><th>Job</th><th>Person</th><th>Basis</th><th>Estimated units</th><th>Actual units</th><th></th></tr></thead><tbody>${assignments.map((r,i)=>`<tr><td>${relationSelect('job_labour_assignments',i,'job_id',r.job_id,jobs,'Select job')}</td><td>${relationSelect('job_labour_assignments',i,'labour_resource_id',r.labour_resource_id,list('labour_resources').map((resource)=>({...resource,name:resource.person_name || state.people.find((person)=>person.id===resource.person_id)?.name || 'HR person'})),'Select assigned person')}</td><td>${select('job_labour_assignments',i,'cost_basis',r.cost_basis||'hourly',[['hourly','Hours'],['daily','Days'],['monthly','Months'],['per_job','Jobs']])}</td><td>${input('job_labour_assignments',i,'estimated_units',r.estimated_units,'number')}</td><td>${input('job_labour_assignments',i,'actual_units',r.actual_units,'number')}</td><td>${remove('job_labour_assignments',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Assign one or more people to each job—for example, two people for two days.')}

      <div class="om-section-head"><div><h3>Variable job costs</h3><p>Record what is known without pretending every cost is predictable. Materials, fuel, parking, tools, subcontractors and commission can be estimated first and confirmed later from Finance evidence.</p></div><button class="om-add" data-om-add="job_cost_items">+ Add cost</button></div>
      ${costs.length ? `<div class="om-table-wrap"><table><thead><tr><th>Job</th><th>Category</th><th>Description</th><th>Estimated</th><th>Actual</th><th>Evidence / note</th><th></th></tr></thead><tbody>${costs.map((r,i)=>`<tr><td>${relationSelect('job_cost_items',i,'job_id',r.job_id,jobs,'Select job')}</td><td>${select('job_cost_items',i,'category',r.category||'materials',[['materials','Materials'],['subcontractor','Subcontractor'],['travel_fuel','Travel / fuel'],['parking','Parking'],['tools_equipment','Tools / equipment'],['commission','Commission'],['delivery','Delivery / logistics'],['other_direct','Other direct cost']])}</td><td>${input('job_cost_items',i,'description',r.description,'text','Known or possible cost')}</td><td>${input('job_cost_items',i,'estimated_cost',r.estimated_cost,'number')}</td><td>${input('job_cost_items',i,'actual_cost',r.actual_cost,'number')}</td><td>${input('job_cost_items',i,'evidence_ref',r.evidence_ref,'text','Receipt, invoice, timesheet or note')}</td><td>${remove('job_cost_items',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Unknown costs can remain blank until they occur; actual Finance evidence can update them later.')}

      <div class="om-section-head"><div><h3>Estimate versus actual</h3><p>The Board sees margin and cost variance by job, without receiving individual salary details.</p></div></div>
      ${economics.length ? `<div class="om-table-wrap"><table><thead><tr><th>Job</th><th>Status</th><th>Est. revenue</th><th>Est. direct cost</th><th>Est. margin</th><th>Actual revenue</th><th>Actual direct cost</th><th>Actual margin</th><th>Cost variance</th></tr></thead><tbody>${economics.map((r)=>`<tr><td>${esc(r.name)}</td><td>${esc(r.status)}</td><td>${money(r.estimated_revenue)}</td><td>${money(r.estimated_direct_cost)}</td><td>${r.estimated_margin_percent == null ? '—' : `${esc(r.estimated_margin_percent)}%`}</td><td>${r.actual_revenue == null ? '—' : money(r.actual_revenue)}</td><td>${money(r.actual_direct_cost)}</td><td>${r.actual_margin_percent == null ? '—' : `${esc(r.actual_margin_percent)}%`}</td><td>${money(r.cost_variance)}</td></tr>`).join('')}</tbody></table></div>` : empty('Save the model to calculate each job estimate and actual result.')}`;
  }

  function stock() {
    const rows = list('inventory_items');
    return `<div class="om-section-head"><div><h3>Stock on hand</h3><p>Raw materials, work in progress, finished goods, consumables, packaging or resale stock.</p></div><div class="om-actions"><label class="om-import">Import CSV/XLSX<input type="file" accept=".csv,.xlsx" data-om-import="inventory"></label><button class="om-add" data-om-add="inventory_items">+ Add stock item</button></div></div>
    ${rows.length ? `<div class="om-table-wrap"><table><thead><tr><th>Item</th><th>Class</th><th>Unit</th><th>On hand</th><th>Reserved</th><th>Unit cost</th><th>Reorder at</th><th>Target</th><th>Lead days</th><th></th></tr></thead><tbody>${rows.map((r,i)=>`<tr><td>${input('inventory_items',i,'name',r.name,'text','Lettuce')}</td><td>${select('inventory_items',i,'stock_class',r.stock_class||'raw_material',[['raw_material','Raw material'],['work_in_progress','Work in progress'],['finished_good','Finished good'],['consumable','Consumable'],['packaging','Packaging'],['resale','Resale stock']])}</td><td>${input('inventory_items',i,'unit',r.unit||'units')}</td><td>${input('inventory_items',i,'quantity_on_hand',r.quantity_on_hand,'number')}</td><td>${input('inventory_items',i,'quantity_reserved',r.quantity_reserved,'number')}</td><td>${input('inventory_items',i,'unit_cost',r.unit_cost,'number')}</td><td>${input('inventory_items',i,'reorder_point',r.reorder_point,'number')}</td><td>${input('inventory_items',i,'target_stock',r.target_stock,'number')}</td><td>${input('inventory_items',i,'lead_time_days',r.lead_time_days,'number')}</td><td>${remove('inventory_items',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Service-only businesses can leave stock empty. Product businesses should enter the stock that ties up cash or constrains delivery.')}
    <div class="om-note">Saving calculates available stock, stock value, shortages and a draft replenishment suggestion. Nothing is ordered without approval.</div>`;
  }

  function procurement() {
    const rows = list('procurement_queue');
    return `<div class="om-quick"><div><strong>Quick add to procurement</strong><span>Example: “4 lettuce needed tomorrow”</span></div><input id="om-quick-procurement" class="om-input" placeholder="4 lettuce needed tomorrow"><button class="om-add" data-om-quick-add="true">Add to list</button></div>
    <div class="om-section-head"><div><h3>Procurement and shopping list</h3><p>Suggestions remain drafts until reviewed. Cash requirement is visible before approval.</p></div><button class="om-add" data-om-add="procurement_queue">+ Add purchase</button></div>
    ${rows.length ? `<div class="om-table-wrap"><table><thead><tr><th>Item</th><th>Quantity</th><th>Unit</th><th>Supplier</th><th>Needed by</th><th>Est. cash</th><th>Lead days</th><th>Status</th><th></th></tr></thead><tbody>${rows.map((r,i)=>`<tr><td>${input('procurement_queue',i,'name',r.name,'text','Lettuce')}</td><td>${input('procurement_queue',i,'quantity',r.quantity,'number')}</td><td>${input('procurement_queue',i,'unit',r.unit||'units')}</td><td>${input('procurement_queue',i,'supplier_name',r.supplier_name)}</td><td>${input('procurement_queue',i,'required_date',r.required_date,'date')}</td><td>${input('procurement_queue',i,'estimated_cash_required',r.estimated_cash_required,'number')}</td><td>${input('procurement_queue',i,'lead_time_days',r.lead_time_days,'number')}</td><td>${select('procurement_queue',i,'status',r.status||'draft',[['suggested','Suggested'],['draft','Draft'],['review','Review'],['approved','Approved'],['ordered','Ordered'],['received','Received'],['cancelled','Cancelled']])}</td><td>${remove('procurement_queue',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Purchasing suggestions and quick additions will appear here.')}`;
  }

  function simpleTable(key, title, description, columns, defaults) {
    const rows = list(key);
    return `<div class="om-section-head"><div><h3>${esc(title)}</h3><p>${esc(description)}</p></div><button class="om-add" data-om-add="${key}">+ Add line</button></div>${rows.length ? `<div class="om-table-wrap"><table><thead><tr>${columns.map(c=>`<th>${esc(c[1])}</th>`).join('')}<th></th></tr></thead><tbody>${rows.map((r,i)=>`<tr>${columns.map(c=>`<td>${input(key,i,c[0],r[c[0]],c[2]||'text')}</td>`).join('')}<td>${remove(key,i)}</td></tr>`).join('')}</tbody></table></div>` : empty(defaults)}`;
  }

  function finance() {
    return renderedConversationFacts('finance', 'targets') + simpleTable('payment_terms','Default and customer payment terms','Examples: 50% upfront / 50% completion, net 30, or a customer-specific exception.',[['name','Customer / default'],['deposit_percent','Deposit %','number'],['balance_due_days','Balance due days','number'],['notes','Terms']], 'Add the default terms once, then only record exceptions.') +
      simpleTable('overheads','Overheads','Confirm values imported from accounting or add monthly recurring costs manually.',[['name','Cost'],['monthly_amount','Monthly amount','number'],['category','Category'],['source','Source']], 'Add software, vehicles, premises, insurance, marketing or professional costs not already imported.') +
      simpleTable('debt_commitments','Debt and finance commitments','One row per loan, card, lease or vehicle finance agreement.',[['name','Lender / facility'],['balance','Balance','number'],['monthly_repayment','Monthly repayment','number'],['interest_rate','Interest %','number'],['remaining_months','Months left','number'],['security','Security / guarantee']], 'Leave empty if the business has no borrowing.') +
      simpleTable('financial_targets','12-month financial targets','Use an amount or percentage and add custom measures when needed.',[['name','Target'],['target_value','Value','number'],['unit','€ / % / days'],['deadline','Deadline','date']], 'Examples: revenue, gross margin, net profit, cash reserve or debtor days.');
  }

  function summary() {
    const m = state.model.inventory_metrics || {}; const e = list('unit_economics'); const queue = list('procurement_queue');
    return `${renderedConversationFacts('summary')}<div class="om-summary-grid"><div><span>Offerings</span><strong>${list('offerings').length}</strong></div><div><span>Total stock value</span><strong>${money(m.total_stock_value)}</strong></div><div><span>Reorder items</span><strong>${m.reorder_items || 0}</strong></div><div><span>Suggested procurement cash</span><strong>${money(m.suggested_procurement_cash_required)}</strong></div><div><span>Purchases awaiting review</span><strong>${queue.filter(x=>['suggested','draft','review'].includes(x.status)).length}</strong></div></div>
    <div class="om-section-head"><div><h3>Unit economics</h3><p>Calculated after saving from price, materials, labour and other direct costs.</p></div></div>${e.length ? `<div class="om-table-wrap"><table><thead><tr><th>Offering</th><th>Price/unit</th><th>Direct cost/unit</th><th>Contribution/unit</th><th>Gross margin</th><th>Monthly revenue</th></tr></thead><tbody>${e.map(r=>`<tr><td>${esc(r.name)}</td><td>${money(r.price_per_unit)}</td><td>${money(r.direct_cost_per_unit)}</td><td>${money(r.contribution_per_unit)}</td><td>${r.gross_margin_percent == null ? '—' : esc(r.gross_margin_percent)+'%'}</td><td>${money(r.expected_monthly_revenue)}</td></tr>`).join('')}</tbody></table></div>` : empty('Save the model to calculate unit economics.')}
    <div class="om-board-note"><strong>Boardroom use</strong><p>The Board receives these structured facts on every meeting: offer economics, production capacity, stock tied up in cash, shortages, procurement cash needs, payment terms, overheads, debt and targets. It can model discount or liquidation scenarios without relying on provider memory.</p></div>`;
  }

  function content() { return ({ offerings, workforce, jobs, stock, procurement, finance, summary }[state.activeTab] || offerings)(); }

  function render() {
    if (!state.loaded) setTimeout(load, 0);
    const mode = state.model.setup_mode || 'simple';
    return `<section class="om-shell" data-aion-operating-model="true"><header class="om-package"><div><small>BUSINESS OPERATING MODEL</small><h2>Products & Services · Workforce · Jobs · Stock · Procurement</h2><p>One shared source of truth for Sales, Operations, HR, Finance and the Boardroom.</p></div><div class="om-mode"><button data-om-mode="simple" data-active="${mode==='simple'}">Simple</button><button data-om-mode="advanced" data-active="${mode==='advanced'}">Advanced</button></div></header><section class="om-terminal"><div class="om-title">&gt; BUILD HOW THE BUSINESS EARNS, DELIVERS AND BUYS</div><nav class="om-tabs">${TABS.map(([key,label])=>`<button data-om-tab="${key}" data-active="${key===state.activeTab}">${esc(label)}</button>`).join('')}</nav><div class="om-content">${content()}</div><footer><div>${state.error ? `<span class="om-error">${esc(state.error)}</span>` : state.savedAt ? `<span class="om-saved">Saved to Business Container at ${esc(state.savedAt)}</span>` : '<span>Changes remain a draft until saved.</span>'}</div><button class="om-save" data-om-save="true" ${state.saving?'disabled':''}>${state.saving?'SAVING…':'SAVE MODEL & UPDATE BOARDROOM'}</button></footer></section></section>`;
  }

  const defaults = {
    offerings: { name:'', offering_type:'service', pricing_basis:'day_rate', price:'', unit:'day', expected_monthly_volume:'' },
    labour_resources: { person_id:'', person_name:'', engagement_type:'employee', cost_basis:'hourly', cost_rate:'', available_hours_month:'' },
    jobs: { name:'', offering_id:'', status:'estimate', estimated_revenue:'', actual_revenue:'', customer_reference:'' },
    job_labour_assignments: { job_id:'', labour_resource_id:'', cost_basis:'hourly', estimated_units:'', actual_units:'' },
    job_cost_items: { job_id:'', category:'materials', description:'', estimated_cost:'', actual_cost:'', evidence_ref:'' },
    production_lines: { name:'', output_unit:'units', capacity_per_day:'', operating_days_month:'', constraint:'' },
    bills_of_materials: { offering_id:'', material_name:'', quantity_per_unit:'', unit:'units', unit_cost:'', waste_percent:'' },
    inventory_items: { name:'', stock_class:'raw_material', unit:'units', quantity_on_hand:'', quantity_reserved:'', unit_cost:'', reorder_point:'', target_stock:'', lead_time_days:'' },
    procurement_queue: { name:'', quantity:'', unit:'units', supplier_name:'', required_date:'', estimated_cash_required:'', lead_time_days:'', status:'draft', requires_approval:true },
    payment_terms: { name:'Default', deposit_percent:'', balance_due_days:'', notes:'' }, overheads:{ name:'', monthly_amount:'', category:'', source:'manual' },
    debt_commitments:{ name:'', balance:'', monthly_repayment:'', interest_rate:'', remaining_months:'', security:'' }, financial_targets:{ name:'', target_value:'', unit:'EUR', deadline:'' },
  };

  document.addEventListener('input', (event) => {
    const el = event.target.closest?.('[data-om-list][data-om-field]'); if (!el) return;
    const row = list(el.dataset.omList)[Number(el.dataset.omIndex)]; if (!row) return;
    row[el.dataset.omField] = el.value;
    if (el.dataset.omList === 'labour_resources' && el.dataset.omField === 'cost_rate') {
      row.rate_source = 'manual_planning_override';
      row.rate_sync_reason = 'owner_edit';
    }
    persistDraft();
  }, true);
  document.addEventListener('change', (event) => {
    const importInput = event.target.closest?.('[data-om-import]');
    if (importInput) { importSpreadsheet(importInput.files?.[0], importInput.dataset.omImport); return; }
    const el = event.target.closest?.('[data-om-list][data-om-field]'); if (!el) return;
    const row = list(el.dataset.omList)[Number(el.dataset.omIndex)]; if (!row) return;
    row[el.dataset.omField] = el.value;
    if (el.dataset.omList === 'labour_resources' && (el.dataset.omField === 'cost_basis' || el.dataset.omField === 'person_id')) {
      syncLabourPlanningRate(row, el.dataset.omField === 'person_id' ? 'person_changed' : 'basis_changed');
      persistDraft();
      rerender();
      return;
    }
    persistDraft();
  }, true);
  document.addEventListener('click', (event) => {
    const tab = event.target.closest?.('[data-om-tab]'); if (tab) { state.activeTab = tab.dataset.omTab; rerender(); return; }
    const mode = event.target.closest?.('[data-om-mode]'); if (mode) { state.model.setup_mode = mode.dataset.omMode; persistDraft(); rerender(); return; }
    const add = event.target.closest?.('[data-om-add]'); if (add) {
      const key=add.dataset.omAdd; const row={...defaults[key]};
      if (key === 'offerings') row.id = localId('offering');
      if (key === 'labour_resources') row.id = localId('labour');
      if (key === 'jobs') row.id = localId('job');
      list(key).push(row); persistDraft(); rerender(); return;
    }
    const route = event.target.closest?.('[data-om-open-workspace]'); if (route) {
      const destination = route.dataset.omOpenWorkspace;
      if (typeof global.setAionSidebarActiveTabHardV1 === 'function') global.setAionSidebarActiveTabHardV1(destination);
      else document.querySelector(`[data-tab="${destination}"]`)?.click();
      return;
    }
    const removeButton = event.target.closest?.('[data-om-remove]'); if (removeButton) { list(removeButton.dataset.omRemove).splice(Number(removeButton.dataset.omIndex),1); persistDraft(); rerender(); return; }
    if (event.target.closest?.('[data-om-save]')) { save(); return; }
    if (event.target.closest?.('[data-om-quick-add]')) {
      const text = String(document.getElementById('om-quick-procurement')?.value || '').trim(); if (!text) return;
      const match = text.match(/^\s*(\d+(?:\.\d+)?)\s+(.+?)(?:\s+(?:needed|by)\s+(.+))?$/i);
      list('procurement_queue').push({ ...defaults.procurement_queue, quantity: match?.[1] || '', name: match?.[2] || text, notes:text, generated_by:'quick_add' });
      persistDraft(); rerender();
    }
  }, true);

  function style() {
    if (document.getElementById('aion-operating-model-style')) return;
    const node=document.createElement('style'); node.id='aion-operating-model-style'; node.textContent=`
      .om-shell{
        --om-ink:#102a43;
        --om-muted:#52667a;
        --om-line:#cbd9e6;
        --om-line-strong:#8fb3c7;
        --om-paper:#ffffff;
        --om-soft:#f5f9fc;
        --om-blue-soft:#edf8fc;
        --om-teal:#0f766e;
        --om-teal-dark:#115e59;
        --om-green:#15803d;
        max-width:1680px;
        margin:0 auto;
        color:var(--om-ink);
        font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
      }
      .om-package{
        border:2px solid #f59e0b;
        padding:18px 22px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:20px;
        background:var(--om-paper);
      }
      .om-package small{color:var(--om-teal);font-weight:900;letter-spacing:.26em}
      .om-package h2{font-family:Inter,system-ui,sans-serif;margin:7px 0 4px;color:var(--om-ink)}
      .om-package p{margin:0;color:var(--om-muted)}
      .om-mode{display:flex;gap:6px}
      .om-shell .om-mode button,
      .om-shell .om-tabs button{
        border:1px solid var(--om-line-strong) !important;
        background:var(--om-paper) !important;
        color:#334e68 !important;
        padding:10px 14px;
        text-transform:uppercase;
        font-weight:900;
        letter-spacing:.08em;
        cursor:pointer;
      }
      .om-shell .om-mode button:hover,
      .om-shell .om-tabs button:hover{background:var(--om-blue-soft) !important;border-color:#38a3c7 !important}
      .om-shell .om-mode button[data-active=true],
      .om-shell .om-tabs button[data-active=true]{
        color:#ffffff !important;
        border-color:var(--om-teal) !important;
        background:var(--om-teal) !important;
      }
      .om-terminal{
        margin-top:16px;
        background:var(--om-paper) !important;
        color:var(--om-ink) !important;
        border:1px solid var(--om-line);
        border-left:5px solid #0ea5e9;
        padding:20px;
        min-height:660px;
      }
      .om-title{color:var(--om-teal) !important;letter-spacing:.23em;font-weight:900;margin-bottom:18px}
      .om-tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:22px}
      .om-content{min-height:500px}
      .om-section-head{display:flex;justify-content:space-between;align-items:end;gap:15px;margin:24px 0 10px}
      .om-shell .om-section-head h3{color:var(--om-ink) !important;margin:0 0 5px}
      .om-shell .om-section-head p{margin:0;color:var(--om-muted) !important}
      .om-actions{display:flex;gap:8px;align-items:center}
      .om-import{
        border:1px solid #0284c7;
        background:var(--om-paper);
        color:#0369a1;
        padding:10px 13px;
        font-weight:900;
        cursor:pointer;
      }
      .om-import:hover{background:#f0f9ff}
      .om-import input{display:none}
      .om-shell .om-add,
      .om-shell .om-save{
        border:1px solid var(--om-green) !important;
        background:var(--om-green) !important;
        color:#ffffff !important;
        padding:11px 16px;
        font-weight:950;
        letter-spacing:.08em;
        text-transform:uppercase;
        cursor:pointer;
      }
      .om-shell .om-add:hover,
      .om-shell .om-save:hover{background:#166534 !important;border-color:#166534 !important}
      .om-shell .om-save:disabled{background:#d7e1e8 !important;border-color:#bdcbd5 !important;color:#617487 !important;cursor:wait}
      .om-table-wrap{overflow:auto;border:1px solid var(--om-line);background:var(--om-paper)}
      .om-table-wrap table{width:100%;border-collapse:collapse;min-width:900px}
      .om-shell .om-table-wrap th{
        color:#29465f !important;
        text-align:left;
        padding:11px 10px;
        background:#eaf1f6 !important;
        border-bottom:1px solid var(--om-line);
        font-size:12px;
      }
      .om-table-wrap td{border-top:1px solid #e1eaf0;padding:6px;background:var(--om-paper)}
      .om-shell .om-input{
        box-sizing:border-box;
        width:100%;
        min-width:90px;
        background:var(--om-paper) !important;
        color:var(--om-ink) !important;
        border:1px solid #b7c8d6 !important;
        padding:10px;
        font:inherit;
        opacity:1 !important;
      }
      .om-shell .om-input::placeholder{color:#8295a8 !important;opacity:1}
      .om-shell .om-input:focus{outline:2px solid #f59e0b !important;outline-offset:0;border-color:#f59e0b !important}
      .om-rate-editor{display:grid;gap:5px;min-width:145px}
      .om-rate-editor small{color:var(--om-muted);font-size:10px;white-space:nowrap}
      .om-shell .om-remove{
        background:#ffffff !important;
        color:#b42318 !important;
        border:1px solid #dc7069 !important;
        font-size:18px;
        cursor:pointer;
      }
      .om-shell .om-remove:hover{background:#fff1f0 !important}
      .om-empty,.om-note,.om-board-note{
        border:1px dashed var(--om-line-strong);
        background:var(--om-soft);
        padding:16px;
        color:var(--om-muted) !important;
      }
      .om-route-note{border:1px solid #f59e0b;background:#fffbeb;padding:16px;margin:10px 0}.om-route-note p{color:var(--om-muted)}
      .om-conversation-facts{display:grid;gap:8px;margin:0 0 18px;padding:14px;background:#f0f7ff;border-left:4px solid #2f80ed}
      .om-conversation-facts-title{color:#1267d6;font-size:11px;font-weight:950;letter-spacing:.14em;text-transform:uppercase}
      .om-conversation-facts article{display:grid;grid-template-columns:minmax(230px,.7fr) minmax(280px,1.3fr);gap:12px;padding:11px 12px;background:#fff;border:1px solid #cfe0f2}
      .om-conversation-facts article strong,.om-conversation-facts article span{display:block}.om-conversation-facts article span{margin-top:4px;color:#617487;font-size:11px}
      .om-conversation-facts article p{margin:0;color:#102a43;font-weight:750}.om-conversation-facts article small{grid-column:1/-1;color:#6b7f91}
      .om-secondary{border:1px solid #0284c7!important;background:#fff!important;color:#0369a1!important;padding:10px 13px;font-weight:900;cursor:pointer}
      .om-note{margin-top:10px}
      .om-quick{
        border:1px solid #55a68b;
        background:#f0fdf7;
        padding:14px;
        display:grid;
        grid-template-columns:1fr minmax(260px,2fr) auto;
        gap:12px;
        align-items:center;
      }
      .om-quick strong{color:var(--om-ink) !important}
      .om-quick span{display:block;color:var(--om-muted) !important;font-size:12px;margin-top:5px}
      .om-summary-grid{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:10px}
      .om-summary-grid div{border:1px solid var(--om-line);background:var(--om-soft) !important;padding:16px}
      .om-summary-grid span{display:block;color:#0369a1 !important;font-size:12px}
      .om-summary-grid strong{display:block;color:var(--om-teal-dark) !important;font-size:23px;margin-top:7px}
      .om-board-note{margin-top:20px;border-style:solid;background:var(--om-blue-soft)}
      .om-board-note strong{color:var(--om-teal-dark) !important}
      .om-board-note p{color:var(--om-muted) !important}
      .om-terminal footer{
        border-top:1px solid var(--om-line);
        margin-top:24px;
        padding-top:16px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:15px;
        color:var(--om-muted);
      }
      .om-error{color:#b42318 !important}
      .om-saved{color:var(--om-green) !important}
      @media(max-width:900px){
        .om-package,.om-terminal footer{align-items:stretch;flex-direction:column}
        .om-quick{grid-template-columns:1fr}
        .om-summary-grid{grid-template-columns:1fr 1fr}
      }
    `; document.head.appendChild(node);
  }

  style();
  global.AionOperatingModelWorkspace = { render, load, save, applyConversationFact, state };
})(window);
