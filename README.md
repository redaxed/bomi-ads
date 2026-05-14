# Bomi Ads Automation

Scripts and notes for managing Bomi Google Ads without hand-building everything in the Google Ads UI.

## Repository layout

- `google-ads-scripts/` - JavaScript files to paste into Google Ads > Tools > Bulk actions > Scripts.
- `scripts/` - local terminal scripts that call the Google Ads API.
- `troff/` - local content ops app for SEO question -> landing blog -> social drafts.
- `docs/` - setup notes, campaign audit findings, and clone prep notes.
- `reports/` - dated ads report artifacts.
- `skills/` - local Codex workflow instructions for recurring ads work.
- `.env.example` - local environment template. Copy it to `.env`; never commit real secrets.

## Current status

We have working Google Ads API access for the Bomi account through local credentials.

Ohio and Indiana campaigns have been created from the `schedule meeting` source campaign. They were created paused, reviewed in Google Ads, and then enabled on 2026-04-24.

Created campaigns:

- Ohio: `23783665086` / `schedule meeting - Ohio 1777010295580` / currently `ENABLED`
- Indiana: `23793592462` / `schedule meeting - Indiana 1777010299107` / currently `ENABLED`

Demand Gen campaigns created from the current Meta visual assets on 2026-05-12:

- Exact titles: `23842274081` / `IL Therapist Reimbursement Review - Exact Titles - Demand Gen - 2026-05-12` / `$20/day` / currently `ENABLED`
- Operators: `23837011356` / `IL Therapist Reimbursement Review - Operators - Demand Gen - 2026-05-12` / `$20/day` / currently `ENABLED`

Pooled EHR-vs-Bomi test created on 2026-05-14:

- Meta/Facebook Feed: campaign `120248005997630170`, ad set `120248006000710170`, ad `120248006007810170` / `$20/day` / currently `ACTIVE`
- Google Demand Gen: campaign `23851846966`, ad group `197222331835`, ad `808795849849` / `$20/day` / currently `PAUSED` pending policy review, with hourly follow-up automation `check-google-ad-review`
- Assets: `assets/ehr_vs_bomi_tax_software_2026-05-14/`

Pooled Own Your Business test created on 2026-05-14:

- Meta/Facebook Feed: campaign `120248011749820170`, ad set `120248011750720170`, ad `120248011752520170` / `$20/day` / currently `PAUSED` pending review, with hourly follow-up automation `check-google-ad-review`
- Google Demand Gen: campaign `23842205493`, ad group `199003668400`, ad `808769311863` / `$20/day` / currently `PAUSED` pending policy review, with hourly follow-up automation `check-google-ad-review`
- Assets: `assets/own_business_handle_insurance_2026-05-14/`

See [docs/WORK_LOG.md](docs/WORK_LOG.md) for the narrative of what has been done so far, [docs/CLONE_PREP.md](docs/CLONE_PREP.md) for the exact account audit and clone plan, and [docs/META_ADS_LEARNINGS.md](docs/META_ADS_LEARNINGS.md) for Meta Ads API and targeting lessons.

## Recommended workflow

1. Keep credentials in local `.env`.
2. Audit first.
3. Run validation before writes.
4. Create new campaigns paused.
5. Review in Google Ads before enabling.

## Daily report automation

The Codex `Ads Report` automation uses [skills/daily-ads-report/SKILL.md](skills/daily-ads-report/SKILL.md). Each run should:

1. Generate the previous full account-local day report.
2. Generate a Slack-ready summary and SVG chart artifact.
3. Commit and push the dated report artifacts to this repo.
4. Post the generated summary to Slack `#gtm`.

The automation posts through the connected Slack app user and should not include secrets or raw credential details.

## Troff content workflow

[troff/](troff/) is the local content tool for turning one SEO question into a reusable content package:

```text
SEO question or source URL -> landing blog draft -> 3-5 key insights -> social drafts -> review queue -> publish
```

It can write blog posts into the sibling `landing` repo, extract the strongest insights from the blog draft, generate LinkedIn/Reddit/Facebook/Instagram/TikTok drafts for enabled channels, and optionally attach generated media card URLs to social posts.

Quick start:

```sh
cd troff
cp .env.example .env
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
.venv/bin/uvicorn app.main:app --reload --port 8080
```

