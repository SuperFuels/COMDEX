from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Dict


"""Truthful catalogue for the external services a small business can connect.

The catalogue deliberately separates a provider's purpose from its implementation
state.  A listed provider is never treated as connected merely because an adapter
or contract exists in the repository.
"""


_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "gmail": {
        "label": "Gmail / Google Workspace",
        "category": "mailbox",
        "purpose": "Read business mail, prepare drafts and send approved replies.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.gmail.credentials",
        "environment": (),
    },
    "microsoft_outlook": {
        "label": "Microsoft Outlook / Microsoft 365",
        "category": "mailbox",
        "purpose": "Read Microsoft 365 mail, prepare drafts and send approved replies through Microsoft Graph.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.microsoft_outlook.credentials",
        "environment": ("MICROSOFT_GRAPH_ACCESS_TOKEN",),
    },
    "mailchimp_marketing": {
        "label": "Mailchimp Marketing",
        "category": "marketing",
        "purpose": "Manage audiences and prepare marketing campaigns; it is not the default appointment-reminder transport.",
        "auth": "api_key_or_oauth2",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.mailchimp_marketing.credentials",
        "environment": ("MAILCHIMP_API_KEY", "MAILCHIMP_SERVER_PREFIX"),
    },
    "resend": {
        "label": "Resend",
        "category": "transactional_email",
        "purpose": "Deliver booking confirmations, reminders, job updates and documents from a verified business domain.",
        "auth": "api_key",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.resend.credentials",
        "environment": ("RESEND_API_KEY", "RESEND_FROM_EMAIL"),
    },
    "postmark": {
        "label": "Postmark",
        "category": "transactional_email",
        "purpose": "Alternative transactional delivery with message streams and delivery history.",
        "auth": "api_key",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.postmark.credentials",
        "environment": ("POSTMARK_SERVER_TOKEN",),
    },
    "sendgrid": {
        "label": "Twilio SendGrid",
        "category": "transactional_email",
        "purpose": "Large-provider alternative for transactional and marketing email.",
        "auth": "api_key",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.sendgrid.credentials",
        "environment": ("SENDGRID_API_KEY",),
    },
    "mailgun": {
        "label": "Mailgun",
        "category": "transactional_email",
        "purpose": "Mature transactional-email alternative with inbound routing and delivery events.",
        "auth": "api_key",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.mailgun.credentials",
        "environment": ("MAILGUN_API_KEY", "MAILGUN_DOMAIN"),
    },
    "brevo": {
        "label": "Brevo",
        "category": "transactional_email",
        "purpose": "European-focused alternative combining transactional email, campaigns and customer messaging.",
        "auth": "api_key",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.brevo.credentials",
        "environment": ("BREVO_API_KEY",),
    },
    "amazon_ses": {
        "label": "Amazon SES",
        "category": "transactional_email",
        "purpose": "Infrastructure-oriented email delivery for businesses already operating on AWS.",
        "auth": "service_account",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.amazon_ses.credentials",
        "environment": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
    },
    "twilio_messaging": {
        "label": "Twilio Messaging",
        "category": "sms",
        "purpose": "Send approved SMS booking confirmations, reminders and field-service updates.",
        "auth": "api_key",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.twilio_messaging.credentials",
        "environment": ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"),
    },
    "google_routes": {
        "label": "Google Maps Routes",
        "category": "routing",
        "purpose": "Travel times, route matrices and multi-stop field schedules with traffic-aware routing.",
        "auth": "api_key",
        "implementation": "catalogued",
        "recommended": True,
        "credential_key": "vault.google_routes.credentials",
        "environment": ("GOOGLE_MAPS_API_KEY",),
    },
    "mapbox_optimization": {
        "label": "Mapbox Optimization",
        "category": "routing",
        "purpose": "Alternative route optimisation and mapping for custom field applications.",
        "auth": "api_key",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.mapbox.credentials",
        "environment": ("MAPBOX_ACCESS_TOKEN",),
    },
    "xero": {
        "label": "Xero",
        "category": "accounting",
        "purpose": "Post approved contacts, invoices and payments into the accounting ledger.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.xero.credentials",
        "environment": (),
    },
    "quickbooks_online": {
        "label": "QuickBooks Online",
        "category": "accounting",
        "purpose": "Alternative ledger integration for customers using Intuit accounting.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.quickbooks_online.credentials",
        "environment": (),
    },
    "sage_accounting": {
        "label": "Sage Business Cloud Accounting",
        "category": "accounting",
        "purpose": "Alternative ledger integration for Sage customers.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.sage_accounting.credentials",
        "environment": (),
    },
    "freeagent": {
        "label": "FreeAgent",
        "category": "accounting",
        "purpose": "UK micro-business and contractor accounting through the shared accountant harness.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": False,
        "credential_key": "vault.freeagent.credentials",
        "environment": (),
    },
    "freshbooks": {
        "label": "FreshBooks",
        "category": "accounting",
        "purpose": "Service-business invoicing and expenses through the shared accountant harness.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": False,
        "credential_key": "vault.freshbooks.credentials",
        "environment": (),
    },
    "zoho_books": {
        "label": "Zoho Books",
        "category": "accounting",
        "purpose": "Accounting alternative for businesses already operating in the Zoho suite.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": False,
        "credential_key": "vault.zoho_books.credentials",
        "environment": (),
    },
    "hubspot": {
        "label": "HubSpot",
        "category": "crm",
        "purpose": "Synchronise contacts, companies, deals and activity with the Sales record.",
        "auth": "oauth2",
        "implementation": "adapter_ready",
        "recommended": True,
        "credential_key": "vault.hubspot.credentials",
        "environment": (),
    },
    "salesforce": {
        "label": "Salesforce",
        "category": "crm",
        "purpose": "Enterprise CRM alternative for accounts, contacts, opportunities and activity.",
        "auth": "oauth2",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.salesforce.credentials",
        "environment": (),
    },
    "pipedrive": {
        "label": "Pipedrive",
        "category": "crm",
        "purpose": "Small-business sales pipeline alternative for people, organisations, deals and activity.",
        "auth": "oauth2",
        "implementation": "catalogued",
        "recommended": True,
        "credential_key": "vault.pipedrive.credentials",
        "environment": (),
    },
    "zoho_crm": {
        "label": "Zoho CRM",
        "category": "crm",
        "purpose": "CRM alternative for businesses already using the Zoho suite.",
        "auth": "oauth2",
        "implementation": "catalogued",
        "recommended": False,
        "credential_key": "vault.zoho_crm.credentials",
        "environment": (),
    },
}


def get_business_integration_catalog() -> Dict[str, Any]:
    providers = []
    for provider_id, definition in _PROVIDERS.items():
        item = deepcopy(definition)
        required_environment = list(item.pop("environment", ()))
        configured = bool(required_environment) and all(bool(os.getenv(key)) for key in required_environment)
        providers.append(
            {
                "provider_id": provider_id,
                **item,
                "configured": configured,
                "connected": False,
                "required_setup": required_environment,
                "live_actions_enabled": False,
            }
        )
    return {
        "schema_version": "tessaris.business_integrations.v1",
        "providers": providers,
        "provider_count": len(providers),
        "payments_deferred": True,
        "claim_boundary": "Configured means required local settings are present. Connected and live actions require a provider health check and an approved, receipt-backed action.",
    }
