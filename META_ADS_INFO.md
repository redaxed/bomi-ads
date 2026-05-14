# Meta Ads Handoff

Last updated: 2026-05-14, America/Los_Angeles

This repo contains operational context for Bomi Meta ads created through the Meta Marketing API. Use this file as the top-level map, then read the relevant per-ad `INFO.md` file before touching any live object.

Do not store secrets in this repo. The local `.env` file is the source for runtime credentials and should remain ignored. Use `#` for comments in `.env` files; do not use `//`, because shell `source .env` treats that as a command.

## Environment

Expected local env vars:

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

Use this Python environment for Meta scripts:

```bash
/Users/dax/.cache/bomi-ads-venv/bin/python
```

It has `requests` installed. The default Homebrew `python3` pointed at Python 3.14 during setup and had a broken `pip`/`pyexpat` import, so prefer the venv above unless that has been intentionally replaced.

## Shared Meta IDs

- Ad account: `act_302351874007793`
- Business: `4788291191452444` (`Bomi Health`)
- Meta app: `952598967576935` (`Bomi Health`)
- Facebook Page: `588675787671641` (`Bomi Health, Inc.`)
- Instagram business account from Page: `17841477913804164` (`@billwithbomi`)
- Historical Instagram actor ID seen on existing creatives: `897453543441565`
- Pixel: `1141810224366108` (`Bomi Pixel`)

## Active Pooled EHR vs Expert Billing Team Test

Created on 2026-05-14 from the Moda-generated EHR-vs-Bomi asset. This stack is
created paused, then activated on 2026-05-14 after user approval.

- Folder: `assets/ehr_vs_bomi_tax_software_2026-05-14/`
- Campaign: `120248005997630170`
- Ad set: `120248006000710170`
- Creative: `998947609178695`
- Ad: `120248006007810170`
- Budget: `$20/day`
- Placement: Facebook Feed only
- Asset: `assets/ehr_vs_bomi_tax_software_2026-05-14/ehr-vs-bomi-square-1080x1080.png`
- Image hash: `28658b8f42d3a9c8f8bafb4c4b4cd1e6`
- Latest status checked on 2026-05-14 after activation: campaign/ad set/ad configured status `ACTIVE`; campaign/ad set/ad effective status `ACTIVE`
- Targeting: Illinois, Ohio, Indiana, New Mexico; age `25-65+`; broad therapist/practice-operator flexible spec; Advantage audience expansion enabled
- Final URL: `https://www.billwithbomi.com/?utm_source=meta&utm_medium=paid_social&utm_campaign=ehr_vs_bomi_pooled_states&utm_content=facebook_feed`

Copy used:

```text
Your EHR gives you the tools. Bomi gives you the expert billing team. Billing + credentialing for therapists, flat 4% of collections, and no new EHR.
```

Headline:

```text
Stop DIY-ing Insurance Billing
```

Description:

```text
Book a free consultation.
```

## Paused Pooled Own Your Business Test

Created on 2026-05-14 from the Moda-generated "Own your business. Let us handle
insurance." asset. This stack is paused and should not be activated without a
separate explicit go.

- Folder: `assets/own_business_handle_insurance_2026-05-14/`
- Campaign: `120248011749820170`
- Ad set: `120248011750720170`
- Creative: `1552847629515540`
- Ad: `120248011752520170`
- Budget: `$20/day`
- Placement: Facebook Feed only
- Asset: `assets/own_business_handle_insurance_2026-05-14/own-business-handle-insurance-square-1080x1080.png`
- Image hash: `bcc6c65cc650af5d1bf6e1b83a11428d`
- Latest status checked on 2026-05-14: campaign/ad set/ad configured status `PAUSED`; campaign/ad set effective status `PAUSED`; ad effective status `PENDING_REVIEW`
- Targeting: Illinois, Ohio, Indiana, New Mexico; age `25-65+`; broad therapist/practice-operator flexible spec; Advantage audience expansion enabled
- Final URL: `https://www.billwithbomi.com/?utm_source=meta&utm_medium=paid_social&utm_campaign=own_business_handle_insurance_pooled_states&utm_content=facebook_feed`

Copy used:

```text
Own your business. Let Bomi handle insurance billing and credentialing for your therapy practice. Flat 4% of collections.
```

Headline:

```text
Own Your Business
```

Description:

```text
Schedule a free consultation.
```

