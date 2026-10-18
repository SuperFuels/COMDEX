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

  // Prices, volume, customer terms, labour, production capacity, materials,
  // overhead lines, debt schedules and targets are structured records in the
  // Business Operating Model. Finance asks only for judgement that cannot be
  // reliably inferred from accounting data or a table.
  const questions = [
    ['currency', 'Please confirm the reporting currency Finance should use.'],
    ['cash_buffer_policy', 'What minimum cash reserve should Finance protect? If the imported closing cash is no longer representative, please also provide the current approximate balance.'],
    ['unrecorded_liabilities', 'Are there any overdue or unrecorded amounts owed to suppliers, contractors or tax authorities that are not visible in the connected accounts? You can say no.'],
    ['tax_context', 'Which taxes does the business currently account for, and how often are they filed? If you are unsure, say that your accountant should confirm this.'],
    ['finance_priorities', 'Is there any financial risk, constraint or priority the records do not show that the Boardroom should know now? You can say no.'],
  ].map(([id, prompt]) => ({ id, prompt, capture_mode: 'conversation', owner: 'finance' }));

  global.AionFinanceDiscoverySchema = Object.freeze({
    version: 'aion.finance.discovery.v2',
    accountingPlatforms,
    evidenceSources,
    questions,
  });
})(window);
