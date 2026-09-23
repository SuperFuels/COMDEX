(function installAionCommerceSourceSchema(global) {
  'use strict';

  const providers = [
    ['shopify', 'Shopify', 'commerce_platform'],
    ['magento', 'Magento / Adobe Commerce', 'commerce_platform'],
    ['square', 'Square', 'point_of_sale_and_payments'],
    ['woocommerce', 'WooCommerce', 'commerce_platform'],
    ['amazon', 'Amazon Marketplace', 'marketplace'],
    ['ebay', 'eBay', 'marketplace'],
  ].map(([id, label, source_type]) => ({ id, label, source_type }));

  const contract = Object.freeze({
    schema_version: 'aion.commerce_source_projection.v1',
    system_owner: 'sales',
    consumers: ['finance', 'operations', 'marketing', 'support', 'boardroom'],
    source_of_truth: 'provider_read_only_sync',
    raw_data_location: 'business_container/sales/commerce_sources/{provider}/syncs/{sync_id}',
    sales_projection: [
      'orders', 'units', 'customers', 'products', 'channels', 'discounts',
      'returns', 'refunds', 'conversion_context',
    ],
    finance_projection: [
      'gross_sales', 'discounts', 'refunds', 'net_sales', 'tax_collected',
      'shipping_income', 'platform_fees', 'payment_fees', 'payouts',
      'cost_of_goods_sold', 'currency', 'period',
    ],
    boundaries: {
      commerce_credentials_owned_by_sales: true,
      finance_receives_normalised_projection: true,
      finance_does_not_duplicate_provider_connection: true,
      raw_order_customer_data_excluded_from_boardroom_prompt: true,
      provider_writes_enabled: false,
      approval_required_for_future_writes: true,
    },
  });

  global.AionCommerceSourceSchema = Object.freeze({ providers, contract });
})(window);