## Current Single-Placement BCCHP Ads

### Instagram Story - BCCHP Illinois Therapists

- Folder: `assets/bomi_bcbs_scammas/meta-instagram-story-2026-05-11-bcchp-il-therapists/`
- Campaign: `120247752438820170`
- Ad set: `120247752439090170`
- Creative: `1668331050960382`
- Ad: `120247752442290170`
- Budget: `$40/day`
- Placement: Instagram Story only
- Asset: `Bomi Health Digital Ad - Instagram Story Ad - 1080x1920.png`
- Image hash: `180cb7cfa5905f28cf4792dc108d6bcc`
- Latest status checked on 2026-05-13: campaign/ad set/ad `ACTIVE`; ad effective status `ACTIVE`; ad set daily budget `4000` cents = `$40/day`
- 2026-05-13 performance at readback: `$0.72` spend, 45 impressions, 0 clicks, 0 landing page views

### Facebook Feed - BCCHP Illinois Therapists

- Folder: `assets/bomi_bcbs_scammas/meta-facebook-feed-2026-05-11-remake-bcchp-il-therapists/`
- Campaign: `120247752446670170`
- Ad set: `120247752447070170`
- Creative: `1323556353061976`
- Ad: `120247752456360170`
- Budget: `$20/day`
- Placement: Facebook Feed only
- Asset: `Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`
- Image hash: `71030145b6872b0bcd12b58476d9ea73`
- Latest status checked on 2026-05-13: campaign `ACTIVE`, ad set `PAUSED`, ad configured status `ACTIVE`, ad effective status `ADSET_PAUSED`
- 2026-05-13 performance at readback: `$0.00` spend, 0 impressions, 0 clicks, 0 landing page views

## Active Recommended Targeting Ads

Created on 2026-05-11 from the 2026-05-11 active BCCHP creative assets, then activated on 2026-05-11 at 18:38 PDT after user approval. These are new objects only; the existing active ads above were not edited.

Campaign:

- Name: `IL BCCHP Reimbursement Review - Leads - 2026-05-11`
- Campaign: `120247816542230170`
- Objective: `OUTCOME_TRAFFIC`
- Latest status readback: campaign `ACTIVE`; effective status `ACTIVE`
- Landing URL base: `https://billwithbomi.com/` with per-ad UTMs

Ad set budget allocation:

| Audience / placement | Daily budget | Folder | Ad set | Creative | Ad | Latest readback |
| --- | ---: | --- | --- | --- | --- | --- |
| Exact therapist titles - Facebook Feed | `$5/day` | `assets/bomi_bcbs_scammas/meta-facebook-feed-2026-05-11-bcchp-il-exact-control-recommended-targeting/` | `120247816542370170` | `860333539716526` | `120247816543370170` | campaign/ad set/ad `ACTIVE`; ad effective `ACTIVE` |
| Exact therapist titles - Instagram Story | `$5/day` | `assets/bomi_bcbs_scammas/meta-instagram-story-2026-05-11-bcchp-il-exact-control-recommended-targeting/` | `120247816543770170` | `1705753187512469` | `120247816544780170` | campaign/ad set/ad `ACTIVE`; ad effective `ACTIVE` |
| Therapist practice operators - Facebook Feed | `$15/day` | `assets/bomi_bcbs_scammas/meta-facebook-feed-2026-05-11-bcchp-il-operator-broad-recommended-targeting/` | `120247816553050170` | `1400493841913512` | `120247816553740170` | campaign/ad set/ad `ACTIVE`; ad effective `ACTIVE` |
| Therapist practice operators - Instagram Story | `$15/day` | `assets/bomi_bcbs_scammas/meta-instagram-story-2026-05-11-bcchp-il-operator-broad-recommended-targeting/` | `120247816554440170` | `926149977121332` | `120247816558010170` | campaign/ad set/ad `ACTIVE`; ad effective `ACTIVE` |

2026-05-13 performance at readback for this campaign: `$14.42` spend, 2,064 impressions, 15 clicks, 12 link clicks, 8 landing page views. Delivery was concentrated in the broad operator ad sets, not the exact-title controls.

The split preserves the recommended `$10/day` exact-title control and `$30/day` broadened operator budget while keeping the currently proven feed/story creative assets placement-specific.

Copy used:

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

## Deleted Rejected EFT/ACH Payment Workflow Ad

