(function installAionOperatingModelWorkspace(global) {
  'use strict';

  const STORAGE_KEY = 'aion.businessOperatingModel.draft.v1';
  const TABS = ['offerings', 'delivery', 'stock', 'procurement', 'finance', 'summary'];
  const state = {
    loaded: false, loading: false, saving: false, error: '', savedAt: '', activeTab: 'offerings',
    model: {
      model_status: 'draft', setup_mode: 'simple', currency: 'EUR', revision: 0,
      offerings: [], pricing_rules: [], payment_terms: [], customer_terms: [], labour_resources: [],
      overheads: [], debt_commitments: [], financial_targets: [], production_lines: [],
      bills_of_materials: [], inventory_items: [], suppliers: [], procurement_queue: [],
      unit_economics: [], inventory_metrics: {}, capacity_model: {}, provenance: {}, source_refs: [],
    },
  };

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const list = (key) => Array.isArray(state.model[key]) ? state.model[key] : (state.model[key] = []);
  const money = (value) => new Intl.NumberFormat('en-GB', { style: 'currency', currency: state.model.currency || 'EUR', maximumFractionDigits: 2 }).format(Number(value || 0));

  function persistDraft() { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.model)); } catch {} }
  function rerender() { if (typeof global.requestRender === 'function') global.requestRender(); }

  async function load() {
    if (state.loading || state.loaded) return;
    state.loading = true;
    try {
      const result = await global.AionBusinessContainerClient?.getOperatingModel?.();
      if (result?.payload) state.model = { ...state.model, ...result.payload };
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

  function remove(listName, index) { return `<button class="om-remove" type="button" data-om-remove="${listName}" data-om-index="${index}" title="Remove row">×</button>`; }
  function empty(message) { return `<div class="om-empty">${esc(message)}</div>`; }

  function offerings() {
    const rows = list('offerings');
    const advanced = state.model.setup_mode === 'advanced';
    return `
      <div class="om-section-head"><div><h3>Products, services and rate card</h3><p>Add one day rate or build a full product catalogue. Use + for each additional line.</p></div><div class="om-actions"><label class="om-import">Import CSV/XLSX<input type="file" accept=".csv,.xlsx" data-om-import="offerings"></label><button class="om-add" data-om-add="offerings">+ Add offering</button></div></div>
      ${rows.length ? `<div class="om-table-wrap"><table><thead><tr><th>Name</th><th>Type</th><th>Charge basis</th><th>Rate</th><th>Unit</th><th>Expected monthly volume</th>${advanced ? '<th>Material/unit</th><th>Labour/unit</th><th>Other direct/unit</th>' : ''}<th></th></tr></thead><tbody>
      ${rows.map((row, i) => `<tr><td>${input('offerings', i, 'name', row.name, 'text', 'Plumber day rate')}</td><td>${select('offerings', i, 'offering_type', row.offering_type || 'service', [['service','Service'],['product','Product'],['subscription','Subscription'],['rental','Rental'],['experience','Experience'],['other','Other']])}</td><td>${select('offerings', i, 'pricing_basis', row.pricing_basis || 'day_rate', [['hourly','Hourly'],['day_rate','Day rate'],['fixed','One-off / fixed'],['per_unit','Per unit'],['subscription','Subscription'],['tiered','Tiered volume'],['quote','Quoted'],['cost_plus','Cost plus']])}</td><td>${input('offerings', i, 'price', row.price, 'number', '0')}</td><td>${input('offerings', i, 'unit', row.unit || 'day', 'text', 'day')}</td><td>${input('offerings', i, 'expected_monthly_volume', row.expected_monthly_volume, 'number', '0')}</td>${advanced ? `<td>${input('offerings', i, 'material_cost_per_unit', row.material_cost_per_unit, 'number')}</td><td>${input('offerings', i, 'labour_cost_per_unit', row.labour_cost_per_unit, 'number')}</td><td>${input('offerings', i, 'other_direct_cost_per_unit', row.other_direct_cost_per_unit, 'number')}</td>` : ''}<td>${remove('offerings', i)}</td></tr>`).join('')}
      </tbody></table></div>` : empty('Start with a service, product, subscription or day rate.')}
      <div class="om-note">Customer-specific prices and payment terms can be added below Finance inputs. Large catalogues can be imported in the next connector stage without changing this model.</div>`;
  }

  function delivery() {
    const labour = list('labour_resources'); const lines = list('production_lines'); const bom = list('bills_of_materials');
    return `
      <div class="om-section-head"><div><h3>People and direct labour</h3><p>Employees, owners, contractors or freelancers used to deliver the work.</p></div><button class="om-add" data-om-add="labour_resources">+ Add labour</button></div>
      ${labour.length ? `<div class="om-table-wrap"><table><thead><tr><th>Role / person</th><th>Engagement</th><th>Cost basis</th><th>Rate</th><th>Available hours/month</th><th></th></tr></thead><tbody>${labour.map((r,i)=>`<tr><td>${input('labour_resources',i,'name',r.name,'text','Plumber')}</td><td>${select('labour_resources',i,'engagement_type',r.engagement_type||'employee',[['owner','Owner'],['employee','Employee'],['contractor','Contractor'],['freelancer','Freelancer'],['agency','Agency']])}</td><td>${select('labour_resources',i,'cost_basis',r.cost_basis||'hourly',[['hourly','Hourly'],['daily','Daily'],['monthly','Monthly salary'],['per_job','Per job'],['per_unit','Per unit']])}</td><td>${input('labour_resources',i,'cost_rate',r.cost_rate,'number')}</td><td>${input('labour_resources',i,'available_hours_month',r.available_hours_month,'number')}</td><td>${remove('labour_resources',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Add labour only if people time is a direct delivery or production cost.')}
      <div class="om-section-head"><div><h3>Production lines or delivery units</h3><p>Optional for factories, kitchens, workshops, crews or service teams.</p></div><button class="om-add" data-om-add="production_lines">+ Add line</button></div>
      ${lines.length ? `<div class="om-table-wrap"><table><thead><tr><th>Line / unit</th><th>Output unit</th><th>Capacity per day</th><th>Operating days/month</th><th>Constraint</th><th></th></tr></thead><tbody>${lines.map((r,i)=>`<tr><td>${input('production_lines',i,'name',r.name,'text','Cake line 1')}</td><td>${input('production_lines',i,'output_unit',r.output_unit,'text','cakes')}</td><td>${input('production_lines',i,'capacity_per_day',r.capacity_per_day,'number')}</td><td>${input('production_lines',i,'operating_days_month',r.operating_days_month,'number')}</td><td>${input('production_lines',i,'constraint',r.constraint,'text','oven capacity')}</td><td>${remove('production_lines',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('A sole trader can leave this empty; factories and production businesses can model each line.')}
      <div class="om-section-head"><div><h3>Materials used per product or job</h3><p>A lightweight bill of materials that links inputs to an offering.</p></div><button class="om-add" data-om-add="bills_of_materials">+ Add material</button></div>
      ${bom.length ? `<div class="om-table-wrap"><table><thead><tr><th>Offering ID / name</th><th>Material</th><th>Quantity per unit</th><th>Unit</th><th>Unit cost</th><th>Waste %</th><th></th></tr></thead><tbody>${bom.map((r,i)=>`<tr><td>${input('bills_of_materials',i,'offering_id',r.offering_id)}</td><td>${input('bills_of_materials',i,'material_name',r.material_name,'text','Flour')}</td><td>${input('bills_of_materials',i,'quantity_per_unit',r.quantity_per_unit,'number')}</td><td>${input('bills_of_materials',i,'unit',r.unit,'text','kg')}</td><td>${input('bills_of_materials',i,'unit_cost',r.unit_cost,'number')}</td><td>${input('bills_of_materials',i,'waste_percent',r.waste_percent,'number')}</td><td>${remove('bills_of_materials',i)}</td></tr>`).join('')}</tbody></table></div>` : empty('Add materials when a product or job consumes stock.')}`;
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
    return simpleTable('payment_terms','Default and customer payment terms','Examples: 50% upfront / 50% completion, net 30, or a customer-specific exception.',[['name','Customer / default'],['deposit_percent','Deposit %','number'],['balance_due_days','Balance due days','number'],['notes','Terms']], 'Add the default terms once, then only record exceptions.') +
      simpleTable('overheads','Overheads','Confirm values imported from accounting or add monthly recurring costs manually.',[['name','Cost'],['monthly_amount','Monthly amount','number'],['category','Category'],['source','Source']], 'Add software, vehicles, premises, insurance, marketing or professional costs not already imported.') +
      simpleTable('debt_commitments','Debt and finance commitments','One row per loan, card, lease or vehicle finance agreement.',[['name','Lender / facility'],['balance','Balance','number'],['monthly_repayment','Monthly repayment','number'],['interest_rate','Interest %','number'],['remaining_months','Months left','number'],['security','Security / guarantee']], 'Leave empty if the business has no borrowing.') +
      simpleTable('financial_targets','12-month financial targets','Use an amount or percentage and add custom measures when needed.',[['name','Target'],['target_value','Value','number'],['unit','€ / % / days'],['deadline','Deadline','date']], 'Examples: revenue, gross margin, net profit, cash reserve or debtor days.');
  }

  function summary() {
    const m = state.model.inventory_metrics || {}; const e = list('unit_economics'); const queue = list('procurement_queue');
    return `<div class="om-summary-grid"><div><span>Offerings</span><strong>${list('offerings').length}</strong></div><div><span>Total stock value</span><strong>${money(m.total_stock_value)}</strong></div><div><span>Reorder items</span><strong>${m.reorder_items || 0}</strong></div><div><span>Suggested procurement cash</span><strong>${money(m.suggested_procurement_cash_required)}</strong></div><div><span>Purchases awaiting review</span><strong>${queue.filter(x=>['suggested','draft','review'].includes(x.status)).length}</strong></div></div>
    <div class="om-section-head"><div><h3>Unit economics</h3><p>Calculated after saving from price, materials, labour and other direct costs.</p></div></div>${e.length ? `<div class="om-table-wrap"><table><thead><tr><th>Offering</th><th>Price/unit</th><th>Direct cost/unit</th><th>Contribution/unit</th><th>Gross margin</th><th>Monthly revenue</th></tr></thead><tbody>${e.map(r=>`<tr><td>${esc(r.name)}</td><td>${money(r.price_per_unit)}</td><td>${money(r.direct_cost_per_unit)}</td><td>${money(r.contribution_per_unit)}</td><td>${r.gross_margin_percent == null ? '—' : esc(r.gross_margin_percent)+'%'}</td><td>${money(r.expected_monthly_revenue)}</td></tr>`).join('')}</tbody></table></div>` : empty('Save the model to calculate unit economics.')}
    <div class="om-board-note"><strong>Boardroom use</strong><p>The Board receives these structured facts on every meeting: offer economics, production capacity, stock tied up in cash, shortages, procurement cash needs, payment terms, overheads, debt and targets. It can model discount or liquidation scenarios without relying on provider memory.</p></div>`;
  }

  function content() { return ({ offerings, delivery, stock, procurement, finance, summary }[state.activeTab] || offerings)(); }

  function render() {
    if (!state.loaded) setTimeout(load, 0);
    const mode = state.model.setup_mode || 'simple';
    return `<section class="om-shell" data-aion-operating-model="true"><header class="om-package"><div><small>BUSINESS OPERATING MODEL</small><h2>Products & Services · Production · Stock · Procurement</h2><p>One shared source of truth for Sales, Operations, HR, Finance and the Boardroom.</p></div><div class="om-mode"><button data-om-mode="simple" data-active="${mode==='simple'}">Simple</button><button data-om-mode="advanced" data-active="${mode==='advanced'}">Advanced</button></div></header><section class="om-terminal"><div class="om-title">&gt; BUILD HOW THE BUSINESS EARNS, DELIVERS AND BUYS</div><nav class="om-tabs">${TABS.map(tab=>`<button data-om-tab="${tab}" data-active="${tab===state.activeTab}">${esc(tab.replace('_',' '))}</button>`).join('')}</nav><div class="om-content">${content()}</div><footer><div>${state.error ? `<span class="om-error">${esc(state.error)}</span>` : state.savedAt ? `<span class="om-saved">Saved to Business Container at ${esc(state.savedAt)}</span>` : '<span>Changes remain a draft until saved.</span>'}</div><button class="om-save" data-om-save="true" ${state.saving?'disabled':''}>${state.saving?'SAVING…':'SAVE MODEL & UPDATE BOARDROOM'}</button></footer></section></section>`;
  }

  const defaults = {
    offerings: { name:'', offering_type:'service', pricing_basis:'day_rate', price:'', unit:'day', expected_monthly_volume:'' },
    labour_resources: { name:'', engagement_type:'employee', cost_basis:'hourly', cost_rate:'', available_hours_month:'' },
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
    row[el.dataset.omField] = el.value; persistDraft();
  }, true);
  document.addEventListener('change', (event) => {
    const importInput = event.target.closest?.('[data-om-import]');
    if (importInput) { importSpreadsheet(importInput.files?.[0], importInput.dataset.omImport); return; }
    const el = event.target.closest?.('[data-om-list][data-om-field]'); if (!el) return;
    const row = list(el.dataset.omList)[Number(el.dataset.omIndex)]; if (!row) return;
    row[el.dataset.omField] = el.value; persistDraft();
  }, true);
  document.addEventListener('click', (event) => {
    const tab = event.target.closest?.('[data-om-tab]'); if (tab) { state.activeTab = tab.dataset.omTab; rerender(); return; }
    const mode = event.target.closest?.('[data-om-mode]'); if (mode) { state.model.setup_mode = mode.dataset.omMode; persistDraft(); rerender(); return; }
    const add = event.target.closest?.('[data-om-add]'); if (add) { const key=add.dataset.omAdd; list(key).push({...defaults[key]}); persistDraft(); rerender(); return; }
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
      .om-shell{max-width:1680px;margin:0 auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.om-package{border:2px solid #f59e0b;padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:20px;background:#fff}.om-package small{color:#0f766e;font-weight:900;letter-spacing:.26em}.om-package h2{font-family:Inter,system-ui,sans-serif;margin:7px 0 4px;color:#0f172a}.om-package p{margin:0;color:#475569}.om-mode{display:flex}.om-mode button,.om-tabs button{border:1px solid #155e75;background:#071426;color:#94a3b8;padding:10px 14px;text-transform:uppercase;font-weight:900;letter-spacing:.08em}.om-mode button[data-active=true],.om-tabs button[data-active=true]{color:#86efac;border-color:#4ade80;background:#063c2a}.om-terminal{margin-top:16px;background:#0f1a31;color:#cbd5e1;border-left:5px solid #0ea5e9;padding:20px;min-height:660px}.om-title{color:#86efac;letter-spacing:.23em;font-weight:900;margin-bottom:18px}.om-tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:22px}.om-content{min-height:500px}.om-section-head{display:flex;justify-content:space-between;align-items:end;gap:15px;margin:24px 0 10px}.om-section-head h3{color:#facc15;margin:0 0 5px}.om-section-head p{margin:0;color:#94a3b8}.om-actions{display:flex;gap:8px;align-items:center}.om-import{border:1px solid #38bdf8;color:#bae6fd;padding:10px 13px;font-weight:900;cursor:pointer}.om-import input{display:none}.om-add,.om-save{border:1px solid #4ade80;background:#22c55e;color:#052e22;padding:11px 16px;font-weight:950;letter-spacing:.08em;text-transform:uppercase;cursor:pointer}.om-table-wrap{overflow:auto;border:1px solid #155e75}.om-table-wrap table{width:100%;border-collapse:collapse;min-width:900px}.om-table-wrap th{color:#7dd3fc;text-align:left;padding:10px;background:#082f49;font-size:12px}.om-table-wrap td{border-top:1px solid #164e63;padding:6px}.om-input{box-sizing:border-box;width:100%;min-width:90px;background:#071426;color:#e2e8f0;border:1px solid #155e75;padding:10px;font:inherit}.om-input:focus{outline:2px solid #fbbf24}.om-remove{background:transparent;color:#fda4af;border:1px solid #ef4444;font-size:18px}.om-empty,.om-note,.om-board-note{border:1px dashed #155e75;padding:16px;color:#94a3b8}.om-note{margin-top:10px}.om-quick{border:1px solid #4ade80;padding:14px;display:grid;grid-template-columns:1fr minmax(260px,2fr) auto;gap:12px;align-items:center}.om-quick span{display:block;color:#94a3b8;font-size:12px;margin-top:5px}.om-summary-grid{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:10px}.om-summary-grid div{border:1px solid #155e75;background:#071426;padding:16px}.om-summary-grid span{display:block;color:#7dd3fc;font-size:12px}.om-summary-grid strong{display:block;color:#86efac;font-size:23px;margin-top:7px}.om-board-note{margin-top:20px;border-style:solid}.om-board-note strong{color:#facc15}.om-terminal footer{border-top:1px solid #155e75;margin-top:24px;padding-top:16px;display:flex;justify-content:space-between;align-items:center;gap:15px}.om-error{color:#fda4af}.om-saved{color:#86efac}@media(max-width:900px){.om-package,.om-terminal footer{align-items:stretch;flex-direction:column}.om-quick{grid-template-columns:1fr}.om-summary-grid{grid-template-columns:1fr 1fr}}
    `; document.head.appendChild(node);
  }

  style();
  global.AionOperatingModelWorkspace = { render, load, save, state };
})(window);
