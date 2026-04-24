# Daily Ads Report - 2026-04-22

Source: Google Ads API REST via local `.env` credentials (attempted; blocked before data retrieval)
Account: Bomi Health, Inc. / `561-309-1482`
Timezone: America/Los_Angeles
Primary window: 2026-04-22
Comparisons: prior day 2026-04-21; same weekday last week 2026-04-15; last 7 full days 2026-04-16 through 2026-04-22
Data freshness: Live API access attempted at 2026-04-23 23:09 PDT / 2026-04-24 06:09 UTC. OAuth token refresh failed locally with DNS error `URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>`, so no Google Ads metrics were returned.

## Executive Readout

No live performance readout is available for 2026-04-22. The automation could not resolve `oauth2.googleapis.com` from the terminal, so spend, clicks, conversions, CPA, pacing, search terms, and campaign-level changes cannot be verified. Treat this report as a data-access blocker, not a performance assessment.

## Scorecard

| Metric | Primary period | Vs prior day | Vs same weekday last week | Last 7 days |
| --- | ---: | ---: | ---: | ---: |
| Cost | Unavailable | Unavailable | Unavailable | Unavailable |
| Impressions | Unavailable | Unavailable | Unavailable | Unavailable |
| Clicks | Unavailable | Unavailable | Unavailable | Unavailable |
| CTR | Unavailable | Unavailable | Unavailable | Unavailable |
| Avg CPC | Unavailable | Unavailable | Unavailable | Unavailable |
| Conversions | Unavailable | Unavailable | Unavailable | Unavailable |
| Conversion rate | Unavailable | Unavailable | Unavailable | Unavailable |
| Cost / conversion | Unavailable | Unavailable | Unavailable | Unavailable |
| Conversion value / ROAS | Unavailable | Unavailable | Unavailable | Unavailable |

## Campaigns

| Campaign | Status | Budget | Cost | Clicks | Conversions | CPA | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `schedule meeting` | Last locally verified enabled | $15.00/day | Unavailable | Unavailable | Unavailable | Unavailable | Last verified in local prep notes from 2026-04-24; daily performance not refreshed. |
| `General Bomi Leads` | Last locally verified enabled | $25.00/day | Unavailable | Unavailable | Unavailable | Unavailable | Last verified in local prep notes from 2026-04-24; daily performance not refreshed. |

## What Changed

- No campaign, spend, conversion, CPA, or search-term change can be verified because the live API request failed before Google Ads returned data.
- The blocker is unchanged from the prior automation run: local terminal DNS/network access cannot resolve Google OAuth endpoints.
- The intended comparison windows for the next successful run are 2026-04-22 vs 2026-04-21, 2026-04-15, and 2026-04-16 through 2026-04-22.

## Watchlist

- Live reporting is blocked until the terminal can resolve `oauth2.googleapis.com` and then reach `googleads.googleapis.com`.
- Daily spend pacing cannot be confirmed against the last verified enabled daily budgets of $15.00/day and $25.00/day.
- Search-term waste, conversion tracking, budget-limited status, policy-limited status, and rank/budget lost impression share could not be checked.

## Recommended Actions

1. Restore terminal DNS/network access for `oauth2.googleapis.com` and `googleads.googleapis.com`, then rerun the daily report for 2026-04-22.
2. If terminal API access will remain unavailable, export Google Ads data for 2026-04-15 through 2026-04-22 with campaign, ad group, search term, cost, impressions, clicks, conversions, conversion value, status, budget, and impression-share columns.
3. Do not make budget, bid, keyword, or campaign changes from this report alone; no live performance data was retrieved.

## Data Notes

- This report uses the previous full calendar day in the account timezone: 2026-04-22 America/Los_Angeles.
- The local workspace identifies the account timezone as America/Los_Angeles and the customer as Bomi Health, Inc. / `561-309-1482`.
- Last locally verified campaign context comes from `docs/CLONE_PREP.md`; it is not a substitute for live daily metrics.
