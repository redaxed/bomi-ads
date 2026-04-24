# Google Ads automation notes

Yes: Google Ads campaigns can be created outside the Google Ads UI.

For this specific one-off cloning task, the lowest-friction path is probably **Google Ads Scripts**:

1. Paste `google_ads_scripts_audit_state_campaigns.js` into Google Ads > Tools > Bulk actions > Scripts.
2. Authorize it in the Google Ads UI.
3. Click Preview to inspect the current Illinois, Ohio, and Indiana campaign state.
4. Paste `google_ads_scripts_clone_state_campaigns.js` into a second script.
5. Click Preview first.
6. Click Run only after reviewing the preview/log output.

The local Google Ads API script is still useful if you want Codex to run the whole workflow from the terminal later.

That API path is:

1. Use the Google Ads API for write operations.
2. Keep credentials in local environment variables or a local `.env` file.
3. Run scripts in this folder from Codex/terminal.
4. Use `validateOnly` first, then apply only after reviewing what will be created.

## Current findings

- The Google Ads API supports creating budgets, campaigns, campaign criteria, ad groups, keywords, and ads through mutate requests.
- Current latest version as of 2026-04-24 is Google Ads API `v24`, released 2026-04-22, with sunset planned for May 2027.
- Google also publishes a Google Ads MCP server, which would be nice inside an agent host, but the current release is read-only. It can list accessible customers and query performance with GAQL, but it cannot create Ohio/Indiana campaigns.
- Google also has a Gemini-powered Google Ads API Developer Assistant, but that is a developer helper, not a campaign-creation agent. The reliable write path is still the API.
- Google Ads Scripts can also execute Google Ads API mutate operations from inside the Ads UI, which avoids local OAuth/developer-token setup for small jobs like this.

Useful official docs:

- Google Ads API create campaigns: https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns
- REST mutate examples: https://developers.google.com/google-ads/api/rest/examples
- Location targeting: https://developers.google.com/google-ads/api/docs/targeting/location-targeting
- Geo targets CSV/API reference: https://developers.google.com/google-ads/api/data/geotargets
- Google Ads API MCP server: https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server
- Credential management: https://developers.google.com/google-ads/api/docs/oauth/credential-management

## Credentials needed

For one-person/local automation, use OAuth user credentials or a service account that has been granted Google Ads account access. The script supports the OAuth refresh-token path:

```sh
export GOOGLE_ADS_DEVELOPER_TOKEN="..."
export GOOGLE_ADS_CLIENT_ID="..."
export GOOGLE_ADS_CLIENT_SECRET="..."
export GOOGLE_ADS_REFRESH_TOKEN="..."
export GOOGLE_ADS_CUSTOMER_ID="1234567890"

# Only if using a manager/MCC login above the client account:
export GOOGLE_ADS_LOGIN_CUSTOMER_ID="0987654321"
```

Do not paste these into chat or commit them. A local `ads/.env` is ignored by this folder's `.gitignore`.

For a single Ads user or manager account, Google's OAuth Playground flow is the lowest-friction official route:

1. Create a Web application OAuth client in Google Cloud.
2. Add `https://developers.google.com/oauthplayground` as an authorized redirect URI.
3. In OAuth Playground, use your own OAuth credentials.
4. Set access type to Offline.
5. Authorize the Google Ads API scope: `https://www.googleapis.com/auth/adwords`.
6. Exchange the authorization code for tokens.
7. Put the `refresh_token`, `client_id`, and `client_secret` into your local shell or `.env`.

## Google Ads Script

`google_ads_scripts_audit_state_campaigns.js` is read-only and should run first. It logs:

- Matched campaigns with names containing Illinois, Ohio, or Indiana.
- Campaign status, budget, bidding strategy, search network settings, geo target settings, tracking template, and final URL suffix.
- Positive and negative location targets.
- Ad groups, keywords, responsive search ads, final URLs, display paths, and common campaign assets.

`google_ads_scripts_clone_state_campaigns.js` is the easiest creation path after the audit:

- No local OAuth refresh token or developer token.
- Runs from the Google Ads account you already have open.
- Uses Google Ads Script Preview as the dry run.
- Creates the cloned campaigns and ads paused.

Paste it into the Google Ads Scripts editor, Preview, then Run.

## Local API Script

`google_ads_clone_state_campaigns.py` is a first-pass campaign cloner for this exact use case:

- Finds an existing source campaign by ID or by name match, defaulting to `Illinois`.
- Creates one paused Search campaign for Ohio and one paused Search campaign for Indiana.
- Copies the source daily budget amount into separate, non-shared budgets.
- Copies basic Search network settings and geo target options.
- Copies ad groups, keyword criteria, and responsive search ads.
- Copies unique campaign sitelinks with target-state URLs, and attaches existing business name/logo assets.
- Rewrites obvious `Illinois` text to the destination state in campaign/ad group names, keywords, headlines, and descriptions.
- Replaces responsive search ad final URLs with:
  - `https://billwithbomi.com/ohio`
  - `https://billwithbomi.com/indiana`
- Adds state-level location targeting by resolving Google geo target constants from the API.

It intentionally does not clone every advanced campaign surface yet: audiences, negative keyword lists, conversion goals, experiments, schedules, bid modifiers, and non-responsive-search ad types should be inspected after the first validate-only run.

### Dry run

This validates the Google Ads mutate operations without creating anything:

```sh
python3 ads/google_ads_clone_state_campaigns.py \
  --source-campaign-name Illinois
```

### Apply

This creates paused campaigns:

```sh
python3 ads/google_ads_clone_state_campaigns.py \
  --source-campaign-name Illinois \
  --apply
```

If the Illinois campaign name is ambiguous, use the exact campaign ID:

```sh
python3 ads/google_ads_clone_state_campaigns.py \
  --source-campaign-id 123456789 \
  --apply
```

### Safer launch flow

1. Run dry-run validation.
2. Review the printed plan.
3. Run `--apply`, which still creates everything paused.
4. Open the Google Ads UI only for final review and policy/asset sanity.
5. Enable the new campaigns manually or add an explicit `--enabled` flag later after the script has proven itself.
