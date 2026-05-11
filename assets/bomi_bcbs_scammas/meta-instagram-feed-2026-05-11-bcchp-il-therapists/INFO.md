# Bomi BCCHP Illinois Therapists Instagram Feed Ad

Last updated: 2026-05-11, America/Los_Angeles

Status: deleted/replaced on 2026-05-11.

Replacement:

- `../meta-instagram-story-2026-05-11-bcchp-il-therapists/INFO.md`

Deleted objects:

- Campaign: `120247746504900170`
- Ad set: `120247746506640170`
- Ad: `120247747608570170`

This folder is the handoff context for the Meta/Instagram ad created from the Bomi BCCHP reimbursement-review creative.

Do not store Meta access tokens here. Runtime secrets live in `/Users/dax/bomi/bomi-ads/.env`, which was verified as git-ignored during setup.

## Created Meta Objects

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Meta app: `952598967576935` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)
- Instagram account shown on Page: `17841477913804164` (`@billwithbomi`, IG business account)
- Instagram actor seen on historical ad creatives: `897453543441565` (`billwithbomi`)
- Pixel found on ad account: `1141810224366108` (`Bomi Pixel`)

Created campaign stack:

- Campaign: `120247746504900170`
- Ad set: `120247746506640170`
- Creative: `904785332565962`
- Ad: `120247747608570170`

Final readback after creation:

- Campaign status: `ACTIVE`
- Ad set status: `ACTIVE`
- Ad status: `ACTIVE`
- Latest ad effective status checked after location-targeting repair on 2026-05-11: `PENDING_REVIEW`
- Ad set daily budget: `2000` cents = `$20/day`
- Landing URL: `https://billwithbomi.com`

## Creative Assets

Source files in the parent folder:

- Facebook/Instagram Feed square asset: `../Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`
- Instagram Story asset: `../Bomi Health Digital Ad - Instagram Story Ad - 1080x1920.png`
- LinkedIn asset: `../Bomi Health Digital Ad - LinkedIn Ad - 1200x628.png`

The created Instagram Feed ad used the square `1080x1080` PNG.

Uploaded image hash:

- `71030145b6872b0bcd12b58476d9ea73`

Media verification on 2026-05-11:

- Creative `904785332565962` readback included `image_hash=71030145b6872b0bcd12b58476d9ea73`.
- Ad account image lookup for that hash returned the stored asset name `Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`.
- Meta returned a valid `INSTAGRAM_STANDARD` ad preview iframe body for ad `120247747608570170`.

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

## Targeting

The ad set is Instagram Feed only:

- `publisher_platforms`: `instagram`
- `instagram_positions`: `stream`

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

Earlier reach estimates from Meta:

- Therapist job-title audience in Illinois: roughly `1.2k-1.4k`
- Therapist job titles + small-business-owner behavior: roughly `1k`
- Psychology interest alone was very broad/noisy: roughly `1.5M-1.7M` in Illinois, so it was intentionally avoided.

Readback after creation showed Meta also returned:

```json
"targeting_automation": {
  "advantage_audience": 1
}
```

This was not explicitly set in the original targeting payload; Meta appears to have added/defaulted it.

## Important Setup Notes

Required local environment variables:

```bash
META_ACCESS_TOKEN=...
META_APP_ID=952598967576935
META_AD_ACCOUNT_ID=302351874007793
META_PAGE_ID=588675787671641
META_INSTAGRAM_ACCOUNT_ID=17841477913804164
```

Optional:

```bash
BOMI_AD_LANDING_URL=https://billwithbomi.com
```

Use the isolated Python environment with `requests` installed:

```bash
/Users/dax/.cache/bomi-ads-venv/bin/python
```

Reason: the system/default Homebrew `python3` pointed at Python 3.14 and had a broken `pip`/`pyexpat` import during setup. A clean venv was created with Python 3.13:

```bash
/Users/dax/.cache/bomi-ads-venv
```

## Gotchas Encountered

0. On 2026-05-11, Meta showed this UI/API delivery error:

   ```text
   Your audience contains a location targeting option that has been removed (people living in, people traveling in or people recently in a location). Before you can publish this ad set, you need to edit this audience to update the type of location targeting used. (#1870194)
   ```

   Cause: the original ad set targeting explicitly sent `geo_locations.location_types=["home"]`.

   Fix applied: updated ad set `120247746506640170` with the same Illinois region, placements, age, and therapist job titles, but omitted the explicit `location_types` field. Meta accepted the update and read back the default combined `location_types=["home","recent"]`.

