# Bomi Ads Automation

Scripts and notes for managing Bomi Google Ads without hand-building everything in the Google Ads UI.

## Repository layout

- `google-ads-scripts/` - JavaScript files to paste into Google Ads > Tools > Bulk actions > Scripts.
- `scripts/` - local terminal scripts that call the Google Ads API.
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

See [docs/WORK_LOG.md](docs/WORK_LOG.md) for the narrative of what has been done so far, and [docs/CLONE_PREP.md](docs/CLONE_PREP.md) for the exact account audit and clone plan.

## Recommended workflow

1. Keep credentials in local `.env`.
2. Audit first.
3. Run validation before writes.
4. Create new campaigns paused.
5. Review in Google Ads before enabling.

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
python3 -m py_compile scripts/google_ads_clone_state_campaigns.py scripts/google_ads_daily_report.py
node --check google-ads-scripts/audit_state_campaigns.js
node --check google-ads-scripts/clone_state_campaigns.js
```

Google Ads API validation passed for both Ohio and Indiana in `validateOnly` mode before the paused campaigns were created.
