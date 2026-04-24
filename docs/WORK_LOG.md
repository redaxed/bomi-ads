# Work Log

This records what has been done so far for Bomi Google Ads automation.

## 2026-04-24

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

### Source of truth cleanup

The local `/Users/dax/bomi/bomi-ads` checkout became the source of truth for ads automation. The real ignored `.env` was copied into that repo, the dated report artifact was preserved under `reports/`, and the old top-level `/Users/dax/bomi/ads` folder was retired.
