(function installAionWorkScheduleWorkspace(global) {
  'use strict';

  const STORAGE_KEY = 'tessaris.workSchedule.workspace.v1';
  const UI_KEY = 'tessaris.workSchedule.ui.v1';
  const API_BASE = String(global.__AION_DESKTOP_STATE__?.apiBase || global.__aionDesktopState?.apiBase || 'http://127.0.0.1:8080').replace(/\/+$/, '');
  const STATUSES = ['new', 'quote_required', 'awaiting_approval', 'awaiting_payment', 'scheduled', 'en_route', 'in_progress', 'paused', 'completed', 'invoiced', 'paid'];
  const TYPE_LABELS = {
    job: 'Job', quote: 'Quote / estimate', appointment: 'Appointment', visit: 'Visit', survey: 'Survey',
    consultation: 'Consultation', meeting: 'Meeting', project_task: 'Project task', order: 'Order'
  };
  const SOURCE_OPTIONS = [
    'Website', 'Google search', 'Google Ads', 'Facebook', 'Instagram', 'LinkedIn', 'TikTok', 'X', 'Pinterest',
    'Referral', 'Returning customer', 'Phone', 'Email', 'Walk-in', 'Customer portal', 'Sales / outbound', 'Back office', 'Other'
  ];

  const esc = (value) => String(value == null ? '' : value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
  const titleCase = (value) => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  const isoDate = (date) => {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  };
  const dateFromIso = (value) => {
    const bits = String(value || '').split('-').map(Number);
    return bits.length === 3 ? new Date(bits[0], bits[1] - 1, bits[2]) : new Date();
  };
  const uid = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const moneyNumber = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  let labourDirectoryCache = null;
  let labourDirectoryLoading = false;
  let gmailHealthLoading = false;
  let gmailHealthChecked = false;
  let gmailHealthSnapshot = null;

  async function hydrateLabourDirectory() {
    if (labourDirectoryCache || labourDirectoryLoading) return;
    const businessId = global.AionBusinessContainerClient?.resolveBusinessId?.();
    if (!businessId) return;
    labourDirectoryLoading = true;
    try {
      const [operatingResult, organisationResponse] = await Promise.all([
        global.AionBusinessContainerClient?.getOperatingModel?.(),
        fetch(`${API_BASE}/api/aion/business/organisation/${encodeURIComponent(businessId)}`),
      ]);
      const organisationResult = organisationResponse?.ok ? await organisationResponse.json() : {};
      labourDirectoryCache = {
        resources: Array.isArray(operatingResult?.payload?.labour_resources) ? operatingResult.payload.labour_resources : [],
        people: Array.isArray(organisationResult?.model?.people) ? organisationResult.model.people : [],
      };
      global.requestRender?.();
    } catch (_) {
      labourDirectoryCache = null;
    } finally {
      labourDirectoryLoading = false;
    }
  }

  function operatingOfferings() {
    return (global.AionOperatingModelWorkspace?.state?.model?.offerings || []).filter((row) => row && (row.id || row.name));
  }

  function operatingModel() {
    const live = global.AionOperatingModelWorkspace?.state?.model;
    if (live && typeof live === 'object') return live;
    try { return JSON.parse(global.localStorage?.getItem('aion.businessOperatingModel.draft.v1') || '{}') || {}; }
    catch (_) { return {}; }
  }

  function businessFoundation() {
    const merged = {};
    for (const live of [
      global.__aionFoundationPacket?.foundation_draft,
      global.__aionFoundationPacket?.approved_business_context,
      global.__aionFoundationPacket?.business_context_draft,
      global.__aionBusinessContextFoundation,
      global.__aionApprovedSmallBusinessFoundation,
    ]) {
      if (live && typeof live === 'object' && !Array.isArray(live)) Object.assign(merged, live);
    }
    for (const key of ['aion.smallBusinessFoundationDraft', 'aion.businessContextFoundation', 'aion.approvedSmallBusinessFoundation', 'aion.businessFoundation', 'aion.businessProfile']) {
      try {
        const value = JSON.parse(global.localStorage?.getItem(key) || '{}');
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          Object.assign(merged, value);
          global.localStorage?.removeItem(key);
          global.AionBusinessContainerClient?.saveFoundationSection?.('business_context_draft', value)
            .catch?.((error) => console.warn('[AION] Legacy work context Vault migration deferred', error));
        }
      } catch (_) {}
    }
    for (const live of [global.state?.smallBusinessFoundationDraft, global.state?.businessContextFoundation, global.state?.approvedSmallBusinessFoundation]) {
      if (live && typeof live === 'object' && !Array.isArray(live)) Object.assign(merged, live);
    }
    const registered = typeof global.getAionRegisteredBusinessIdentity === 'function'
      ? global.getAionRegisteredBusinessIdentity()
      : null;
    if ((!merged.business_name || /^your business$/i.test(String(merged.business_name).trim())) && registered?.registered) {
      merged.business_name = registered.business_name;
      merged.business_id = merged.business_id || registered.business_id;
    }
    return merged;
  }

  function quoteIdentity() {
    const business = businessFoundation();
    let payments = {};
    try { payments = JSON.parse(global.localStorage?.getItem('tessaris.businessPaymentSettings.v1') || '{}') || {}; } catch (_) { payments = {}; }
    const design = global.state?.brandFoundationState?.brandMap?.visualIdentity?.designSystem
      || global.state?.brandFoundationState?.brandIntelligenceMap?.visualIdentity?.designSystem || {};
    const assets = Array.isArray(design.assets) ? design.assets : [];
    const logo = assets.find((asset) => ['primary_logo', 'horizontal_logo', 'stacked_logo'].includes(String(asset?.role || ''))) || {};
    const colours = Array.isArray(design.primaryColours) ? design.primaryColours : Array.isArray(design.primary_colors) ? design.primary_colors : [];
    const savedDeposit = payments.default_deposit_percent;
    const legacyImplicitDeposit = String(savedDeposit ?? '').trim() === '50'
      && payments.default_deposit_percent_explicit !== true
      && payments.default_deposit_percent_explicit !== 'true';
    return {
      name: business.business_name || 'Your business', address: business.business_address || '',
      email: business.contact_email || '', phone: business.phone_number || '', website: business.website || '',
      terms: business.quotation_terms || '', includeTerms: String(business.include_terms_on_quotes || 'yes') !== 'no',
      validDays: Math.max(1, Number(business.quote_valid_days || 30)), accent: colours[0] || '#2563eb',
      quoteEmailSubject: business.quote_email_subject || 'Your quotation {quote_number}',
      quoteEmailBody: String(business.quote_email_body || 'Hi {customer_name},\n\nPlease see attached your quotation {quote_number}.\n\nKind regards,\n{business_name}').replace(/^\*\*([\s\S]*)\*\*$/, '$1'),
      logo: business.quote_logo_data_url || logo.src || logo.data_url || logo.url || '',
      currency: String(payments.payment_currency || 'EUR').toUpperCase(),
      paymentMethod: payments.default_payment_method || 'bank_transfer',
      bank: {
        accountName: payments.bank_account_name || '', bankName: payments.bank_name || '',
        sortCode: payments.bank_sort_code || '', accountNumber: payments.bank_account_number || '',
        iban: payments.bank_iban || '', bic: payments.bank_bic_swift || '',
      },
      paymentReferenceTemplate: payments.payment_reference_template || '{quote_number}',
      defaultDepositPercent: legacyImplicitDeposit || savedDeposit === '' || savedDeposit == null
        ? null
        : Math.min(100, Math.max(0, moneyNumber(savedDeposit))),
      stripeConnected: String(payments.stripe_connection_status || '').toLowerCase() === 'connected',
      stripePaymentLink: payments.stripe_payment_link || payments.stripe_checkout_link || '',
      stripeAccountLabel: payments.stripe_account_label || '',
      paymentLinks: {
        stripe: payments.stripe_payment_link || payments.stripe_checkout_link || '',
        paypal: payments.paypal_payment_link || '',
        square: payments.square_payment_link || '',
        gocardless: payments.gocardless_payment_link || '',
        revolut: payments.revolut_payment_link || '',
        sumup: payments.sumup_payment_link || '',
        mollie: payments.mollie_payment_link || '',
        braintree: payments.braintree_payment_link || '',
        worldpay: payments.worldpay_payment_link || '',
        adyen: payments.adyen_payment_link || '',
        checkout_com: payments.checkout_com_payment_link || '',
      },
    };
  }

  function financialPercentage(pattern, fallback) {
    const row = (operatingModel().financial_targets || []).find((item) => pattern.test(String(item?.name || '')));
    const value = Number(row?.target_value);
    return Number.isFinite(value) && value >= 0 && value < 100 ? value : fallback;
  }

  function quotePricingPolicy() {
    return {
      targetMargin: financialPercentage(/target gross margin/i, 60),
      minimumMargin: financialPercentage(/minimum acceptable (?:gross )?margin|minimum gross margin/i, 45),
      rules: Array.isArray(operatingModel().pricing_rules) ? operatingModel().pricing_rules : [],
    };
  }

  function categoryPricing(category, cost) {
    const policy = quotePricingPolicy();
    const aliases = category === 'external' ? ['external','supplier_subcontractor','subcontractor'] : [category];
    const rule = policy.rules.find((item) => aliases.includes(String(item?.category || item?.applies_to || '').toLowerCase()))
      || policy.rules.find((item) => ['all','default',''].includes(String(item?.category || item?.applies_to || '').toLowerCase()));
    const method = String(rule?.rule_type || (rule?.markup_percent != null ? 'cost_plus' : 'target_margin'));
    const percentage = method === 'cost_plus' ? Number(rule?.markup_percent) : Number(rule?.target_margin_percent);
    const applied = Number.isFinite(percentage) && percentage >= 0 ? percentage : policy.targetMargin;
    const amount = method === 'cost_plus'
      ? cost * (1 + applied / 100)
      : cost / Math.max(0.05, 1 - Math.min(applied, 95) / 100);
    return { category, cost, amount: Math.round((amount + Number.EPSILON) * 100) / 100, method, percentage: applied, rule: rule?.name || 'Board-approved target margin' };
  }

  function quoteRecommendation(costs = {}) {
    const lines = [
      categoryPricing('materials', moneyNumber(costs.materials)),
      categoryPricing('labour', moneyNumber(costs.labour)),
      categoryPricing('external', moneyNumber(costs.external)),
    ];
    const totalCost = lines.reduce((sum, line) => sum + line.cost, 0);
    const suggestedPrice = lines.reduce((sum, line) => sum + line.amount, 0);
    const policy = quotePricingPolicy();
    return { lines, totalCost, suggestedPrice: Math.round((suggestedPrice + Number.EPSILON) * 100) / 100, ...policy };
  }

  function grossMargin(cost, price) {
    return price > 0 ? Math.round((((price - cost) / price) * 100 + Number.EPSILON) * 100) / 100 : 0;
  }

  function quoteLineTypes(selected = '') {
    return ['Service','Materials','Labour','Equipment','Subcontractor','Travel','Discount','Other']
      .map((value) => `<option value="${value.toLowerCase()}" ${String(selected).toLowerCase() === value.toLowerCase() ? 'selected' : ''}>${value}</option>`).join('');
  }

  function labourRateProfile(person, basis, rate) {
    const costing = person?.workforce_costing || {};
    const hoursPerDay = moneyNumber(costing.hours_per_day) || 8;
    const hourly = moneyNumber(costing.effective_hourly_cost) || (basis === 'hourly' ? rate : basis === 'daily' ? rate / hoursPerDay : 0);
    const daily = moneyNumber(costing.effective_daily_cost) || (basis === 'daily' ? rate : hourly * hoursPerDay);
    const monthly = moneyNumber(costing.effective_monthly_cost) || (basis === 'monthly' ? rate : 0);
    const perJob = basis === 'per_job' ? rate : 0;
    return { hourly, daily, monthly, perJob, hoursPerDay };
  }

  function labourPeople() {
    hydrateLabourDirectory();
    const operatingWorkspace = global.AionOperatingModelWorkspace;
    if (!operatingWorkspace?.state?.loaded && !operatingWorkspace?.state?.loading) operatingWorkspace?.load?.();
    if (!global.AionHrPeopleWorkspace?.state?.model) global.AionHrPeopleWorkspace?.ensureDashboardData?.();
    const people = [
      ...(global.AionHrPeopleWorkspace?.state?.model?.people || []),
      ...(operatingWorkspace?.state?.people || []),
      ...(labourDirectoryCache?.people || []),
    ].filter((person, index, all) => person?.status === 'active' && all.findIndex((candidate) => String(candidate?.id) === String(person.id)) === index);
    const byId = new Map(people.map((person) => [String(person.id), person]));
    const resources = [
      ...(Array.isArray(operatingModel().labour_resources) ? operatingModel().labour_resources : []),
      ...(labourDirectoryCache?.resources || []),
    ].filter((resource, index, all) => all.findIndex((candidate) => String(candidate?.id || candidate?.person_id) === String(resource?.id || resource?.person_id)) === index);
    const rows = resources.map((resource) => {
      const person = byId.get(String(resource.person_id || '')) || {};
      const costing = person.workforce_costing || {};
      const basis = String(resource.cost_basis || costing.basis || 'hourly').toLowerCase();
      const rate = moneyNumber(resource.cost_rate ?? resource.planning_rate ?? (basis === 'daily' ? costing.effective_daily_cost : costing.effective_hourly_cost) ?? costing.base_rate);
      const name = resource.person_name || person.name || 'Worker';
      return { id:String(resource.id || resource.person_id || name), person_id:String(resource.person_id || ''), name, basis, rate, ...labourRateProfile(person, basis, rate) };
    });
    people.forEach((person) => {
      if (rows.some((row) => row.person_id && row.person_id === String(person.id))) return;
      const costing = person.workforce_costing || {};
      const basis = String(costing.basis || 'hourly').toLowerCase();
      const rate = moneyNumber(basis === 'daily' ? costing.effective_daily_cost : costing.effective_hourly_cost) || moneyNumber(costing.base_rate);
      rows.push({ id:String(person.id), person_id:String(person.id), name:person.name || 'Worker', basis, rate, ...labourRateProfile(person, basis, rate) });
    });
    return rows.filter((row, index) => row.name && rows.findIndex((candidate) => candidate.name === row.name && candidate.basis === row.basis) === index);
  }

  function labourPersonSelect(child) {
    const people = labourPeople();
    const selected = String(child.labour_resource_id || child.person_id || '');
    return `<label class="ws-labour-person">Person / contractor<select data-ws-labour-person><option value="">Manual labour cost</option>${people.map((person) => `<option value="${esc(person.id)}" data-name="${esc(person.name)}" data-rate="${esc(person.rate)}" data-basis="${esc(person.basis)}" data-hourly="${esc(person.hourly)}" data-daily="${esc(person.daily)}" data-monthly="${esc(person.monthly)}" data-perjob="${esc(person.perJob)}" ${selected === person.id ? 'selected' : ''}>${esc(person.name)} · ${person.rate ? `${person.rate.toFixed(2)} / ${person.basis === 'daily' ? 'day' : person.basis === 'monthly' ? 'month' : person.basis === 'per_job' ? 'job' : 'hour'}` : 'rate not set'}</option>`).join('')}</select></label>`;
  }

  function labourBasisSelect(child) {
    const selected = String(child.rate_basis || 'hourly');
    return `<label class="ws-labour-basis">Rate basis<select data-ws-labour-basis><option value="hourly" ${selected === 'hourly' ? 'selected' : ''}>Hourly</option><option value="daily" ${selected === 'daily' ? 'selected' : ''}>Day rate</option><option value="per_job" ${selected === 'per_job' ? 'selected' : ''}>Per job</option></select></label>`;
  }

  function defaultQuoteLines(item) {
    const estimate = item?.cost_estimate || {};
    const costs = [
      ['Materials','materials',moneyNumber(estimate.material_cost)],
      ['Labour','labour',moneyNumber(estimate.labour_cost)],
      ['External costs','external',moneyNumber(estimate.external_cost)],
    ].filter(([, , cost]) => cost > 0);
    const children = costs.map(([description, type, cost]) => {
      const pricing = categoryPricing(type, cost);
      return { id:uid('calc'), description, type, quantity:1, cost_price:cost, margin_percent:pricing.method === 'cost_plus' ? grossMargin(cost, pricing.amount) : pricing.percentage };
    });
    const existing = Array.isArray(item?.quote?.line_items) ? item.quote.line_items : [];
    if (existing.length) return existing.map((row) => ({ id:uid('line'), description:row.description || item.title, type:row.type || 'service', quantity:moneyNumber(row.quantity) || 1, unit_price:moneyNumber(row.unit_price), vat_rate:moneyNumber(row.tax_rate ?? item.quote?.tax_rate ?? 20), children:[] }));
    return [{ id:uid('line'), description:item?.title || 'Work', type:'service', quantity:1, unit_price:moneyNumber(item?.quote?.subtotal || item?.quote?.amount), vat_rate:20, children }];
  }

  function quoteDraftLines(item) {
    item.quote = item.quote || { status:'draft' };
    if (!Array.isArray(item.quote.draft_lines) || !item.quote.draft_lines.length) item.quote.draft_lines = defaultQuoteLines(item);
    return item.quote.draft_lines;
  }

  function childSellTotal(child) {
    const quantity = Math.max(0, moneyNumber(child.quantity) || 1);
    const cost = Math.max(0, moneyNumber(child.cost_price));
    const margin = Math.min(95, Math.max(0, moneyNumber(child.margin_percent)));
    return quantity * cost / Math.max(0.05, 1 - margin / 100);
  }

  function grossMarginExplanation(child) {
    const identity = quoteIdentity();
    const quantity = Math.max(0, moneyNumber(child.quantity) || 1);
    const cost = quantity * Math.max(0, moneyNumber(child.cost_price));
    const margin = Math.min(95, Math.max(0, moneyNumber(child.margin_percent)));
    if (!(cost > 0)) {
      return 'Gross margin is the percentage of the selling price left after this cost. It is different from markup.';
    }
    const sell = childSellTotal(child);
    const markupSell = cost * (1 + margin / 100);
    const costShare = Math.max(5, 100 - margin);
    return `${identity.currency} ${cost.toFixed(2)} cost ÷ ${costShare.toFixed(2).replace(/\.00$/, '')}% = ${identity.currency} ${sell.toFixed(2)} sell. A ${margin.toFixed(2).replace(/\.00$/, '')}% markup would instead be ${identity.currency} ${markupSell.toFixed(2)}.`;
  }

  function parentLineTotal(parent) {
    const children = Array.isArray(parent.children) ? parent.children : [];
    return children.length ? children.reduce((sum, child) => sum + childSellTotal(child), 0) : Math.max(0, moneyNumber(parent.quantity) || 1) * Math.max(0, moneyNumber(parent.unit_price));
  }

  function quoteTotals(item) {
    const lines = quoteDraftLines(item);
    const customerAmounts = lines.map((line) => Math.round((parentLineTotal(line) + Number.EPSILON) * 100) / 100);
    const subtotal = customerAmounts.reduce((sum, amount) => sum + amount, 0);
    const tax = lines.reduce((sum, line, index) => sum + customerAmounts[index] * Math.max(0, moneyNumber(line.vat_rate)) / 100, 0);
    return { lines, subtotal, tax, total:subtotal + tax };
  }

  function quotePaymentReference(item) {
    const identity = quoteIdentity();
    const number = item?.quote?.number || 'QUOTE-NUMBER';
    return String(identity.paymentReferenceTemplate || '{quote_number}').replaceAll('{quote_number}', number);
  }

  function defaultPaymentSchedule(item, preset = 'unplanned') {
    const deposit = quoteIdentity().defaultDepositPercent;
    if (preset === 'upfront') return [{ id:uid('stage'), label:'Full payment', amount_type:'percent', amount_value:100, due_type:'acceptance', due_value:'' }];
    if (preset === 'phased') return [
      { id:uid('stage'), label:'First payment', amount_type:'fixed', amount_value:'', due_type:'acceptance', due_value:'' },
      { id:uid('stage'), label:'Progress payment', amount_type:'fixed', amount_value:'', due_type:'days', due_value:'' },
      { id:uid('stage'), label:'Final balance', amount_type:'balance', amount_value:'', due_type:'completion', due_value:'' },
    ];
    if (preset === 'deposit') return [
      { id:uid('stage'), label:'Deposit', amount_type:'percent', amount_value:deposit == null ? '' : deposit, due_type:'acceptance', due_value:'' },
      { id:uid('stage'), label:'Final balance', amount_type:'balance', amount_value:'', due_type:'completion', due_value:'' },
    ];
    return [
      { id:uid('stage'), label:'Payment', amount_type:'fixed', amount_value:'', due_type:'acceptance', due_value:'' },
    ];
  }

  function paymentSchedule(item) {
    item.quote = item.quote || { status:'draft' };
    if (!Array.isArray(item.quote.payment_schedule) || !item.quote.payment_schedule.length) item.quote.payment_schedule = defaultPaymentSchedule(item);
    return item.quote.payment_schedule;
  }

  function paymentStageAmounts(item) {
    const total = quoteTotals(item).total;
    let allocated = 0;
    return paymentSchedule(item).map((stage) => {
      let amount = stage.amount_type === 'fixed' ? moneyNumber(stage.amount_value) : stage.amount_type === 'percent' ? total * moneyNumber(stage.amount_value) / 100 : 0;
      if (stage.amount_type === 'balance') amount = Math.max(0, total - allocated);
      allocated += amount;
      return { ...stage, calculated_amount:Math.round((amount + Number.EPSILON) * 100) / 100 };
    });
  }

  function dueText(stage) {
    if (stage.due_type === 'acceptance') return 'When the quote is accepted';
    if (stage.due_type === 'completion') return 'On completion';
    if (stage.due_type === 'date') return stage.due_value ? `On ${stage.due_value}` : 'Choose a date';
    if (stage.due_type === 'days') return `${moneyNumber(stage.due_value) || 0} days after acceptance`;
    return 'Due date to be agreed';
  }

  function renderPaymentPlan(item) {
    const identity = quoteIdentity();
    const stages = paymentStageAmounts(item);
    const total = quoteTotals(item).total;
    const scheduled = stages.reduce((sum, stage) => sum + stage.calculated_amount, 0);
    const difference = Math.round((total - scheduled + Number.EPSILON) * 100) / 100;
    const missingAmount = stages.some((stage) => stage.amount_type !== 'balance' && !(moneyNumber(stage.amount_value) > 0));
    const method = item.quote?.payment_method || identity.paymentMethod;
    const onlineMethods = ['stripe','paypal','square','gocardless','revolut','sumup','mollie','braintree','worldpay','adyen','checkout_com'];
    const providerName = { stripe:'Stripe', paypal:'PayPal', square:'Square', gocardless:'GoCardless', revolut:'Revolut Business', sumup:'SumUp', mollie:'Mollie', braintree:'Braintree', worldpay:'Worldpay', adyen:'Adyen', checkout_com:'Checkout.com' }[method] || 'online payment provider';
    const providerMissing = onlineMethods.includes(method) && !identity.paymentLinks?.[method];
    return `<article class="ws-payment-plan"><header><div><span>PAYMENT PLAN</span><strong>Choose when the customer pays</strong><p>Set one payment, a deposit and balance, or phased payments. The quote number is used as the payment reference.</p></div><div class="ws-payment-presets"><button type="button" data-ws-payment-preset="upfront">All upfront</button><button type="button" data-ws-payment-preset="deposit">Deposit + balance</button><button type="button" data-ws-payment-preset="phased">Phased payments</button></div></header><label class="ws-payment-method">How can the customer pay?<select data-ws-payment-method-choice="${esc(item.id)}"><option value="bank_transfer" ${method === 'bank_transfer' ? 'selected' : ''}>Bank transfer</option><option value="stripe" ${method === 'stripe' ? 'selected' : ''}>Stripe</option><option value="paypal" ${method === 'paypal' ? 'selected' : ''}>PayPal</option><option value="square" ${method === 'square' ? 'selected' : ''}>Square</option><option value="gocardless" ${method === 'gocardless' ? 'selected' : ''}>GoCardless</option><option value="customer_choice" ${method === 'customer_choice' ? 'selected' : ''}>Customer chooses bank or online</option></select></label>${providerMissing ? `<div class="ws-payment-warning"><strong>${providerName} is not connected.</strong><span>Connect ${providerName} under Connections → Payments, or save its hosted payment link under Business → Financial Information.</span></div>` : ''}<div class="ws-payment-stages">${stages.map((stage, index) => `<div class="ws-payment-stage" data-ws-payment-stage="${esc(stage.id)}"><b>${index + 1}</b><input aria-label="Payment stage name" data-ws-payment-stage-field="label" value="${esc(stage.label)}"><select aria-label="Amount type" data-ws-payment-stage-field="amount_type"><option value="percent" ${stage.amount_type === 'percent' ? 'selected' : ''}>Percent</option><option value="fixed" ${stage.amount_type === 'fixed' ? 'selected' : ''}>Fixed amount</option><option value="balance" ${stage.amount_type === 'balance' ? 'selected' : ''}>Remaining balance</option></select><input aria-label="Payment amount" type="number" min="0" step="0.01" data-ws-payment-stage-field="amount_value" value="${esc(stage.amount_value)}" placeholder="Enter amount" ${stage.amount_type === 'balance' ? 'disabled' : ''}><select aria-label="Payment due" data-ws-payment-stage-field="due_type"><option value="acceptance" ${stage.due_type === 'acceptance' ? 'selected' : ''}>On acceptance</option><option value="days" ${stage.due_type === 'days' ? 'selected' : ''}>Days after acceptance</option><option value="date" ${stage.due_type === 'date' ? 'selected' : ''}>Specific date</option><option value="completion" ${stage.due_type === 'completion' ? 'selected' : ''}>On completion</option></select><input aria-label="Due value" data-ws-payment-stage-field="due_value" value="${esc(stage.due_value)}" placeholder="${stage.due_type === 'date' ? 'YYYY-MM-DD' : stage.due_type === 'days' ? 'Days' : 'Not needed'}" ${['acceptance','completion'].includes(stage.due_type) ? 'disabled' : ''}><strong>${esc(identity.currency)} ${esc(stage.calculated_amount.toFixed(2))}</strong><button type="button" title="Remove payment stage" data-ws-remove-payment-stage="${esc(stage.id)}">×</button></div>`).join('')}</div><button type="button" class="ws-add-payment-stage" data-ws-add-payment-stage="${esc(item.id)}">+ Add payment stage</button><footer><span>Payment reference <b>${esc(quotePaymentReference(item))}</b></span><span class="${missingAmount || Math.abs(difference) > 0.01 ? 'warning' : ''}">${missingAmount ? 'Enter each payment amount or percentage' : Math.abs(difference) > 0.01 ? `${difference > 0 ? 'Unallocated' : 'Over-allocated'} ${identity.currency} ${Math.abs(difference).toFixed(2)}` : `Scheduled total ${identity.currency} ${scheduled.toFixed(2)}`}</span></footer></article>`;
  }

  function renderQuoteBuilder(item) {
    const { lines, subtotal, tax, total } = quoteTotals(item);
    const rewriteState = state.ui.descriptionRewrite?.itemId === item.id ? state.ui.descriptionRewrite : {};
    return `<article class="ws-quote-builder"><header><div><span>INTERNAL QUOTE BUILDER</span><strong>Build the price, then create a clean customer draft</strong><p>Black rows are shown to the customer. Blue calculation rows are private workings and are rolled into their parent line.</p></div></header><label class="ws-quote-description"><span>Description of work shown to the customer</span><textarea rows="5" data-ws-quote-description="${esc(item.id)}" placeholder="Write your rough description here. Spelling and wording do not need to be perfect.">${esc(item.quote?.description_of_work || '')}</textarea><div class="ws-description-actions"><button type="button" data-ws-rewrite-description="${esc(item.id)}" ${rewriteState.status === 'working' ? 'disabled' : ''}>${rewriteState.status === 'working' ? 'Rewriting with the local model…' : 'Rewrite professionally with SI'}</button><small>This appears on the quotation and PDF. SI corrects the writing but does not add work you did not describe. Review and edit it before sending.</small></div>${rewriteState.status === 'error' ? `<small class="error">${esc(rewriteState.error)}</small>` : rewriteState.status === 'done' ? '<small class="success">Professional draft added. Please review it before saving or sending.</small>' : ''}</label><div class="ws-quote-builder-table"><div class="ws-quote-builder-head"><span>Description</span><span>Type</span><span>Qty</span><span>VAT %</span><span>Customer total</span><span></span></div>${lines.map((line) => `<section class="ws-quote-parent" data-ws-quote-line="${esc(line.id)}"><div class="ws-quote-parent-row"><input aria-label="Customer description" data-ws-quote-parent-field="description" value="${esc(line.description)}"><select aria-label="Line type" data-ws-quote-parent-field="type">${quoteLineTypes(line.type)}</select><input aria-label="Quantity" type="number" min="0" step="0.01" data-ws-quote-parent-field="quantity" value="${esc(line.quantity || 1)}"><input aria-label="VAT percentage" type="number" min="0" step="0.01" data-ws-quote-parent-field="vat_rate" value="${esc(line.vat_rate ?? 20)}"><strong>${esc(parentLineTotal(line).toFixed(2))}</strong><button type="button" title="Remove line" data-ws-remove-quote-line="${esc(line.id)}">×</button></div><div class="ws-quote-children">${(line.children || []).map((child) => `<div class="ws-quote-child-wrap"><div class="ws-quote-child ${String(child.type).toLowerCase() === 'labour' ? 'is-labour' : ''}" data-ws-quote-child="${esc(child.id)}"><span>INTERNAL · HIDDEN FROM CUSTOMER</span><input aria-label="Working description" data-ws-quote-child-field="description" value="${esc(child.description)}"><select aria-label="Cost type" data-ws-quote-child-field="type">${quoteLineTypes(child.type)}</select>${String(child.type).toLowerCase() === 'labour' ? `${labourPersonSelect(child)}${labourBasisSelect(child)}` : ''}<label>${String(child.type).toLowerCase() === 'labour' ? (child.rate_basis === 'daily' ? 'Days' : child.rate_basis === 'monthly' ? 'Months' : child.rate_basis === 'per_job' ? 'Jobs' : 'Hours') : 'Quantity'}<input aria-label="Quantity" type="number" min="0" step="0.01" data-ws-quote-child-field="quantity" value="${esc(child.quantity || 1)}"></label><label>${String(child.type).toLowerCase() === 'labour' ? 'Cost rate' : 'Cost price'}<input type="number" min="0" step="0.01" data-ws-quote-child-field="cost_price" value="${esc(child.cost_price || '')}"></label><label>Gross margin %<input type="number" min="0" max="95" step="0.01" data-ws-quote-child-field="margin_percent" value="${esc(child.margin_percent ?? quotePricingPolicy().targetMargin)}"></label><b>Sell ${esc(childSellTotal(child).toFixed(2))}</b><button type="button" title="Remove internal working" data-ws-remove-quote-child="${esc(child.id)}">×</button></div><small class="ws-margin-explanation">${esc(grossMarginExplanation(child))}</small></div>`).join('')}</div><button type="button" class="ws-add-working" data-ws-add-quote-child="${esc(line.id)}">+ Add private cost / working</button></section>`).join('')}<div class="ws-add-quote-line-row"><button type="button" class="primary" data-ws-add-quote-line="${esc(item.id)}">+ Add another customer quote line</button><small>Use a new line for the next customer-facing section, then add its private costs underneath.</small></div></div><footer><span>Draft subtotal <b>${esc(subtotal.toFixed(2))}</b></span><span>VAT <b>${esc(tax.toFixed(2))}</b></span><span>Total <b>${esc(total.toFixed(2))}</b></span></footer></article>`;
  }

  function mondayOf(date) {
    const result = new Date(date);
    const day = result.getDay() || 7;
    result.setDate(result.getDate() - day + 1);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  function makeInitialData() {
    const monday = mondayOf(new Date());
    const day = (offset) => {
      const value = new Date(monday);
      value.setDate(value.getDate() + offset);
      return isoDate(value);
    };
    return {
      revision: 1,
      items: [
        {
          id: 'sample_roof_installation', sample: true, title: 'New roof installation', customer: 'Client example',
          type: 'job', status: 'scheduled', date: day(1), time: '08:30', duration: 420,
          assignee: 'Kevin Robinson + team', location: 'Customer site', source: 'Back office',
          notes: 'Materials and access to be confirmed before arrival.', documents: [], updates: [],
          quote: { status: 'approved', amount: '4850.00' }, invoice: { status: 'not_created', amount: '' }
        },
        {
          id: 'sample_quote_visit', sample: true, title: 'Roof survey and quote', customer: 'New website enquiry',
          type: 'survey', status: 'quote_required', date: day(2), time: '10:00', duration: 90,
          assignee: 'James Double', location: 'Customer site', source: 'Website booking',
          notes: 'Customer uploaded two photographs with the booking.', documents: ['roof-photo-1.jpg', 'roof-photo-2.jpg'], updates: [],
          quote: { status: 'not_created', amount: '' }, invoice: { status: 'not_created', amount: '' }
        },
        {
          id: 'sample_consultation', sample: true, title: 'Client consultation', customer: 'Prospective client',
          type: 'appointment', status: 'scheduled', date: day(4), time: '14:00', duration: 60,
          assignee: 'Rebecca Newman', location: 'Video meeting', source: 'Sales agent',
          notes: 'Discuss requirements and agree the next action.', documents: [], updates: [],
          quote: { status: 'not_created', amount: '' }, invoice: { status: 'not_created', amount: '' }
        }
      ],
      intake: [
        { id: 'intake_website', channel: 'Website', title: 'Request for an estimate', customer: 'Website visitor', received: '12 minutes ago', state: 'Needs review' },
        { id: 'intake_phone', channel: 'Agent', title: 'Call-back and availability request', customer: 'New lead', received: 'Today', state: 'Ready to schedule' }
      ]
    };
  }

  function loadData() {
    try {
      const parsed = JSON.parse(global.localStorage?.getItem(STORAGE_KEY) || 'null');
      if (parsed && Array.isArray(parsed.items) && Array.isArray(parsed.intake)) return parsed;
    } catch (_) {}
    const initial = makeInitialData();
    return initial;
  }

  function loadUi() {
    if (global.__aionWorkScheduleUiState && typeof global.__aionWorkScheduleUiState === 'object') {
      return { ...global.__aionWorkScheduleUiState };
    }
    try {
      const parsed = JSON.parse(global.localStorage?.getItem(UI_KEY) || 'null');
      if (parsed && typeof parsed === 'object') {
        global.__aionWorkScheduleUiState = { ...parsed };
        global.localStorage?.removeItem(UI_KEY);
        return parsed;
      }
    } catch (_) {}
    return { view: 'calendar', week: isoDate(mondayOf(new Date())), selectedId: '', panelTab: 'overview', modal: '' };
  }

  const state = { data: loadData(), ui: loadUi(), hydrated: false, syncing: false, syncPending: false, syncError: '', conflicts: [] };
  let signatureDrawing = null;
  const workspaceId = () => String(global.AionBusinessContainerClient?.resolveBusinessId?.() || global.__aionDesktopState?.workspaceId || global.state?.activeWorkspaceId || 'home-fixed');
  const endpoint = (suffix = '') => `${API_BASE}/api/aion/business/work-schedule/${encodeURIComponent(workspaceId())}${suffix}`;
  const applyModel = (model) => {
    if (!model || !Array.isArray(model.items)) return;
    state.data = model;
    state.data.intake = Array.isArray(model.intake) ? model.intake : [];
    state.conflicts = Array.isArray(model.conflicts) ? model.conflicts : [];
  };
  async function syncToBackend() {
    if (!state.hydrated) return;
    if (state.syncing) { state.syncPending = true; return; }
    state.syncing = true; state.syncError = '';
    try {
      const response = await fetch(endpoint(), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: state.data, changed_by: 'desktop_user' }) });
      const payload = await response.json();
      if (!response.ok || payload.ok === false) throw new Error(payload.detail || payload.error || 'Shared schedule could not be saved');
      applyModel(payload.model);
      try { global.localStorage?.removeItem(STORAGE_KEY); } catch (_) {}
    } catch (error) { state.syncError = String(error?.message || error); }
    finally {
      state.syncing = false; rerender();
      if (state.syncPending) { state.syncPending = false; void syncToBackend(); }
    }
  }
  async function hydrate() {
    if (state.hydrated) return;
    state.hydrated = true;
    try {
      const response = await fetch(endpoint()); const payload = await response.json();
      if (!response.ok || !payload.model) throw new Error(payload.detail || 'Shared schedule is unavailable');
      if (Number(payload.model.revision || 0) === 0) {
        const localItems = (state.data.items || []).filter((item) => !item.sample);
        if (localItems.length || (state.data.intake || []).some((item) => !String(item.id || '').startsWith('intake_website') && !String(item.id || '').startsWith('intake_phone'))) {
          state.data.items = localItems; await syncToBackend();
        } else applyModel(payload.model);
      } else applyModel(payload.model);
    } catch (error) { state.syncError = String(error?.message || error); }
    rerender();
  }
  async function refreshFromBackend() {
    if (!state.hydrated || state.syncing || document.hidden) return;
    try {
      const response = await fetch(endpoint());
      const payload = await response.json();
      if (!response.ok || !payload.model) return;
      if (Number(payload.model.revision || 0) > Number(state.data.revision || 0)) {
        applyModel(payload.model);
        rerender();
      }
    } catch (_) {}
  }
  const persist = () => {
    state.data.revision = Number(state.data.revision || 0) + 1;
    void syncToBackend();
  };
  const persistUi = () => {
    global.__aionWorkScheduleUiState = { ...state.ui };
  };
  const rerender = () => {
    persistUi();
    if (typeof global.requestRender === 'function') global.requestRender();
    else if (typeof global.render === 'function') global.render();
  };
  async function hydrateGmailHealth() {
    if (gmailHealthLoading || gmailHealthChecked) return;
    // The Local Node health endpoint still opens legacy SQLite registries as a
    // side effect. Discovery journeys qualify customer-data writes, so do not
    // let a passive status decoration contaminate an unrelated journey. The
    // explicit connector journey continues to exercise the endpoint itself.
    if (global.aionDesktop?.businessDataDiscoveryEnabled === true) {
      gmailHealthSnapshot = global.__aionGmailHealth || { connected:false };
      gmailHealthChecked = true;
      return;
    }
    gmailHealthLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/local-node/connectors/gmail/health`);
      const payload = await response.json();
      const authStatus = String(payload?.auth_status || '').toLowerCase();
      const connectorHealth = String(payload?.connector_health || '').toLowerCase();
      gmailHealthSnapshot = {
        ...payload,
        connected: authStatus === 'connected' && ['available', 'connected', 'healthy'].includes(connectorHealth),
      };
      global.__aionGmailHealth = gmailHealthSnapshot;
    } catch (_) {
      gmailHealthSnapshot = global.__aionGmailHealth || { connected:false };
    } finally {
      gmailHealthLoading = false;
      gmailHealthChecked = true;
      rerender();
    }
  }
  const workItem = (id) => state.data.items.find((item) => String(item.id) === String(id));
  const customerRecord = (id, name = '') => (state.data.customers || []).find((customer) =>
    (id && String(customer.id) === String(id)) || (!id && name && String(customer.name || '').toLowerCase() === String(name).toLowerCase())
  );
  const customerForItem = (item) => {
    const customer = customerRecord(item?.customer_id, item?.customer) || {};
    return {
      id: customer.id || item?.customer_id || '',
      name: customer.name || item?.customer || '',
      email: customer.email || item?.customer_email || '',
      phone: customer.phone || item?.customer_phone || '',
      address: customer.billing_address || customer.address || item?.customer_address || item?.location || '',
      serviceAddress: customer.service_address || item?.location || '',
    };
  };
  const addUpdate = (item, text) => {
    item.updates = [...(item.updates || []), { text, at: new Date().toLocaleString() }];
  };
  const readBase64 = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || '').split(',', 2)[1] || '');
    reader.onerror = () => reject(reader.error || new Error('File could not be read'));
    reader.readAsDataURL(file);
  });
  async function apiPost(url, body) {
    const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.detail || payload.error || 'The request could not be completed');
    return payload;
  }

  function statusBadge(status) {
    return `<span class="ws-status ws-status-${esc(status)}">${esc(titleCase(status))}</span>`;
  }

  function formatDay(date) {
    return new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short' }).format(date);
  }

  function renderHeader() {
    const items = state.data.items;
    const scheduled = items.filter((item) => ['scheduled', 'en_route', 'in_progress', 'paused'].includes(item.status)).length;
    const unscheduled = items.filter((item) => !item.date).length + state.data.intake.length;
    const quotes = items.filter((item) => ['quote_required', 'awaiting_approval'].includes(item.status)).length;
    const active = items.filter((item) => !['completed', 'invoiced', 'paid'].includes(item.status)).length;
    return `<header class="ws-header">
      <div><span>WORK · BOOKINGS · DELIVERY</span><h1>Work &amp; Schedule</h1><p>One record from the first customer request through scheduling, work on site, evidence, quote and invoice.</p></div>
      <div class="ws-header-actions"><span class="ws-sync-state ${state.syncError ? 'error' : ''}">${state.syncError ? `Not synced · ${esc(state.syncError)}` : state.syncing ? 'Saving…' : state.hydrated ? 'Shared with mobile' : 'Connecting…'}</span><button type="button" data-ws-open-intake>Review intake <b>${state.data.intake.length}</b></button><button type="button" data-ws-new-customer>+ Customer</button><button type="button" class="primary" data-ws-new>+ New work</button></div>
      <div class="ws-metrics"><article><b>${scheduled}</b><span>Scheduled</span></article><article><b>${unscheduled}</b><span>Needs scheduling</span></article><article><b>${quotes}</b><span>Quotes requiring action</span></article><article><b>${active}</b><span>Open work</span></article></div>
    </header>`;
  }

  function renderViewTabs() {
    const tabs = [['calendar', 'Calendar'], ['board', 'Job board'], ['field', 'Field workspace'], ['intake', 'Booking inbox'], ['customers', 'Customers'], ['reminders', 'Reminders'], ['stock', 'Stock & materials']];
    return `<nav class="ws-view-tabs" aria-label="Work and Schedule views">${tabs.map(([key, label]) => `<button type="button" class="${state.ui.view === key ? 'active' : ''}" data-ws-view="${key}">${label}${key === 'intake' ? `<span>${state.data.intake.length}</span>` : ''}</button>`).join('')}</nav>`;
  }

  function renderCalendar() {
    const start = mondayOf(dateFromIso(state.ui.week));
    const days = Array.from({ length: 7 }, (_, index) => {
      const value = new Date(start);
      value.setDate(value.getDate() + index);
      return value;
    });
    const end = days[6];
    const range = `${new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'long' }).format(start)} – ${new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'long', year: 'numeric' }).format(end)}`;
    return `<section class="ws-calendar-panel">
      <header class="ws-calendar-toolbar"><div><span>WEEKLY SCHEDULE</span><h2>${esc(range)}</h2></div><div><button type="button" data-ws-week="prev">‹</button><button type="button" data-ws-week="today">Today</button><button type="button" data-ws-week="next">›</button></div></header>
      <div class="ws-calendar-grid">${days.map((date) => {
        const key = isoDate(date);
        const entries = state.data.items.filter((item) => item.date === key).sort((a, b) => String(a.time).localeCompare(String(b.time)));
        const today = key === isoDate(new Date());
        return `<section class="ws-calendar-day ${today ? 'today' : ''}" data-ws-drop-date="${key}"><header><span>${esc(formatDay(date))}</span><button type="button" data-ws-new-date="${key}" aria-label="Add work on ${esc(formatDay(date))}">+</button></header><div class="ws-day-items">${entries.map((item) => `<button type="button" draggable="true" class="ws-calendar-card ws-kind-${esc(item.type)}" data-ws-item="${esc(item.id)}"><time>${esc(item.time || 'All day')}</time><strong>${esc(item.title)}</strong><small>${esc(item.customer || 'No customer')}</small><em>${esc(item.assignee || 'Unassigned')}</em>${item.sample ? '<i>Sample</i>' : ''}</button>`).join('') || `<button type="button" class="ws-empty-day" data-ws-new-date="${key}">Schedule work</button>`}</div></section>`;
      }).join('')}</div>
      <footer class="ws-calendar-footer"><span><i class="job"></i> Job</span><span><i class="appointment"></i> Appointment</span><span><i class="survey"></i> Survey / quote</span><small>Drag a card to another day. ${state.conflicts.length ? `${state.conflicts.length} scheduling clash${state.conflicts.length === 1 ? '' : 'es'} need attention.` : 'No resource clashes detected.'}</small></footer>
    </section>`;
  }

  function renderBoard() {
    const lanes = [
      ['new', 'New / unscheduled'], ['quote_required', 'Quote required'], ['awaiting_approval', 'Quote sent / awaiting acceptance'], ['awaiting_payment', 'Awaiting payment'],
      ['scheduled', 'Scheduled'], ['active_work', 'In progress / travelling'], ['completed', 'Completed']
    ];
    return `<section class="ws-board"><header><div><span>DELIVERY PIPELINE</span><h2>Job board</h2></div><p>Move every work item from request to completion without losing the customer, schedule or evidence.</p></header><div class="ws-board-lanes">${lanes.map(([status, label]) => {
      const rows = state.data.items.filter((item) => item.status === status || (status === 'active_work' && ['en_route', 'in_progress', 'paused'].includes(item.status)) || (status === 'completed' && ['completed', 'invoiced', 'paid'].includes(item.status)));
      return `<section class="ws-board-lane"><header><strong>${label}</strong><span>${rows.length}</span></header>${rows.map((item) => {
        const accepted = item.quote?.status === 'customer_approved';
        const paymentProblem = ['payment_configuration_required', 'delivery_failed'].includes(item.payment_request?.status);
        return `<button type="button" data-ws-item="${esc(item.id)}"><small>${esc(TYPE_LABELS[item.type] || titleCase(item.type))}${item.date ? ` · ${esc(item.date)}` : ''}</small><div class="ws-board-card-flags">${accepted ? '<strong class="accepted">✓ Accepted</strong>' : ''}${paymentProblem ? `<strong class="attention">${item.payment_request?.status === 'payment_configuration_required' ? 'Payment setup required' : 'Invoice delivery failed'}</strong>` : ''}</div><b>${esc(item.title)}</b><span>${esc(item.customer)}</span>${item.quote?.status === 'sent' ? '<strong>Quotation sent · waiting for customer</strong>' : ''}<em>${esc(item.assignee || 'Unassigned')}</em></button>`;
      }).join('') || '<p>No work here</p>'}</section>`;
    }).join('')}</div></section>`;
  }

  function renderIntake() {
    return `<section class="ws-intake"><header><div><span>INBOUND REQUESTS</span><h2>Booking inbox</h2><p>Website bookings, calls, emails and agent-created requests arrive here for review before they become scheduled work.</p></div><button type="button" data-ws-new>+ Add request</button></header><div class="ws-intake-list">${state.data.intake.map((item) => `<article><div class="ws-channel">${esc(item.channel)}</div><div><strong>${esc(item.title)}</strong><span>${esc(item.customer)} · ${esc(item.received)}</span></div><small>${esc(item.state)}</small><button type="button" data-ws-convert-intake="${esc(item.id)}">Review request</button></article>`).join('') || '<div class="ws-empty"><strong>Inbox clear</strong><span>No booking requests are waiting for review.</span></div>'}</div></section>`;
  }

  function renderCustomers() {
    const customers = Array.isArray(state.data.customers) ? state.data.customers : [];
    return `<section class="ws-customers"><header><div><span>CUSTOMER RECORDS</span><h2>Customers and their work</h2><p>Contact details are saved once and reused for bookings, quotes, invoices and messages.</p></div><button type="button" class="primary" data-ws-new-customer>+ Customer</button></header><div>${customers.map((customer) => { const items=(customer.work_item_ids || []).map(workItem).filter(Boolean); const recent=items.slice().sort((a,b) => String(b.updated_at || b.date || '').localeCompare(String(a.updated_at || a.date || '')))[0]; return `<article><div class="ws-customer-avatar">${esc(String(customer.name || 'C').split(/\s+/).slice(0, 2).map((word) => word[0]).join('').toUpperCase())}</div><div><strong>${esc(customer.name || 'Unnamed customer')}</strong><span>${esc([customer.contact_name, customer.email, customer.phone].filter(Boolean).join(' · ') || 'Contact details not completed')}</span><small>${items.length} work item${items.length === 1 ? '' : 's'}${recent ? ` · Last activity ${esc(recent.date || recent.updated_at || 'Not scheduled')}` : ''}</small></div><div class="ws-customer-actions"><button type="button" class="primary" data-ws-customer-quote="${esc(customer.id)}">+ New quote</button><button type="button" data-ws-edit-customer="${esc(customer.id)}">Edit customer</button>${recent ? `<button type="button" data-ws-item="${esc(recent.id)}">Open history</button>` : ''}</div></article>`; }).join('') || '<div class="ws-empty"><strong>No customers yet</strong><span>Create the first customer record, then use it for work, quotations and invoices.</span><button type="button" class="primary" data-ws-new-customer>+ Customer</button></div>'}</div></section>`;
  }

  function renderCustomerPage() {
    if (state.ui.modal !== 'customer') return '';
    const existing = customerRecord(state.ui.customerId) || {};
    const editing = Boolean(existing.id);
    const billingAddress = existing.billing_address || existing.address || '';
    const sameAddress = Boolean(billingAddress && existing.service_address && String(billingAddress).trim() === String(existing.service_address).trim());
    return `<section class="ws-detail-panel ws-create-page" aria-label="${editing ? 'Edit customer' : 'Create customer'}"><header class="ws-record-header"><div class="ws-record-heading"><button type="button" class="ws-record-back" data-ws-close-customer>← Back to Customers</button><span>CUSTOMER RECORD</span><h1>${editing ? 'Edit customer details' : 'Create a new customer'}</h1><p>Save the contact and address once. New work, quotations, invoices and customer messages will use these details automatically.</p></div><div class="ws-create-stage"><small>CRM RECORD</small><strong>${editing ? 'Saved customer' : 'New customer'}</strong><span>${editing ? `${(existing.work_item_ids || []).length} linked work record${(existing.work_item_ids || []).length === 1 ? '' : 's'}` : 'Nothing is sent when this record is saved.'}</span></div></header><form class="ws-create-form ws-customer-form" data-ws-customer-form><input type="hidden" name="id" value="${esc(existing.id)}"><label>Customer type<select name="customer_type"><option value="person" ${existing.customer_type !== 'business' ? 'selected' : ''}>Person</option><option value="business" ${existing.customer_type === 'business' ? 'selected' : ''}>Business</option></select></label><label>Name or organisation<input required name="name" value="${esc(existing.name)}" placeholder="Customer or business name"></label><label>Contact person<input name="contact_name" value="${esc(existing.contact_name)}" placeholder="Main contact, if different"></label><label>Email<input type="email" name="email" value="${esc(existing.email)}" placeholder="name@example.com"></label><label>Phone<input name="phone" value="${esc(existing.phone)}" placeholder="Phone number"></label><label>Source<select name="source">${SOURCE_OPTIONS.map((source) => `<option value="${esc(source)}" ${source === (existing.source || 'Back office') ? 'selected' : ''}>${esc(source)}</option>`).join('')}</select></label><label class="wide">Billing address<textarea name="billing_address" data-ws-billing-address placeholder="Address shown on quotations and invoices">${esc(billingAddress)}</textarea></label><label class="wide ws-address-match"><input type="checkbox" name="service_same_as_billing" value="yes" data-ws-same-address ${sameAddress ? 'checked' : ''}><span>Use the billing address as the service address</span></label><label class="wide">Service address<textarea name="service_address" data-ws-service-address placeholder="Usual address where work takes place" ${sameAddress ? 'readonly' : ''}>${esc(sameAddress ? billingAddress : existing.service_address)}</textarea></label><label class="wide">Customer notes<textarea name="notes" placeholder="Preferences, access information or useful relationship notes">${esc(existing.notes)}</textarea></label><footer><button type="button" data-ws-close-customer>Cancel</button><button type="submit" class="primary">${editing ? 'Save customer changes' : 'Create customer'}</button></footer></form></section>`;
  }

  function renderReminders() {
    const rows = state.data.reminders || [];
    return `<section class="ws-intake"><header><div><span>CUSTOMER COMMUNICATION</span><h2>Reminders ready for review</h2><p>Upcoming appointment messages are prepared here. Nothing is described as sent until a messaging provider confirms delivery.</p></div><button type="button" data-ws-prepare-all-reminders>Prepare upcoming reminders</button></header><div class="ws-intake-list">${rows.map((row) => `<article><div class="ws-channel">${esc(String(row.channel || 'manual').toUpperCase())}</div><div><strong>${esc(row.message)}</strong><span>${esc(row.recipient || 'No customer contact recorded')} · ${esc(row.prepared_at || '')}</span></div><small>${esc(titleCase(row.status || 'needs_review'))}</small><button type="button" data-ws-item="${esc(row.item_id)}">Open work</button></article>`).join('') || '<div class="ws-empty"><strong>No reminders prepared</strong><span>Open a work item to add customer contact details, or prepare reminders for upcoming scheduled work.</span></div>'}</div></section>`;
  }

  function renderStock() {
    const totals = new Map();
    (state.data.stock_movements || []).forEach((row) => {
      const key = row.name || 'Unnamed item';
      const current = totals.get(key) || { quantity: 0, unit: row.unit || 'item', movements: 0 };
      current.quantity += Number(row.quantity || 0); current.movements += 1; totals.set(key, current);
    });
    return `<section class="ws-stock"><header><div><span>STOCK · PURCHASING · RETURNS</span><h2>Materials ledger</h2><p>Record stock received, allocated to work, used on site or returned. Every movement stays tied to the shared business record.</p></div></header><form data-ws-stock-form><input required name="name" placeholder="Material or stock item"><input required type="number" min="0.01" step="0.01" name="quantity" placeholder="Quantity"><input name="unit" placeholder="Unit"><select name="movement_type"><option value="receive">Receive stock</option><option value="allocate">Allocate / use</option><option value="return">Return to stock</option><option value="adjust">Reduce / adjust</option></select><button class="primary" type="submit">Record movement</button></form><div class="ws-stock-grid">${Array.from(totals.entries()).map(([name, row]) => `<article><span>${esc(row.unit)}</span><strong>${esc(name)}</strong><b>${esc(row.quantity)}</b><small>${row.movements} recorded movement${row.movements === 1 ? '' : 's'}</small></article>`).join('') || '<div class="ws-empty"><strong>No stock recorded</strong><span>Add the first delivery or allocation above.</span></div>'}</div></section>`;
  }

  function renderDelivery(item) {
    const minutes = (item.time_entries || []).reduce((sum, row) => sum + Number(row.minutes || 0), 0);
    const route = item.location ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(item.location)}` : '';
    return `<section class="ws-delivery"><div class="ws-delivery-summary"><article><span>TIME RECORDED</span><strong>${Math.floor(minutes / 60)}h ${minutes % 60}m</strong></article><article><span>MATERIALS</span><strong>${(item.materials || []).length}</strong></article>${route ? `<a href="${route}" target="_blank" rel="noreferrer">Open route in Maps ↗</a>` : '<small>Add a location to open route planning.</small>'}</div><h3>Checklist</h3><div class="ws-checklist">${(item.checklist || []).map((row) => `<label><input type="checkbox" data-ws-check-item="${esc(item.id)}" data-ws-check-id="${esc(row.id)}" ${row.done ? 'checked' : ''}><span>${esc(row.label)}</span></label>`).join('') || '<p>No checklist steps yet.</p>'}</div><form data-ws-checklist-form="${esc(item.id)}"><input required name="label" placeholder="Add a step, inspection or evidence requirement"><button type="submit">Add step</button></form><h3>Materials used or required</h3><div class="ws-material-list">${(item.materials || []).map((row) => `<article><label><input type="checkbox" data-ws-material-item="${esc(item.id)}" data-ws-material-id="${esc(row.id)}" ${row.used ? 'checked' : ''}> Used</label><strong>${esc(row.name)}</strong><span>${esc(row.quantity)} ${esc(row.unit)}${row.unit_cost ? ` · £${esc(row.unit_cost)} each` : ''}</span></article>`).join('') || '<p>No materials recorded.</p>'}</div><form data-ws-material-form="${esc(item.id)}"><input required name="name" placeholder="Material"><input type="number" step="0.01" min="0" name="quantity" value="1"><input name="unit" placeholder="Unit" value="item"><input inputmode="decimal" name="unit_cost" placeholder="Unit cost"><button type="submit">Add material</button></form><h3>Time entries</h3><div class="ws-time-list">${(item.time_entries || []).map((row) => `<article><strong>${esc(row.minutes)} minutes</strong><span>${esc(row.note || 'Work time')} · ${esc(row.by || '')}</span></article>`).join('') || '<p>No time has been recorded.</p>'}</div><form data-ws-time-form="${esc(item.id)}"><input required type="number" min="1" max="1440" name="minutes" placeholder="Minutes"><input name="note" placeholder="What was the time for?"><button type="submit">Add time</button></form></section>`;
  }

  function renderFieldWorkspace() {
    const today = isoDate(new Date());
    const ordered = state.data.items.slice().sort((a, b) => `${a.date || '9999'} ${a.time || '99:99'}`.localeCompare(`${b.date || '9999'} ${b.time || '99:99'}`));
    let work = ordered.filter((item) => item.date === today || ['en_route', 'in_progress', 'paused'].includes(item.status));
    if (!work.length) work = ordered.filter((item) => item.date && item.date >= today && !['completed', 'invoiced', 'paid'].includes(item.status)).slice(0, 6);
    const active = work.filter((item) => ['en_route', 'in_progress', 'paused'].includes(item.status)).length;
    const missingEvidence = work.filter((item) => !(item.documents || []).length).length;
    const actionButtons = (item) => {
      if (['new', 'quote_required', 'awaiting_approval', 'scheduled'].includes(item.status)) return `<button type="button" data-ws-field-action="en_route" data-ws-field-item="${esc(item.id)}">On my way</button><button type="button" class="primary" data-ws-field-action="start" data-ws-field-item="${esc(item.id)}">Start work</button>`;
      if (item.status === 'en_route') return `<button type="button" class="primary" data-ws-field-action="start" data-ws-field-item="${esc(item.id)}">Arrived · start</button>`;
      if (item.status === 'in_progress') return `<button type="button" data-ws-field-action="pause" data-ws-field-item="${esc(item.id)}">Pause</button><button type="button" class="primary" data-ws-field-action="complete" data-ws-field-item="${esc(item.id)}">Complete work</button>`;
      if (item.status === 'paused') return `<button type="button" class="primary" data-ws-field-action="start" data-ws-field-item="${esc(item.id)}">Resume work</button>`;
      return '';
    };
    return `<section class="ws-field">
      <header><div><span>FIELD &amp; PRACTITIONER WORKSPACE</span><h2>My workday</h2><p>Complete the same work record used by scheduling: instructions, notes, evidence, customer sign-off, documents and payment outcome.</p></div><div class="ws-field-summary"><article><b>${work.length}</b><small>On this workday</small></article><article><b>${active}</b><small>Active now</small></article><article><b>${missingEvidence}</b><small>Evidence missing</small></article></div></header>
      <div class="ws-field-layout"><aside><strong>Designed for the person doing the work</strong><p>This focused view works on a desktop, tablet or phone. It shows only what is needed before, during and after the visit.</p><ul><li>Review customer and site instructions</li><li>Start, pause and complete work</li><li>Add notes, photos and certificates</li><li>Capture customer sign-off</li><li>Record time and materials</li></ul></aside>
      <div class="ws-field-device"><div class="ws-field-device-head"><div><span>${esc(formatDay(new Date()))}</span><strong>Assigned work</strong></div><small>Shared live record</small></div><div class="ws-field-list">${work.map((item, index) => `<article class="ws-field-card ${['en_route','in_progress','paused'].includes(item.status) ? 'active' : ''}"><div class="ws-field-time"><time>${esc(item.time || 'Any time')}</time><span>${Number(item.duration || 0) >= 60 ? `${Math.round(Number(item.duration) / 60 * 10) / 10} hr` : `${esc(item.duration || 0)} min`}</span></div><div class="ws-field-main"><div class="ws-field-card-top"><small>${index === 0 ? 'NEXT WORK' : esc(TYPE_LABELS[item.type] || titleCase(item.type))}</small>${statusBadge(item.status)}</div><h3>${esc(item.title)}</h3><p>${esc(item.customer)} · ${esc(item.location || 'Location not recorded')}</p><em>Assigned to ${esc(item.assignee || 'Unassigned')}</em><div class="ws-field-actions">${actionButtons(item)}<button type="button" data-ws-item="${esc(item.id)}" data-ws-panel-open="documents">Details &amp; evidence</button></div></div></article>`).join('') || '<div class="ws-empty"><strong>No assigned work</strong><span>The schedule is clear for now.</span></div>'}</div></div></div>
    </section>`;
  }

  function renderNewModal() {
    if (state.ui.modal !== 'new') return '';
    const preset = state.ui.newDraft || {};
    const reviewingRequest = Boolean(preset.intake_id);
    const estimate = preset.cost_estimate || {};
    const offerings = operatingOfferings();
    const recommendation = quoteRecommendation({ materials: estimate.material_cost, labour: estimate.labour_cost, external: estimate.external_cost });
    const currentPrice = moneyNumber(preset.quote?.subtotal || preset.quote?.amount);
    const currentMargin = grossMargin(recommendation.totalCost, currentPrice);
    const selectedSource = String(preset.source || (reviewingRequest ? 'Website' : 'Back office'));
    const sourceChoices = SOURCE_OPTIONS.includes(selectedSource) ? SOURCE_OPTIONS : [selectedSource, ...SOURCE_OPTIONS];
    const customers = Array.isArray(state.data.customers) ? state.data.customers : [];
    const selectedCustomerId = String(preset.customer_id || '');
    const selectedCustomer = customerRecord(selectedCustomerId, preset.customer) || {};
    return `<section class="ws-detail-panel ws-create-page" aria-label="${reviewingRequest ? 'Review inbound request' : 'Prepare new work'}"><header class="ws-record-header"><div class="ws-record-heading"><button type="button" class="ws-record-back" data-ws-close>← Back to ${reviewingRequest ? 'booking inbox' : 'Work & Schedule'}</button><span>${reviewingRequest ? 'REQUEST REVIEW · PREPARE QUOTE OR JOB' : 'NEW SHARED WORK RECORD'}</span><h1>${reviewingRequest ? 'Review request and prepare the work' : 'Prepare a job, quote or appointment'}</h1><p>${reviewingRequest ? 'Check the customer request, add the missing details and pricing, then approve it into the shared work record. You will continue in its Quotes & invoices tab.' : 'Prepare the details clearly before saving. Scheduling, estimates, delivery, evidence, quote and invoice will all use this record.'}</p></div><div class="ws-create-stage"><small>CURRENT STAGE</small><strong>${reviewingRequest ? 'Human review' : 'Draft preparation'}</strong><span>${reviewingRequest ? 'Next: linked work record · Quotes & invoices' : 'Nothing is live until you save it.'}</span></div></header><form class="ws-create-form" data-ws-new-form>
      ${reviewingRequest ? `<input type="hidden" name="intake_id" value="${esc(preset.intake_id)}"><div class="wide ws-review-notice"><span>INBOUND REQUEST</span><strong>${esc(preset.title || 'Customer request')}</strong><p>${esc(preset.customer || 'Customer not recorded')} · ${esc(preset.source || 'Source not recorded')} · Review before accepting</p></div>` : ''}
      <label class="wide">Work title<input required name="title" placeholder="e.g. New roof installation" value="${esc(preset.title)}"></label>
      <label>Source<select required name="source" aria-label="Source — where this request came from">${sourceChoices.map((source) => `<option value="${esc(source)}" ${source === selectedSource ? 'selected' : ''}>${esc(source)}</option>`).join('')}</select></label>
      <label>Record type<select name="type" data-ws-new-type>${Object.entries(TYPE_LABELS).map(([key, label]) => `<option value="${key}" ${(preset.type || 'job') === key ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
      <section class="wide ws-customer-capture"><div><span>CUSTOMER</span><strong>Select the saved customer for this work</strong><p>The customer’s current CRM details will automatically appear on the quotation, invoice and prepared email.</p></div><label>Customer record<select name="customer_id" data-ws-customer-select><option value="">No customer selected</option>${customers.map((customer) => `<option value="${esc(customer.id)}" ${String(customer.id) === String(selectedCustomer.id || selectedCustomerId) ? 'selected' : ''}>${esc(customer.name || customer.email || 'Saved customer')}</option>`).join('')}</select></label><button type="button" data-ws-new-customer-from-work>+ Add customer</button><input type="hidden" name="customer" value="${esc(selectedCustomer.name || preset.customer)}"><input type="hidden" name="customer_email" value="${esc(selectedCustomer.email || preset.customer_email)}"><input type="hidden" name="customer_phone" value="${esc(selectedCustomer.phone || preset.customer_phone)}"><input type="hidden" name="customer_address" value="${esc(selectedCustomer.billing_address || selectedCustomer.address || preset.customer_address || preset.location)}"><div class="ws-selected-customer" data-ws-customer-summary><strong>${esc(selectedCustomer.name || preset.customer || 'No customer selected')}</strong><span>${esc([selectedCustomer.email || preset.customer_email, selectedCustomer.phone || preset.customer_phone].filter(Boolean).join(' · ') || 'Choose a saved customer or add one first.')}</span><small>${esc(selectedCustomer.billing_address || selectedCustomer.address || preset.customer_address || '')}</small></div></section>
      <label class="wide">Product or service<select name="offering_id"><option value="">Not linked yet</option>${offerings.map((row) => `<option value="${esc(row.id || row.name)}" ${String(preset.offering_id || '') === String(row.id || row.name) ? 'selected' : ''}>${esc(row.name || row.id)}</option>`).join('')}</select></label>
      <details class="wide ws-internal-details"><summary><span>Internal scheduling and record details</span><small>Date, assignment, resources, location and internal notes</small></summary><div class="ws-internal-grid"><label>Date<input type="date" name="date" value="${esc(preset.date || isoDate(new Date()))}"></label><label>Start time<input type="time" name="time" value="${esc(preset.time || '09:00')}"></label><label>Duration<select name="duration">${[[30,'30 minutes'],[60,'1 hour'],[90,'1½ hours'],[120,'2 hours'],[240,'Half day'],[480,'Full day']].map(([value,label]) => `<option value="${value}" ${Number(preset.duration || 60) === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label><label>Assigned person or team<input name="assignee" placeholder="Choose or leave unassigned" value="${esc(preset.assignee)}"></label><label>Status<select name="status" data-ws-new-status>${['new','quote_required','awaiting_approval','scheduled','in_progress','completed'].map((status) => `<option value="${status}" ${status === (preset.status || (preset.type === 'quote' ? 'quote_required' : 'scheduled')) ? 'selected' : ''}>${titleCase(status)}</option>`).join('')}</select></label><label>Repeat<select name="recurrence_frequency"><option value="none">Does not repeat</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label><label>Number of visits<input type="number" min="1" max="52" name="recurrence_count" value="1"></label><label>Rooms, vehicles or equipment<input name="resource_ids" placeholder="e.g. Van 1, Surgery 2"></label><label class="wide">Location<input name="location" placeholder="Customer site, clinic, office or video call" value="${esc(preset.location)}"></label><label class="wide">Instructions and notes<textarea name="notes" placeholder="Access, requirements, preparation or internal notes">${esc(preset.notes)}</textarea></label></div></details>
      <div class="wide ws-form-section"><span>AI-ENHANCED QUOTE &amp; JOB COSTING</span><strong>Enter the real estimated costs for this job</strong><p>Variable materials and labour do not need one fixed catalogue cost. Tessaris prices this job from the actual estimate using the approved margin rules.</p></div>
      <label>Estimated materials<input type="number" min="0" step="0.01" name="estimated_material_cost" data-ws-pricing-cost="materials" placeholder="Optional" value="${esc(estimate.material_cost)}"></label>
      <label>Estimated labour<input type="number" min="0" step="0.01" name="estimated_labour_cost" data-ws-pricing-cost="labour" placeholder="Optional" value="${esc(estimate.labour_cost)}"></label>
      <label>Estimated external costs<input type="number" min="0" step="0.01" name="estimated_external_cost" data-ws-pricing-cost="external" placeholder="Subcontractor, hire, delivery…" value="${esc(estimate.external_cost)}"></label>
      <label>Proposed customer price<input type="number" min="0" step="0.01" name="quote_amount" data-ws-quote-price placeholder="Optional" value="${esc(preset.quote?.subtotal || preset.quote?.amount || '')}"></label>
      <section class="wide ws-ai-quote-guidance" data-ws-ai-quote-guidance>
        <div><span>AI RECOMMENDATION · DRAFT</span><strong data-ws-ai-suggested>${recommendation.totalCost ? recommendation.suggestedPrice.toFixed(2) : 'Add costs to calculate'}</strong><p data-ws-ai-explanation>${recommendation.totalCost ? `Based on ${recommendation.totalCost.toFixed(2)} estimated direct cost and the approved pricing rules.` : `Target margin ${recommendation.targetMargin}% · minimum ${recommendation.minimumMargin}%. Add the known costs above.`}</p></div>
        <div class="ws-ai-margin ${currentPrice && currentMargin < recommendation.minimumMargin ? 'warning' : ''}" data-ws-ai-margin><small>Current quote margin</small><b>${currentPrice ? `${currentMargin.toFixed(2)}%` : 'Not priced'}</b><em>${currentPrice && currentMargin < recommendation.minimumMargin ? `Below the ${recommendation.minimumMargin}% minimum` : `Minimum ${recommendation.minimumMargin}%`}</em></div>
        <button type="button" data-ws-accept-ai-price data-ws-recommended-price="${recommendation.suggestedPrice.toFixed(2)}" ${recommendation.totalCost ? '' : 'disabled'}>Use recommended price</button>
        <small>Highlighted suggestions are not final. Review the scope and costs before approving or sending the quote. You can edit the price at any time.</small>
      </section>
      <footer><button type="button" data-ws-close>${reviewingRequest ? 'Return to inbox' : 'Cancel'}</button><button type="submit" class="primary">${reviewingRequest ? 'Approve and create work record' : 'Save work record'}</button></footer>
    </form></section>`;
  }

  function refreshNewQuoteGuidance(form) {
    if (!form) return;
    const costs = {};
    form.querySelectorAll('[data-ws-pricing-cost]').forEach((input) => { costs[input.dataset.wsPricingCost] = input.value; });
    const recommendation = quoteRecommendation(costs);
    const priceInput = form.querySelector('[data-ws-quote-price]');
    const currentPrice = moneyNumber(priceInput?.value);
    const margin = grossMargin(recommendation.totalCost, currentPrice);
    const suggested = form.querySelector('[data-ws-ai-suggested]');
    const explanation = form.querySelector('[data-ws-ai-explanation]');
    const marginBox = form.querySelector('[data-ws-ai-margin]');
    const accept = form.querySelector('[data-ws-accept-ai-price]');
    if (suggested) suggested.textContent = recommendation.totalCost ? recommendation.suggestedPrice.toFixed(2) : 'Add costs to calculate';
    if (explanation) explanation.textContent = recommendation.totalCost
      ? `Based on ${recommendation.totalCost.toFixed(2)} estimated direct cost. Target margin ${recommendation.targetMargin}%; minimum ${recommendation.minimumMargin}%.`
      : `Target margin ${recommendation.targetMargin}% · minimum ${recommendation.minimumMargin}%. Add the known costs above.`;
    if (marginBox) {
      const below = currentPrice > 0 && margin < recommendation.minimumMargin;
      marginBox.classList.toggle('warning', below);
      const bold = marginBox.querySelector('b'); const note = marginBox.querySelector('em');
      if (bold) bold.textContent = currentPrice ? `${margin.toFixed(2)}%` : 'Not priced';
      if (note) note.textContent = below ? `Below the ${recommendation.minimumMargin}% minimum` : `Minimum ${recommendation.minimumMargin}%`;
    }
    if (accept) { accept.disabled = !recommendation.totalCost; accept.dataset.wsRecommendedPrice = recommendation.suggestedPrice.toFixed(2); }
    form.dataset.wsRecommendedPrice = recommendation.suggestedPrice.toFixed(2);
    form.dataset.wsTargetMargin = String(recommendation.targetMargin);
    form.dataset.wsMinimumMargin = String(recommendation.minimumMargin);
  }

  function renderQuotation(item) {
    const identity = quoteIdentity();
    const customer = customerForItem(item);
    const { lines, subtotal, tax, total } = quoteTotals(item);
    const issued = item.quote?.created_at ? new Date(item.quote.created_at) : new Date();
    const valid = new Date(issued); valid.setDate(valid.getDate() + identity.validDays);
    const dateText = (value) => Number.isNaN(value.getTime()) ? 'Not set' : value.toLocaleDateString('en-GB');
    const accent = /^#[0-9a-f]{3,8}$/i.test(String(identity.accent)) ? identity.accent : '#2563eb';
    const vatLabel = new Set(lines.map((line) => moneyNumber(line.vat_rate))).size === 1 ? `VAT (${esc(moneyNumber(lines[0]?.vat_rate))}%)` : 'VAT';
    const method = item.quote?.payment_method || identity.paymentMethod;
    const stages = paymentStageAmounts(item);
    const bankBits = [identity.bank.accountName && `Account: ${identity.bank.accountName}`, identity.bank.bankName, identity.bank.sortCode && `Sort / routing: ${identity.bank.sortCode}`, identity.bank.accountNumber && `Account no: ${identity.bank.accountNumber}`, identity.bank.iban && `IBAN: ${identity.bank.iban}`, identity.bank.bic && `BIC / SWIFT: ${identity.bank.bic}`].filter(Boolean);
    const providerLabel = { stripe:'Stripe', paypal:'PayPal', square:'Square', gocardless:'GoCardless', revolut:'Revolut Business', sumup:'SumUp', mollie:'Mollie', braintree:'Braintree', worldpay:'Worldpay', adyen:'Adyen', checkout_com:'Checkout.com' }[method];
    const paymentCopy = method === 'bank_transfer' ? (bankBits.length ? bankBits.join(' · ') : 'Bank details will be supplied before payment is due.') : providerLabel ? (identity.paymentLinks?.[method] ? `A secure ${providerLabel} payment link will be supplied with the payment request.` : `${providerLabel} payment is awaiting connection.`) : 'Pay by bank transfer or by the secure online link supplied with the payment request.';
    return `<article class="ws-quotation" style="--quote-accent:${esc(accent)}"><header><div class="ws-quote-business">${identity.logo ? `<img src="${esc(identity.logo)}" alt="${esc(identity.name)} logo">` : `<button type="button" class="ws-upload-logo" data-ws-upload-logo title="Add your business logo in Key Business Info"><span>Upload logo</span></button>`}<div><strong>${esc(identity.name)}</strong><span>${esc(identity.address)}</span><span>${esc([identity.phone, identity.email, identity.website].filter(Boolean).join(' · '))}</span></div></div><div class="ws-quote-title"><h2>QUOTATION</h2><dl><div><dt>Quote number</dt><dd>${esc(item.quote?.number || 'Assigned when generated')}</dd></div><div><dt>Date</dt><dd>${esc(dateText(issued))}</dd></div><div><dt>Valid until</dt><dd>${esc(dateText(valid))}</dd></div></dl></div></header><section class="ws-quote-customer"><span>QUOTATION FOR</span><strong>${esc(customer.name || 'Customer details required')}</strong><p>${esc([customer.address, customer.email, customer.phone].filter(Boolean).join(' · '))}</p></section><section class="ws-quote-scope"><span>DESCRIPTION OF WORK</span><p>${esc(item.title)}</p><small>${esc(item.quote?.description_of_work || 'Scope to be confirmed in the draft quotation.')}</small></section><table><thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>VAT</th><th>Amount</th></tr></thead><tbody>${lines.map((line) => { const quantity=Math.max(0,moneyNumber(line.quantity)||1); const amount=parentLineTotal(line); return `<tr><td>${esc(line.description)}</td><td>${esc(quantity)}</td><td>${esc((amount/quantity).toFixed(2))}</td><td>${esc(moneyNumber(line.vat_rate))}%</td><td>${esc(amount.toFixed(2))}</td></tr>`; }).join('')}</tbody><tfoot><tr><td colspan="4">Subtotal</td><td>${esc(subtotal.toFixed(2))}</td></tr><tr><td colspan="4">${vatLabel}</td><td>${esc(tax.toFixed(2))}</td></tr><tr><td colspan="4">TOTAL QUOTE</td><td>${esc(total.toFixed(2))}</td></tr></tfoot></table><section class="ws-quote-payment"><span>PAYMENT SCHEDULE</span>${stages.map((stage) => `<div><strong>${esc(stage.label)}</strong><span>${esc(dueText(stage))}</span><b>${esc(identity.currency)} ${esc(stage.calculated_amount.toFixed(2))}</b></div>`).join('')}<p>${esc(paymentCopy)}</p><p><strong>Payment reference:</strong> ${esc(quotePaymentReference(item))}</p></section><label class="ws-quote-terms-toggle"><input type="checkbox" data-ws-quote-include-terms="${esc(item.id)}" ${identity.includeTerms ? 'checked' : ''}> Include the saved Terms &amp; Conditions</label>${identity.terms ? `<section class="ws-quote-terms"><span>TERMS &amp; CONDITIONS</span><p>${esc(identity.terms)}</p></section>` : `<section class="ws-quote-terms missing"><span>TERMS &amp; CONDITIONS</span><p>No quotation terms are saved yet. Add them under Business → Terms &amp; Conditions.</p></section>`}<footer>This customer draft hides all cost prices, margins and private calculation rows.</footer></article>`;
  }

  function latestQuoteDocument(item) {
    return [...(item?.documents || [])].reverse().find((document) => document?.kind === 'quote' && document?.id);
  }

  function quoteDocumentUrl(item, document) {
    return document ? endpoint(`/items/${encodeURIComponent(item.id)}/files/${encodeURIComponent(document.id)}`) : '';
  }

  function quoteEmailText(template, item, identity) {
    const customer = customerForItem(item);
    return String(template || '')
      .replaceAll('{customer_name}', String(customer.name || 'there'))
      .replaceAll('{quote_number}', String(item.quote?.number || ''))
      .replaceAll('{business_name}', String(identity.name || ''));
  }

  function renderQuoteDelivery(item) {
    void hydrateGmailHealth();
    const identity = quoteIdentity();
    const customer = customerForItem(item);
    const document = latestQuoteDocument(item);
    if (!document) return '';
    const emailState = item.quote_email_delivery || item.quote_email_draft || {};
    const quoteAccepted = item.quote?.status === 'customer_approved';
    const visibleEmailError = emailState.error && emailState.failed_at
      && (Date.now() - new Date(emailState.failed_at).getTime()) < 10 * 60 * 1000
      ? emailState.error
      : '';
    const gmailHealth = gmailHealthSnapshot || global.__aionGmailHealth || {};
    const gmailIsConnected = gmailHealth.connected === true
      || gmailHealth.auth_status === 'connected'
      || gmailHealth.connector_health === 'available';
    const gmailNeedsConnection = Boolean(visibleEmailError)
      && /no connected gmail account|gmail.+not connected|reauthori[sz]|invalid authentication|invalid credentials|unauthenticated|oauth/i.test(visibleEmailError);
    const subject = emailState.subject || quoteEmailText(identity.quoteEmailSubject, item, identity);
    const body = emailState.body || quoteEmailText(identity.quoteEmailBody, item, identity);
    const recipient = emailState.to || customer.email || '';
    return `<article class="ws-quote-delivery">
      <span>SEND OR SHARE QUOTE</span>
      <strong>${esc(document.name || `${item.quote?.number || 'Quotation'}.pdf`)}</strong>
      <p>${quoteAccepted ? 'The customer has accepted this quotation. The PDF remains available to save or share for your records.' : 'The numbered PDF is ready. Review the message below, then send it now with the PDF and acceptance button attached, or save/share it yourself.'}</p>
      <div class="ws-quote-delivery-actions">
        <button type="button" data-ws-save-quote="${esc(item.id)}" data-ws-document-id="${esc(document.id)}">Save PDF…</button>
        <button type="button" data-ws-share-quote="${esc(item.id)}" data-ws-document-id="${esc(document.id)}">Share PDF…</button>
      </div>
      ${quoteAccepted ? '' : `<label>To<input type="email" data-ws-quote-email-to="${esc(item.id)}" value="${esc(recipient)}" placeholder="customer@example.com"></label>
      <label>Subject<input data-ws-quote-email-subject="${esc(item.id)}" value="${esc(subject)}"></label>
      <label>Message<textarea data-ws-quote-email-body="${esc(item.id)}" rows="6">${esc(body)}</textarea></label>
      <button type="button" class="primary" data-ws-send-quote-email="${esc(item.id)}" data-ws-document-id="${esc(document.id)}">Send quotation to customer</button>
      <small>This sends the email immediately with the branded PDF and an Accept quotation button. Acceptance automatically creates and emails the invoice for the payment stage due.</small>`}
      ${emailState.status === 'sent'
        ? `<small class="success">Quotation sent to ${esc(emailState.to)}${emailState.sent_at ? ` on ${esc(new Date(emailState.sent_at).toLocaleString())}` : ''}. ${quoteAccepted ? 'Customer acceptance has been recorded.' : 'Waiting for customer acceptance.'}</small>`
        : gmailNeedsConnection
          ? `<div class="ws-gmail-recovery"><div><strong>Gmail is not connected</strong><small>The quotation was not sent. Connect or re-authorise Gmail in your normal browser, then return here and send it again.</small></div><button type="button" data-ws-connect-gmail>Connect Gmail</button></div>`
          : visibleEmailError
            ? `<small class="error">The quotation was not sent: ${esc(String(visibleEmailError).replace(/[.\s]+$/, ''))}.</small>`
            : ''}
      <button type="button" class="ws-edit-email-template" data-ws-edit-quote-email-template>Edit this templated email in Business settings →</button>
    </article>`;
  }

  function renderCommercial(item) {
    const identity = quoteIdentity();
    const totals = quoteTotals(item);
    const subtotal = totals.subtotal;
    const builderCosts = { materials:0, labour:0, external:0 };
    totals.lines.forEach((line) => (line.children || []).forEach((child) => {
      const cost = Math.max(0, moneyNumber(child.quantity) || 1) * Math.max(0, moneyNumber(child.cost_price));
      if (child.type === 'materials') builderCosts.materials += cost;
      else if (child.type === 'labour') builderCosts.labour += cost;
      else builderCosts.external += cost;
    }));
    const total = builderCosts.materials + builderCosts.labour + builderCosts.external;
    const proposed = subtotal;
    const recommendation = quoteRecommendation(builderCosts);
    const quoteMargin = grossMargin(recommendation.totalCost, proposed);
    const belowFloor = proposed > 0 && quoteMargin < recommendation.minimumMargin;
    const quoteAccepted = item.quote?.status === 'customer_approved';
    const hasNumberedQuote = Boolean(item.quote?.number && latestQuoteDocument(item));
    const hasDraftInvoice = Boolean(item.invoice?.number || (item.documents || []).some((document) => document?.kind === 'invoice'));
    return `<section class="ws-commercial">
      ${item.source_request ? `<article class="ws-source-request"><span>LINKED INBOUND REQUEST</span><strong>${esc(item.source_request.title || item.title)}</strong><p>${esc(item.source_request.channel || item.source || 'Booking inbox')} · ${esc(item.source_request.customer || item.customer || 'Customer not recorded')} · reviewed into this work record</p></article>` : ''}
      <article class="ws-ai-commercial-guidance ${belowFloor ? 'warning' : ''}"><span>AI PRICING REVIEW · DRAFT</span><strong>${recommendation.totalCost ? `Recommended customer price · ${esc(recommendation.suggestedPrice.toFixed(2))}` : 'Add private costs in the quote builder for a recommendation'}</strong><p>${recommendation.totalCost ? `The recommendation uses the materials, labour and external costs in the private working rows below. Target margin ${esc(recommendation.targetMargin)}%; minimum ${esc(recommendation.minimumMargin)}%.` : `Add private cost / working rows beneath each customer quote line. Those rows remain hidden from the customer.`}</p>${proposed && total ? `<small>${belowFloor ? `Warning: the current ${esc(quoteMargin.toFixed(2))}% margin is below the ${esc(recommendation.minimumMargin)}% minimum.` : `Current quote margin: ${esc(quoteMargin.toFixed(2))}%.`}</small>` : ''}${recommendation.totalCost ? `<button type="button" data-ws-use-recommended-quote="${esc(item.id)}" data-ws-recommended-price="${esc(recommendation.suggestedPrice.toFixed(2))}">Use recommendation in draft quote</button>` : ''}<p>Review and edit the recommendation before approval. Tessaris will never send or publish it automatically.</p></article>
      ${renderQuoteBuilder(item)}
      ${renderPaymentPlan(item)}
      ${renderQuotation(item)}
      <article class="ws-quote-to-invoice"><span>QUOTE TO INVOICE</span><strong>${hasDraftInvoice ? esc(item.invoice?.number || 'Payment invoice created') : hasNumberedQuote ? `${esc(item.quote?.number)} · Waiting for customer acceptance` : 'Create the customer quote first'}</strong><p>${hasDraftInvoice ? 'Customer acceptance automatically created the invoice for the payment stage that is now due.' : hasNumberedQuote ? 'When the customer accepts, Tessaris will create the due payment invoice and deliver it using the payment methods configured on the quote.' : 'Create the numbered customer quotation before converting it into an invoice.'}</p>${hasNumberedQuote ? '' : `<button type="button" class="primary" data-ws-create-quote="${esc(item.id)}">Create numbered quotation PDF</button>`}<div class="ws-invoice-fields"><label>Description<input data-ws-invoice-description="${esc(item.id)}" value="${esc(item.title)}"></label><label>Amount before tax<input inputmode="decimal" data-ws-invoice-amount="${esc(item.id)}" value="${esc(item.invoice?.subtotal || item.invoice?.amount || subtotal.toFixed(2))}" placeholder="0.00"></label><label>Tax %<input inputmode="decimal" data-ws-invoice-tax="${esc(item.id)}" value="${esc(item.invoice?.tax_rate || '20')}"></label></div>${hasDraftInvoice ? `<small>${quoteAccepted ? `Customer acceptance recorded${item.quote?.approved_at ? ` ${esc(new Date(item.quote.approved_at).toLocaleString())}` : ''}.` : ''} ${['awaiting_bank_payment','awaiting_card_payment','awaiting_customer_payment'].includes(item.payment_request?.status) ? 'The payment invoice has been sent automatically.' : 'Payment delivery needs attention below.'}</small>` : ''}</article>
      <article class="ws-payment"><span>AUTOMATIC PAYMENT</span><strong>${item.payment_request?.status === 'awaiting_bank_payment' ? 'Invoice sent · awaiting bank transfer' : item.payment_request?.status === 'awaiting_card_payment' ? 'Invoice sent · awaiting card payment' : item.payment_request?.status === 'awaiting_customer_payment' ? 'Invoice sent · awaiting customer payment' : item.payment_request?.status === 'payment_configuration_required' ? 'Payment setup needs attention' : item.payment_request?.status === 'delivery_failed' ? 'Invoice email could not be delivered' : item.payment_request?.status === 'draft_needs_approval' ? 'Earlier payment request · not sent' : quoteAccepted ? 'Preparing the payment invoice' : 'Starts when the customer accepts'}</strong><p>${item.payment_request?.status === 'awaiting_bank_payment' ? 'Do not mark this as paid or move it to scheduling until the bank transaction is reconciled.' : item.payment_request?.status === 'payment_configuration_required' ? `The invoice was not emailed because ${esc(String(item.payment_request.delivery_error || 'payment details are missing').replaceAll('_', ' '))}. Complete Financial Information, then return here and send the invoice.` : item.payment_request?.status === 'delivery_failed' ? `Delivery failed: ${esc(item.payment_request.delivery_error || 'Check Gmail and the customer email address.')}` : item.payment_request?.status === 'draft_needs_approval' ? 'This request was created before automatic delivery was enabled and has not been sent. New quote acceptances use the automatic flow.' : 'Acceptance creates the invoice for the amount currently due and emails it without another prepare step.'}</p>${item.payment_request ? `<small>${esc(item.payment_request.label)} · ${esc(item.payment_request.currency)} ${esc(moneyNumber(item.payment_request.amount).toFixed(2))} · Reference ${esc(item.payment_request.reference)} · ${esc(titleCase(item.payment_request.status))}</small>` : ''}${['payment_configuration_required','delivery_failed'].includes(item.payment_request?.status) ? `<div class="ws-payment-recovery"><button type="button" data-ws-open-financial-settings>Open Financial Information</button><button type="button" class="primary" data-ws-retry-payment-delivery="${esc(item.id)}">Send invoice now</button></div>` : ''}</article>
      ${renderQuoteDelivery(item)}
      <p>Bank transfers remain awaiting reconciliation. Card payments can move forward only after the payment provider confirms success.</p>
    </section>`;
  }

  function renderDetailPanel() {
    const item = workItem(state.ui.selectedId);
    if (!item) return '';
    const customer = customerForItem(item);
    const panelTab = state.ui.panelTab || 'overview';
    const tabs = [['overview','Overview'],['delivery','Checklist, time & materials'],['updates','Work updates'],['documents','Files & evidence'],['signoff','Customer sign-off'],['commercial','Quotes & invoices']];
    const returnLabels = { board: 'Job board', calendar: 'Calendar', field: 'Field workspace', intake: 'Booking inbox', customers: 'Customers', reminders: 'Reminders', stock: 'Stock & materials' };
    const customerRecords = state.data.items.filter((row) => {
      const rowCustomer = customerForItem(row);
      return (customer.id && rowCustomer.id === customer.id) || (!customer.id && rowCustomer.name.trim().toLowerCase() === customer.name.trim().toLowerCase());
    }).length;
    return `<section class="ws-detail-panel ws-record-page" aria-label="Work record for ${esc(item.title)}">
      <header class="ws-record-header"><div class="ws-record-heading"><button type="button" class="ws-record-back" data-ws-close-item>← Back to ${esc(returnLabels[state.ui.view] || 'Work & Schedule')}</button><span>WORK RECORD · ${esc(TYPE_LABELS[item.type] || titleCase(item.type))}</span><h1>${esc(item.title)}</h1><p>${esc(customer.name || 'Customer not recorded')}</p></div><div class="ws-record-controls"><small>Record reference</small><strong>${esc(item.id)}</strong><label>Status<select data-ws-status="${esc(item.id)}">${STATUSES.map((status) => `<option value="${status}" ${status === item.status ? 'selected' : ''}>${titleCase(status)}</option>`).join('')}</select></label></div></header>
      <div class="ws-record-summary"><article><span>STATUS</span>${statusBadge(item.status)}${item.sample ? '<span class="ws-sample">Sample record</span>' : ''}</article><article><span>CUSTOMER</span><strong>${esc(customer.name || 'Not recorded')}</strong><small>${esc([customer.email, customer.phone].filter(Boolean).join(' · ') || `${customerRecords} linked work ${customerRecords === 1 ? 'record' : 'records'}`)}</small></article><article><span>SCHEDULE</span><strong>${esc(item.date || 'Not scheduled')}</strong><small>${esc(item.time || 'Time not set')} · ${esc(item.duration || 0)} minutes</small></article><article><span>ASSIGNED TO</span><strong>${esc(item.assignee || 'Unassigned')}</strong><small>${esc(item.location || customer.serviceAddress || 'Location not recorded')}</small></article></div>
      <nav class="ws-record-tabs" aria-label="Work record sections">${tabs.map(([key,label]) => `<button type="button" class="${panelTab === key ? 'active' : ''}" data-ws-panel-tab="${key}">${label}</button>`).join('')}</nav>
      <div class="ws-detail-body">${panelTab === 'overview' ? `<section class="ws-overview"><dl><div><dt>Date and time</dt><dd>${esc(item.date || 'Not scheduled')} · ${esc(item.time || 'Time not set')}</dd></div><div><dt>Duration</dt><dd>${esc(item.duration || 0)} minutes</dd></div><div><dt>Assigned to</dt><dd>${esc(item.assignee || 'Unassigned')}</dd></div><div><dt>Location</dt><dd>${esc(item.location || customer.serviceAddress || 'Not recorded')}</dd></div><div><dt>Source</dt><dd>${esc(item.source || 'Not recorded')}</dd></div><div><dt>Customer</dt><dd>${esc(customer.name || 'Not recorded')}${customer.email ? `<br>${esc(customer.email)}` : ''}${customer.phone ? `<br>${esc(customer.phone)}` : ''}</dd></div></dl><article><span>WORK INSTRUCTIONS</span><p>${esc(item.notes || 'No instructions have been added.')}</p></article><button type="button" data-ws-duplicate="${esc(item.id)}">Schedule another visit</button></section>` : ''}
      ${panelTab === 'delivery' ? renderDelivery(item) : ''}
      ${panelTab === 'updates' ? `<section class="ws-updates"><div>${(item.updates || []).map((update) => `<article><strong>${esc(update.text)}</strong><span>${esc(update.at)}</span></article>`).join('') || '<p>No work updates yet. Notes from the office or the person doing the work will appear here.</p>'}</div><form data-ws-update-form="${esc(item.id)}"><textarea name="update" required placeholder="Add a note, outcome, measurement or next action"></textarea><button class="primary" type="submit">Add update</button></form></section>` : ''}
      ${panelTab === 'documents' ? `<section class="ws-documents"><div>${(item.documents || []).map((file) => { const document = typeof file === 'string' ? { name: file } : file; const fileUrl = document.id && document.stored_name ? endpoint(`/items/${encodeURIComponent(item.id)}/files/${encodeURIComponent(document.id)}`) : ''; return `<article><span>${esc(titleCase(document.kind || 'file'))}</span><strong>${esc(document.name || 'Attached file')}</strong><small>${document.size ? `${Math.ceil(Number(document.size) / 1024)} KB · ` : ''}Attached to this shared work record</small>${fileUrl ? `<div class="ws-file-actions"><a href="${fileUrl}?inline=true" target="_blank" rel="noreferrer">Open document</a><a href="${fileUrl}" download>Save PDF…</a></div>` : ''}</article>`; }).join('') || '<p>No photographs, certificates or documents have been added.</p>'}</div><label class="ws-upload">+ Add photos, certificates or files<input type="file" multiple data-ws-file="${esc(item.id)}"></label><div class="ws-document-actions"><button type="button" data-ws-create-document="service_report" data-ws-document-item="${esc(item.id)}">Create service report</button><button type="button" data-ws-create-document="completion_certificate" data-ws-document-item="${esc(item.id)}">Create completion certificate</button></div><small class="ws-helper">Files and generated PDFs are stored in the business workspace and are available to authorised desktop and mobile users.</small></section>` : ''}
      ${panelTab === 'signoff' ? `<section class="ws-signoff">${item.customerSignature?.dataUrl ? `<div class="ws-signed"><span>CUSTOMER SIGN-OFF RECORDED</span><img src="${esc(item.customerSignature.dataUrl)}" alt="Customer signature"><strong>${esc(item.customerSignature.name || 'Customer')}</strong><small>${esc(item.customerSignature.signedAt || '')}</small><button type="button" data-ws-replace-signature="${esc(item.id)}">Replace signature</button></div>` : `<div class="ws-signoff-copy"><span>COMPLETION CONFIRMATION</span><h3>Ask the customer to sign</h3><p>The signature is stored on this work record with the customer name and time. It confirms attendance or completion; it does not replace contractual acceptance terms.</p></div><label>Customer name<input data-ws-signature-name="${esc(item.id)}" placeholder="Name of person signing"></label><canvas class="ws-signature-pad" data-ws-signature-pad="${esc(item.id)}" width="560" height="180" aria-label="Customer signature pad"></canvas><div class="ws-signature-actions"><button type="button" data-ws-clear-signature="${esc(item.id)}">Clear</button><button type="button" class="primary" data-ws-save-signature="${esc(item.id)}">Save customer sign-off</button></div>`}</section>` : ''}
      ${panelTab === 'commercial' ? renderCommercial(item) : ''}</div>
    </section>`;
  }

  function renderSurface(renderSidebar) {
    void hydrate();
    const content = state.ui.view === 'board' ? renderBoard() : state.ui.view === 'field' ? renderFieldWorkspace() : state.ui.view === 'intake' ? renderIntake() : state.ui.view === 'customers' ? renderCustomers() : state.ui.view === 'reminders' ? renderReminders() : state.ui.view === 'stock' ? renderStock() : renderCalendar();
    const workspace = `${renderHeader()}${renderViewTabs()}<form class="ws-pilot-bar" data-ws-pilot-form><div><span>WORK PILOT</span><strong>Delegate the booking and admin</strong><small>Say it naturally: “Book a roof survey for Alex next Tuesday at 10 and assign James.”</small></div><input name="instruction" required placeholder="Tell Work Pilot what to book or change…"><button type="submit" class="primary">Prepare</button></form>${state.ui.pilotMessage ? `<div class="ws-pilot-result">${esc(state.ui.pilotMessage)}</div>` : ''}${state.conflicts.length ? `<section class="ws-conflicts"><strong>Scheduling clashes</strong>${state.conflicts.map((row) => `<button type="button" data-ws-item="${esc(row.item_ids?.[0] || '')}">${esc(row.message)}</button>`).join('')}</section>` : ''}${content}`;
    const creationPage = state.ui.modal === 'new' ? renderNewModal() : state.ui.modal === 'customer' ? renderCustomerPage() : '';
    const selectedRecord = !creationPage && state.ui.selectedId ? renderDetailPanel() : '';
    const extraPaymentProviders = [
      ['revolut', 'Revolut Business'], ['sumup', 'SumUp'], ['mollie', 'Mollie'],
      ['braintree', 'Braintree'], ['worldpay', 'Worldpay'], ['adyen', 'Adyen'], ['checkout_com', 'Checkout.com'],
    ].map(([value, label]) => `<option value="${value}" ${state.ui.selectedId && workItem(state.ui.selectedId)?.quote?.payment_method === value ? 'selected' : ''}>${label}</option>`).join('');
    return `<div class="surface-shell ws-surface" data-aion-work-schedule="true">${typeof renderSidebar === 'function' ? renderSidebar() : ''}<main class="ws-shell">${creationPage || selectedRecord || workspace}</main></div>`
      .replace('<option value="customer_choice"', `${extraPaymentProviders}<option value="customer_choice"`);
  }

  function openNew(preset = {}) {
    state.ui.modal = 'new';
    state.ui.newDraft = preset;
    rerender();
  }

  function openCustomer(customerId = '', returnToWork = false) {
    state.ui.modal = 'customer';
    state.ui.customerId = customerId;
    state.ui.customerReturnToWork = Boolean(returnToWork);
    rerender();
  }

  function openCustomerQuote(customerId) {
    const customer = customerRecord(customerId);
    if (!customer) return;
    const now = new Date().toISOString();
    const item = {
      id:uid('work'), title:`Quotation for ${customer.name || 'customer'}`, type:'quote', status:'quote_required',
      source:customer.source || 'Back office', customer_id:customer.id, customer:customer.name || '',
      customer_email:customer.email || '', customer_phone:customer.phone || '',
      customer_address:customer.billing_address || customer.address || '',
      date:'', time:'', duration:60, assignee:'', location:customer.service_address || customer.billing_address || customer.address || '',
      notes:'', sample:false, documents:[], updates:[{ text:'Draft quotation created from the customer record.', at:now, by:'desktop_user' }],
      cost_estimate:{ material_cost:'', labour_cost:'', external_cost:'', currency:global.AionOperatingModelWorkspace?.state?.model?.currency || 'EUR', source:'shared_work_record', updated_at:now },
      quote:{ status:'draft', amount:'', subtotal:'', description_of_work:'', draft_lines:[{ id:uid('line'), description:'New quote line', type:'service', quantity:1, unit_price:0, vat_rate:20, children:[] }] },
      invoice:{ status:'not_created', amount:'' }, created_at:now, updated_at:now,
    };
    state.data.items.push(item);
    customer.work_item_ids = [...new Set([...(customer.work_item_ids || []), item.id])];
    state.ui.modal = ''; state.ui.selectedId = item.id; state.ui.panelTab = 'commercial'; state.ui.view = 'customers';
    persist(); rerender();
  }

  function bindEvents() {
    if (global.__aionWorkScheduleEventsBound) return;
    global.__aionWorkScheduleEventsBound = true;
    document.addEventListener('click', (event) => {
      const target = event.target;
      const view = target?.closest?.('[data-ws-view]');
      if (view) { state.ui.view = view.dataset.wsView; rerender(); return; }
      if (target?.closest?.('[data-ws-open-intake]')) { state.ui.view = 'intake'; rerender(); return; }
      const editCustomer = target?.closest?.('[data-ws-edit-customer]');
      if (editCustomer) { openCustomer(editCustomer.dataset.wsEditCustomer); return; }
      const customerQuote = target?.closest?.('[data-ws-customer-quote]');
      if (customerQuote) { openCustomerQuote(customerQuote.dataset.wsCustomerQuote); return; }
      if (target?.closest?.('[data-ws-new-customer-from-work]')) {
        const form = target.closest('[data-ws-new-form]');
        if (form) {
          const values = Object.fromEntries(new FormData(form).entries());
          state.ui.newDraft = {
            ...(state.ui.newDraft || {}), ...values,
            cost_estimate:{ material_cost:values.estimated_material_cost || '', labour_cost:values.estimated_labour_cost || '', external_cost:values.estimated_external_cost || '' },
            quote:{ ...(state.ui.newDraft?.quote || {}), amount:values.quote_amount || '', subtotal:values.quote_amount || '' },
          };
        }
        openCustomer('', true); return;
      }
      if (target?.closest?.('[data-ws-new-customer]')) { state.ui.view = 'customers'; openCustomer(''); return; }
      if (target?.closest?.('[data-ws-close-customer]')) {
        const returnToWork = state.ui.customerReturnToWork;
        state.ui.modal = returnToWork ? 'new' : '';
        state.ui.customerId = ''; state.ui.customerReturnToWork = false;
        rerender(); return;
      }
      const dated = target?.closest?.('[data-ws-new-date]');
      if (dated) { openNew({ date: dated.dataset.wsNewDate, status: 'scheduled' }); return; }
      if (target?.closest?.('[data-ws-new]')) { openNew({}); return; }
      if (target?.closest?.('[data-ws-close]')) { state.ui.modal = ''; state.ui.newDraft = {}; rerender(); return; }
      const acceptAiPrice = target?.closest?.('[data-ws-accept-ai-price]');
      if (acceptAiPrice) {
        const form = acceptAiPrice.closest('[data-ws-new-form]');
        const price = form?.querySelector?.('[data-ws-quote-price]');
        if (price && acceptAiPrice.dataset.wsRecommendedPrice) {
          price.value = acceptAiPrice.dataset.wsRecommendedPrice;
          price.dataset.wsAiAccepted = 'true';
          refreshNewQuoteGuidance(form);
        }
        return;
      }
      const itemButton = target?.closest?.('[data-ws-item]');
      if (itemButton) { state.ui.selectedId = itemButton.dataset.wsItem; state.ui.panelTab = itemButton.dataset.wsPanelOpen || 'overview'; rerender(); return; }
      if (target?.closest?.('[data-ws-close-item]')) { state.ui.selectedId = ''; rerender(); return; }
      const panelTab = target?.closest?.('[data-ws-panel-tab]');
      if (panelTab) { state.ui.panelTab = panelTab.dataset.wsPanelTab; rerender(); return; }
      const fieldAction = target?.closest?.('[data-ws-field-action]');
      if (fieldAction) {
        const item = workItem(fieldAction.dataset.wsFieldItem);
        const action = fieldAction.dataset.wsFieldAction;
        if (item) {
          if (action === 'en_route') { item.status = 'en_route'; addUpdate(item, 'Marked on the way to the customer.'); }
          if (action === 'start') { item.status = 'in_progress'; addUpdate(item, 'Work started.'); }
          if (action === 'pause') { item.status = 'paused'; addUpdate(item, 'Work paused.'); }
          if (action === 'complete') { item.status = 'completed'; addUpdate(item, 'Work marked complete. Evidence and customer sign-off can still be added.'); }
          persist(); rerender();
        }
        return;
      }
      const week = target?.closest?.('[data-ws-week]');
      if (week) {
        const current = mondayOf(dateFromIso(state.ui.week));
        if (week.dataset.wsWeek === 'today') state.ui.week = isoDate(mondayOf(new Date()));
        else { current.setDate(current.getDate() + (week.dataset.wsWeek === 'next' ? 7 : -7)); state.ui.week = isoDate(current); }
        rerender(); return;
      }
      const convert = target?.closest?.('[data-ws-convert-intake]');
      if (convert) {
        const intake = state.data.intake.find((row) => row.id === convert.dataset.wsConvertIntake);
        if (intake) {
          const quoteRequest = /quote|estimate|quotation|pricing/i.test(`${intake.title || ''} ${intake.message || ''}`);
          openNew({
            intake_id: intake.id, title: intake.title, customer: intake.customer,
            customer_id: intake.customer_id, customer_email: intake.customer_email || intake.email,
            customer_phone: intake.customer_phone || intake.phone,
            customer_address: intake.customer_address || intake.address,
            source: intake.channel, notes: intake.message || intake.notes || '',
            date: intake.date || '', time: intake.time || '', duration: intake.duration || 60,
            location: intake.service_address || intake.location || intake.customer_address || intake.address || '',
            assignee: intake.assignee || '', type: quoteRequest ? 'quote' : 'job',
            status: quoteRequest ? 'quote_required' : intake.state === 'Ready to schedule' ? 'scheduled' : 'new',
          });
        }
        return;
      }
      const duplicate = target?.closest?.('[data-ws-duplicate]');
      if (duplicate) {
        const item = workItem(duplicate.dataset.wsDuplicate);
        if (item) openNew({ title: `Follow-up · ${item.title}`, customer: item.customer, type: 'visit', assignee: item.assignee, location: item.location, notes: `Follow-up for ${item.id}`, status: 'scheduled' });
        return;
      }
      if (target?.closest?.('[data-ws-upload-logo]')) {
        if (typeof global.openAionBusinessLogoSettings === 'function') global.openAionBusinessLogoSettings();
        return;
      }
      if (target?.closest?.('[data-ws-edit-quote-email-template]')) {
        if (typeof global.openAionBusinessQuoteEmailSettings === 'function') global.openAionBusinessQuoteEmailSettings();
        return;
      }
      const rewriteDescription = target?.closest?.('[data-ws-rewrite-description]');
      if (rewriteDescription) {
        const item = workItem(rewriteDescription.dataset.wsRewriteDescription);
        const textarea = item ? document.querySelector(`[data-ws-quote-description="${CSS.escape(item.id)}"]`) : null;
        const source = textarea?.value?.trim() || '';
        if (!item || !source) {
          state.ui.descriptionRewrite = { itemId:item?.id || '', status:'error', error:'Write a rough description first, then choose Rewrite professionally with SI.' };
          rerender(); return;
        }
        item.quote = { ...(item.quote || {}), description_of_work:source };
        state.ui.descriptionRewrite = { itemId:item.id, status:'working', error:'' };
        rewriteDescription.disabled = true;
        rerender();
        void apiPost(endpoint('/rewrite-description'), { text:source }).then((payload) => {
          const changed = workItem(item.id);
          if (changed && String(payload.description || '').trim()) {
            changed.quote = { ...(changed.quote || {}), description_of_work:String(payload.description).trim() };
            state.ui.descriptionRewrite = { itemId:item.id, status:'done', error:'' };
            persist(); rerender();
          }
        }).catch((error) => {
          state.ui.descriptionRewrite = { itemId:item.id, status:'error', error:String(error?.message || error) };
          rerender();
        });
        return;
      }
      const addQuoteLine = target?.closest?.('[data-ws-add-quote-line]');
      if (addQuoteLine) {
        const item = workItem(addQuoteLine.dataset.wsAddQuoteLine);
        if (item) { quoteDraftLines(item).push({ id:uid('line'), description:'New quote line', type:'service', quantity:1, unit_price:0, vat_rate:20, children:[] }); persist(); rerender(); }
        return;
      }
      const addQuoteChild = target?.closest?.('[data-ws-add-quote-child]');
      if (addQuoteChild) {
        const item = workItem(state.ui.selectedId); const line = item && quoteDraftLines(item).find((row) => row.id === addQuoteChild.dataset.wsAddQuoteChild);
        if (line) { line.children = line.children || []; line.children.push({ id:uid('calc'), description:'Cost item', type:'materials', quantity:1, cost_price:0, margin_percent:quotePricingPolicy().targetMargin }); persist(); rerender(); }
        return;
      }
      const removeQuoteLine = target?.closest?.('[data-ws-remove-quote-line]');
      if (removeQuoteLine) {
        const item = workItem(state.ui.selectedId); if (item) { item.quote.draft_lines = quoteDraftLines(item).filter((row) => row.id !== removeQuoteLine.dataset.wsRemoveQuoteLine); if (!item.quote.draft_lines.length) item.quote.draft_lines = defaultQuoteLines(item); persist(); rerender(); }
        return;
      }
      const removeQuoteChild = target?.closest?.('[data-ws-remove-quote-child]');
      if (removeQuoteChild) {
        const item = workItem(state.ui.selectedId); if (item) { quoteDraftLines(item).forEach((line) => { line.children = (line.children || []).filter((row) => row.id !== removeQuoteChild.dataset.wsRemoveQuoteChild); }); persist(); rerender(); }
        return;
      }
      const paymentPreset = target?.closest?.('[data-ws-payment-preset]');
      if (paymentPreset) {
        const item = workItem(state.ui.selectedId);
        if (item) { item.quote = { ...(item.quote || {}), payment_schedule:defaultPaymentSchedule(item, paymentPreset.dataset.wsPaymentPreset) }; persist(); rerender(); }
        return;
      }
      const addPaymentStage = target?.closest?.('[data-ws-add-payment-stage]');
      if (addPaymentStage) {
        const item = workItem(addPaymentStage.dataset.wsAddPaymentStage);
        if (item) { paymentSchedule(item).push({ id:uid('stage'), label:'Next payment', amount_type:'fixed', amount_value:'', due_type:'date', due_value:'' }); persist(); rerender(); }
        return;
      }
      const removePaymentStage = target?.closest?.('[data-ws-remove-payment-stage]');
      if (removePaymentStage) {
        const item = workItem(state.ui.selectedId);
        if (item) { item.quote.payment_schedule = paymentSchedule(item).filter((stage) => stage.id !== removePaymentStage.dataset.wsRemovePaymentStage); if (!item.quote.payment_schedule.length) item.quote.payment_schedule = defaultPaymentSchedule(item, 'upfront'); persist(); rerender(); }
        return;
      }
      const quote = target?.closest?.('[data-ws-create-quote]');
      if (quote) {
        const item = workItem(quote.dataset.wsCreateQuote);
        const lines = quoteDraftLines(item).map((line) => { const quantity=Math.max(0,moneyNumber(line.quantity)||1); const amount=parentLineTotal(line); return { description:line.description || item.title, type:line.type || 'service', quantity, unit_price:(amount/quantity).toFixed(2), tax_rate:moneyNumber(line.vat_rate) }; });
        const identity = quoteIdentity();
        const customer = customerForItem(item);
        const includeTerms = Boolean(document.querySelector(`[data-ws-quote-include-terms="${CSS.escape(item.id)}"]`)?.checked);
        const documentProfile = { business: identity, customer, description_of_work:item.quote?.description_of_work || '', terms: includeTerms ? identity.terms : '', include_terms: includeTerms, valid_days: identity.validDays, payment_method:item.quote?.payment_method || identity.paymentMethod, payment_schedule:paymentStageAmounts(item), payment_reference:identity.paymentReferenceTemplate || '{quote_number}' };
        const draftLines = JSON.parse(JSON.stringify(quoteDraftLines(item)));
        const paymentScheduleDraft = JSON.parse(JSON.stringify(paymentSchedule(item)));
        const paymentMethodDraft = item.quote?.payment_method || identity.paymentMethod;
        void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/documents`), { kind: 'quote', actor_id: 'desktop_user', line_items: lines, tax_rate: '0', document_profile: documentProfile }).then((payload) => { applyModel(payload.schedule); const changed = workItem(item.id); if (changed) { changed.quote = { ...(changed.quote || {}), draft_lines:draftLines, payment_schedule:paymentScheduleDraft, payment_method:paymentMethodDraft }; changed.quote_email_draft = {}; if (changed.status === 'quote_required') changed.status = 'awaiting_approval'; persist(); } rerender(); }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      const recommendedQuote = target?.closest?.('[data-ws-use-recommended-quote]');
      if (recommendedQuote) {
        const item = workItem(recommendedQuote.dataset.wsUseRecommendedQuote);
        const amount = recommendedQuote.dataset.wsRecommendedPrice || '';
        const input = item ? document.querySelector(`[data-ws-quote-amount="${CSS.escape(item.id)}"]`) : null;
        if (item && amount) {
          item.quote = { ...(item.quote || {}), status:'draft', amount, subtotal:amount, pricing_recommendation:{ ...(item.quote?.pricing_recommendation || {}), accepted:true, accepted_at:new Date().toISOString(), editable:true } };
          const firstLine = quoteDraftLines(item)[0];
          if (firstLine) { firstLine.children = []; firstLine.quantity = 1; firstLine.unit_price = moneyNumber(amount); }
          if (input) input.value = amount;
          addUpdate(item, 'AI pricing recommendation applied to the draft quote for human review.');
          persist(); rerender();
        }
        return;
      }
      const invoice = target?.closest?.('[data-ws-create-invoice]');
      if (invoice) {
        const item = workItem(invoice.dataset.wsCreateInvoice);
        const acceptanceWasAlreadyRecorded = item?.quote?.status === 'customer_approved';
        const amount = document.querySelector(`[data-ws-invoice-amount="${CSS.escape(item.id)}"]`)?.value || '';
        const description = document.querySelector(`[data-ws-invoice-description="${CSS.escape(item.id)}"]`)?.value || item.title;
        const taxRate = document.querySelector(`[data-ws-invoice-tax="${CSS.escape(item.id)}"]`)?.value || '0';
        void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/documents`), { kind: 'invoice', actor_id: 'desktop_user', line_items: [{ description, quantity: 1, unit_price: amount || '0' }], tax_rate: taxRate }).then((payload) => {
          applyModel(payload.schedule);
          const changed = workItem(item.id);
          if (changed && !acceptanceWasAlreadyRecorded) {
            changed.quote = { ...(changed.quote || {}), status:'customer_approved', approved_at:new Date().toISOString(), accepted_source:'recorded_by_business' };
            addUpdate(changed, 'Customer quotation acceptance recorded and the accepted quote converted into a draft invoice.');
            persist();
          }
          rerender();
        }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      const shareQuote = target?.closest?.('[data-ws-share-quote],[data-ws-save-quote]');
      if (shareQuote) {
        const itemId = shareQuote.dataset.wsShareQuote || shareQuote.dataset.wsSaveQuote;
        const mode = shareQuote.dataset.wsShareQuote ? 'share' : 'save';
        const item = workItem(itemId);
        const documentRecord = item && (item.documents || []).find((row) => row.id === shareQuote.dataset.wsDocumentId);
        if (item && documentRecord) {
          const url = quoteDocumentUrl(item, documentRecord);
          if (global.aionDesktop?.saveOrSharePdf) {
            void global.aionDesktop.saveOrSharePdf({ mode, url, filename:documentRecord.name || 'quotation.pdf', text:`Quotation ${item.quote?.number || ''} for ${item.customer || 'customer'}` })
              .then((result) => { if (result && result.ok === false && !result.cancelled) throw new Error(result.error || 'The PDF could not be shared'); })
              .catch((error) => { state.syncError = String(error?.message || error); rerender(); });
            return;
          }
          void fetch(url).then(async (response) => {
            if (!response.ok) throw new Error('The quotation PDF could not be opened');
            const blob = await response.blob();
            const file = new File([blob], documentRecord.name || 'quotation.pdf', { type:'application/pdf' });
            if (mode === 'share' && navigator.share && (!navigator.canShare || navigator.canShare({ files:[file] }))) {
              await navigator.share({ title:item.quote?.number || 'Quotation', text:`Quotation for ${item.customer || 'customer'}`, files:[file] });
              return;
            }
            const anchor = document.createElement('a');
            anchor.href = URL.createObjectURL(blob); anchor.download = documentRecord.name || 'quotation.pdf'; anchor.click();
            setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
          }).catch((error) => { state.syncError = String(error?.message || error); rerender(); });
        }
        return;
      }
      const quoteEmail = target?.closest?.('[data-ws-send-quote-email]');
      if (quoteEmail) {
        const item = workItem(quoteEmail.dataset.wsSendQuoteEmail);
        if (item) {
          const to = document.querySelector(`[data-ws-quote-email-to="${CSS.escape(item.id)}"]`)?.value?.trim() || '';
          const subject = document.querySelector(`[data-ws-quote-email-subject="${CSS.escape(item.id)}"]`)?.value?.trim() || '';
          const body = document.querySelector(`[data-ws-quote-email-body="${CSS.escape(item.id)}"]`)?.value?.trim() || '';
          quoteEmail.disabled = true;
          item.quote_email_delivery = { status:'sending', to, subject, body, document_id:quoteEmail.dataset.wsDocumentId };
          void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/quote-email-send`), { document_id:quoteEmail.dataset.wsDocumentId, to, subject, body, actor_id:'desktop_user' })
            .then((payload) => {
              if (payload.schedule) applyModel(payload.schedule);
              const changed = workItem(item.id);
              if (!changed) return;
              changed.quote_email_delivery = { ...changed.quote_email_delivery, status:'sent', to, subject, body, document_id:quoteEmail.dataset.wsDocumentId, message_id:payload.message_id || '', acceptance_url:payload.acceptance_url || '', sent_at:payload.sent_at || new Date().toISOString(), error:'' };
              state.ui.selectedId = '';
              state.ui.modal = '';
              state.ui.view = 'board';
              rerender();
            })
            .catch((error) => {
              item.quote_email_delivery = { ...item.quote_email_delivery, status:'unavailable', error:String(error?.message || error), failed_at:new Date().toISOString() };
              persist(); rerender();
            });
        }
        return;
      }
      const connectGmail = target?.closest?.('[data-ws-connect-gmail]');
      if (connectGmail) {
        if (typeof global.openAionPhase17KGmailOAuth === 'function') {
          global.openAionPhase17KGmailOAuth();
        } else if (typeof global.openAionGmailConnectionSettings === 'function') {
          global.openAionGmailConnectionSettings();
        }
        return;
      }
      const portal = target?.closest?.('[data-ws-create-portal]');
      if (portal) {
        const item = workItem(portal.dataset.wsCreatePortal);
        void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/portal-access`), { actor_id: 'desktop_user', expires_days: 30 }).then((payload) => { applyModel(payload.schedule); state.ui.portalLink = `${location.origin}${API_BASE}/api/aion/business/work-schedule/portal/${payload.token}/page`; rerender(); }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      if (target?.closest?.('[data-ws-prepare-all-reminders]')) {
        const upcoming = (state.data.items || []).filter((row) => row.date && !['completed','cancelled','paid'].includes(row.status));
        Promise.all(upcoming.map((row) => apiPost(endpoint('/actions'), { operation: 'prepare_reminder', fields: { id: row.id }, actor_id: 'desktop_user' }))).then((results) => { const latest = results[results.length - 1]; if (latest?.model) applyModel(latest.model); rerender(); }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      const documentButton = target?.closest?.('[data-ws-create-document]');
      if (documentButton) {
        const item = workItem(documentButton.dataset.wsDocumentItem);
        if (item) {
          documentButton.disabled = true;
          void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/documents`), { kind: documentButton.dataset.wsCreateDocument, actor_id: 'desktop_user' })
            .then((payload) => { applyModel(payload.schedule); rerender(); })
            .catch((error) => { state.syncError = String(error?.message || error); rerender(); });
        }
        return;
      }
      const clearSignature = target?.closest?.('[data-ws-clear-signature]');
      if (clearSignature) {
        const canvas = document.querySelector(`[data-ws-signature-pad="${CSS.escape(clearSignature.dataset.wsClearSignature)}"]`);
        canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height); return;
      }
      const saveSignature = target?.closest?.('[data-ws-save-signature]');
      if (saveSignature) {
        const item = workItem(saveSignature.dataset.wsSaveSignature);
        const canvas = document.querySelector(`[data-ws-signature-pad="${CSS.escape(item.id)}"]`);
        const name = document.querySelector(`[data-ws-signature-name="${CSS.escape(item.id)}"]`)?.value?.trim() || '';
        if (item && canvas && name) {
          item.customerSignature = { name, signedAt: new Date().toLocaleString(), dataUrl: canvas.toDataURL('image/png') };
          addUpdate(item, `Customer sign-off recorded for ${name}.`); persist(); rerender();
        } else if (!name) {
          document.querySelector(`[data-ws-signature-name="${CSS.escape(item.id)}"]`)?.focus();
        }
        return;
      }
      const replaceSignature = target?.closest?.('[data-ws-replace-signature]');
      if (replaceSignature) { const item = workItem(replaceSignature.dataset.wsReplaceSignature); if (item) { delete item.customerSignature; persist(); rerender(); } return; }
      if (target?.closest?.('[data-ws-open-financial-settings]')) {
        if (typeof global.openAionBusinessFinancialSettings === 'function') global.openAionBusinessFinancialSettings();
        return;
      }
      const retryPayment = target?.closest?.('[data-ws-retry-payment-delivery]');
      if (retryPayment) {
        const item = workItem(retryPayment.dataset.wsRetryPaymentDelivery);
        if (item) {
          const identity = quoteIdentity();
          const emailState = item.quote_email_delivery || item.quote_email_draft || {};
          retryPayment.disabled = true;
          void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/retry-payment-delivery`), {
            acceptance_url:emailState.acceptance_url || '',
            payment_method:item.quote?.payment_method || identity.paymentMethod,
            business:{ name:identity.name, email:identity.email, currency:identity.currency, bank:identity.bank, stripePaymentLink:identity.stripePaymentLink, paymentLinks:identity.paymentLinks },
            actor_id:'desktop_user',
          }).then((payload) => {
            if (payload.schedule) applyModel(payload.schedule);
            rerender();
          }).catch((error) => {
            state.syncError = String(error?.message || error);
            retryPayment.disabled = false;
            rerender();
          });
        }
        return;
      }
      const preparePayment = target?.closest?.('[data-ws-prepare-payment]');
      if (preparePayment) {
        const item = workItem(preparePayment.dataset.wsPreparePayment);
        const amount = document.querySelector(`[data-ws-payment-amount="${CSS.escape(item.id)}"]`)?.value || '';
        const method = document.querySelector(`[data-ws-payment-method="${CSS.escape(item.id)}"]`)?.value || 'Card';
        item.payment = { status: 'request_prepared', amount, method, recordedAt: new Date().toLocaleString() };
        addUpdate(item, `Payment request prepared${amount ? ` for £${amount}` : ''} by ${method}. Approval is still required before sending or charging.`); persist(); rerender(); return;
      }
      const recordPayment = target?.closest?.('[data-ws-record-payment]');
      if (recordPayment) {
        const item = workItem(recordPayment.dataset.wsRecordPayment);
        const amount = document.querySelector(`[data-ws-payment-amount="${CSS.escape(item.id)}"]`)?.value || '';
        const method = document.querySelector(`[data-ws-payment-method="${CSS.escape(item.id)}"]`)?.value || 'Card';
        item.payment = { status: 'received', amount, method, recordedAt: new Date().toLocaleString() };
        item.invoice = { ...(item.invoice || {}), status: 'paid', amount: item.invoice?.amount || amount }; item.status = 'paid';
        addUpdate(item, `Payment received recorded${amount ? `: £${amount}` : ''} via ${method}.`); persist(); rerender(); return;
      }
    }, true);

    document.addEventListener('pointerdown', (event) => {
      const canvas = event.target?.closest?.('[data-ws-signature-pad]');
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const context = canvas.getContext('2d');
      context.strokeStyle = '#102a43'; context.lineWidth = 2.5; context.lineCap = 'round'; context.lineJoin = 'round';
      context.beginPath(); context.moveTo((event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height);
      signatureDrawing = { canvas, context };
      canvas.setPointerCapture?.(event.pointerId); event.preventDefault();
    }, true);
    document.addEventListener('pointermove', (event) => {
      if (!signatureDrawing) return;
      const { canvas, context } = signatureDrawing;
      const rect = canvas.getBoundingClientRect();
      context.lineTo((event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height); context.stroke(); event.preventDefault();
    }, true);
    document.addEventListener('pointerup', () => { signatureDrawing = null; }, true);
    document.addEventListener('pointercancel', () => { signatureDrawing = null; }, true);

    document.addEventListener('change', (event) => {
      const quoteDescription = event.target?.closest?.('[data-ws-quote-description]');
      if (quoteDescription) {
        const item = workItem(quoteDescription.dataset.wsQuoteDescription);
        if (item) { item.quote = { ...(item.quote || {}), description_of_work:quoteDescription.value.trim() }; persist(); rerender(); }
        return;
      }
      const paymentMethod = event.target?.closest?.('[data-ws-payment-method-choice]');
      if (paymentMethod) {
        const item = workItem(paymentMethod.dataset.wsPaymentMethodChoice);
        if (item) { item.quote = { ...(item.quote || {}), payment_method:paymentMethod.value }; persist(); rerender(); }
        return;
      }
      const paymentField = event.target?.closest?.('[data-ws-payment-stage-field]');
      if (paymentField) {
        const item = workItem(state.ui.selectedId);
        const stageElement = paymentField.closest('[data-ws-payment-stage]');
        const stage = item && paymentSchedule(item).find((row) => row.id === stageElement?.dataset.wsPaymentStage);
        if (stage) { const key=paymentField.dataset.wsPaymentStageField; stage[key] = key === 'amount_value' ? moneyNumber(paymentField.value) : paymentField.value; persist(); rerender(); }
        return;
      }
      const labourBasis = event.target?.closest?.('[data-ws-labour-basis]');
      if (labourBasis) {
        const item = workItem(state.ui.selectedId);
        const lineElement = labourBasis.closest('[data-ws-quote-line]');
        const childElement = labourBasis.closest('[data-ws-quote-child]');
        const line = item && quoteDraftLines(item).find((row) => row.id === lineElement?.dataset.wsQuoteLine);
        const child = line && (line.children || []).find((row) => row.id === childElement?.dataset.wsQuoteChild);
        if (child) {
          child.rate_basis = labourBasis.value || 'hourly';
          const personSelect = childElement.querySelector('[data-ws-labour-person]');
          const option = personSelect?.selectedOptions?.[0];
          const rateKey = child.rate_basis === 'daily' ? 'daily' : child.rate_basis === 'monthly' ? 'monthly' : child.rate_basis === 'per_job' ? 'perjob' : 'hourly';
          if (personSelect?.value && moneyNumber(option?.dataset?.[rateKey]) > 0) child.cost_price = moneyNumber(option.dataset[rateKey]);
          persist(); rerender();
        }
        return;
      }
      const labourSelect = event.target?.closest?.('[data-ws-labour-person]');
      if (labourSelect) {
        const item = workItem(state.ui.selectedId);
        const lineElement = labourSelect.closest('[data-ws-quote-line]');
        const childElement = labourSelect.closest('[data-ws-quote-child]');
        const line = item && quoteDraftLines(item).find((row) => row.id === lineElement?.dataset.wsQuoteLine);
        const child = line && (line.children || []).find((row) => row.id === childElement?.dataset.wsQuoteChild);
        if (child) {
          const option = labourSelect.selectedOptions?.[0];
          child.labour_resource_id = labourSelect.value || '';
          child.person_id = labourSelect.value || '';
          child.type = 'labour';
          if (labourSelect.value) {
            child.description = option?.dataset.name || child.description;
            child.rate_basis = option?.dataset.basis || 'hourly';
            const rateKey = child.rate_basis === 'daily' ? 'daily' : child.rate_basis === 'monthly' ? 'monthly' : child.rate_basis === 'per_job' ? 'perjob' : 'hourly';
            child.cost_price = moneyNumber(option?.dataset?.[rateKey]) || moneyNumber(option?.dataset.rate);
          } else {
            child.rate_basis = child.rate_basis || 'hourly';
          }
          persist(); rerender();
        }
        return;
      }
      const quoteField = event.target?.closest?.('[data-ws-quote-parent-field],[data-ws-quote-child-field]');
      if (quoteField) {
        const item = workItem(state.ui.selectedId); const lineElement = quoteField.closest('[data-ws-quote-line]');
        const line = item && quoteDraftLines(item).find((row) => row.id === lineElement?.dataset.wsQuoteLine);
        if (line) {
          const childElement = quoteField.closest('[data-ws-quote-child]');
          const targetRow = childElement ? (line.children || []).find((row) => row.id === childElement.dataset.wsQuoteChild) : line;
          const key = quoteField.dataset.wsQuoteChildField || quoteField.dataset.wsQuoteParentField;
          if (targetRow && key) targetRow[key] = ['quantity','unit_price','vat_rate','cost_price','margin_percent'].includes(key) ? moneyNumber(quoteField.value) : quoteField.value;
          persist(); rerender();
        }
        return;
      }
      const customerSelect = event.target?.closest?.('[data-ws-customer-select]');
      if (customerSelect) {
        const customer = (state.data.customers || []).find((row) => String(row.id) === String(customerSelect.value));
        const form = customerSelect.form;
        if (form) {
          const put = (name, value) => { const input = form.elements.namedItem(name); if (input) input.value = value || ''; };
          put('customer', customer?.name); put('customer_email', customer?.email); put('customer_phone', customer?.phone); put('customer_address', customer?.billing_address || customer?.address);
          const location = form.elements.namedItem('location');
          if (location && !location.value && customer) location.value = customer.service_address || customer.billing_address || customer.address || '';
          const summary = form.querySelector('[data-ws-customer-summary]');
          if (summary) summary.innerHTML = customer
            ? `<strong>${esc(customer.name || 'Unnamed customer')}</strong><span>${esc([customer.email, customer.phone].filter(Boolean).join(' · ') || 'Contact details not completed')}</span><small>${esc(customer.billing_address || customer.address || '')}</small>`
            : '<strong>No customer selected</strong><span>Choose a saved customer or add one first.</span><small></small>';
        }
        return;
      }
      const newType = event.target?.closest?.('[data-ws-new-type]');
      if (newType) {
        const status = newType.form?.querySelector?.('[data-ws-new-status]');
        if (status && (status.value === 'scheduled' || status.value === 'quote_required')) {
          status.value = newType.value === 'quote' ? 'quote_required' : 'scheduled';
        }
        return;
      }
      const status = event.target?.closest?.('[data-ws-status]');
      if (status) { const item = workItem(status.dataset.wsStatus); if (item) { item.status = status.value; persist(); rerender(); } return; }
      const checklist = event.target?.closest?.('[data-ws-check-item]');
      if (checklist) { const item = workItem(checklist.dataset.wsCheckItem); const row = item?.checklist?.find((entry) => entry.id === checklist.dataset.wsCheckId); if (row) { row.done = checklist.checked; addUpdate(item, `${row.label}: ${row.done ? 'completed' : 'reopened'}.`); persist(); rerender(); } return; }
      const material = event.target?.closest?.('[data-ws-material-item]');
      if (material) { const item = workItem(material.dataset.wsMaterialItem); const row = item?.materials?.find((entry) => entry.id === material.dataset.wsMaterialId); if (row) { row.used = material.checked; persist(); rerender(); } return; }
      const file = event.target?.closest?.('[data-ws-file]');
      if (file) {
        const item = workItem(file.dataset.wsFile);
        if (item) {
          const uploads = Array.from(file.files || []).map(async (entry) => {
            const data = await readBase64(entry);
            const payload = await apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/files`), { filename: entry.name, content_type: entry.type || 'application/octet-stream', data_base64: data, actor_id: 'desktop_user' });
            applyModel(payload.schedule);
          });
          void Promise.all(uploads).then(rerender).catch((error) => { state.syncError = String(error?.message || error); rerender(); });
        }
      }
    }, true);

    document.addEventListener('input', (event) => {
      const customerForm = event.target?.closest?.('[data-ws-customer-form]');
      if (customerForm && event.target.matches?.('[data-ws-billing-address]')) {
        const same = customerForm.querySelector('[data-ws-same-address]');
        const service = customerForm.querySelector('[data-ws-service-address]');
        if (same?.checked && service) service.value = event.target.value;
        return;
      }
      const form = event.target?.closest?.('[data-ws-new-form]');
      if (!form || (!event.target.matches?.('[data-ws-pricing-cost]') && !event.target.matches?.('[data-ws-quote-price]'))) return;
      if (event.target.matches?.('[data-ws-quote-price]')) event.target.dataset.wsAiAccepted = 'false';
      refreshNewQuoteGuidance(form);
    }, true);

    document.addEventListener('change', (event) => {
      if (!event.target?.matches?.('[data-ws-same-address]')) return;
      const form = event.target.closest('[data-ws-customer-form]');
      const billing = form?.querySelector('[data-ws-billing-address]');
      const service = form?.querySelector('[data-ws-service-address]');
      if (!service) return;
      if (event.target.checked) {
        service.value = billing?.value || '';
        service.setAttribute('readonly', 'readonly');
      } else {
        service.removeAttribute('readonly');
      }
    }, true);

    document.addEventListener('dragstart', (event) => {
      const card = event.target?.closest?.('[data-ws-item][draggable="true"]');
      if (card) event.dataTransfer?.setData('text/work-item', card.dataset.wsItem || '');
    }, true);
    document.addEventListener('dragover', (event) => {
      if (event.target?.closest?.('[data-ws-drop-date]')) event.preventDefault();
    }, true);
    document.addEventListener('drop', (event) => {
      const day = event.target?.closest?.('[data-ws-drop-date]');
      const id = event.dataTransfer?.getData('text/work-item');
      const item = workItem(id);
      if (day && item) { event.preventDefault(); item.date = day.dataset.wsDropDate; addUpdate(item, `Rescheduled to ${item.date}.`); persist(); rerender(); }
    }, true);

    document.addEventListener('submit', (event) => {
      const customerForm = event.target?.closest?.('[data-ws-customer-form]');
      if (customerForm) {
        event.preventDefault();
        const values = Object.fromEntries(new FormData(customerForm).entries());
        const existing = customerRecord(values.id) || {};
        const customer = {
          ...existing,
          id: values.id || uid('customer'),
          name: String(values.name || '').trim(),
          customer_type: values.customer_type || 'person',
          contact_name: String(values.contact_name || '').trim(),
          email: String(values.email || '').trim(),
          phone: String(values.phone || '').trim(),
          billing_address: String(values.billing_address || '').trim(),
          address: String(values.billing_address || '').trim(),
          service_address: String(values.service_same_as_billing === 'yes' ? values.billing_address : values.service_address || '').trim(),
          source: values.source || 'Back office',
          notes: String(values.notes || '').trim(),
          work_item_ids: Array.isArray(existing.work_item_ids) ? existing.work_item_ids : [],
          updated_at: new Date().toISOString(),
        };
        state.data.customers = Array.isArray(state.data.customers) ? state.data.customers : [];
        const index = state.data.customers.findIndex((row) => String(row.id) === String(customer.id));
        if (index >= 0) state.data.customers[index] = customer; else state.data.customers.push(customer);
        const returnToWork = state.ui.customerReturnToWork;
        if (returnToWork) {
          state.ui.newDraft = { ...(state.ui.newDraft || {}), customer_id:customer.id, customer:customer.name, customer_email:customer.email, customer_phone:customer.phone, customer_address:customer.billing_address, location:state.ui.newDraft?.location || customer.service_address || customer.billing_address };
          state.ui.modal = 'new';
        } else {
          state.ui.modal = '';
          state.ui.view = 'customers';
        }
        state.ui.customerId = ''; state.ui.customerReturnToWork = false;
        persist(); rerender(); return;
      }
      const pilot = event.target?.closest?.('[data-ws-pilot-form]');
      if (pilot) {
        event.preventDefault();
        const instruction = String(new FormData(pilot).get('instruction') || '').trim();
        if (!instruction) return;
        state.ui.pilotMessage = 'Understanding your request…'; rerender();
        void apiPost(endpoint('/interpret'), { text: instruction }).then((payload) => {
          const result = payload.interpretation || {};
          if (result.intent === 'update_work' && result.ready) {
            const words = String(result.query || '').toLowerCase().split(/\s+/).filter((word) => word.length > 2);
            const matches = state.data.items.filter((item) => {
              const haystack = `${item.title || ''} ${item.customer || ''} ${item.id || ''}`.toLowerCase();
              return words.length && words.every((word) => haystack.includes(word));
            });
            if (matches.length === 1) {
              Object.assign(matches[0], result.fields || {});
              addUpdate(matches[0], `Work Pilot applied: ${result.summary}.`);
              state.ui.pilotMessage = `${result.summary}. The shared work record has been updated.`;
              state.ui.selectedId = matches[0].id; state.ui.panelTab = 'overview'; persist(); rerender(); return;
            }
            state.ui.pilotMessage = matches.length ? `I found ${matches.length} possible work items. Open the correct one before changing it.` : `I could not find one work item matching “${result.query || ''}”.`;
            rerender(); return;
          }
          state.ui.pilotMessage = result.missing_fields?.length ? `I understood the request. Please add: ${result.missing_fields.join(', ')}.` : 'I understood the request. Check the details, then create it.';
          openNew(result.fields || {});
        }).catch((error) => { state.ui.pilotMessage = `I could not prepare that request: ${error?.message || error}`; rerender(); });
        return;
      }
      const create = event.target?.closest?.('[data-ws-new-form]');
      if (create) {
        event.preventDefault();
        const values = Object.fromEntries(new FormData(create).entries());
        const intakeId = String(values.intake_id || '').trim();
        const sourceRequest = intakeId ? state.data.intake.find((entry) => String(entry.id) === intakeId) : null;
        const quoteAmount = values.quote_amount;
        const recommendation = quoteRecommendation({ materials: values.estimated_material_cost, labour: values.estimated_labour_cost, external: values.estimated_external_cost });
        const quoteMargin = grossMargin(recommendation.totalCost, moneyNumber(quoteAmount));
        const costEstimate = {
          material_cost: values.estimated_material_cost || '',
          labour_cost: values.estimated_labour_cost || '',
          external_cost: values.estimated_external_cost || '',
          currency: global.AionOperatingModelWorkspace?.state?.model?.currency || 'EUR',
          source: 'shared_work_record',
          updated_at: new Date().toISOString(),
        };
        delete values.quote_amount;
        delete values.estimated_material_cost;
        delete values.estimated_labour_cost;
        delete values.estimated_external_cost;
        delete values.intake_id;
        values.recurrence = { frequency: values.recurrence_frequency || 'none', count: Number(values.recurrence_count || 1) };
        values.resource_ids = String(values.resource_ids || '').split(',').map((value) => value.trim()).filter(Boolean);
        delete values.recurrence_frequency; delete values.recurrence_count;
        let selectedCustomer = customerRecord(values.customer_id, values.customer);
        if (!selectedCustomer && String(values.customer || '').trim()) {
          selectedCustomer = {
            id: values.customer_id || uid('customer'), name:String(values.customer).trim(),
            email:String(values.customer_email || '').trim(), phone:String(values.customer_phone || '').trim(),
            billing_address:String(values.customer_address || '').trim(), address:String(values.customer_address || '').trim(),
            service_address:String(values.location || '').trim(), source:values.source || 'Back office',
            customer_type:'person', work_item_ids:[], updated_at:new Date().toISOString(),
          };
          state.data.customers = Array.isArray(state.data.customers) ? state.data.customers : [];
          state.data.customers.push(selectedCustomer);
        }
        if (selectedCustomer) {
          values.customer_id = selectedCustomer.id;
          values.customer = selectedCustomer.name || '';
          values.customer_email = selectedCustomer.email || '';
          values.customer_phone = selectedCustomer.phone || '';
          values.customer_address = selectedCustomer.billing_address || selectedCustomer.address || '';
          if (!values.location) values.location = selectedCustomer.service_address || selectedCustomer.billing_address || selectedCustomer.address || '';
        }
        const item = {
          id: uid('work'), ...values, duration: Number(values.duration || 60), sample: false,
          source_request: sourceRequest ? {
            id: sourceRequest.id, title: sourceRequest.title, customer: sourceRequest.customer,
            customer_id: sourceRequest.customer_id || '', channel: sourceRequest.channel,
            received: sourceRequest.received, received_at: sourceRequest.received_at || '',
            source_reference: sourceRequest.source_reference || '',
            sales_opportunity_id: sourceRequest.sales_opportunity_id || '',
            reviewed_at: new Date().toISOString(),
          } : null,
          documents: [], updates: [], cost_estimate: costEstimate,
          quote: { status: quoteAmount ? 'draft' : 'not_created', amount: quoteAmount || '', subtotal: quoteAmount || '', gross_margin_percentage: quoteMargin || '', pricing_recommendation: { status:'draft_recommendation', suggested_amount: recommendation.suggestedPrice, target_margin_percentage: recommendation.targetMargin, minimum_margin_percentage: recommendation.minimumMargin, accepted: create.querySelector('[data-ws-quote-price]')?.dataset.wsAiAccepted === 'true', editable:true, generated_at:new Date().toISOString() } },
          invoice: { status: 'not_created', amount: '' },
        };
        state.data.items.push(item);
        if (selectedCustomer) selectedCustomer.work_item_ids = [...new Set([...(selectedCustomer.work_item_ids || []), item.id])];
        if (intakeId) state.data.intake = state.data.intake.filter((entry) => String(entry.id) !== intakeId);
        persist(); state.ui.modal = ''; state.ui.newDraft = {}; state.ui.selectedId = item.id; state.ui.panelTab = intakeId || item.type === 'quote' ? 'commercial' : 'overview'; rerender(); return;
      }
      const update = event.target?.closest?.('[data-ws-update-form]');
      if (update) {
        event.preventDefault();
        const item = workItem(update.dataset.wsUpdateForm);
        const text = String(new FormData(update).get('update') || '').trim();
        if (item && text) { item.updates = [...(item.updates || []), { text, at: new Date().toLocaleString() }]; persist(); rerender(); }
        return;
      }
      const checklist = event.target?.closest?.('[data-ws-checklist-form]');
      if (checklist) { event.preventDefault(); const item = workItem(checklist.dataset.wsChecklistForm); const label = String(new FormData(checklist).get('label') || '').trim(); if (item && label) { item.checklist = [...(item.checklist || []), { id: uid('check'), label, done: false }]; persist(); rerender(); } return; }
      const material = event.target?.closest?.('[data-ws-material-form]');
      if (material) { event.preventDefault(); const item = workItem(material.dataset.wsMaterialForm); const values = Object.fromEntries(new FormData(material).entries()); if (item && values.name) { item.materials = [...(item.materials || []), { id: uid('material'), name: values.name, quantity: Number(values.quantity || 0), unit: values.unit || 'item', unit_cost: values.unit_cost || '', used: false }]; persist(); rerender(); } return; }
      const time = event.target?.closest?.('[data-ws-time-form]');
      if (time) { event.preventDefault(); const item = workItem(time.dataset.wsTimeForm); const values = Object.fromEntries(new FormData(time).entries()); if (item && Number(values.minutes) > 0) { item.time_entries = [...(item.time_entries || []), { id: uid('time'), minutes: Number(values.minutes), note: values.note || '', at: new Date().toISOString(), by: 'desktop_user' }]; persist(); rerender(); } return; }
      const stock = event.target?.closest?.('[data-ws-stock-form]');
      if (stock) { event.preventDefault(); const values = Object.fromEntries(new FormData(stock).entries()); const quantity = Number(values.quantity || 0); const signed = ['receive','return'].includes(values.movement_type) ? quantity : -quantity; state.data.stock_movements = [...(state.data.stock_movements || []), { id: uid('stock'), name: values.name, quantity: signed, unit: values.unit || 'item', movement_type: values.movement_type, at: new Date().toISOString(), by: 'desktop_user' }]; persist(); rerender(); return; }
    }, true);
  }

  function ensureStyles() {
    if (document.getElementById('aion-work-schedule-styles')) return;
    const style = document.createElement('style');
    style.id = 'aion-work-schedule-styles';
    style.textContent = `
      .ws-field-device-head strong{color:#fff}.ws-detail-panel>nav button{flex:1;padding:10px 8px;font-size:10px}.ws-detail-panel>nav button:last-child{min-width:142px}
      @media(max-width:1050px){.ws-calendar-grid{grid-template-columns:repeat(7,minmax(170px,1fr))}.ws-metrics{grid-template-columns:1fr 1fr}.ws-header{grid-template-columns:1fr}.ws-header-actions{grid-row:2}.ws-intake-list article{grid-template-columns:70px 1fr}.ws-intake-list article>small,.ws-intake-list article>button{grid-column:2}.ws-calendar-footer small{display:none}.ws-field-layout{grid-template-columns:1fr}.ws-field-layout>aside{display:none}}
      @media(max-width:720px){.ws-surface{padding:0 10px 50px 76px!important}.ws-header{padding:20px 16px}.ws-header h1{font-size:26px}.ws-view-tabs{padding:0;overflow:auto}.ws-pilot-bar{align-items:flex-start;flex-direction:column}.ws-modal form{grid-template-columns:1fr}.ws-modal label.wide,.ws-modal footer{grid-column:1}.ws-overview dl,.ws-commercial{grid-template-columns:1fr}.ws-commercial>p,.ws-commercial article.ws-payment{grid-column:1}.ws-calendar-footer{overflow:auto}.ws-field>header{display:grid}.ws-field-summary{overflow:auto}.ws-field-layout{padding:8px}.ws-field-device{border-radius:0}.ws-field-card{grid-template-columns:72px 1fr}.ws-field-time{padding:12px 9px}.ws-field-actions button{flex:1}.ws-payment>div{display:grid}.ws-document-actions{display:grid!important}}
    `;
    document.head.appendChild(style);
  }

  ensureStyles();
  bindEvents();
  if (global.__aionWorkScheduleRefreshTimer) global.clearInterval(global.__aionWorkScheduleRefreshTimer);
  global.__aionWorkScheduleRefreshTimer = global.setInterval(() => { void refreshFromBackend(); }, 8000);
  global.AionWorkScheduleWorkspace = { render: renderSurface, state, openNew };
})(window);
