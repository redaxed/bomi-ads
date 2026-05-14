# Targeting Feedback Implementation

Date: 2026-05-14, applied around 14:00 PDT.

## What Changed

Google Search was cleaned up and expanded using the targeting-feedback plan:

- Disabled Content/Display expansion on the Illinois, Ohio, and New Mexico state Search campaigns.
- Left Indiana's Content network off; it was already disabled before this pass.
- Created one new enabled Search ad group per state campaign named `Payer/program phrase + exact`.
- Added payer/program keywords as both phrase and exact match in those new ad groups.
- Added one enabled responsive search ad in each new payer/program ad group.
- Added the shared conservative negative map to General Bomi Leads and all four state Search campaigns.
- Preserved every existing campaign budget.
- Did not create or change any Demand Gen or Meta objects.

## Scripts

- `/Users/dax/bomi/bomi-ads/scripts/google_ads_optimize_state_payer_targeting.py`
  - Validates by default.
  - Applies only with `--apply`.
  - Has `--read-only` readback for campaign network settings, payer ad groups, payer keyword counts, RSA status, and negative counts.
- `/Users/dax/bomi/bomi-ads/scripts/google_ads_plan_demand_gen_segments.py`
  - Config-only scaffold for future Demand Gen segmentation.
  - Does not call Google Ads or create objects.

## Validation

Initial API validation caught exemptible Google policy flags on a few `behavioral health` and `billing help` keywords. The script now adds exemption keys for:

- `HEALTH_IN_PERSONALIZED_ADS`
- `THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT`

Final validation passed:

```text
VALIDATE ONLY: 418 operations
{}
```

Apply passed:

```text
APPLIED: 418 operations
```

An immediate idempotency check then returned:

```text
No Google Ads changes needed.
```

## Campaign Readback

| Campaign | ID | Status | Primary status | Budget | Search network | Content network | Partner search |
| --- | ---: | --- | --- | ---: | --- | --- | --- |
| General Bomi Leads | `23591492785` | `ENABLED` | `ELIGIBLE` | `$25/day` | `false` | `false` | `false` |
| Illinois / `schedule meeting` | `23586656126` | `ENABLED` | `ELIGIBLE` | `$20/day` | `true` | `false` | `false` |
| Ohio / `schedule meeting - Ohio 1777010295580` | `23783665086` | `ENABLED` | `ELIGIBLE` | `$20/day` | `true` | `false` | `false` |
| Indiana / `schedule meeting - Indiana 1777010299107` | `23793592462` | `ENABLED` | `ELIGIBLE` | `$20/day` | `true` | `false` | `false` |
| New Mexico / `schedule meeting - New Mexico 1777091221508` | `23786543262` | `ENABLED` | `ELIGIBLE` | `$20/day` | `true` | `false` | `false` |

## New Payer Ad Groups

All four payer/program ad groups are enabled. The new RSAs are enabled but still in Google review immediately after creation.

| State | Campaign ID | Ad group ID | Keywords present | RSA ad ID | RSA status | Approval | Review |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Illinois | `23586656126` | `193750706822` | `30/30` | `808831359264` | `ENABLED` | `UNKNOWN` | `REVIEW_IN_PROGRESS` |
| Ohio | `23783665086` | `194310231497` | `28/28` | `808865425120` | `ENABLED` | `UNKNOWN` | `REVIEW_IN_PROGRESS` |
| Indiana | `23793592462` | `195852581745` | `28/28` | `808865467198` | `ENABLED` | `UNKNOWN` | `REVIEW_IN_PROGRESS` |
| New Mexico | `23786543262` | `194310233417` | `26/26` | `808865467363` | `ENABLED` | `UNKNOWN` | `REVIEW_IN_PROGRESS` |

## Negative Readback

The full planned negative map is present on each Search campaign:

| Campaign | ID | Planned negatives present |
| --- | ---: | ---: |
| General Bomi Leads | `23591492785` | `59/59` |
| Illinois / `schedule meeting` | `23586656126` | `59/59` |
| Ohio / `schedule meeting - Ohio 1777010295580` | `23783665086` | `59/59` |
| Indiana / `schedule meeting - Indiana 1777010299107` | `23793592462` | `59/59` |
| New Mexico / `schedule meeting - New Mexico 1777091221508` | `23786543262` | `59/59` |

## Payer Name Verification

Current payer/program naming was checked against official or state-adjacent sources immediately before implementation:

- Illinois HFS HealthChoice Illinois managed care plan materials: [hfs.illinois.gov](https://hfs.illinois.gov/medicalclients/managedcare.html)
- Ohio Medicaid managed-care and PNM materials: [SPBM managed-care plan links](https://spbm.medicaid.ohio.gov/SPContent/DocumentLibrary/Community%20Resources), [ODM provider enrollment](https://medicaid.ohio.gov/resources-for-providers/enrollment-and-support/provider-enrollment), and [ODM centralized credentialing FAQ](https://dam.assets.ohio.gov/image/upload/managedcare.medicaid.ohio.gov/PNM/Centralized-Credentialing-FAQ.pdf)
- Indiana Medicaid managed-care plan materials: [in.gov/medicaid](https://www.in.gov/medicaid/providers/business-transactions/managed-care-health-plans/)
- New Mexico HCA Turquoise Care health plans and Turquoise Claims materials: [hca.nm.gov Turquoise Care](https://www.hca.nm.gov/turquoise-care-health-plans/) and [hca.nm.gov Turquoise Claims](https://www.hca.nm.gov/providers/turquoise-claims/)

## What To Watch

- The four new RSAs should be checked again after review clears.
- The 24-hour and 72-hour follow-up reports should compare spend, clicks, conversions, CPA, and search terms by campaign, with special attention to whether payer/program exact+phrase traffic improves qualified intent.
- Meta and Demand Gen remain in planning mode for this feedback pass. The next creative/targeting step is self-selection copy and form qualification, not additional broad audience expansion.
