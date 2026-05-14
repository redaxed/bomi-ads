# Work Log

This records what has been done so far for Bomi Google Ads automation.

## 2026-05-12

### Meta visual asset port to Google Demand Gen

Created a reusable local script for Demand Gen creation:

- `scripts/google_ads_create_il_therapist_demand_gen.py`

The script validates first, creates objects paused, reads them back, and can then enable the created campaigns after successful readback. It uses the existing ignored Google Ads `.env` credentials and does not print secrets.

The current Meta visual assets under `assets/bomi_bcbs_scammas/` were uploaded into Google Ads as image assets:

- `Bomi Health Digital Ad - LinkedIn Ad - 1200x628.png`
- `Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png`
- `Bomi Health Digital Ad - Instagram Story Ad - 1080x1920.png`

The Google port uses Demand Gen rather than Search because the source request was to reuse the visual/social assets and targeting. Google budgets are campaign-level, so the requested `$20/day` per ad was implemented as two separate `$20/day` campaigns instead of one shared-budget campaign.

Created and enabled campaigns:

- Operators: `23837011356` / `IL Therapist Reimbursement Review - Operators - Demand Gen - 2026-05-12` / budget `15578697010` / `$20/day`
- Exact titles: `23842274081` / `IL Therapist Reimbursement Review - Exact Titles - Demand Gen - 2026-05-12` / budget `15568781036` / `$20/day`

Ad groups and ads:

- Operators ad group `197990234842`; ad `808693089263`; final URL `https://www.billwithbomi.com/illinois?utm_source=google&utm_medium=paid_demandgen&utm_campaign=il_therapist_reimbursement_review&utm_content=operator_broad`
- Exact-title ad group `197990234802`; ad `808693089260`; final URL `https://www.billwithbomi.com/illinois?utm_source=google&utm_medium=paid_demandgen&utm_campaign=il_therapist_reimbursement_review&utm_content=exact_titles`

Targeting readback:

- Channel: `DEMAND_GEN`
- Geo: Illinois `geoTargetConstants/21147`
- Location option: `PRESENCE`
- Language: English `languageConstants/1000`
- Audience resources: operators `customers/5613091482/audiences/346802586`, exact titles `customers/5613091482/audiences/346802583`
- Optimized targeting: enabled for the operator campaign, disabled for the exact-title campaign

Post-enable readback showed both campaigns `ENABLED` with primary status `LEARNING`. Both ads were `ENABLED` with policy review still `REVIEW_IN_PROGRESS` immediately after creation.

### Indiana search network cleanup

After reviewing state-clone performance, the Indiana campaign `23793592462` showed weak conversion efficiency and most of its high impression volume came from the Search campaign's Content/Display network:

- Content/Display: `$114.59` spend, `10,042` impressions, `36` clicks, `0` conversions
- Google Search: `$135.06` spend, `340` impressions, `8` clicks, `0` conversions
- Search network: `$40.98` spend, `92` impressions, `22` clicks, `1` conversion

The campaign had the same core setup as Ohio/New Mexico, so this was treated as a network quality issue rather than a broken geo/ad configuration. On 2026-05-12, `target_content_network` was disabled for Indiana only. Readback confirmed:

- `targetGoogleSearch=true`
- `targetSearchNetwork=true`
- `targetContentNetwork=false`
- `targetPartnerSearchNetwork=false`

### Indiana IHCP keyword and query cleanup

After Indiana performance review showed low-quality query volume from broad Medicaid/provider-enrollment matches, the Indiana Search campaign was tightened with a validated Google Ads API mutation.

Campaign:

- `23793592462` / `schedule meeting - Indiana 1777010299107`
- Ad group `196920927778` / `Ad group 1`

Live changes applied:

- Added IHCP positive keywords:
  - phrase `ihcp therapist billing`
  - phrase `indiana ihcp therapist billing`
  - phrase `ihcp therapy billing`
  - phrase `indiana health coverage programs billing`
  - phrase `ihcp credentialing`
  - exact `ihcp billing`
- Added query-cleanup negatives:
  - phrase `cpt code`
  - broad `90832`
  - broad `90837`
  - broad `npi`
  - phrase `transportation provider`
  - phrase `provider portal`
  - broad `interchange`
  - phrase `medical billing startups`
  - phrase `add on codes`
  - phrase `how to become a medicaid provider`
- Fixed Indiana sitelink asset `352641782552` description typo from `SimplePractice, TherapyNotes ect` to `SimplePractice, TherapyNotes, etc.`

Validation:

```text
VALIDATE ONLY: 16 operations
{}
VALIDATE ONLY: 1 operations
{}
```

