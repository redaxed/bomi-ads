# Bomi BCCHP Exact Control Facebook Feed Ad

Last updated: 2026-05-11 18:38 PDT, America/Los_Angeles

This is a new Facebook Feed ad created from the recommended targeting rebuild and activated on 2026-05-11 after user approval. The existing active Facebook Feed ad was not edited.

Do not store Meta access tokens here. Runtime secrets live in `/Users/dax/bomi/bomi-ads/.env`, which should remain git-ignored. Use `#` for comments in `.env` files, not `//`.

## Created Meta Objects

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)
- Campaign: `120247816542230170`
- Ad set: `120247816542370170`
- Creative: `860333539716526`
- Ad: `120247816543370170`

Latest readback on 2026-05-11 18:38 PDT:

- Campaign status: `ACTIVE`
- Campaign effective status: `ACTIVE`
- Ad set status: `ACTIVE`
- Ad set effective status: `ACTIVE`
- Ad status: `ACTIVE`
- Ad configured status: `ACTIVE`
- Ad effective status: `ACTIVE`
- Ad set daily budget: `500` cents = `$5/day`

## Creative

Source file:

- `../Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`

Uploaded image hash:

- `71030145b6872b0bcd12b58476d9ea73`

Media verification:

- Creative `860333539716526` readback included `image_hash=71030145b6872b0bcd12b58476d9ea73`.
- Meta returned valid `DESKTOP_FEED_STANDARD` and `MOBILE_FEED_STANDARD` preview iframe bodies for ad `120247816543370170`.

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
https://billwithbomi.com/?utm_source=meta&utm_medium=paid_social&utm_campaign=bcchp_reimbursement_review_il&utm_content=fb_feed_exact_control&utm_audience=exact_control
```

Effective object story:

- `588675787671641_122188396040865755`

## Targeting

The ad set is Facebook Feed only:

- `publisher_platforms`: `facebook`
- `facebook_positions`: `feed`

Geo and age:

- Illinois, region key `3856`
- Meta readback location types: `home` and `recent`
- Age `25-65+`

Audience expansion:

- `targeting_automation.advantage_audience`: `0`

Job-title/work-position audience:

- `108163765872304` - Mental health counselor
- `722313654550739` - Licensed Clinical Mental Health Counselor
- `330966250435806` - Licensed Professional Counselor (LPC)
- `334533013408721` - Licensed Clinical Social Worker (LCSW)
- `125071804208180` - Licensed Clinical Social Worker/Therapist
- `723240677773091` - Licensed Marriage and Family Therapist (LMFT)
- `1554307254818982` - Clinical Psychologist
- `335586239976066` - Licensed Clinical Psychologist
- `407489252757668` - Counseling Psychologist
- `1461653794055392` - Psychotherapist-Counselor
- `593422084126001` - Behavioral Therapist
- `108359589220684` - Owner/Psychotherapist
- `718196931629654` - Psychologist, Private Practice

## Creation Notes

- Created paused, then activated on 2026-05-11 at 18:38 PDT.
- This ad is the exact-title control, with the same title list as the existing May 11 ads but with updated BCBSIL Medicaid / BCCHP copy.
- This ad points to the live homepage with UTMs.
- A first attempt to create the full campaign split discovered that the local `.env` ad account did not match the documented Bomi Meta ad account; the final objects were created under `act_302351874007793`.
