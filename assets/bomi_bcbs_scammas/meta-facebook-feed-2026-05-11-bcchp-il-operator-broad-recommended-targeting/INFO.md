# Bomi BCCHP Operator Broad Facebook Feed Ad

Last updated: 2026-05-11 18:38 PDT, America/Los_Angeles

This is a new Facebook Feed ad created from the recommended broadened therapist/operator/admin targeting and activated on 2026-05-11 after user approval. The existing active Facebook Feed ad was not edited.

Do not store Meta access tokens here. Runtime secrets live in `/Users/dax/bomi/bomi-ads/.env`, which should remain git-ignored. Use `#` for comments in `.env` files, not `//`.

## Created Meta Objects

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)
- Campaign: `120247816542230170`
- Ad set: `120247816553050170`
- Creative: `1400493841913512`
- Ad: `120247816553740170`

Latest readback on 2026-05-11 18:38 PDT:

- Campaign status: `ACTIVE`
- Campaign effective status: `ACTIVE`
- Ad set status: `ACTIVE`
- Ad set effective status: `ACTIVE`
- Ad status: `ACTIVE`
- Ad configured status: `ACTIVE`
- Ad effective status: `ACTIVE`
- Ad set daily budget: `1500` cents = `$15/day`

## Creative

Source file:

- `../Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`

Uploaded image hash:

- `71030145b6872b0bcd12b58476d9ea73`

Media verification:

- Creative `1400493841913512` readback included `image_hash=71030145b6872b0bcd12b58476d9ea73`.
- Meta returned valid `DESKTOP_FEED_STANDARD` and `MOBILE_FEED_STANDARD` preview iframe bodies for ad `120247816553740170`.

Ad copy used:

```text
For Illinois therapy practices billing BCBSIL Medicaid / BCCHP: Bomi reviews reimbursement patterns, denials, RIN setup, and potential underpayments. Book a free BCCHP billing review.
```

Headline:

```text
BCCHP Claim Review
```

Description:

```text
BCBSIL Medicaid billing checks for Illinois therapy practices.
```

CTA:

```text
BOOK_NOW
```

Landing URL:

```text
https://billwithbomi.com/?utm_source=meta&utm_medium=paid_social&utm_campaign=bcchp_reimbursement_review_il&utm_content=fb_feed_operator_broad&utm_audience=operator_broad
```

Effective object story:

- `588675787671641_122188396214865755`

## Targeting

The ad set is Facebook Feed only:

- `publisher_platforms`: `facebook`
- `facebook_positions`: `feed`

Geo and age:

- Illinois, region key `3856`
- Meta readback location types: `home` and `recent`
- Age `25-65+`

Audience expansion:

- `targeting_automation.advantage_audience`: `1`

The therapist/operator/admin/practice signals are inside one `flexible_spec` group so Meta can match any of them. The group includes:

- Existing exact therapist work-position list from the May 11 control ads
- Practice/admin/billing roles: Practice Manager, Medical Practice Manager, Medical Office Manager, Billing Manager, Medical Biller, Medical Insurance Biller, Billing Specialist, Medical Billing Specialist, Medical Billing and Coding Specialist, Credentialing Specialist
- Director/operator roles: Clinical Director, Clinic Director, Director of Clinical Services, Executive director, Executive Director/CEO
- Industries/B2B: Healthcare and Medical Services, Community and Social Services, Administrative Services, Management, Business Decision Makers, Business decision maker titles and interests, Company size: 1-10 employees, Company size: 11-100 employees
- Behavior/interest: Small business owners, Blue Cross Blue Shield Association

## Creation Notes

- Created paused, then activated on 2026-05-11 at 18:38 PDT.
- The broad targeting was first attempted with the categories at top level; Meta rejected that as too narrow. The accepted version uses one `flexible_spec` group.
- Meta Targeting Search did not return targetable matches for several recommended EHR/tool/interest terms, so only targetable returned signals were included.
- This ad points to the live homepage with UTMs.