Post-apply readback confirmed all 16 criteria were `ENABLED` and sitelink asset `352641782552` now reads `SimplePractice, TherapyNotes, etc.`

Landing page copy was also updated in `/Users/dax/bomi/landing/app/indiana/page.tsx` to mention Indiana Medicaid / IHCP workflow where the page already discussed Indiana Medicaid workflow.

### Ohio budget bump

Based on recent Ohio efficiency (`5` conversions over the last 7 days at roughly `$24` CPA, with budget-limited impression share), the Ohio Search campaign budget was increased after validate-only API approval.

Campaign:

- `23783665086` / `schedule meeting - Ohio 1777010295580`
- Budget `15527871518` / `schedule meeting - Ohio 1777010295580`
- Budget sharing readback: `explicitly_shared=false`; only Ohio uses the budget.

Change:

- From `$15/day` to `$20/day`

Validation:

```text
validateOnly budget update: {}
```

Post-apply readback confirmed:

- Campaign status: `ENABLED`
- Campaign primary status: `ELIGIBLE`
- Budget amount: `$20/day`

### Remaining state budget bumps

After the Ohio move, the remaining enabled state Search campaigns were increased to match `$20/day`. Each budget was checked first to confirm it was not shared by another non-removed campaign.

Changes:

- Illinois / `schedule meeting` campaign `23586656126`: budget `15388854853` from `$15/day` to `$20/day`
- New Mexico campaign `23786543262`: budget `15530260682` from `$15/day` to `$20/day`
- Indiana campaign `23793592462`: budget `15532453350` from `$15/day` to `$20/day`

Validation:

```text
validateOnly budget update for 3 operations: {}
```

Post-apply readback confirmed all four state Search campaigns are now `ENABLED`, `ELIGIBLE`, and at `$20/day`:

- Illinois / `23586656126`
- Ohio / `23783665086`
- New Mexico / `23786543262`
- Indiana / `23793592462`

## 2026-05-14

### EHR vs expert billing team paused-ad build

Prepared reusable scripts for the pooled-state EHR-vs-Bomi ad plan:

- `scripts/moda_generate_ehr_vs_bomi_assets.py`
- `scripts/meta_create_ehr_vs_bomi_pooled.py`
- `scripts/google_ads_create_ehr_vs_bomi_demand_gen.py`

The planned test is:

- Meta/Facebook Feed only, paused, `$20/day`, pooled across Illinois, Ohio, Indiana, and New Mexico.
- Google Demand Gen, paused, `$20/day`, pooled across Illinois, Ohio, Indiana, and New Mexico.
- Homepage landing URL with platform-specific UTMs.
- Safer creative wording: `Your EHR is like DIY tax software. BillWithBomi is like having a CPA.`

After the Moda API keys were refreshed, Moda preflight on 2026-05-14 showed:

- `credits_remaining=1500`
- Default Bomi Health brand kit `bk_0PHT577BFH8E9VV0M9QYNM1M24`
- Bomi logo upload succeeded and deduplicated on retry

To conserve credits, the final generation used one `lite` Moda square task and
created the landscape and portrait derivatives locally from that square asset.
The task succeeded:

- Task: `task_419RMBQN1T9ZCVPPW8F3KNGWEF`
- Canvas: `cvs_3KGFAVNS0Y98V9NKPD5V3VZJ1P`
- Credits remaining after generation: `1290`
- Asset folder: `assets/ehr_vs_bomi_tax_software_2026-05-14/`

Verified generated files:

- `ehr-vs-bomi-square-1080x1080.png`
- `ehr-vs-bomi-landscape-1200x628.png`
- `ehr-vs-bomi-portrait-padded-1080x1920.png`

Meta paused creation:

- Campaign: `120248005997630170`
- Ad set: `120248006000710170`
- Creative: `998947609178695`
- Ad: `120248006007810170`
- Budget: `$20/day`
- Placement: Facebook Feed only
- Readback: campaign/ad set/ad configured status `PAUSED`; campaign/ad set effective status `PAUSED`; ad effective status `PENDING_REVIEW`

Google Demand Gen paused creation:

- Campaign: `23851846966`
- Budget: `15572267732` / `$20/day`
- Ad group: `197222331835`
- Ad: `808795849849`
- Audience: `customers/5613091482/audiences/347573090`
- Readback: campaign/ad group/ad status `PAUSED`; campaign primary status `PAUSED`; policy review `REVIEW_IN_PROGRESS`

Google `validateOnly` passed before applying. No existing active campaigns were
modified, and no new objects were activated.

Activation follow-up on 2026-05-14:

