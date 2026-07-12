(function installAionFinanceDiscoverySchema(global) {
  'use strict';

  const accountingPlatforms = [
    ['xero', 'Xero', 'Cloud accounting and bookkeeping'],
    ['quickbooks', 'QuickBooks', 'Accounting, invoices and expenses'],
    ['sage', 'Sage', 'Accounting, payroll and compliance'],
    ['freeagent', 'FreeAgent', 'Small-business accounting'],
    ['freshbooks', 'FreshBooks', 'Invoices, time and expenses'],
    ['zoho_books', 'Zoho Books', 'Accounting and finance operations'],
    ['other', 'Other software', 'Record another accounting system'],
    ['none', 'No accounting software', 'Continue with records or estimates'],
  ].map(([id, label, description]) => ({ id, label, description }));

  const evidenceSources = [
    ['spreadsheets', 'Spreadsheets', 'Budgets, cash flow, costs or sales data'],
    ['bank_statements', 'Bank statements', 'Cash movement and reconciliation evidence'],
    ['invoices_receipts', 'Invoices & receipts', 'Income, suppliers and expense evidence'],
    ['management_accounts', 'Management accounts', 'Profit and loss, balance sheet and reports'],
    ['vat_tax', 'VAT / tax reports', 'Tax obligations, filings and payment dates'],
    ['payroll', 'Payroll records', 'Wages, contractors and employment costs'],
    ['payment_processors', 'Payment processors', 'Stripe, PayPal, card or marketplace receipts'],
    ['crm_sales', 'CRM / sales records', 'Pipeline, won revenue and customer value'],
  ].map(([id, label, description]) => ({ id, label, description }));

  const questions = [
    ['revenue_model', 'How does the business charge customers, and what are the main prices or price ranges?'],
    ['revenue_monthly', 'What is the average monthly revenue? A range is fine.'],
    ['revenue_pattern', 'Is revenue steady, seasonal, project-based, recurring, or a mixture?'],
    ['direct_costs', 'What direct costs are incurred when delivering a sale or job?'],
    ['fixed_costs', 'What are the main fixed monthly overheads and their approximate amounts?'],
    ['labour_owner', 'What does owner time cost the business, and how many delivery hours are available each month?'],
    ['cash_position', 'What is the current cash position and minimum cash buffer the business should protect?'],
    ['receivables', 'How much is currently owed by customers, and how quickly do customers usually pay?'],
    ['payables', 'What is currently owed to suppliers, tax authorities, lenders, or contractors?'],
    ['tax_vat', 'What VAT, sales-tax, corporation-tax, or other tax obligations apply?'],
    ['debt_finance', 'Does the business have loans, credit cards, leases, or other finance commitments?'],
    ['targets_limits', 'What profit, cash, revenue, or cost targets matter most, and what spending requires approval?'],
  ].map(([id, prompt]) => ({ id, prompt }));

  global.AionFinanceDiscoverySchema = Object.freeze({
    version: 'aion.finance.discovery.v1',
    accountingPlatforms,
    evidenceSources,
    questions,
  });
})(window);
