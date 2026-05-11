# Bomi BCCHP Illinois Therapists Facebook Feed Ad

Last updated: 2026-05-11, America/Los_Angeles

Status: deleted/replaced on 2026-05-11.

Replacement:

- `../meta-facebook-feed-2026-05-11-remake-bcchp-il-therapists/INFO.md`

Deleted objects:

- Campaign: `120247750689930170`
- Ad set: `120247750691660170`
- Ad: `120247750713680170`

This folder is the handoff context for the Meta/Facebook Feed ad created from the Bomi BCCHP reimbursement-review square creative.

Do not store Meta access tokens here. Runtime secrets live in `/Users/dax/bomi/bomi-ads/.env`, which should remain git-ignored.

## Created Meta Objects

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Meta app: `952598967576935` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)
- Pixel found on ad account: `1141810224366108` (`Bomi Pixel`)

Created campaign stack:

- Campaign: `120247750689930170`
- Ad set: `120247750691660170`
- Creative: `973798215359235`
- Ad: `120247750713680170`

Final readback after creation:

- Campaign status: `ACTIVE`
- Ad set status: `ACTIVE`
- Ad status: `ACTIVE`
- Latest ad effective status checked after location-targeting repair on 2026-05-11: `PENDING_REVIEW`
- Ad set daily budget: `2000` cents = `$20/day`
- Landing URL: `https://billwithbomi.com`

## Creative

Source file in the parent folder:

- `../Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`

Uploaded image hash:

- `71030145b6872b0bcd12b58476d9ea73`

Media verification on 2026-05-11:

- Creative `973798215359235` readback included `image_hash=71030145b6872b0bcd12b58476d9ea73`.
- Ad account image lookup for that hash returned the stored asset name `Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`.
- Meta returned valid `DESKTOP_FEED_STANDARD` and `MOBILE_FEED_STANDARD` ad preview iframe bodies for ad `120247750713680170`.

Ad copy used:

```text
Illinois therapists: BCCHP payments lower than expected? Bomi reviews reimbursements and helps identify underpayments. Book a free consultation.
```

Headline:

```text
BCCHP payments lower than expected?
```

Description:

```text
Reimbursement reviews for Illinois therapy practices.
```

CTA:

```text
BOOK_NOW
```

Effective object story after creation:

- `588675787671641_122188256438865755`

## Targeting

The ad set is Facebook Feed only:

- `publisher_platforms`: `facebook`
- `facebook_positions`: `feed`

Geo and age:

- Location: people living in Illinois
- Region key: `3856`
- Current Meta readback location types after 2026-05-11 repair: `home` and `recent`
- Age: `25-65+`

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

Readback after creation showed Meta also returned:

```json
"targeting_automation": {
  "advantage_audience": 1
}
```

This was not explicitly set in the original targeting payload; Meta appears to have added/defaulted it.

## Creation Flow

Created through Meta Graph API `v22.0` using the isolated Python environment:

```bash
/Users/dax/.cache/bomi-ads-venv/bin/python
```

High-level flow:

1. Upload/reuse the square image through `/act_302351874007793/adimages`.
2. Create campaign paused with:
   - `objective=OUTCOME_TRAFFIC`
   - `buying_type=AUCTION`
   - `special_ad_categories=[]`
   - `is_adset_budget_sharing_enabled=false`
3. Create ad set paused with:
   - `daily_budget=2000`
   - `billing_event=IMPRESSIONS`
   - `optimization_goal=LINK_CLICKS`
   - `bid_strategy=LOWEST_COST_WITHOUT_CAP`
   - `destination_type=WEBSITE`
   - Facebook Feed-only targeting
4. Create Page-backed creative with `page_id=588675787671641`.
5. Create ad paused.
6. Activate campaign, ad set, and ad after all pieces exist.
7. Read back `status` and `effective_status`.

## Safety Notes

- The user explicitly asked to create the Facebook one after the Instagram ad and accepted the same `$20/day` pattern.
- On 2026-05-11, the ad set had the same deprecated explicit `geo_locations.location_types=["home"]` selector as the Instagram ad set. It was proactively updated by omitting explicit `location_types`; Meta accepted the update and read back `location_types=["home","recent"]`.
- Future agents should not mutate or pause this ad without reading current status first and confirming the requested change.
- Never commit or print `META_ACCESS_TOKEN`.
- If creating another ad, create a sibling folder with its own `INFO.md` immediately after creation.