Set `LANDING_REPO_PATH=/Users/dax/bomi/landing` for host-local blog publishing. For Docker, mount `../../landing:/landing` and set `LANDING_REPO_PATH=/landing` inside `.env`.

## Credentials

Copy the example file:

```sh
cp .env.example .env
```

Fill in:

```sh
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_CUSTOMER_ID=
GOOGLE_ADS_LOGIN_CUSTOMER_ID=
```

Do not paste secrets into chat and do not commit `.env`. The local source-of-truth checkout keeps the real ignored file at `/Users/dax/bomi/bomi-ads/.env`; Codex automation worktrees should read that absolute path if their temporary checkout does not have its own `.env`.

Credential setup details are in [docs/API_ACCESS.md](docs/API_ACCESS.md).

## Google Ads UI scripts

Use these when you want a low-friction UI path:

- [google-ads-scripts/audit_state_campaigns.js](google-ads-scripts/audit_state_campaigns.js) - read-only audit script.
- [google-ads-scripts/clone_state_campaigns.js](google-ads-scripts/clone_state_campaigns.js) - UI-run clone script.

Paste into Google Ads > Tools > Bulk actions > Scripts. Use Preview before Run.

## Local API script

Use this when you want Codex or a terminal to audit/validate/apply from the API:

- [scripts/google_ads_clone_state_campaigns.py](scripts/google_ads_clone_state_campaigns.py)
- [scripts/google_ads_daily_report.py](scripts/google_ads_daily_report.py)
- [scripts/google_ads_create_il_therapist_demand_gen.py](scripts/google_ads_create_il_therapist_demand_gen.py)
- [scripts/moda_generate_ehr_vs_bomi_assets.py](scripts/moda_generate_ehr_vs_bomi_assets.py)
- [scripts/meta_create_ehr_vs_bomi_pooled.py](scripts/meta_create_ehr_vs_bomi_pooled.py)
- [scripts/google_ads_create_ehr_vs_bomi_demand_gen.py](scripts/google_ads_create_ehr_vs_bomi_demand_gen.py)
- [scripts/moda_generate_own_business_assets.py](scripts/moda_generate_own_business_assets.py)
- [scripts/meta_create_own_business_pooled.py](scripts/meta_create_own_business_pooled.py)
- [scripts/google_ads_create_own_business_demand_gen.py](scripts/google_ads_create_own_business_demand_gen.py)

Validate only:

```sh
set -a
source .env
set +a
python3 scripts/google_ads_clone_state_campaigns.py --source-campaign-id 23586656126
```

Create paused Ohio and Indiana campaigns:

```sh
set -a
source .env
set +a
python3 scripts/google_ads_clone_state_campaigns.py --source-campaign-id 23586656126 --apply
```

## Validation

Local syntax checks:

```sh
python3 -m py_compile scripts/google_ads_clone_state_campaigns.py scripts/google_ads_daily_report.py scripts/google_ads_create_il_therapist_demand_gen.py
node --check google-ads-scripts/audit_state_campaigns.js
node --check google-ads-scripts/clone_state_campaigns.js
```

Google Ads API validation passed for both Ohio and Indiana in `validateOnly` mode before the paused campaigns were created.

The pooled EHR-vs-Bomi workflow generated one Moda square asset on 2026-05-14 and derived the extra formats locally to conserve credits. Meta and Google Demand Gen objects were created paused first; Meta was later activated after user approval, while Google Demand Gen remains paused pending review:

```sh
python3 scripts/moda_generate_ehr_vs_bomi_assets.py
/Users/dax/.cache/bomi-ads-venv/bin/python scripts/meta_create_ehr_vs_bomi_pooled.py --apply
python3 scripts/google_ads_create_ehr_vs_bomi_demand_gen.py
python3 scripts/google_ads_create_ehr_vs_bomi_demand_gen.py --apply
```

The pooled Own Your Business workflow used the same low-credit pattern: one
Moda square asset, local derivatives, then paused Meta and Google Demand Gen
objects:

```sh
python3 scripts/moda_generate_own_business_assets.py
/Users/dax/.cache/bomi-ads-venv/bin/python scripts/meta_create_own_business_pooled.py --apply
python3 scripts/google_ads_create_own_business_demand_gen.py
python3 scripts/google_ads_create_own_business_demand_gen.py --apply
```
