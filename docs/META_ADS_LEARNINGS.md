# Meta Ads Learnings

Last updated: 2026-05-11, America/Los_Angeles

This repo can safely create and inspect Bomi Meta ads through the Marketing API, but it is production-adjacent. Prefer read-only checks first, create new objects paused, and only activate after explicit user approval.

## Current Working API Pattern

- Use Graph API `v22.0`.
- Use `/Users/dax/.cache/bomi-ads-venv/bin/python`; it has the needed `requests` dependency.
- Runtime secrets live only in local ignored `.env`.
- The documented Bomi Meta ad account is `act_302351874007793`. On 2026-05-11, the local `.env` `META_AD_ACCOUNT_ID` did not match that account, so scripts used the documented account explicitly.
- Create campaigns with `objective=OUTCOME_TRAFFIC`, `buying_type=AUCTION`, `special_ad_categories=[]`, `is_adset_budget_sharing_enabled=false`, and `status=PAUSED`.
- Create ad sets with ad-set-level `daily_budget`, `billing_event=IMPRESSIONS`, `optimization_goal=LINK_CLICKS`, `bid_strategy=LOWEST_COST_WITHOUT_CAP`, `destination_type=WEBSITE`, and `status=PAUSED`.
- Create Page-backed creatives with `page_id=588675787671641`; direct `instagram_actor_id` creation failed for this setup.
- After creation or activation, read back campaign/ad-set/ad `status`, `effective_status`, budgets, targeting, creative IDs, and previews.

## Targeting Lessons

- The exact therapist-title audience is small but useful as a control. Keep it separate from broader scaling tests.
- For broader therapist/practice-operator ads, use Illinois plus age `25-65+`, therapist/admin/billing/operator signals, and `targeting_automation.advantage_audience=1`.
- Put heterogeneous signals inside a single `flexible_spec` group. A top-level mix of work positions, industries, behaviors, and interests caused Meta to reject the audience as too narrow.
- Do not include generic `Psychology` as a scale lever for niche B2B billing offers; earlier checks showed it is far too noisy.
- Targeting Search changes over time. On 2026-05-11, Meta did not return usable targetable terms for several desired EHR/tool terms such as `SimplePractice`, `TherapyNotes`, `Sessions Health`, `Availity`, `CAQH`, `Psychology Today`, `Medicaid`, `Medical billing`, `Revenue cycle management`, or `Mental health care`.
- The `/reachestimate` endpoint returned a permissions error for the available token even though normal reads/writes worked, so do not depend on reach estimates until permissions are fixed.

## Location And Placement Gotchas

- Do not explicitly send `geo_locations.location_types=["home"]`. Meta rejects it as a removed location-targeting option. Send the Illinois region key and let Meta read back the accepted default `["home","recent"]`.
- Square 1080x1080 assets are a natural fit for Facebook/Instagram feed placements.
- Story placements should use 1080x1920 story-specific assets.
- Always request previews after creation. `DESKTOP_FEED_STANDARD`, `MOBILE_FEED_STANDARD`, and `INSTAGRAM_STORY` preview bodies have been useful smoke checks.

## Copy And Landing Page Notes

- Use business-operations language, not personal financial or health-attribute language.
- For BCCHP ads, `BCBSIL Medicaid / BCCHP` is clearer than only saying `BCCHP`.
- Use UTMs on every ad so reporting can separate campaign, content, and audience.
- A credit-card/EFT workflow ad was rejected under `Financial and Insurance Products and Services`. The likely trigger was the combination of `virtual credit cards`, `insurance payments`, `EFT/ACH direct deposit`, and `payment workflows` in a campaign created with `special_ad_categories=[]`. Future payment-workflow ads should either avoid financial-product/payment-service framing or be rebuilt intentionally as a financial-products/services special-ad-category campaign with compliant targeting.
- If the user confirms a payout-workflow ad should not be treated as financial-products/services, remove the designation by updating the campaign to `special_ad_categories=[]`; readback should show an empty array. The 2026-05-11 replacement kept broad Illinois feed targeting after the designation was removed.

## Activation Discipline

- Creating paused objects is not the same as launching spend.
- Activating a campaign requires the campaign, ad set, and ad all to be `ACTIVE`.
- Read back immediately after activation. On 2026-05-11, the recommended BCCHP campaign, four ad sets, and four ads all read back `ACTIVE` with effective status `ACTIVE`.
- Existing active ads are not automatically replaced. If new ads are activated while old ads remain active, total spend increases.