Created on 2026-05-11 from the first credit-card workflow square asset. The rejected ad was deleted on 2026-05-11 after the user supplied an updated asset. As of the 2026-05-13 API readback, the campaign and ad set show `ACTIVE`, but the only known ad is `DELETED`, so this stack has no deliverable ad. Do not infer delivery from the campaign/ad set status alone.

- Folder: `assets/credit_cards/meta-feed-2026-05-11-eft-ach-operator-broad/`
- Campaign: `120247819413340170`
- Ad set: `120247819413720170`
- Creative: `2138892863576570`
- Ad: `120247819417890170`
- Ad set budget: `$15/day`; the known ad is deleted and not delivering
- Placement: Facebook Feed + Instagram Feed
- Original asset at creation time: `assets/credit_cards/Bomi Health Ad Campaign - Meta Ad - Tired of This_.png`
- Image hash: `555585bb6aebde5242f5c57bb8a093bd`
- Latest status checked on 2026-05-13: campaign/ad set `ACTIVE`; ad configured/effective status `DELETED`
- 2026-05-13 performance at readback: `$0.00` spend, 0 impressions, 0 clicks, 0 landing page views
- Rejection readback: `Financial and Insurance Products and Services`
- Likely trigger: the asset and copy combine `virtual credit cards`, `insurance payments`, `EFT/ACH direct deposit`, and `payment workflows`. Meta treats ads promoting insurance or payment services as financial products/services, and this campaign was created with `special_ad_categories=[]`.

Copy used:

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

## Active Payout Workflow Replacement

Created on 2026-05-11 from the updated credit-card workflow square asset. This stack was originally documented as paused, but the 2026-05-13 API readback shows the campaign, ad set, and ad are all `ACTIVE` and spending. It was initially created with `FINANCIAL_PRODUCTS_SERVICES`, then the designation was removed on 2026-05-11 after user clarification.

- Folder: `assets/credit_cards/meta-feed-2026-05-11-payout-workflow-financial-category/`
- Campaign: `120247820755190170`
- Ad set: `120247820755420170`
- Creative: `2209355609892966`
- Ad: `120247820756460170`
- Budget: `$15/day`
- Placement: Facebook Feed + Instagram Feed
- Asset: `assets/credit_cards/Bomi Health Ad Campaign - Meta Ad - Tired of This_ (1).png`
- Image hash: `4b91972376b85837345eee4d1447a21c`
- Special ad categories: `[]`
- Latest status checked on 2026-05-13: campaign/ad set/ad `ACTIVE`; ad effective status `ACTIVE`
- 2026-05-13 performance at readback: `$7.38` spend, 924 impressions, 18 clicks, 14 link clicks, 6 landing page views

The replacement currently uses broad Illinois feed targeting. It does not yet restore the detailed therapist/operator `flexible_spec` targeting from the rejected first version.

Copy used:

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

## Deleted/Replaced Stacks

- Old Instagram Feed stack: campaign `120247746504900170`, ad set `120247746506640170`, ad `120247747608570170` - all `DELETED`
- Old Facebook Feed stack: campaign `120247750689930170`, ad set `120247750691660170`, ad `120247750713680170` - all `DELETED`

The old handoff folders were retained and marked as deleted/replaced:

- `assets/bomi_bcbs_scammas/meta-instagram-feed-2026-05-11-bcchp-il-therapists/`
- `assets/bomi_bcbs_scammas/meta-facebook-feed-2026-05-11-bcchp-il-therapists/`

## Standard Creation Rules

Every time a Meta ad is created from this repo:

1. Create objects paused first.
2. Activate only after the campaign, ad set, creative, and ad all exist.
3. Read back `status`, `effective_status`, budget, targeting, and creative ID.
4. Create a per-ad folder next to the relevant assets.
5. Add an `INFO.md` in that folder with IDs, copy, targeting, budget, asset path, image hash, creation gotchas, and current readback.
6. Update this top-level file with a one-entry summary and a link/path to the per-ad folder.
7. Never store or print access tokens.

## Targeting Used For BCCHP Therapist Ads

Geo and age:

- Illinois, region key `3856`
- Current Meta readback: `location_types=["home","recent"]`
- Age `25-65+`

Audience expansion:

- Current remade ad sets explicitly read back `targeting_automation.advantage_audience=0`

Job-title/work-position IDs:

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

