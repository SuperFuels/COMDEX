(function installAionFinanceModelBuilder(global) {
  'use strict';
  function numbers(value) { return (String(value || '').replace(/,/g, '').match(/-?\d+(?:\.\d+)?/g) || []).map(Number).filter(Number.isFinite); }
  function midpoint(value) {
    const found = numbers(value); if (!found.length) return null;
    const text = String(value || '').toLowerCase();
    // Evidence summaries commonly contain a monthly amount followed by its
    // annual total.  Those are two different periods, not a numeric range.
    if (/average\s+monthly|per\s+month|monthly.+(?:annual|fy\d{4}|total)/i.test(text)) return found[0];
    const explicitRange = /\bbetween\b|\bfrom\b[^.]{0,30}\bto\b|\d\s*[-–—]\s*[€£$]?\s*\d/i.test(text);
    return explicitRange && found.length > 1 ? (found[0] + found[1]) / 2 : found[0];
  }
  function money(value, field) { const amount = midpoint(value); return amount == null ? null : { value: amount, field, source: 'founder_provided_text', verification: 'unverified' }; }
  function build(state = {}) {
    const a = state.answers || {}, monthlyRevenue = money(a.revenue_monthly, 'revenue_monthly'), fixedMonthly = money(a.fixed_cost_monthly, 'fixed_cost_monthly'), directMonthly = money(a.direct_cost_monthly, 'direct_cost_monthly');
    const metrics = {}, assumptions = [], missing_information = [];
    if (monthlyRevenue) { metrics.average_monthly_revenue = monthlyRevenue; metrics.annualised_revenue = { value: monthlyRevenue.value * 12, calculation: 'average_monthly_revenue * 12', verification: 'calculated_from_unverified_input' }; }
    if (monthlyRevenue && directMonthly) { const gross = monthlyRevenue.value - directMonthly.value; metrics.monthly_gross_profit = { value: gross, calculation: 'monthly_revenue - monthly_direct_costs', verification: 'calculated_from_unverified_input' }; metrics.gross_margin_percent = { value: monthlyRevenue.value ? gross / monthlyRevenue.value * 100 : null, calculation: 'gross_profit / revenue * 100', verification: 'calculated_from_unverified_input' }; }
    if (monthlyRevenue && directMonthly && fixedMonthly) { const net = monthlyRevenue.value - directMonthly.value - fixedMonthly.value; metrics.monthly_operating_surplus = { value: net, calculation: 'revenue - direct_costs - fixed_costs', verification: 'calculated_from_unverified_input' }; metrics.operating_margin_percent = { value: monthlyRevenue.value ? net / monthlyRevenue.value * 100 : null, calculation: 'operating_surplus / revenue * 100', verification: 'calculated_from_unverified_input' }; }
    if (numbers(a.fixed_cost_monthly).length > 1) assumptions.push({ field: 'fixed_cost_monthly', text: 'The supplied numeric range midpoint was used.', requires_review: true });
    if (!monthlyRevenue) missing_information.push('numeric average monthly revenue');
    if (!directMonthly) missing_information.push('numeric monthly direct costs');
    if (!fixedMonthly) missing_information.push('numeric monthly fixed costs');
    if (!String(a.cash_position || '').trim()) missing_information.push('cash balance and protected cash buffer');
    return { pricing_model: { charging_and_prices: a.revenue_model || null, source: 'finance_discovery' }, direct_cost_model: { parsed_monthly_direct_cost: directMonthly }, capacity_model: { owner_capacity_and_cost: a.labour_owner || null }, metrics, assumptions, missing_information };
  }
  global.AionFinanceModelBuilder = Object.freeze({ build, numbers, midpoint });
})(window);