1. The first token had read scopes but the Dax user was not assigned ad-account tasks on `act_302351874007793`.

   Symptom:

   ```text
   The user doesn't have the permission to create ads with this ad account
   ```

   Fix: assign Dax to the ad account in Business Settings with campaign/ad management permissions, or use a token from a user already assigned to the ad account.

2. Meta required `is_adset_budget_sharing_enabled=false` when creating a campaign that uses ad-set-level budget.

   Symptom:

   ```text
   Must specify True or False in is_adset_budget_sharing_enabled field
   ```

3. Direct `instagram_actor_id` creative creation failed, even with both the IG business account ID and the historical ad-creative actor ID.

   Failed IDs:

   - `17841477913804164`
   - `897453543441565`

   Symptom:

   ```text
   Param instagram_actor_id must be a valid Instagram account id
   ```

   Working path: create a Page-backed creative with `page_id` only, then attach it to an Instagram-only ad set. This created a Page-backed effective story ID while the placement remained Instagram Feed only.

4. Before the app was switched live/public, Page-backed creative creation failed.

   Symptom:

   ```text
   Ads creative post was created by an app that is in development mode. It must be in public to create this ad.
   ```

   Fix: switch the Meta app out of development mode.

5. Partial objects were created before the final creative succeeded.

   The reusable campaign/ad set created during the successful final flow are:

   - Campaign: `120247746504900170`
   - Ad set: `120247746506640170`

   Future scripts should reuse these only when intentionally modifying this exact ad stack. Otherwise create new names/objects to avoid accidental edits.

## General API Flow That Worked

Use Graph API version `v22.0`.

1. Upload image to the ad account:

   ```text
   POST /act_302351874007793/adimages
   multipart field: filename=@...1080x1080.png
   ```

2. Create campaign:

   ```json
   {
     "objective": "OUTCOME_TRAFFIC",
     "buying_type": "AUCTION",
     "special_ad_categories": "[]",
     "is_adset_budget_sharing_enabled": "false",
     "status": "PAUSED"
   }
   ```

3. Create ad set with ad-set budget:

   ```json
   {
     "daily_budget": "2000",
     "billing_event": "IMPRESSIONS",
     "optimization_goal": "LINK_CLICKS",
     "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
     "destination_type": "WEBSITE",
     "status": "PAUSED"
   }
   ```

4. Create Page-backed creative:

   ```json
   {
     "object_story_spec": {
       "page_id": "588675787671641",
       "link_data": {
         "image_hash": "71030145b6872b0bcd12b58476d9ea73",
         "link": "https://billwithbomi.com",
         "message": "Illinois therapists: BCCHP payments lower than expected? Bomi reviews reimbursements and helps identify underpayments. Book a free consultation.",
         "name": "BCCHP payments lower than expected?",
         "description": "Reimbursement reviews for Illinois therapy practices.",
         "call_to_action": {
           "type": "BOOK_NOW",
           "value": {
             "link": "https://billwithbomi.com"
           }
         }
       }
     }
   }
   ```

5. Create ad paused:

   ```json
   {
     "adset_id": "120247746506640170",
     "creative": {
       "creative_id": "904785332565962"
     },
     "status": "PAUSED"
   }
   ```

6. Activate campaign, ad set, and ad only after all objects exist:

   ```text
   POST /{campaign_id} status=ACTIVE
   POST /{adset_id} status=ACTIVE
   POST /{ad_id} status=ACTIVE
   ```

## Safety Notes For Future LLMs

- Never print, commit, or store `META_ACCESS_TOKEN`.
- Before making spend-affecting changes, read back the campaign/ad set/ad statuses and confirm the user explicitly asked for the change.
- If creating test objects, create them `PAUSED` first and activate only after every piece exists.
- If pausing this live ad, pause the ad or ad set first; then read back `status` and `effective_status`.
- The user explicitly authorized the $20/day ad creation/activation on 2026-05-11.
- The token previously pasted in chat should be treated as exposed; recommend rotating tokens after this work if not already done.
