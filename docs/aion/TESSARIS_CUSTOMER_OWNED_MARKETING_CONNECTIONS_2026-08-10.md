# Tessaris Customer-Owned Marketing Connections

**Date:** 10 August 2026  
**Status:** implemented; production provider applications and live account exams remain deployment tasks

## Outcome

Tessaris now has a provider-neutral Marketing Connections Centre for Meta, Google Ads, YouTube, LinkedIn and TikTok. Each Tessaris business authorises its own platform account through OAuth. The platform account remains owned and billed by that customer; Tessaris holds only delegated access.

Account connection does not authorise publication or advertising spend. Three permissions remain distinct:

1. performance analytics;
2. approved organic publishing;
3. advertising management.

An exact content/campaign package and a separate approval remain mandatory before any external execution. Advertising additionally requires a bounded spend ceiling and owner-level authority.

## Security and tenancy

- OAuth uses state, a 15-minute pending authorisation and PKCE.
- Access and refresh tokens are stored in macOS Keychain under `com.tessaris.marketing.oauth`; tokens never enter the Business Container or renderer.
- Business files contain only provider, scopes, public account identifiers, selected accounts, health, audit timestamps and a non-secret Keychain reference.
- Every secret key is namespaced by canonical business ID and provider.
- Disconnect removes token material and clears account selection.
- Read-only connector exams enumerate accounts but cannot publish, message or spend.
- Explicit provider selection never falls through to another provider.

The current desktop authentication boundary is honest: if the organisation has no people records, `desktop_user` receives a single-user bootstrap for connection administration. Once active people exist, `marketing.connect_accounts` is required. Owner/Director and Marketing Manager include that capability; Marketing Contributor does not. Only Owner/Director includes `marketing.approve_spend`.

## Provider assets

Meta discovery includes Pages, linked Instagram business accounts and advertising accounts. Google Ads enumerates accessible customer IDs using Tessaris's developer token. YouTube enumerates channels. LinkedIn and TikTok enumerate the authorised member/creator identity. A user must explicitly select the asset used by the publication connector.

## Deployment configuration

Tessaris operates one reviewed developer application per platform, while every customer grants access to their own accounts. Required server-side configuration is:

- Meta: `META_APP_ID`, `META_APP_SECRET`, optionally `META_GRAPH_API_VERSION`;
- Google/YouTube: `GOOGLE_MARKETING_CLIENT_ID`, `GOOGLE_MARKETING_CLIENT_SECRET` (or the existing Google client variables);
- Google Ads: `GOOGLE_ADS_DEVELOPER_TOKEN`, optionally `GOOGLE_ADS_API_VERSION`;
- LinkedIn: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`;
- TikTok: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`;
- callback base: `AION_PUBLIC_BACKEND_URL`.

Production requires registering the exact callback URLs, completing each platform's app review where required, setting a public HTTPS callback base, and running read-only exams. Those are external deployment facts, not missing application architecture.

## Deliberate boundary

No post, advertisement, message or external change was made during this build. Paid provider credentials were not invented, and no live platform authorisation was attempted. Publication execution remains closed even after OAuth until the separately hash-bound package and authority checks pass.