Earlier reach checks indicated this audience is small but high-intent: roughly `1.2k-1.4k` people in Illinois before placement-specific delivery filtering. The broad `Psychology` interest was intentionally avoided because it was much noisier.

## Recommended Broad Operator Targeting Created 2026-05-11

The broad operator ad sets use Illinois, age `25-65+`, placement-specific feed/story targeting, and `targeting_automation.advantage_audience=1`.

The detailed targeting suggestions are wrapped in one `flexible_spec` group so Meta can match any of the therapist/operator/admin/industry/behavior/interest signals instead of intersecting all categories. A first attempt that placed these categories at the top level was rejected by Meta as too narrow.

Work-position signals:

- Exact therapist titles listed above
- `911356208895948` - Practice Manager
- `1569299249954237` - Medical Practice Manager
- `893771870644160` - Medical Office Manager
- `668500706594423` - Billing Manager
- `768293416579944` - Medical Biller
- `884216444934879` - Medical Insurance Biller
- `786660018082739` - Billing Specialist
- `342225789309645` - Medical Billing Specialist
- `432841263549002` - Medical Billing and Coding Specialist
- `331557573704439` - Credentialing Specialist
- `544823505660174` - Clinical Director
- `1581181608766724` - Clinic Director
- `1568941850012049` - Director of Clinical Services
- `105563979478424` - Executive director
- `134988453211643` - Executive Director/CEO

Industry / B2B signals:

- `6012903159383` - Healthcare and Medical Services
- `6012903168383` - Community and Social Services
- `6008888954983` - Administrative Services
- `6009003311983` - Management
- `6262428231783` - Business Decision Makers
- `6262428209783` - Business decision maker titles and interests
- `6377169550583` - Company size: 1-10 employees
- `6377134779583` - Company size: 11-100 employees

Behavior / interest signals:

- `6002714898572` - Small business owners
- `6002921291555` - Blue Cross Blue Shield Association

Targeting Search notes from 2026-05-11: Meta did not return targetable matches for several recommended tool/interest terms, including `SimplePractice`, `TherapyNotes`, `Sessions Health`, `Availity`, `CAQH`, `Psychology Today`, `Medicaid`, `Medical billing`, `Revenue cycle management`, or `Mental health care`. Only targetable returned terms were used.

## Known Meta API Gotchas

- Campaigns using ad-set-level budgets required `is_adset_budget_sharing_enabled=false`.
- Do not explicitly send `geo_locations.location_types=["home"]`. Meta returned error `#1870194` saying the location targeting option had been removed. The repair that worked was to send Illinois region targeting while omitting `location_types`; Meta then read back the accepted default `["home","recent"]`.
- Direct `instagram_actor_id` creative creation failed for both `17841477913804164` and `897453543441565`; the working path was a Page-backed creative attached to an Instagram-only ad set.
- If the Meta app is in development mode, Page-backed creative creation can fail with an app-mode error. The app needed to be live/public.
- If the token user lacks ad-account tasks, image/ad creation fails even when read access works.
- On 2026-05-11, the local `.env` value for `META_AD_ACCOUNT_ID` did not match the documented Bomi Meta ad account. Creation for the recommended targeting ads used the documented shared account `act_302351874007793`.
- The Meta `/reachestimate` endpoint returned a permission error for this token even though normal campaign/ad-set/ad reads and writes succeeded, so no fresh reach estimate was recorded for the recommended targeting build.

## Safe Readback Snippet

```bash
set -a
source .env
set +a
/Users/dax/.cache/bomi-ads-venv/bin/python - <<'PY'
import json, os, requests

base = "https://graph.facebook.com/v22.0"
token = os.environ["META_ACCESS_TOKEN"]
headers = {"Authorization": f"Bearer {token}"}

for node, fields in [
    ("120247752438820170", "id,name,status,effective_status"),
    ("120247752439090170", "id,name,status,effective_status,daily_budget"),
    ("120247752442290170", "id,name,status,effective_status,configured_status"),
    ("120247752446670170", "id,name,status,effective_status"),
    ("120247752447070170", "id,name,status,effective_status,daily_budget"),
    ("120247752456360170", "id,name,status,effective_status,configured_status"),
]:
    r = requests.get(f"{base}/{node}", params={"fields": fields}, headers=headers, timeout=30)
    print(json.dumps(r.json(), indent=2, sort_keys=True))
PY
```
