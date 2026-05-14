# Bomi Payout Workflow Meta Feed Ad

Last updated: 2026-05-13, America/Los_Angeles

This is the replacement for the rejected credit-card/EFT ad. It uses the updated square asset. It was initially created with `FINANCIAL_PRODUCTS_SERVICES` because Meta rejected the prior version under `Financial and Insurance Products and Services`; that designation was removed on 2026-05-11 after user clarification.

Important current-state note: this stack was originally documented as paused, but the 2026-05-13 API readback shows the campaign, ad set, and ad are all `ACTIVE` and spending.

Do not store Meta access tokens here. Runtime secrets live in `/Users/dax/bomi/bomi-ads/.env`, which should remain git-ignored. Use `#` for comments in `.env` files, not `//`.

## Created Meta Objects

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)
- Campaign: `120247820755190170`
- Ad set: `120247820755420170`
- Creative: `2209355609892966`
- Ad: `120247820756460170`

Latest readback on 2026-05-13:

- Campaign status: `ACTIVE`
- Campaign effective status: `ACTIVE`
- Campaign special ad categories: `[]`
- Ad set status: `ACTIVE`
- Ad set configured status: `ACTIVE`
- Ad set effective status: `ACTIVE`
- Ad status: `ACTIVE`
- Ad configured status: `ACTIVE`
- Ad effective status: `ACTIVE`
- Ad set daily budget: `1500` cents = `$15/day`
- 2026-05-13 performance at readback: `$7.38` spend, 924 impressions, 18 clicks, 14 link clicks, 6 landing page views

## Creative

Source file:

- `../Bomi Health Ad Campaign - Meta Ad - Tired of This_ (1).png`

Uploaded image hash:

- `4b91972376b85837345eee4d1447a21c`

Media verification:

- Source asset is a 1080x1080 PNG.
- Creative `2209355609892966` readback included `image_hash=4b91972376b85837345eee4d1447a21c`.
- Meta returned valid `DESKTOP_FEED_STANDARD`, `MOBILE_FEED_STANDARD`, and `INSTAGRAM_STANDARD` preview iframe bodies for ad `120247820756460170`.

Ad copy used:

```text
For Illinois therapy practices: Bomi helps clean up payout workflows and move insurance payments toward simpler direct deposit reconciliation. Book a free consult.
```

Headline:

```text
Simpler Payout Workflows
```

Description:

```text
Billing workflow support for Illinois therapy practices.
```

CTA:

```text
BOOK_NOW
```

Landing URL:

```text
https://billwithbomi.com/?utm_source=meta&utm_medium=paid_social&utm_campaign=eft_ach_payment_workflows_il_sac&utm_content=meta_feed_payout_workflows_financial_category&utm_audience=illinois_broad_sac
```

Effective object story:

- `588675787671641_122188404704865755`

## Targeting

The ad set targets Meta Feed placements:

- `publisher_platforms`: `facebook`, `instagram`
- `facebook_positions`: `feed`
- `instagram_positions`: `stream`

Geo and age:

- Illinois, region key `3856`
- Meta readback location types: `home` and `recent`
- Age `18-65+`

Targeting caveat:

- The prior rejected version used detailed therapist/operator `flexible_spec` targeting.
- This replacement currently does not use detailed targeting; it uses broad Illinois feed targeting.
- Meta readback still returned `targeting_automation.advantage_audience=1`.

## Creation Notes

- Created paused.
- The rejected previous ad `120247819417890170` was deleted before this replacement was created.
- The campaign was initially created with `special_ad_categories=["FINANCIAL_PRODUCTS_SERVICES"]` and `special_ad_category_country=["US"]`, then updated to `special_ad_categories=[]` on 2026-05-11.
- This stack uses the documented Bomi Meta ad account `act_302351874007793`.
- The campaign/ad set/ad are already active as of the 2026-05-13 readback. Do not change status, budget, targeting, or creative without explicit user approval because the ad set has a `$15/day` budget.
