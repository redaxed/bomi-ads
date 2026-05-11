# Bomi BCCHP Illinois Therapists Instagram Story Ad

Last updated: 2026-05-11, America/Los_Angeles

This is the fresh Instagram Story remake created after the original Instagram Feed stack appeared bugged. The old Instagram objects were deleted before this stack was created.

Do not store Meta access tokens here. Runtime secrets live in `/Users/dax/bomi/bomi-ads/.env`, which should remain git-ignored. Use `#` for comments in `.env` files, not `//`.

## Created Meta Objects

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Meta app: `952598967576935` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)

Created campaign stack:

- Campaign: `120247752438820170`
- Ad set: `120247752439090170`
- Creative: `1668331050960382`
- Ad: `120247752442290170`

Latest readback on 2026-05-11:

- Campaign status: `ACTIVE`
- Ad set status: `ACTIVE`
- Ad status: `ACTIVE`
- Ad effective status: `ACTIVE`
- Ad set daily budget: `2000` cents = `$20/day`
- Landing URL: `https://billwithbomi.com`

## Deleted Previous Stack

- Old campaign: `120247746504900170` - `DELETED`
- Old ad set: `120247746506640170` - `DELETED`
- Old ad: `120247747608570170` - `DELETED`

## Creative

Source file:

- `../Bomi Health Digital Ad - Instagram Story Ad - 1080x1920.png`

Uploaded image hash:

- `180cb7cfa5905f28cf4792dc108d6bcc`

Media verification:

- Creative `1668331050960382` readback included `image_hash=180cb7cfa5905f28cf4792dc108d6bcc`.
- Ad account image lookup returned stored asset name `Bomi Health Digital Ad - Instagram Story Ad - 1080x1920.png`.
- Ad account image lookup returned dimensions `1080x1920`.
- Meta returned a valid `INSTAGRAM_STORY` preview iframe body for ad `120247752442290170`.
- Directly fetching that iframe URL outside Ads Manager returned `404 Not Found`, so a broken preview pane does not necessarily mean the media is absent from the creative record.

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

Effective object story:

- `588675787671641_122188261346865755`

## Targeting

The ad set is Instagram Story only:

- `publisher_platforms`: `instagram`
- `instagram_positions`: `story`
- `device_platforms`: `mobile`

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

- Created objects paused first.
- Activated campaign, ad set, and ad only after the full stack existed.
- Used repaired location-targeting approach: send Illinois region without explicitly sending removed `location_types=["home"]`.
- Meta readback still returns default `location_types=["home","recent"]`.
