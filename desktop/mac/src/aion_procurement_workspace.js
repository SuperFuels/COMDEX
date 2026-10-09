(function installAionProcurementWorkspace(global) {
  'use strict';

  const ui = { tab: 'stock', quickText: '' };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const operating = () => global.AionOperatingModelWorkspace;
  const model = () => operating()?.state?.model || {};
  const rows = (key) => Array.isArray(model()[key]) ? model()[key] : (model()[key] = []);
  const money = (value) => new Intl.NumberFormat('en-GB', { style: 'currency', currency: model().currency || 'EUR', maximumFractionDigits: 2 }).format(Number(value || 0));
  const input = (collection, index, field, value, type = 'text', placeholder = '') => `<input class="prw-input" type="${type}" data-prw-list="${collection}" data-prw-index="${index}" data-prw-field="${field}" value="${esc(value)}" placeholder="${esc(placeholder)}">`;
  const select = (collection, index, field, value, options) => `<select class="prw-input" data-prw-list="${collection}" data-prw-index="${index}" data-prw-field="${field}">${options.map(([key,label]) => `<option value="${esc(key)}" ${String(value) === String(key) ? 'selected' : ''}>${esc(label)}</option>`).join('')}</select>`;
  const remove = (collection, index) => `<button class="prw-remove" type="button" data-prw-remove="${collection}" data-prw-index="${index}" aria-label="Remove row">×</button>`;
  const empty = (title, body) => `<div class="prw-empty"><strong>${esc(title)}</strong><span>${esc(body)}</span></div>`;

  function persist() {
    operating()?.persistDraft?.();
  }

  function refresh() {
    if (typeof global.requestRender === 'function') global.requestRender();
  }

  function metrics() {
    const stock = rows('inventory_items');
    const queue = rows('procurement_queue');
    const stockValue = stock.reduce((sum, item) => sum + Number(item.quantity_on_hand || 0) * Number(item.unit_cost || 0), 0);
    const reorder = stock.filter((item) => Number(item.reorder_point || 0) > 0 && Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0) <= Number(item.reorder_point || 0)).length;
    const awaiting = queue.filter((item) => ['suggested','draft','review'].includes(String(item.status || 'draft'))).length;
    const cash = queue.filter((item) => !['cancelled','received'].includes(String(item.status || ''))).reduce((sum, item) => sum + Number(item.estimated_cash_required || 0), 0);
    return { stockValue, reorder, awaiting, cash };
  }

  function stockView() {
    const stock = rows('inventory_items');
    return `<section class="prw-panel"><header><div><small>STOCK CONTROL</small><h3>Stock on hand</h3><p>Track only stock that ties up cash or can delay delivery. Service-only businesses can leave this empty.</p></div><button class="prw-primary" type="button" data-prw-add="inventory_items">+ Add stock item</button></header>
      ${stock.length ? `<div class="prw-table"><table><thead><tr><th>Item</th><th>Class</th><th>Unit</th><th>On hand</th><th>Reserved</th><th>Available</th><th>Unit cost</th><th>Reorder at</th><th>Target</th><th>Lead days</th><th></th></tr></thead><tbody>${stock.map((item,index) => `<tr><td>${input('inventory_items',index,'name',item.name,'text','Item name')}</td><td>${select('inventory_items',index,'stock_class',item.stock_class || 'raw_material',[['raw_material','Raw material'],['work_in_progress','Work in progress'],['finished_good','Finished good'],['consumable','Consumable'],['packaging','Packaging'],['resale','Resale stock']])}</td><td>${input('inventory_items',index,'unit',item.unit || 'units')}</td><td>${input('inventory_items',index,'quantity_on_hand',item.quantity_on_hand,'number')}</td><td>${input('inventory_items',index,'quantity_reserved',item.quantity_reserved,'number')}</td><td><strong>${esc(Math.max(0, Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0)))}</strong></td><td>${input('inventory_items',index,'unit_cost',item.unit_cost,'number')}</td><td>${input('inventory_items',index,'reorder_point',item.reorder_point,'number')}</td><td>${input('inventory_items',index,'target_stock',item.target_stock,'number')}</td><td>${input('inventory_items',index,'lead_time_days',item.lead_time_days,'number')}</td><td>${remove('inventory_items',index)}</td></tr>`).join('')}</tbody></table></div>` : empty('No stock items yet', 'Add materials, consumables or finished products only when the quantity matters to delivery or cash.')}
      <div class="prw-note"><strong>Automatic replenishment insight</strong><span>Saving recalculates available stock, value, shortages and draft purchase suggestions. It never places an order.</span></div>
    </section>`;
  }

  function purchaseView() {
    const queue = rows('procurement_queue');
    return `<section class="prw-panel"><div class="prw-quick"><div><small>QUICK ADD</small><strong>What needs buying?</strong><span>For example: “4 tins of paint needed Friday”</span></div><input class="prw-input" data-prw-quick-input value="${esc(ui.quickText)}" placeholder="Describe the item and when it is needed"><button class="prw-primary" type="button" data-prw-quick-add>Add draft</button></div>
      <header><div><small>APPROVAL-GATED PURCHASING</small><h3>Purchasing list</h3><p>Compare needs, supplier, timing and estimated cash before anyone approves an order.</p></div><button class="prw-primary" type="button" data-prw-add="procurement_queue">+ Add purchase</button></header>
      ${queue.length ? `<div class="prw-table"><table><thead><tr><th>Item</th><th>Quantity</th><th>Unit</th><th>Supplier</th><th>Needed by</th><th>Est. cash</th><th>Lead days</th><th>Status</th><th></th></tr></thead><tbody>${queue.map((item,index) => `<tr><td>${input('procurement_queue',index,'name',item.name,'text','Item to buy')}</td><td>${input('procurement_queue',index,'quantity',item.quantity,'number')}</td><td>${input('procurement_queue',index,'unit',item.unit || 'units')}</td><td>${input('procurement_queue',index,'supplier_name',item.supplier_name,'text','Optional')}</td><td>${input('procurement_queue',index,'required_date',item.required_date,'date')}</td><td>${input('procurement_queue',index,'estimated_cash_required',item.estimated_cash_required,'number')}</td><td>${input('procurement_queue',index,'lead_time_days',item.lead_time_days,'number')}</td><td>${select('procurement_queue',index,'status',item.status || 'draft',[['suggested','Suggested'],['draft','Draft'],['review','Needs review'],['approved','Approved'],['ordered','Ordered'],['received','Received'],['cancelled','Cancelled']])}</td><td>${remove('procurement_queue',index)}</td></tr>`).join('')}</tbody></table></div>` : empty('Nothing waiting to be bought', 'Add a draft need here or ask Procurement Pilot to review stock and suggest what should be purchased.')}
      <div class="prw-warning"><strong>No silent purchasing</strong><span>Drafts and recommendations may be prepared here. Supplier contact, payment and order placement remain behind explicit approval.</span></div>
    </section>`;
  }

  function supplierView() {
    const suppliers = rows('suppliers');
    return `<section class="prw-panel"><header><div><small>SUPPLIER RECORD</small><h3>Suppliers and terms</h3><p>Keep the comparison evidence needed to choose a supplier without relying on memory.</p></div><button class="prw-primary" type="button" data-prw-add="suppliers">+ Add supplier</button></header>
      ${suppliers.length ? `<div class="prw-table"><table><thead><tr><th>Supplier</th><th>Contact</th><th>Typical items</th><th>Lead days</th><th>Payment terms</th><th>Minimum order</th><th>Notes / evidence</th><th></th></tr></thead><tbody>${suppliers.map((item,index) => `<tr><td>${input('suppliers',index,'name',item.name,'text','Supplier name')}</td><td>${input('suppliers',index,'contact',item.contact,'text','Email or phone')}</td><td>${input('suppliers',index,'categories',item.categories,'text','Materials supplied')}</td><td>${input('suppliers',index,'lead_time_days',item.lead_time_days,'number')}</td><td>${input('suppliers',index,'payment_terms',item.payment_terms,'text','e.g. 30 days')}</td><td>${input('suppliers',index,'minimum_order',item.minimum_order,'number')}</td><td>${input('suppliers',index,'notes',item.notes,'text','Quote or comparison note')}</td><td>${remove('suppliers',index)}</td></tr>`).join('')}</tbody></table></div>` : empty('No supplier records yet', 'Add suppliers when comparisons, lead times, minimum orders or payment terms affect a buying decision.')}
    </section>`;
  }

  function render() {
    const workspace = operating();
    if (!workspace?.state?.loaded && !workspace?.state?.loading) setTimeout(() => workspace?.load?.(), 0);
    const m = metrics();
    const view = ui.tab === 'purchases' ? purchaseView() : ui.tab === 'suppliers' ? supplierView() : stockView();
    return `<section class="prw-shell" data-aion-procurement-workspace="true">
      <div class="prw-metrics"><article><strong>${money(m.stockValue)}</strong><span>Stock value</span></article><article><strong>${m.reorder}</strong><span>At or below reorder point</span></article><article><strong>${m.awaiting}</strong><span>Purchases awaiting review</span></article><article><strong>${money(m.cash)}</strong><span>Estimated purchase cash</span></article></div>
      <nav class="prw-tabs" aria-label="Stock and procurement workspace"><button data-prw-tab="stock" data-active="${ui.tab === 'stock'}">Stock</button><button data-prw-tab="purchases" data-active="${ui.tab === 'purchases'}">Purchasing</button><button data-prw-tab="suppliers" data-active="${ui.tab === 'suppliers'}">Suppliers</button></nav>
      ${view}
      <footer><span>${workspace?.state?.error ? esc(workspace.state.error) : workspace?.state?.savedAt ? `Saved to the Business Map at ${esc(workspace.state.savedAt)}` : 'Changes remain a draft until saved.'}</span><button class="prw-primary" type="button" data-prw-save ${workspace?.state?.saving ? 'disabled' : ''}>${workspace?.state?.saving ? 'Saving…' : 'Save & update Boardroom'}</button></footer>
    </section>`;
  }

  const defaults = {
    inventory_items: { name:'', stock_class:'raw_material', unit:'units', quantity_on_hand:'', quantity_reserved:'', unit_cost:'', reorder_point:'', target_stock:'', lead_time_days:'' },
    procurement_queue: { name:'', quantity:'', unit:'units', supplier_name:'', required_date:'', estimated_cash_required:'', lead_time_days:'', status:'draft', requires_approval:true },
    suppliers: { name:'', contact:'', categories:'', lead_time_days:'', payment_terms:'', minimum_order:'', notes:'' },
  };

  document.addEventListener('input', (event) => {
    const quick = event.target.closest?.('[data-prw-quick-input]');
    if (quick) { ui.quickText = quick.value; return; }
    const field = event.target.closest?.('[data-prw-list][data-prw-field]');
    if (!field) return;
    const row = rows(field.dataset.prwList)[Number(field.dataset.prwIndex)];
    if (!row) return;
    row[field.dataset.prwField] = field.value;
    persist();
  }, true);

  document.addEventListener('change', (event) => {
    const field = event.target.closest?.('[data-prw-list][data-prw-field]');
    if (!field) return;
    const row = rows(field.dataset.prwList)[Number(field.dataset.prwIndex)];
    if (!row) return;
    row[field.dataset.prwField] = field.value;
    persist();
  }, true);

  document.addEventListener('click', (event) => {
    const tab = event.target.closest?.('[data-prw-tab]');
    if (tab) { ui.tab = tab.dataset.prwTab; refresh(); return; }
    const add = event.target.closest?.('[data-prw-add]');
    if (add) { rows(add.dataset.prwAdd).push({ ...defaults[add.dataset.prwAdd] }); persist(); refresh(); return; }
    const removeButton = event.target.closest?.('[data-prw-remove]');
    if (removeButton) { rows(removeButton.dataset.prwRemove).splice(Number(removeButton.dataset.prwIndex), 1); persist(); refresh(); return; }
    if (event.target.closest?.('[data-prw-quick-add]')) {
      const text = String(ui.quickText || '').trim();
      if (!text) return;
      const match = text.match(/^\s*(\d+(?:\.\d+)?)\s+(.+?)(?:\s+(?:needed|by)\s+(.+))?$/i);
      rows('procurement_queue').push({ ...defaults.procurement_queue, quantity:match?.[1] || '', name:match?.[2] || text, notes:text, generated_by:'quick_add' });
      ui.quickText = ''; persist(); refresh(); return;
    }
    if (event.target.closest?.('[data-prw-save]')) operating()?.save?.();
  }, true);

  function installStyle() {
    if (document.getElementById('aion-procurement-workspace-style')) return;
    const style = document.createElement('style');
    style.id = 'aion-procurement-workspace-style';
    style.textContent = `
      .prw-shell{min-height:100%;padding:18px;color:#14213d;background:#f7f9fc;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;box-sizing:border-box}.prw-metrics{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:10px}.prw-metrics article{padding:15px;border:1px solid #d9e2ec;border-radius:12px;background:#fff}.prw-metrics strong,.prw-metrics span{display:block}.prw-metrics strong{font-size:22px;color:#2563eb}.prw-metrics span{margin-top:5px;color:#66758a;font-size:11px}.prw-tabs{display:flex;gap:7px;margin:16px 0;padding:10px;border:1px solid #d9e2ec;border-radius:12px;background:#eef3f9}.prw-tabs button{border:1px solid #cbd5e1;border-radius:999px;background:#fff;color:#334155;padding:8px 13px;font-weight:800;cursor:pointer}.prw-tabs button[data-active=true]{border-color:#2563eb;background:#eef5ff;color:#1d4ed8}.prw-panel{padding:18px;border:1px solid #d9e2ec;border-top:4px solid #2563eb;border-radius:15px;background:#fff;min-height:430px}.prw-panel>header{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;margin-bottom:16px}.prw-panel small,.prw-quick small{display:block;color:#2563eb;font-size:9px;font-weight:900;letter-spacing:.15em}.prw-panel h3{margin:5px 0;color:#14213d;font-size:20px}.prw-panel p{margin:0;color:#66758a;font-size:12px}.prw-primary{border:1px solid #2563eb;border-radius:10px;background:#2563eb;color:#fff;padding:9px 13px;font-weight:800;cursor:pointer}.prw-primary:disabled{opacity:.5}.prw-table{overflow:auto;border:1px solid #d9e2ec;border-radius:12px}.prw-table table{width:100%;min-width:1120px;border-collapse:collapse}.prw-table th{padding:10px;background:#f3f6fa;color:#66758a;font-size:9px;letter-spacing:.08em;text-align:left;text-transform:uppercase}.prw-table td{padding:7px;border-top:1px solid #e6ebf1}.prw-input{width:100%;min-width:90px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:#14213d;padding:8px}.prw-remove{border:1px solid #fecaca;border-radius:7px;background:#fff;color:#b91c1c;font-size:17px;cursor:pointer}.prw-empty{display:grid;place-items:center;gap:7px;min-height:260px;border:1px dashed #bfd2fb;border-radius:12px;background:#f8fbff;text-align:center}.prw-empty span{max-width:480px;color:#66758a;font-size:12px}.prw-note,.prw-warning{display:flex;gap:10px;margin-top:13px;padding:13px;border-radius:10px;font-size:11px}.prw-note{border:1px solid #bfd2fb;background:#eef5ff}.prw-warning{border:1px solid #f3d38d;background:#fff9e8;color:#744c08}.prw-quick{display:grid;grid-template-columns:minmax(220px,.7fr) minmax(280px,1.3fr) auto;gap:12px;align-items:center;margin-bottom:18px;padding:14px;border:1px solid #bfd2fb;border-radius:12px;background:#eef5ff}.prw-quick strong,.prw-quick span{display:block}.prw-quick span{margin-top:4px;color:#66758a;font-size:11px}.prw-shell footer{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:15px;padding-top:14px;border-top:1px solid #d9e2ec;color:#66758a;font-size:11px}@media(max-width:900px){.prw-metrics{grid-template-columns:1fr 1fr}.prw-quick{grid-template-columns:1fr}.prw-panel>header,.prw-shell footer{flex-direction:column}}
    `;
    document.head.appendChild(style);
  }

  installStyle();
  global.AionProcurementWorkspace = { render, state: ui };
})(window);
