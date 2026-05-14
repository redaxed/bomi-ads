# Bomi EFT/ACH Payment Workflow Meta Feed Ad

Last updated: 2026-05-13, America/Los_Angeles

This is a Meta Feed ad created from the first credit-card workflow square asset. It used similar Illinois therapist/practice-operator targeting to the recommended BCCHP broadened ad sets. Meta later rejected the ad under `Financial and Insurance Products and Services`, and the rejected ad was deleted on 2026-05-11.

Important current-state note: the 2026-05-13 API readback shows the campaign and ad set as `ACTIVE`, but the only known ad is `DELETED`. This stack has no deliverable ad and showed `$0.00` spend at the 2026-05-13 readback. Do not use campaign/ad set status alone as proof that the rejected ad is live.

Do not store Meta access tokens here. Runtime secrets live in `/Users/dax/bomi/bomi-ads/.env`, which should remain git-ignored. Use `#` for comments in `.env` files, not `//`.

## Created Meta Objects

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)
- Campaign: `120247819413340170`
- Ad set: `120247819413720170`
- Creative: `2138892863576570`
- Ad: `120247819417890170`

Latest readback on 2026-05-13:

- Campaign status: `ACTIVE`
- Campaign effective status: `ACTIVE`
- Ad set status: `ACTIVE`
- Ad set effective status: `ACTIVE`
- Ad status: `DELETED`
- Ad configured status: `DELETED`
- Ad effective status: `DELETED`
- Ad set daily budget: `1500` cents = `$15/day`
- 2026-05-13 performance at readback: `$0.00` spend, 0 impressions, 0 clicks, 0 landing page views

Rejection readback on 2026-05-11:

```text
Financial and Insurance Products and Services: It looks like your ad contains content that is not allowed on Meta's Advertising platforms. This goes against our Advertising Standards, Community Standards or Terms of Service. Visit Business Support Home to understand why your ad was removed and how to fix it.
```

Likely trigger:

- The creative headline says `virtual credit cards`.
- The image says `Insurance payments`.
- The copy says `EFT/ACH direct deposit` and `payment workflows`.
- The campaign was created with `special_ad_categories=[]`.

Meta's financial-products special ad category includes insurance and payment services. If this offer is resubmitted as a financial-products/services ad, expect special-ad-category targeting restrictions; the current detailed therapist/operator `flexible_spec` may need to be simplified or removed.

## Creative

Source file:

- `../Bomi Health Ad Campaign - Meta Ad - Tired of This_.png`

Uploaded image hash:

- `555585bb6aebde5242f5c57bb8a093bd`

Media verification:

- Source asset is a 1080x1080 PNG.
- Creative `2138892863576570` readback included `image_hash=555585bb6aebde5242f5c57bb8a093bd`.
- Meta returned valid `DESKTOP_FEED_STANDARD`, `MOBILE_FEED_STANDARD`, and `INSTAGRAM_STANDARD` preview iframe bodies for ad `120247819417890170`.

Ad copy used:

```text
For Illinois therapy practices: Bomi helps move insurance payment workflows toward EFT/ACH direct deposit and cleaner reconciliation. Book a free consult.
```

Headline:

```text
Clean Up Insurance Payments
```

Description:

```text
EFT/ACH and billing workflow support for therapists.
```

CTA:

```text
BOOK_NOW
```

Landing URL:

```text
https://billwithbomi.com/?utm_source=meta&utm_medium=paid_social&utm_campaign=eft_ach_payment_workflows_il&utm_content=meta_feed_credit_cards_operator_broad&utm_audience=operator_broad
```

Effective object story:

- `588675787671641_122188402856865755`

## Targeting

The ad set targets Meta Feed placements:

- `publisher_platforms`: `facebook`, `instagram`
- `facebook_positions`: `feed`
- `instagram_positions`: `stream`

Geo and age:

- Illinois, region key `3856`
- Meta readback location types: `home` and `recent`
- Age `25-65+`

Audience expansion:

- `targeting_automation.advantage_audience`: `1`

The therapist/operator/admin/practice signals are inside one `flexible_spec` group so Meta can match any of them. The group includes:

- Existing exact therapist work-position list from the May 11 BCCHP control ads
- Practice/admin/billing roles: Practice Manager, Medical Practice Manager, Medical Office Manager, Billing Manager, Medical Biller, Medical Insurance Biller, Billing Specialist, Medical Billing Specialist, Medical Billing and Coding Specialist, Credentialing Specialist
- Director/operator roles: Clinical Director, Clinic Director, Director of Clinical Services, Executive director, Executive Director/CEO
- Industries/B2B: Healthcare and Medical Services, Community and Social Services, Administrative Services, Management, Business Decision Makers, Business decision maker titles and interests, Company size: 1-10 employees, Company size: 11-100 employees
- Behavior/interest: Small business owners, Blue Cross Blue Shield Association

## Creation Notes

- Created paused.
- The `.textClipping` file in `assets/credit_cards/` contains the asset title; the uploadable image is `Bomi Health Ad Campaign - Meta Ad - Tired of This_.png`.
- This stack uses the documented Bomi Meta ad account `act_302351874007793`.
- The campaign/ad set read back active as of 2026-05-13, but the known ad is deleted. Do not recreate, retry, or add a new ad to this stack without explicit user approval because the ad set has a `$15/day` budget.
- Do not retry this exact creative/copy unchanged; it has already been disapproved.
- The rejected ad object `120247819417890170` was deleted on 2026-05-11.
- Replacement stack: `../meta-feed-2026-05-11-payout-workflow-financial-category/INFO.md`.