- Meta was activated after user approval.
- Meta activation readback: campaign/ad set/ad configured status `ACTIVE`; campaign/ad set/ad effective status `ACTIVE`; ad set budget remained `$20/day`.
- Google Demand Gen was not activated because policy review remained `REVIEW_IN_PROGRESS` with approval status `UNKNOWN`.
- A thread follow-up automation was created to recheck Google review hourly and enable only campaign `23851846966`, ad group `197222331835`, and ad `808795849849` after approval clears.

Commands:

```sh
python3 scripts/moda_generate_ehr_vs_bomi_assets.py
/Users/dax/.cache/bomi-ads-venv/bin/python scripts/meta_create_ehr_vs_bomi_pooled.py --apply
python3 scripts/google_ads_create_ehr_vs_bomi_demand_gen.py
python3 scripts/google_ads_create_ehr_vs_bomi_demand_gen.py --apply
```

### Own your business paused-ad build

Prepared campaign-specific wrappers that reuse the proven EHR workflow helpers:

- `scripts/moda_generate_own_business_assets.py`
- `scripts/meta_create_own_business_pooled.py`
- `scripts/google_ads_create_own_business_demand_gen.py`

The planned test is:

- Meta/Facebook Feed only, paused, `$20/day`, pooled across Illinois, Ohio, Indiana, and New Mexico.
- Google Demand Gen, paused, `$20/day`, pooled across Illinois, Ohio, Indiana, and New Mexico.
- Homepage landing URL with platform-specific UTMs.
- Creative wording: `Own your business. Let us handle insurance.`

The repo agent notes were updated to make the low-credit Moda path explicit:
default to one `lite` square master, then create landscape/portrait derivatives
locally unless extra Moda generations are explicitly approved or needed after
visual/file verification.

Moda generation:

- Preflight credits remaining: `1290`
- Default Bomi Health brand kit: `bk_0PHT577BFH8E9VV0M9QYNM1M24`
- Task: `task_4X68C2FG1G9R3SSER2HA52YDX4`
- Canvas: `cvs_1WHG24DYJV96AVVEESRV54392Y`
- Credits remaining after generation: `1290`
- Asset folder: `assets/own_business_handle_insurance_2026-05-14/`

Verified generated files:

- `own-business-handle-insurance-square-1080x1080.png`
- `own-business-handle-insurance-landscape-1200x628.png`
- `own-business-handle-insurance-portrait-padded-1080x1920.png`

Meta paused creation:

- Campaign: `120248011749820170`
- Ad set: `120248011750720170`
- Creative: `1552847629515540`
- Ad: `120248011752520170`
- Budget: `$20/day`
- Placement: Facebook Feed only
- Readback: campaign/ad set/ad configured status `PAUSED`; campaign/ad set effective status `PAUSED`; ad effective status `PENDING_REVIEW`

Google Demand Gen paused creation:

- Campaign: `23842205493`
- Budget: `15572396876` / `$20/day`
- Ad group: `199003668400`
- Ad: `808769311863`
- Audience: `customers/5613091482/audiences/347578874`
- Readback: campaign/ad group/ad status `PAUSED`; campaign primary status `PAUSED`; policy review `REVIEW_IN_PROGRESS`

Google `validateOnly` passed before applying. No existing active campaigns were
modified, and no new objects were activated.

The existing hourly thread follow-up automation `check-google-ad-review` was
updated to also watch this Own Your Business Meta/Google stack. It should only
activate the exact listed Meta and Google objects after the relevant reviews
clear, while leaving all other ads untouched.

Commands:

```sh
python3 scripts/moda_generate_own_business_assets.py
/Users/dax/.cache/bomi-ads-venv/bin/python scripts/meta_create_own_business_pooled.py --apply
python3 scripts/google_ads_create_own_business_demand_gen.py
python3 scripts/google_ads_create_own_business_demand_gen.py --apply
```

## 2026-04-24

### Troff content workflow

Added `troff/` to the ads automation repo as a local content ops app for:

- Turning SEO questions or source URLs into landing-ready blog drafts.
- Extracting 3-5 reusable insights from each blog.
- Generating channel-native social drafts from those insights.
- Reviewing, queuing, and publishing blog/social pieces through configured landing and Postiz integrations.
- Optionally attaching generated media card URLs to selected social surfaces.

### Goal

Avoid rebuilding campaigns manually in the Google Ads UI. The immediate requested task was to clone the current Illinois campaign setup for:

- Ohio: `https://billwithbomi.com/ohio`
- Indiana: `https://billwithbomi.com/indiana`

### Research and approach

We checked the current Google Ads automation options:

