# Ohio and Indiana Google Ads clone prep

Prepared on 2026-04-24 using Google Ads API `v24`.

During prep, clone checks were run with `validateOnly`. The campaigns were later created paused after validation.

## Account

- Customer: `561-309-1482` / Bomi Health, Inc.
- Currency: USD
- Time zone: America/Los_Angeles
- Manager login customer: `981-286-6982`

## Current enabled campaigns

### `schedule meeting`

- Campaign ID: `23586656126`
- Type: Search
- Status: enabled
- Bidding: Maximize Conversions
- Budget: `$15/day`
- Location intent: presence only
- Locations: Illinois, Champaign, Paxton, Urbana
- Language: English
- Last 30 days: `$460.31` cost, `226` clicks, `6,812` impressions, `21` conversions
- Final URL: `https://www.billwithbomi.com/illinois`
- Assets: 8 unique campaign assets after dedupe, including sitelinks, business name, and logo

This is the recommended source campaign for Ohio and Indiana cloning because it has the clearer Illinois-specific copy and stronger recent conversion count.

### `General Bomi Leads`

- Campaign ID: `23591492785`
- Type: Search
- Status: enabled
- Bidding: Maximize Conversions
- Budget: `$25/day`
- Location intent: presence or interest
- Locations: Illinois
- Language: English
- Last 30 days: `$748.70` cost, `74` clicks, `2,351` impressions, `3` conversions
- Final URL: `https://www.billwithbomi.com/illinois`

This campaign also targets Illinois, but it looks broader and is not the first clone candidate.

## Prepared clone

Source campaign:

```sh
23586656126 # schedule meeting
```

Targets:

- Ohio: `https://billwithbomi.com/ohio`, geo target `geoTargetConstants/21168`
- Indiana: `https://billwithbomi.com/indiana`, geo target `geoTargetConstants/21148`

The API script prepares, per target state:

- 1 new non-shared campaign budget copied from source (`$15/day`)
- 1 new Search campaign, created paused
- State-level location targeting
- 1 ad group copied from source
- Keywords copied from source, with Illinois/IL rewritten to target state
- Harmonic Office Solutions keywords excluded from the clones
- `illinois medicaid` replaced with provider-intent Medicaid keywords for each target state
- Broad negatives added for consumer/government Medicaid traffic: `pregnant`, `apply`, `office`, `phone number`, `eligibility`, `portal`, `gov`
- 1 responsive search ad copied from source, created paused
- 8 unique campaign assets copied/attached:
  - Sitelinks are recreated with target-state URLs and state text updates
  - Business name and logo assets are attached from existing account assets
- EU political advertising declaration set to `DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING`
- Existing exemptible keyword policy keys included for third-party support keywords that already exist in the source campaign

## Validation status

Validated clean:

```sh
set -a
source .env
set +a
python3 scripts/google_ads_clone_state_campaigns.py --source-campaign-id 23586656126
```

Google returned `{}` for both target mutations in validate-only mode.

No campaigns were created during validation.

## Created campaigns

The apply command was run after validation:

```sh
set -a
source .env
set +a
python3 scripts/google_ads_clone_state_campaigns.py --source-campaign-id 23586656126 --apply
```

Created paused campaigns:

- Ohio: `23783665086` / `schedule meeting - Ohio 1777010295580`
- Indiana: `23793592462` / `schedule meeting - Indiana 1777010299107`

Post-create verification:

- Both campaigns are `PAUSED`
- Both budgets are `$15/day`
- Ohio targets `Ohio, United States`
- Indiana targets `Indiana, United States`
- Ads are paused and point to the state landing pages:
  - `https://billwithbomi.com/ohio`
  - `https://billwithbomi.com/indiana`
- Ad copy was rewritten for each state, including `Free Credentialing (OH/IN)` and state-specific descriptions
- Sitelinks point to target-state URL anchors, including pricing, booking, credentialing, EHR, included, and Medicare/Medicaid sections
- Business name and business logo assets are attached
- Harmonic keywords are not present in the cloned campaigns
- Provider-intent Medicaid keywords and broad negatives are present

Review the new campaigns in Google Ads before enabling them.
