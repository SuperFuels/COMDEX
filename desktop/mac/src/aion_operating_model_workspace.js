(function installAionOperatingModelWorkspace(global) {
  'use strict';

  const STORAGE_KEY = 'aion.businessOperatingModel.draft.v1';
  const TABS = [
    ['offerings', 'Offerings'], ['workforce', 'Workforce & capacity'],
    ['summary', 'Summary'],
  ];
  const state = {
    loaded: false, loading: false, saving: false, error: '', savedAt: '', activeTab: 'offerings', people: [], financeModel: {}, detailOfferingIndex: null,
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
  let draftSaveTimer = null;
  let draftSaveChain = Promise.resolve();

  function ensureRelationshipIds() {
    [['offerings','offering'],['labour_resources','labour'],['jobs','job']].forEach(([key,prefix]) => {
      list(key).forEach((row) => { if (!row.id) row.id = localId(prefix); });
    });
  }

  function persistDraft() {
    global.__aionOperatingModelDraft = state.model;
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    if (!global.AionBusinessContainerClient?.saveOperatingModel) return;
    clearTimeout(draftSaveTimer);
    draftSaveTimer = setTimeout(() => {
      draftSaveChain = draftSaveChain.catch(() => null).then(async () => {
        const expected = Number(state.model.revision || 0) || null;
        const result = await global.AionBusinessContainerClient.saveOperatingModel(state.model, expected);
        if (result?.payload) state.model = { ...state.model, ...result.payload };
        global.__aionOperatingModelDraft = state.model;
        return result;
      }).catch((error) => {
        state.error = `Draft Vault sync is pending: ${String(error?.message || error)}`;
      });
    }, 650);
  }
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
      state.error = `Conversation fact remains in memory; Business Vault sync is pending: ${String(error?.message || error)}`;
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
    let retryAfterStartup = false;
    try {
      if (!global.AionBusinessContainerClient?.getOperatingModel) throw new Error('Business Container is still starting');
      const result = await global.AionBusinessContainerClient.getOperatingModel();
      if (!result?.payload) throw new Error('Saved operating model is not available yet');
      state.model = { ...state.model, ...result.payload };
      try {
        const businessId = global.AionBusinessContainerClient?.resolveBusinessId?.();
        const financeResponse = await fetch(`http://127.0.0.1:8080/api/aion/business/data/finance-model/${encodeURIComponent(businessId)}`);
        const financeResult = financeResponse.ok ? await financeResponse.json() : null;
        state.financeModel = financeResult?.payload || {};
      } catch { state.financeModel = {}; }
      try {
        const businessId = global.AionBusinessContainerClient?.resolveBusinessId?.();
        const response = await fetch(`http://127.0.0.1:8080/api/aion/business/organisation/${encodeURIComponent(businessId)}`);
        const organisation = response.ok ? await response.json() : null;
        state.people = (organisation?.model?.people || []).filter((person) => person.status === 'active');
      } catch { state.people = []; }
      ensureRelationshipIds();
    } catch (error) {
      if (!String(error).includes('404')) state.error = String(error?.message || error);
      retryAfterStartup = true;
      try {
        const draft = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
        if (draft) {
          state.model = { ...state.model, ...draft };
          global.__aionOperatingModelDraft = state.model;
          localStorage.removeItem(STORAGE_KEY);
          persistDraft();
        } else if (global.__aionOperatingModelDraft) {
          state.model = { ...state.model, ...global.__aionOperatingModelDraft };
        }
      } catch {}
    } finally {
      state.loading = false; state.loaded = true; rerender();
      if (retryAfterStartup) {
        setTimeout(() => {
          state.loaded = false;
          state.error = '';
          load();
        }, 1800);
      }
    }
  }

  async function save() {
    state.saving = true; state.error = ''; rerender();
    try {
      clearTimeout(draftSaveTimer);
      await draftSaveChain.catch(() => null);
      // Quoted work is costed on the individual quote/job. Persist the same
      // classification shown in the UI so Boardroom does not ask the owner to
      // fill catalogue cost cells that deliberately do not apply.
      list('offerings').forEach((row) => {
        if (!row.cost_treatment && row.pricing_basis === 'quote') row.cost_treatment = 'quoted_per_job';
      });
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
      global.dispatchEvent(new CustomEvent('aion:operating-model-saved', {
        detail: {
          ...(result || {}),
          operating_model: state.model,
          saved_at: new Date().toISOString(),
          source: 'products_services',
        },
      }));
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

  function offeringCostTreatment(row) {
    if (row?.cost_treatment) return row.cost_treatment;
    if (row?.pricing_basis === 'quote') return 'quoted_per_job';
    return 'not_set';
  }

  function offeringCostCells(row, index) {
    const treatment = offeringCostTreatment(row);
    if (treatment === 'standard_estimate') {
      return `<td>${input('offerings', index, 'material_cost_per_unit', row.material_cost_per_unit, 'number', 'Optional')}</td><td>${input('offerings', index, 'labour_cost_per_unit', row.labour_cost_per_unit, 'number', 'Optional')}</td><td>${input('offerings', index, 'other_direct_cost_per_unit', row.other_direct_cost_per_unit, 'number', 'Optional')}</td>`;
    }
    const messages = {
      labour_only: 'Materials and external costs do not normally apply. Labour comes from Workforce & capacity.',
      quoted_per_job: 'Costs vary by customer or project. Estimate them on the shared record in Work & Schedule.',
      no_direct_costs: 'No direct delivery costs apply to this offering.',
      not_set: 'Choose how this offering is normally costed. You do not need to fill every cost cell.',
    };
    return `<td colspan="3"><div class="om-cost-guidance" data-tone="${treatment === 'not_set' ? 'attention' : 'ready'}">${esc(messages[treatment] || messages.not_set)}</div></td>`;
  }

  function offeringImages(row) {
    const images = Array.isArray(row?.image_urls) ? row.image_urls.filter(Boolean) : [];
    const primary = row?.primary_image_url || row?.image_url || '';
    return primary && !images.includes(primary) ? [primary, ...images] : images;
  }

  function catalogueImageSource(value) {
    const source = String(value || '').trim();
    if (!source || /^(https?:|data:|blob:|file:)/i.test(source)) return source;
    const workspaceId = String(global.AionBusinessContainerClient?.resolveBusinessId?.() || 'workspace');
    const fileName = source.split(/[\\/]/).filter(Boolean).pop() || '';
    if ((source.startsWith('/runtime/uploads/marketing_assets/') || source.includes('/uploads/marketing_assets/')) && fileName) {
      return `http://127.0.0.1:8080/api/local-node/marketing/assets/${encodeURIComponent(fileName)}?workspace_id=${encodeURIComponent(workspaceId)}`;
    }
    if (source.startsWith('/local-runtime/')) return `http://127.0.0.1:8080${source}`;
    return source;
  }

  function offeringDetailButton(row, index) {
    const images = offeringImages(row);
    const ready = Boolean((row.product_url || row.url) && images.length);
    return `<button class="om-detail-button" type="button" data-om-offering-details="${index}" title="Edit product or service details">
      <span class="om-detail-thumb">${images[0] ? `<img data-om-catalogue-img src="${esc(catalogueImageSource(images[0]))}" alt=""><span hidden>${esc(row.offering_type === 'service' ? 'S' : 'P')}</span>` : esc(row.offering_type === 'service' ? 'S' : 'P')}</span>
      <span><strong>Product / service details</strong><small>${ready ? `${images.length} image${images.length === 1 ? '' : 's'} · Link added` : images.length ? `${images.length} image${images.length === 1 ? '' : 's'} · Add link` : 'Add images, details and link'}</small></span>
    </button>`;
  }

  function offeringStoreConnection() {
    return `<section class="om-store-connection">
      <div><strong>Connected store catalogue</strong><span>Map Shopify, WooCommerce or another provider without duplicating the products and services above.</span></div>
      <button class="om-secondary" type="button" data-om-open-connections="true">Connect or map a store</button>
    </section>`;
  }

  function offeringDetailsModal() {
    if (state.detailOfferingIndex == null) return '';
    const index = Number(state.detailOfferingIndex);
    const row = Number.isInteger(index) ? list('offerings')[index] : null;
    if (!row) return '';
    const images = offeringImages(row);
    const source = row.catalogue_source || row.catalog_source || row.import_source || 'manual';
    return `<div class="om-detail-backdrop" data-om-close-details="true" role="presentation">
      <section class="om-detail-modal" role="dialog" aria-modal="true" aria-labelledby="om-detail-title" data-om-detail-panel="true">
        <header><div><small>PRODUCT / SERVICE DETAILS</small><h3 id="om-detail-title">${esc(row.name || 'Untitled offering')}</h3><p>Add the same useful catalogue information you would keep in an online store. These facts and images can then be reused by Marketing.</p></div><button type="button" data-om-close-details="true" aria-label="Close product details">×</button></header>
        <div class="om-detail-body">
          <div class="om-detail-fields">
            <label>Product or service title${input('offerings', index, 'name', row.name || '', 'text', 'Product or service title')}</label>
            <label class="om-detail-wide">Description<textarea class="om-input" rows="5" data-om-list="offerings" data-om-index="${index}" data-om-field="description" placeholder="What it is, who it helps and the important product or service details">${esc(row.description || '')}</textarea></label>
            <label class="om-detail-wide">Product or service page${input('offerings', index, 'product_url', row.product_url || row.url || '', 'url', 'https://example.com/products/item')}</label>
            <label>Catalogue source${select('offerings', index, 'catalogue_source', source, [['manual','Created in Tessaris'],['catalogue_spreadsheet','Spreadsheet import'],['shopify','Shopify'],['woocommerce','WooCommerce'],['squarespace','Squarespace'],['wix','Wix'],['custom','Other connected store']])}</label>
            <label>SKU / external ID${input('offerings', index, 'external_id', row.external_id || row.sku || '', 'text', 'SKU or provider product ID')}</label>
          </div>
          <div class="om-detail-images">
            <div><strong>Product or service images</strong><span>Upload several images. Choose which one Marketing should use as the primary image.</span></div>
            <div class="om-image-grid">${images.length ? images.map((url, imageIndex) => `<article data-primary="${url === (row.primary_image_url || images[0])}"><div class="om-image-frame"><img data-om-catalogue-img src="${esc(catalogueImageSource(url))}" alt="${esc(row.name || 'Catalogue image')}"><span hidden>Image unavailable<br><small>Upload a replacement or remove this reference.</small></span></div><div><button type="button" data-om-set-primary-image="${imageIndex}">${url === (row.primary_image_url || images[0]) ? 'Primary image' : 'Make primary'}</button><button type="button" data-om-remove-offering-image="${imageIndex}" aria-label="Remove image">Remove</button></div></article>`).join('') : '<div class="om-image-empty">No images added yet.</div>'}</div>
            <label class="om-image-upload">+ Upload images<input type="file" accept="image/*" multiple data-om-offering-images="${index}"></label>
            <label class="om-image-url">Add an image URL<div><input class="om-input" type="url" data-om-image-url-input="${index}" placeholder="https://…/product-image.jpg"><button class="om-secondary" type="button" data-om-add-image-url="${index}">Add image</button></div></label>
          </div>
        </div>
        <footer><span>Details remain part of this Products &amp; Services record.</span><button class="om-add" type="button" data-om-close-details="true">Done</button></footer>
      </section>
    </div>`;
  }

  function offerings() {
    const rows = list('offerings');
    const advanced = state.model.setup_mode === 'advanced';
    return `${renderedConversationFacts('offerings')}
      <div class="om-section-head"><div><h3>Products, services and rate card</h3><p>Add one day rate or build a full product catalogue. Use + for each additional line.</p></div><div class="om-actions"><label class="om-import">Import CSV/XLSX<input type="file" accept=".csv,.xlsx" data-om-import="offerings"></label><button class="om-add" data-om-add="offerings">+ Add offering</button></div></div>
      ${advanced ? `<div class="om-guidance-card"><strong>Only enter costs that normally apply.</strong><span>For labour-only services choose “Labour only”. For work priced separately each time choose “Varies by quote/job”. For repeatable products or services choose “Standard estimate” and complete only the relevant cost boxes.</span></div>` : ''}
      ${rows.length ? `<div class="om-table-wrap"><table><thead><tr><th>Name</th><th>Type</th><th>Product / service details</th><th>Charge basis</th><th>Rate</th><th>Unit</th><th>Expected monthly volume</th>${advanced ? '<th>How is this costed?</th><th>Est. materials</th><th>Est. direct labour</th><th>Est. external costs</th>' : ''}<th></th></tr></thead><tbody>
      ${rows.map((row, i) => `<tr><td>${input('offerings', i, 'name', row.name, 'text', 'Plumber day rate')}</td><td>${select('offerings', i, 'offering_type', row.offering_type || 'service', [['service','Service'],['product','Product'],['subscription','Subscription'],['rental','Rental'],['experience','Experience'],['other','Other']])}</td><td>${offeringDetailButton(row, i)}</td><td>${select('offerings', i, 'pricing_basis', row.pricing_basis || 'day_rate', [['hourly','Hourly'],['day_rate','Day rate'],['fixed','One-off / fixed'],['per_unit','Per unit'],['subscription','Subscription'],['tiered','Tiered volume'],['quote','Quoted'],['cost_plus','Cost plus']])}</td><td>${input('offerings', i, 'price', row.price, 'number', '0')}</td><td>${input('offerings', i, 'unit', row.unit || 'day', 'text', 'day')}</td><td>${input('offerings', i, 'expected_monthly_volume', row.expected_monthly_volume, 'number', '0')}</td>${advanced ? `<td>${select('offerings', i, 'cost_treatment', offeringCostTreatment(row), [['not_set','Choose…'],['labour_only','Labour only'],['standard_estimate','Standard estimate'],['quoted_per_job','Varies by quote/job'],['no_direct_costs','No direct costs']])}</td>${offeringCostCells(row, i)}` : ''}<td>${remove('offerings', i)}</td></tr>`).join('')}
      </tbody></table></div>` : empty('Start with a service, product, subscription or day rate.')}
      ${offeringStoreConnection()}
      <div class="om-note"><strong>What counts as a direct cost?</strong> Materials are items consumed to deliver the sale. External costs include subcontractors, equipment hire, delivery or disposal tied to that sale. General costs such as insurance, vehicles and software belong under Overheads.</div>`;
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

  function financeMetricValue(key) {
    const record = state.financeModel?.authoritative_metrics?.[key] || state.financeModel?.metrics?.[key];
    const value = record && typeof record === 'object' ? record.value : record;
    return Number.isFinite(Number(value)) ? Number(value) : null;
  }

  function marginDecisionCard(options = {}) {
    const embeddedInFinance = options.embeddedInFinance === true;
    const actualMargin = financeMetricValue('gross_margin_percent');
    const directCosts = financeMetricValue('direct_costs');
    const targets = list('financial_targets');
    const target = targets.find((row) => /target gross margin/i.test(String(row.name || '')));
    const floor = targets.find((row) => /minimum acceptable (?:gross )?margin|minimum gross margin/i.test(String(row.name || '')));
    return `<section class="om-decision-card">
      <div>
        <span>GUIDED FINANCE DECISION</span>
        <h3>Agree the margin you want the business to protect</h3>
        <p>${actualMargin == null ? 'No reliable historical gross-margin percentage is available yet.' : `The accepted accounts show a historical gross margin of <strong>${esc(actualMargin.toFixed(1))}%</strong>${directCosts == null ? '' : ` and total direct costs of <strong>${esc(money(directCosts))}</strong>`}. These are evidence, not targets.`}</p>
        <p>You do not need to invent a percentage. Ask the Finance Pilot to recommend a target and a minimum safety floor, then accept or adjust them.</p>
      </div>
      <div class="om-decision-status">
        <div><small>Target margin</small><strong>${target?.target_value ? `${esc(target.target_value)}%` : 'Not agreed'}</strong></div>
        <div><small>Minimum margin</small><strong>${floor?.target_value ? `${esc(floor.target_value)}%` : 'Not agreed'}</strong></div>
      </div>
      <div class="om-actions">
        ${embeddedInFinance
          ? '<button class="om-add" type="button" data-om-finance-prompt="Recommend a sensible target gross margin and minimum safety floor using the accepted accounts. Explain the reasoning and do not save a target until I agree.">Ask Finance Pilot to recommend targets</button>'
          : '<button class="om-add" type="button" data-om-open-workspace="finance">Discuss with Finance Pilot</button>'}
        <button class="om-secondary" type="button" data-om-add-margin-targets="true">I already know my targets</button>
      </div>
    </section>`;
  }

  function quotePricingRules() {
    const rows = list('pricing_rules');
    const categories = [['all','All quote costs'],['materials','Materials'],['labour','Labour'],['supplier_subcontractor','Subcontractors / external costs'],['other','Other costs']];
    return `<div class="om-section-head"><div><h3>Default quote pricing rules</h3><p>Use these rules when a job has variable costs. Tessaris applies them to the actual materials, labour and external costs entered on each quote. The suggested price stays editable and the minimum margin remains visible.</p></div><button class="om-add" data-om-add="pricing_rules">+ Add pricing rule</button></div>
      ${rows.length ? `<div class="om-table-wrap"><table><thead><tr><th>Applies to</th><th>Method</th><th>Percentage</th><th>Notes</th><th></th></tr></thead><tbody>${rows.map((row,i)=>{ const method = row.rule_type || (row.target_margin_percent != null ? 'target_margin' : 'cost_plus'); const percentField = method === 'cost_plus' ? 'markup_percent' : 'target_margin_percent'; return `<tr><td>${select('pricing_rules',i,'category',row.category || row.applies_to || 'all',categories)}</td><td>${select('pricing_rules',i,'rule_type',method,[['target_margin','Protect gross margin'],['cost_plus','Add markup to cost']])}</td><td>${input('pricing_rules',i,percentField,row[percentField],'number','0')}</td><td>${input('pricing_rules',i,'notes',row.notes,'text','Approved by founder / Board')}</td><td>${remove('pricing_rules',i)}</td></tr>`; }).join('')}</tbody></table></div>` : empty('No category-specific rules are saved. Quotes will use the agreed overall target gross margin until you add one.')}`;
  }

  function finance(options = {}) {
    return renderedConversationFacts('finance', 'targets') + marginDecisionCard(options) + quotePricingRules() + simpleTable('payment_terms','Default and customer payment terms','Set the normal deposit and balance timing once. Add another row only when a customer has an agreed exception.',[['name','Customer / default'],['deposit_percent','Deposit %','number'],['balance_due_days','Balance due days','number'],['notes','Plain-language terms']], 'Add the default terms once, then only record genuine customer exceptions.') +
      simpleTable('overheads','Monthly overheads','Recurring business costs that are not tied to one sale or job. Confirm accounting imports and add only costs that are missing.',[['name','Cost'],['monthly_amount','Monthly amount','number'],['category','Type'],['source','Source / evidence']], 'Examples include software, vehicles, premises, insurance and professional fees. Do not repeat direct materials or subcontractor costs.') +
      simpleTable('debt_commitments','Borrowing and finance commitments','Add one row for each loan, card, lease or vehicle finance agreement so Finance can see the monthly cash commitment.',[['name','Lender / facility'],['balance','Balance remaining','number'],['monthly_repayment','Monthly payment','number'],['interest_rate','Interest %','number'],['remaining_months','Months left','number'],['security','Security / guarantee']], 'Leave this empty when the business has no borrowing or finance agreements.') +
      simpleTable('financial_targets','Agreed 12-month financial targets','Record only targets you already know or have agreed with the Finance Pilot or Board. Historical results are evidence, not automatic targets.',[['name','Target'],['target_value','Value','number'],['unit','€ / % / days'],['deadline','Review date','date']], 'No targets have been agreed yet. Ask the Finance Pilot for a recommendation rather than guessing.');
  }

  function summary() {
    const e = list('unit_economics');
    return `${renderedConversationFacts('summary')}<div class="om-summary-grid"><div><span>Offerings</span><strong>${list('offerings').length}</strong></div><div><span>People assigned</span><strong>${list('labour_resources').length}</strong></div><div><span>Delivery units</span><strong>${list('production_lines').length}</strong></div><div><span>Materials mapped</span><strong>${list('bills_of_materials').length}</strong></div><div><span>Unit economics</span><strong>${e.length}</strong></div></div>
    <div class="om-section-head"><div><h3>Unit economics</h3><p>Calculated after saving from price, materials, labour and other direct costs.</p></div></div>${e.length ? `<div class="om-table-wrap"><table><thead><tr><th>Offering</th><th>Price/unit</th><th>Direct cost/unit</th><th>Contribution/unit</th><th>Gross margin</th><th>Monthly revenue</th></tr></thead><tbody>${e.map(r=>`<tr><td>${esc(r.name)}</td><td>${money(r.price_per_unit)}</td><td>${money(r.direct_cost_per_unit)}</td><td>${money(r.contribution_per_unit)}</td><td>${r.gross_margin_percent == null ? '—' : esc(r.gross_margin_percent)+'%'}</td><td>${money(r.expected_monthly_revenue)}</td></tr>`).join('')}</tbody></table></div>` : empty('Save the model to calculate unit economics.')}
    <div class="om-board-note"><strong>Boardroom use</strong><p>The Board receives the structured catalogue, direct-cost assumptions, workforce capacity and unit economics from this workspace. Stock and purchasing come from Stock &amp; Procurement; payment terms, overheads, debt and targets come from Finance.</p></div>`;
  }

  function content() { return ({ offerings, workforce, summary }[state.activeTab] || offerings)(); }

  function render() {
    if (!state.loaded) setTimeout(load, 0);
    if (!TABS.some(([key]) => key === state.activeTab)) state.activeTab = 'offerings';
    const mode = state.model.setup_mode || 'simple';
    return `<section class="om-shell" data-aion-operating-model="true"><header class="om-package"><div><small>PILOT · PRODUCTS &amp; SERVICES COMMAND CENTRE</small><h2>Products &amp; services coordination</h2><p>Catalogue, pricing, delivery capacity and commercial decisions in one governed operating model. Customer jobs and quotes live in Work &amp; Schedule. Stock and purchasing live in Stock &amp; Procurement. Payment terms, overheads, borrowing and targets live in Finance.</p></div><div class="om-mode" aria-label="Operating model detail"><button data-om-mode="simple" data-active="${mode==='simple'}">Simple</button><button data-om-mode="advanced" data-active="${mode==='advanced'}">Advanced</button></div></header><section class="om-terminal"><div class="om-context"><div><span>BUSINESS OPERATING MODEL</span><strong>How the business earns and delivers</strong></div><b>SHARED SOURCE OF TRUTH</b></div><nav class="om-tabs" aria-label="Products and services workspace views">${TABS.map(([key,label])=>`<button data-om-tab="${key}" data-active="${key===state.activeTab}">${esc(label)}</button>`).join('')}</nav><div class="om-content">${content()}</div><footer><div>${state.error ? `<span class="om-error">${esc(state.error)}</span>` : state.savedAt ? `<span class="om-saved">Saved to Business Container at ${esc(state.savedAt)}</span>` : '<span>Changes remain a draft until saved.</span>'}</div><button class="om-save" data-om-save="true" ${state.saving?'disabled':''}>${state.saving?'Saving…':'Save model & update Boardroom'}</button></footer></section>${offeringDetailsModal()}</section>`;
  }

  const defaults = {
    offerings: { name:'', description:'', offering_type:'service', pricing_basis:'day_rate', price:'', unit:'day', expected_monthly_volume:'', cost_treatment:'not_set', product_url:'', primary_image_url:'', image_urls:[], catalogue_source:'manual', external_id:'' },
    labour_resources: { person_id:'', person_name:'', engagement_type:'employee', cost_basis:'hourly', cost_rate:'', available_hours_month:'' },
    jobs: { name:'', offering_id:'', status:'estimate', estimated_revenue:'', actual_revenue:'', customer_reference:'' },
    job_labour_assignments: { job_id:'', labour_resource_id:'', cost_basis:'hourly', estimated_units:'', actual_units:'' },
    job_cost_items: { job_id:'', category:'materials', description:'', estimated_cost:'', actual_cost:'', evidence_ref:'' },
    production_lines: { name:'', output_unit:'units', capacity_per_day:'', operating_days_month:'', constraint:'' },
    bills_of_materials: { offering_id:'', material_name:'', quantity_per_unit:'', unit:'units', unit_cost:'', waste_percent:'' },
    inventory_items: { name:'', stock_class:'raw_material', unit:'units', quantity_on_hand:'', quantity_reserved:'', unit_cost:'', reorder_point:'', target_stock:'', lead_time_days:'' },
    procurement_queue: { name:'', quantity:'', unit:'units', supplier_name:'', required_date:'', estimated_cash_required:'', lead_time_days:'', status:'draft', requires_approval:true },
    payment_terms: { name:'Default', deposit_percent:'', balance_due_days:'', notes:'' }, overheads:{ name:'', monthly_amount:'', category:'', source:'manual' },
    pricing_rules: { name:'Quote pricing rule', category:'all', rule_type:'target_margin', target_margin_percent:'', markup_percent:'', notes:'', approval_status:'draft' },
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
  document.addEventListener('error', (event) => {
    const image = event.target?.matches?.('[data-om-catalogue-img]') ? event.target : null;
    if (!image) return;
    image.hidden = true;
    if (image.nextElementSibling) image.nextElementSibling.hidden = false;
  }, true);
  document.addEventListener('change', (event) => {
    const offeringImage = event.target.closest?.('[data-om-offering-image],[data-om-offering-images]');
    if (offeringImage) {
      const files = [...(offeringImage.files || [])];
      const rowIndex = Number(offeringImage.dataset.omOfferingImages ?? offeringImage.dataset.omOfferingImage);
      const row = list('offerings')[rowIndex];
      if (!files.length || !row) return;
      const form = new FormData(); files.forEach((file) => form.append('files', file, file.name));
      const workspaceId = encodeURIComponent(String(global.AionBusinessContainerClient?.resolveBusinessId?.() || 'workspace'));
      state.saving = true; state.error = ''; rerender();
      fetch(`http://127.0.0.1:8080/api/local-node/marketing/assets/upload?workspace_id=${workspaceId}`, { method:'POST', body:form })
        .then(async (response) => { const body = await response.json(); if (!response.ok || !body?.ok) throw new Error(body?.detail || 'Image upload failed'); return body; })
        .then((body) => {
          const items = Array.isArray(body?.items) ? body.items : [];
          const added = items.map((item) => item.url || item.file_path || '').filter(Boolean);
          const existing = offeringImages(row);
          row.image_urls = [...new Set([...existing, ...added])];
          if (!row.primary_image_url && row.image_urls.length) row.primary_image_url = row.image_urls[0];
          row.primary_image_file_path = items[0]?.file_path || row.primary_image_file_path || '';
          row.primary_image_source = 'business_upload';
          persistDraft();
        })
        .catch((error) => { state.error = String(error?.message || error); })
        .finally(() => { state.saving = false; rerender(); });
      return;
    }
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
    if (el.dataset.omList === 'offerings' && el.dataset.omField === 'cost_treatment') {
      persistDraft();
      rerender();
      return;
    }
    persistDraft();
  }, true);
  document.addEventListener('click', (event) => {
    const detailButton = event.target.closest?.('[data-om-offering-details]');
    if (detailButton) { state.detailOfferingIndex = Number(detailButton.dataset.omOfferingDetails); rerender(); return; }
    const closeDetails = event.target.closest?.('button[data-om-close-details]');
    if (closeDetails || (event.target.matches?.('.om-detail-backdrop[data-om-close-details]'))) { state.detailOfferingIndex = null; persistDraft(); rerender(); return; }
    const addImageUrl = event.target.closest?.('[data-om-add-image-url]');
    if (addImageUrl) {
      const index = Number(addImageUrl.dataset.omAddImageUrl);
      const row = list('offerings')[index];
      const field = document.querySelector(`[data-om-image-url-input="${index}"]`);
      const url = String(field?.value || '').trim();
      if (!row || !url) return;
      row.image_urls = [...new Set([...offeringImages(row), url])];
      if (!row.primary_image_url) row.primary_image_url = url;
      persistDraft(); rerender(); return;
    }
    const setPrimary = event.target.closest?.('[data-om-set-primary-image]');
    if (setPrimary) {
      const row = list('offerings')[Number(state.detailOfferingIndex)];
      const url = offeringImages(row)[Number(setPrimary.dataset.omSetPrimaryImage)];
      if (row && url) { row.primary_image_url = url; persistDraft(); rerender(); }
      return;
    }
    const removeImage = event.target.closest?.('[data-om-remove-offering-image]');
    if (removeImage) {
      const row = list('offerings')[Number(state.detailOfferingIndex)];
      if (!row) return;
      const images = offeringImages(row);
      const removed = images.splice(Number(removeImage.dataset.omRemoveOfferingImage), 1)[0];
      row.image_urls = images;
      if (removed && row.primary_image_url === removed) row.primary_image_url = images[0] || '';
      persistDraft(); rerender(); return;
    }
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
    if (event.target.closest?.('[data-om-open-connections]')) {
      if (typeof global.setAionSidebarActiveTabHardV1 === 'function') global.setAionSidebarActiveTabHardV1('vault');
      else document.querySelector('[data-tab="vault"]')?.click();
      return;
    }
    const financePrompt = event.target.closest?.('[data-om-finance-prompt]'); if (financePrompt) {
      const input = document.querySelector('[data-aion-finance-pilot-input]');
      if (input) {
        input.value = financePrompt.dataset.omFinancePrompt || '';
        input.focus();
        input.scrollIntoView?.({ block:'nearest' });
      }
      return;
    }
    if (event.target.closest?.('[data-om-add-margin-targets]')) {
      const targets = list('financial_targets');
      if (!targets.some((row) => /target gross margin/i.test(String(row.name || '')))) {
        targets.push({ name:'Target gross margin', target_value:'', unit:'%', deadline:'', decision_status:'owner_to_confirm' });
      }
      if (!targets.some((row) => /minimum acceptable (?:gross )?margin|minimum gross margin/i.test(String(row.name || '')))) {
        targets.push({ name:'Minimum acceptable gross margin', target_value:'', unit:'%', deadline:'', decision_status:'owner_to_confirm' });
      }
      persistDraft(); rerender(); return;
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
        --om-ink:#14213d;
        --om-muted:#66758a;
        --om-line:#d9e2ec;
        --om-line-strong:#b9c7d8;
        --om-paper:#ffffff;
        --om-soft:#f7f9fc;
        --om-blue-soft:#eef5ff;
        --om-teal:#2563eb;
        --om-teal-dark:#1d4ed8;
        --om-green:#2563eb;
        min-height:100%;
        width:100%;
        color:var(--om-ink);
        background:#f7f9fc;
        font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        box-sizing:border-box;
      }
      .om-package{
        border-top:4px solid var(--om-teal);
        border-bottom:1px solid var(--om-line);
        padding:25px 32px 23px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:20px;
        background:#f7f9fc;
        box-sizing:border-box;
      }
      .om-package>div:first-child{flex:1 1 auto;min-width:0}
      .om-package small{color:var(--om-teal);font-size:10px;font-weight:900;letter-spacing:.22em}
      .om-package h2{margin:8px 0 5px;color:#171717;font-size:28px;line-height:1.15}
      .om-package p{margin:0;color:var(--om-muted);font-size:13px;line-height:1.45;max-width:1180px}
      .om-mode{display:flex;flex:0 0 190px;min-width:190px;gap:0;border:1px solid var(--om-line);border-radius:9px;overflow:hidden;background:#fff;box-sizing:border-box}
      .om-shell .om-mode button,
      .om-shell .om-tabs button{
        border:0 !important;
        background:transparent !important;
        color:#526071 !important;
        padding:10px 15px;
        font-weight:750;
        cursor:pointer;
      }
      .om-shell .om-mode button{flex:1 1 50%;min-width:0;font-size:12px;border-radius:7px!important;margin:3px;padding-left:10px;padding-right:10px;white-space:nowrap}
      .om-shell .om-mode button:hover,
      .om-shell .om-tabs button:hover{background:var(--om-blue-soft) !important;color:var(--om-teal-dark)!important}
      .om-shell .om-mode button[data-active=true],
      .om-shell .om-tabs button[data-active=true]{
        color:#ffffff !important;
        background:var(--om-teal) !important;
      }
      .om-terminal{
        background:var(--om-paper) !important;
        color:var(--om-ink) !important;
        padding:0 32px 32px;
        min-height:660px;
      }
      .om-context{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:20px 0 14px}
      .om-context span{display:block;color:var(--om-teal);font-size:10px;letter-spacing:.17em;font-weight:900;margin-bottom:5px}
      .om-context strong{display:block;color:#172033;font-size:16px}
      .om-context>b{border:1px solid #c8d8fb;background:#eef5ff;color:var(--om-teal-dark);padding:7px 10px;border-radius:999px;font-size:9px;letter-spacing:.11em;white-space:nowrap}
      .om-tabs{display:flex;flex-wrap:wrap;gap:4px;margin:0 -4px 24px;border-bottom:1px solid var(--om-line);padding:0 4px}
      .om-shell .om-tabs button{border-radius:8px 8px 0 0!important;font-size:12px;padding:12px 15px}
      .om-shell .om-tabs button[data-active=true]{background:transparent!important;color:var(--om-teal-dark)!important;box-shadow:inset 0 -3px 0 var(--om-teal)}
      .om-content{min-height:500px;max-width:1800px}
      .om-section-head{display:flex;justify-content:space-between;align-items:end;gap:15px;margin:26px 0 12px}
      .om-shell .om-section-head h3{color:#172033 !important;margin:0 0 5px;font-size:19px}
      .om-shell .om-section-head p{margin:0;color:var(--om-muted) !important;font-size:13px;line-height:1.45}
      .om-actions{display:flex;gap:8px;align-items:center}
      .om-import{
        border:1px solid var(--om-line-strong);
        background:var(--om-paper);
        color:#344054;
        padding:10px 13px;
        border-radius:11px;
        font-size:12px;
        font-weight:750;
        cursor:pointer;
      }
      .om-import:hover{background:var(--om-soft)}
      .om-import input{display:none}
      .om-shell .om-add,
      .om-shell .om-save{
        border:1px solid var(--om-green) !important;
        background:var(--om-green) !important;
        color:#ffffff !important;
        padding:10px 15px;
        border-radius:11px;
        font-weight:750;
        cursor:pointer;
      }
      .om-shell .om-add:hover,.om-shell .om-save:hover{background:var(--om-teal-dark) !important;border-color:var(--om-teal-dark) !important}
      .om-shell .om-save:disabled{background:#d7e1e8 !important;border-color:#bdcbd5 !important;color:#617487 !important;cursor:wait}
      .om-table-wrap{overflow:auto;border:1px solid var(--om-line);border-radius:14px;background:var(--om-paper)}
      .om-table-wrap table{width:100%;border-collapse:collapse;min-width:900px}
      .om-shell .om-table-wrap th{
        color:#667085 !important;
        text-align:left;
        padding:11px 12px;
        background:#f4f6f8 !important;
        border-bottom:1px solid var(--om-line);
        font-size:10px;
        font-weight:850;
        letter-spacing:.08em;
        text-transform:uppercase;
      }
      .om-table-wrap td{border-top:1px solid #e8ecf2;padding:7px;background:var(--om-paper)}
      .om-table-wrap tbody tr:hover td{background:#fbfdfd}
      .om-shell .om-input{
        box-sizing:border-box;
        width:100%;
        min-width:90px;
        background:var(--om-paper) !important;
        color:var(--om-ink) !important;
        border:1px solid #cbd3df !important;
        border-radius:6px;
        padding:10px 11px;
        font:inherit;
        font-size:13px;
        opacity:1 !important;
      }
      .om-shell .om-input::placeholder{color:#8295a8 !important;opacity:1}
      .om-shell .om-input:focus{outline:2px solid rgba(37,99,235,.16)!important;outline-offset:0;border-color:var(--om-teal)!important}
      .om-rate-editor{display:grid;gap:5px;min-width:145px}
      .om-rate-editor small{color:var(--om-muted);font-size:10px;white-space:nowrap}
      .om-shell .om-remove{
        background:#ffffff !important;
        color:#8a3f3f !important;
        border:1px solid #e6caca !important;
        border-radius:6px;
        font-size:16px;
        cursor:pointer;
      }
      .om-shell .om-remove:hover{background:#fff1f0 !important}
      .om-empty,.om-note,.om-board-note{
        border:1px solid var(--om-line);
        border-radius:8px;
        background:var(--om-soft);
        padding:16px;
        color:var(--om-muted) !important;
        font-size:13px;
      }
      .om-guidance-card{display:grid;gap:5px;margin:0 0 12px;padding:13px 15px;border:1px solid #bfdbfe;border-radius:11px;background:#eff6ff;color:#1e3a5f;font-size:12px;line-height:1.45}
      .om-guidance-card strong{color:#1d4ed8;font-size:13px}.om-guidance-card span{color:#475569}
      .om-detail-button{display:grid;grid-template-columns:34px minmax(145px,1fr);align-items:center;gap:9px;min-width:210px;width:100%;padding:5px 7px;border:1px solid #d7e1ec;border-radius:8px;background:#f8fbff;color:#172033;text-align:left;cursor:pointer}.om-detail-button:hover{border-color:#93b4ff;background:#eef5ff}.om-detail-button>span:last-child{display:grid;gap:2px}.om-detail-button strong{font-size:11px}.om-detail-button small{color:#66758a;font-size:9px}.om-detail-thumb{width:32px;height:32px;display:grid;place-items:center;overflow:hidden;border:1px solid #d9e2ec;border-radius:7px;background:#fff;color:#2563eb;font-weight:900}.om-detail-thumb img{width:100%;height:100%;object-fit:cover}.om-store-connection{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-top:16px;padding:14px 16px;border:1px solid #bfdbfe;border-radius:12px;background:#eff6ff}.om-store-connection>div{display:grid;gap:4px}.om-store-connection strong{color:#1d4ed8}.om-store-connection span{color:#475569;font-size:12px;line-height:1.45}.om-detail-backdrop{position:fixed;inset:0;z-index:10050;display:grid;place-items:center;padding:28px;background:rgba(15,23,42,.48);backdrop-filter:blur(3px)}.om-detail-modal{display:flex;flex-direction:column;width:min(920px,calc(100vw - 56px));max-height:calc(100vh - 76px);overflow:hidden;border:1px solid #cbd5e1;border-radius:18px;background:#fff;box-shadow:0 28px 80px rgba(15,23,42,.25)}.om-detail-modal>header{display:flex;justify-content:space-between;gap:20px;padding:22px 24px 18px;border-bottom:1px solid #dbe4ef}.om-detail-modal>header small{color:#2563eb;font-size:10px;font-weight:900;letter-spacing:.16em}.om-detail-modal>header h3{margin:6px 0 4px!important;font-size:24px!important}.om-detail-modal>header p{max-width:680px;margin:0;color:#66758a;font-size:12px;line-height:1.45}.om-detail-modal>header button{width:38px;height:38px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#172033;font-size:25px;cursor:pointer}.om-detail-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(320px,.9fr);gap:24px;padding:22px 24px;overflow:auto}.om-detail-fields{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-content:start}.om-detail-fields label,.om-image-url{display:grid;gap:6px;color:#526071;font-size:10px;font-weight:850;letter-spacing:.06em;text-transform:uppercase}.om-detail-fields .om-detail-wide{grid-column:1/-1}.om-detail-fields textarea{resize:vertical;line-height:1.45}.om-detail-images{display:grid;align-content:start;gap:12px}.om-detail-images>div:first-child{display:grid;gap:4px}.om-detail-images>div:first-child strong{color:#172033}.om-detail-images>div:first-child span{color:#66758a;font-size:11px;line-height:1.4}.om-image-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.om-image-grid article{overflow:hidden;border:2px solid transparent;border-radius:10px;background:#f8fafc}.om-image-grid article[data-primary=true]{border-color:#2563eb}.om-image-grid img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover}.om-image-grid article div{display:flex;justify-content:space-between;gap:6px;padding:7px}.om-image-grid button{border:0;background:transparent;color:#526071;font-size:9px;font-weight:800;cursor:pointer}.om-image-grid article[data-primary=true] button:first-child{color:#2563eb}.om-image-grid button:last-child{color:#9f3a38}.om-image-empty{grid-column:1/-1;display:grid;place-items:center;min-height:120px;border:1px dashed #b9c7d8;border-radius:10px;color:#8295a8;font-size:12px}.om-image-upload{justify-self:start;border:1px solid #b9c7d8;border-radius:9px;padding:9px 12px;color:#344054;font-size:11px;font-weight:750;cursor:pointer}.om-image-upload input{display:none}.om-image-url>div{display:grid;grid-template-columns:1fr auto;gap:7px}.om-detail-modal>footer{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:15px 24px;border-top:1px solid #dbe4ef;background:#f8fafc}.om-detail-modal>footer span{color:#66758a;font-size:11px}
      .om-image-frame{display:grid!important;place-items:center!important;min-height:145px;padding:0!important;background:#f1f5f9;color:#64748b;text-align:center;font-size:11px;line-height:1.35}.om-image-frame small{font-size:9px}.om-image-grid article>.om-image-frame+div{display:flex;justify-content:space-between;gap:6px;padding:7px}
      .om-cost-guidance{min-width:360px;padding:9px 11px;border:1px solid #dbeafe;border-radius:8px;background:#f8fbff;color:#475569;font-size:11px;line-height:1.4}
      .om-cost-guidance[data-tone=attention]{border-color:#fde68a;background:#fffbeb;color:#854d0e}
      .om-decision-card{display:grid;grid-template-columns:minmax(320px,1.4fr) minmax(250px,.6fr);gap:16px;margin:4px 0 28px;padding:18px;border:1px solid #bfdbfe;border-radius:14px;background:#f8fbff}
      .om-decision-card>div>span{display:block;color:#2563eb;font-size:10px;font-weight:900;letter-spacing:.15em}.om-decision-card h3{margin:6px 0;color:#172033;font-size:19px}.om-decision-card p{margin:7px 0 0;color:#53657a;font-size:13px;line-height:1.5}.om-decision-card p strong{color:#172033}
      .om-decision-status{display:grid;grid-template-columns:1fr 1fr;gap:8px}.om-decision-status div{display:grid;align-content:center;padding:12px;border:1px solid #dbeafe;border-radius:10px;background:#fff}.om-decision-status small{color:#64748b}.om-decision-status strong{margin-top:5px;color:#1e3a5f}
      .om-decision-card>.om-actions{grid-column:1/-1;justify-content:flex-start}
      .om-route-note{border:1px solid #ead79a;border-radius:8px;background:#fffbeb;padding:16px;margin:10px 0}.om-route-note p{color:var(--om-muted)}
      .om-conversation-facts{display:grid;gap:8px;margin:0 0 18px;padding:14px;background:#eef5ff;border:1px solid #c8d8fb;border-left:4px solid var(--om-teal);border-radius:12px}
      .om-conversation-facts-title{color:var(--om-teal-dark);font-size:10px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}
      .om-conversation-facts article{display:grid;grid-template-columns:minmax(230px,.7fr) minmax(280px,1.3fr);gap:12px;padding:11px 12px;background:#fff;border:1px solid #d9e2ec;border-radius:10px}
      .om-conversation-facts article strong,.om-conversation-facts article span{display:block}.om-conversation-facts article span{margin-top:4px;color:#617487;font-size:11px}
      .om-conversation-facts article p{margin:0;color:#102a43;font-weight:750}.om-conversation-facts article small{grid-column:1/-1;color:#6b7f91}
      .om-secondary{border:1px solid var(--om-teal)!important;background:#fff!important;color:var(--om-teal-dark)!important;padding:10px 13px;border-radius:11px;font-weight:750;cursor:pointer}
      .om-note{margin-top:10px}
      .om-quick{
        border:1px solid #c8d8fb;
        border-radius:12px;
        background:#eef5ff;
        padding:14px;
        display:grid;
        grid-template-columns:1fr minmax(260px,2fr) auto;
        gap:12px;
        align-items:center;
      }
      .om-quick strong{color:var(--om-ink) !important}
      .om-quick span{display:block;color:var(--om-muted) !important;font-size:12px;margin-top:5px}
      .om-summary-grid{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:10px}
      .om-summary-grid div{border:1px solid var(--om-line);border-radius:12px;background:#fff!important;padding:16px}
      .om-summary-grid span{display:block;color:#667085 !important;font-size:12px}
      .om-summary-grid strong{display:block;color:var(--om-teal-dark) !important;font-size:23px;margin-top:7px}
      .om-board-note{margin-top:20px;background:var(--om-blue-soft)}
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
        font-size:12px;
      }
      .om-error{color:#b42318 !important}
      .om-saved{color:var(--om-green) !important}
      @media(max-width:900px){
        .om-package,.om-terminal footer,.om-context{align-items:stretch;flex-direction:column}
        .om-package,.om-terminal{padding-left:18px;padding-right:18px}
        .om-quick{grid-template-columns:1fr}
        .om-summary-grid{grid-template-columns:1fr 1fr}
        .om-decision-card{grid-template-columns:1fr}.om-cost-guidance{min-width:220px}
        .om-store-connection{align-items:stretch;flex-direction:column}.om-detail-backdrop{padding:12px}.om-detail-modal{width:calc(100vw - 24px);max-height:calc(100vh - 24px)}.om-detail-body{grid-template-columns:1fr}.om-detail-fields{grid-template-columns:1fr}.om-detail-fields .om-detail-wide{grid-column:auto}
      }
    `; document.head.appendChild(node);
  }

  style();
  global.AionOperatingModelWorkspace = { render, renderFinanceFoundations: () => finance({ embeddedInFinance:true }), load, save, applyConversationFact, persistDraft, rerender, resolveImageUrl: catalogueImageSource, state };
})(window);