- Google Ads Scripts are good for one-off UI-managed tasks and can read/mutate account resources from inside Google Ads.
- Google Ads API is the best path for Codex-driven terminal automation.
- Google's Google Ads MCP server exists, but it is read-only, so it is useful for inspection rather than campaign creation.

Decision: keep both options in this repo.

- `google-ads-scripts/` contains paste-into-Google-Ads scripts.
- `scripts/` contains local API scripts Codex can run.

### API access setup

We created local Google Ads API access using:

- A Google Ads manager account developer token.
- A Google Cloud OAuth client.
- An OAuth refresh token for the scope `https://www.googleapis.com/auth/adwords`.
- Bomi advertiser customer ID.
- Manager login customer ID.

The real credentials live outside this repo in a local ignored `.env` file. They were not committed.

### Read-only account audit

Codex successfully queried the Bomi Ads account through the Google Ads API.

Account:

- Customer: `561-309-1482` / Bomi Health, Inc.
- Currency: USD
- Time zone: America/Los_Angeles
- Status: enabled

Enabled campaigns found:

- `schedule meeting` (`23586656126`)
- `General Bomi Leads` (`23591492785`)

`schedule meeting` was selected as the recommended Ohio/Indiana clone source because it is more explicitly Illinois/local and had stronger recent conversion volume.

Detailed audit notes are in [CLONE_PREP.md](CLONE_PREP.md).

### Clone preparation

The local API script was expanded to clone:

- Budget.
- Campaign settings.
- State location targeting.
- Ad group.
- Keywords.
- Responsive search ad.
- Unique sitelinks with target-state URLs.
- Existing business name/logo assets.

It also handles:

- Required EU political advertising declaration.
- Existing exemptible policy keys for third-party-support-related keywords in the source campaign.
- State copy replacement for Illinois/IL and the existing "Serving Illinois and Indiana practices" description.
- Launch keyword cleanup:
  - Excludes Harmonic Office Solutions keywords from state clones.
  - Replaces broad `illinois medicaid` with provider-intent Medicaid keywords per state.
  - Adds broad negatives for consumer/government Medicaid terms.

### Validation

The clone was validated with Google Ads API `validateOnly` for both Ohio and Indiana.

Result:

```text
VALIDATE ONLY: Ohio ... operations: 38 ... {}
VALIDATE ONLY: Indiana ... operations: 38 ... {}
No campaigns were created.
```

Local syntax checks also pass:

```sh
python3 -m py_compile scripts/google_ads_clone_state_campaigns.py
node --check google-ads-scripts/audit_state_campaigns.js
node --check google-ads-scripts/clone_state_campaigns.js
```

### Repository publication

The automation and docs were pushed to:

```text
https://github.com/redaxed/bomi-ads
```

Initial commit:

```text
7cb4aed Add Google Ads automation scripts
```

The repo was then reorganized so Google Ads UI scripts live in `google-ads-scripts/`, terminal scripts live in `scripts/`, and documentation lives in `docs/`.

### Campaign creation

After the keyword cleanup was added, validation was run again:

```text
VALIDATE ONLY: Ohio ... operations: 44 ... {}
VALIDATE ONLY: Indiana ... operations: 44 ... {}
```

Then the API script was run with `--apply`.

Created paused campaigns:

- Ohio: `23783665086` / `schedule meeting - Ohio 1777010295580`
- Indiana: `23793592462` / `schedule meeting - Indiana 1777010299107`

Post-create verification confirmed:

- Both campaigns are paused.
- Each has a `$15/day` copied budget.
- Ohio targets `geoTargetConstants/21168` / Ohio.
- Indiana targets `geoTargetConstants/21148` / Indiana.
- Ads are paused and point to the correct state landing pages.
- Sitelinks are enabled and point to the correct target-state URL anchors.
- Business name and business logo assets are attached.
- Harmonic keywords were excluded.
- State Medicaid provider-intent keywords and broad negatives were created.

### Campaign enablement

After review in Google Ads, the Ohio and Indiana cloned campaigns were enabled on 2026-04-24.

A live Google Ads API reporting pull later confirmed both state clones currently report `ENABLED`:

- Ohio: `23783665086` / `schedule meeting - Ohio 1777010295580`
- Indiana: `23793592462` / `schedule meeting - Indiana 1777010299107`

Daily report campaign status reflects the current API campaign state. Metrics still reflect the selected report window.

### Source of truth cleanup

The local `/Users/dax/bomi/bomi-ads` checkout became the source of truth for ads automation. The real ignored `.env` was copied into that repo, the dated report artifact was preserved under `reports/`, and the old top-level `/Users/dax/bomi/ads` folder was retired.
