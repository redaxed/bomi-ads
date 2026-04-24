# Google Ads API access for Codex

Goal: let Codex run read-only audits and tightly-scoped campaign creation from the terminal without using the Google Ads UI for every change.

Do not paste secrets into chat. Put secrets in a local ignored file such as `ads/.env` or a local JSON key file.

## What Codex can do with API access

- List accessible Google Ads accounts.
- Audit campaigns, budgets, targeting, ad groups, keywords, ads, and assets.
- Validate campaign mutations before creating anything.
- Create paused campaigns, budgets, ad groups, keywords, and ads.
- Produce change summaries and local scripts for repeatable workflows.

Default safety posture for Bomi ads work:

- Audit first.
- Validate-only / dry run before writes.
- Create new campaigns and ads paused.
- Do not enable campaigns or increase spend without explicit confirmation.

## Exact setup path

You need two different kinds of access:

1. **A Google Ads API developer token** from a Google Ads manager account.
2. **Authentication to your actual ads customer account** through OAuth or a service account.

Seeing `The API Center is only available to manager accounts` is expected if you are in a normal advertiser account. The API Center lives under a manager account, sometimes called an MCC account.

### Step 1: Create or use a Google Ads manager account

If you already have a Google Ads manager account, use that.

If you do not:

1. Go to `https://ads.google.com/home/tools/manager-accounts/`.
2. Create a manager account.
3. If Google will not let your existing email create one, use a separate Google login that is not already tied to a Google Ads advertiser account.

This does not replace the current Bomi ads account. It is a parent/manager shell that can link to it.

### Step 2: Link the Bomi advertiser account to the manager account

From the manager account:

1. Click the Accounts icon.
2. Open Sub-account settings.
3. Click `+`.
4. Choose Link existing account.
5. Enter the customer ID of the existing Bomi Google Ads account.
6. Send the link request.

Then accept the request from the existing Bomi advertiser account:

1. Open the Bomi Google Ads account.
2. Go to Admin > Access and security.
3. Open the Managers tab.
4. Accept the pending manager link request.

### Step 3: Get the developer token

From the manager account:

1. Go to `https://ads.google.com/aw/apicenter`.
2. Complete the API Access form if needed.
3. Copy the developer token when Google issues one.

Important: if Google only gives the token **Test Account Access**, it will not work against the live Bomi account. Explorer, Basic, or Standard access should be usable for production accounts, subject to Google limits and review.

### Step 4: Create OAuth credentials

For the fastest local setup:

1. Open Google Cloud Console.
2. Create or choose a project.
3. Enable the Google Ads API for that project.
4. Configure the OAuth consent screen if prompted.
5. Create an OAuth client ID.
6. Use either a Desktop app client or a Web app client.
7. Save the `client_id` and `client_secret`.

### Step 5: Generate a refresh token

Use Google's user-credentials helper, OAuth Playground, or another OAuth flow for the scope:

```text
https://www.googleapis.com/auth/adwords
```

Keep the resulting `refresh_token` local. Do not paste it into chat.

### Step 6: Put credentials into `ads/.env`

Create `ads/.env` from `.env.example`:

```sh
cp ads/.env.example ads/.env
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

Notes:

- `GOOGLE_ADS_CUSTOMER_ID` is the Bomi advertiser account that owns the Illinois campaign.
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` is the manager account ID if the OAuth user authenticates through the manager account. If unsure, include the manager account ID.
- Customer IDs can include dashes; the script strips them.

### Step 7: Ask Codex to test read-only access

Ask Codex to run an access check or audit. The first API call should be read-only. The first write-capable run should be validate-only.

## Authentication options

There are two practical choices.

#### Option A: OAuth refresh token

Best for a quick one-person setup.

Needed env vars:

```sh
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_CUSTOMER_ID=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
```

The existing `google_ads_clone_state_campaigns.py` supports this path now.

#### Option B: service account

Best for durable automation because access is tied to an app account, not a human user.

High-level setup:

1. Create a Google Cloud service account.
2. Download its JSON key locally.
3. Add the service account email as a user in Google Ads: Admin > Access and security.
4. Give it only the access level needed for the work.
5. Store the key file somewhere local and ignored, for example `ads/service-account.local.json`.

The current Python script does not yet load service-account JSON directly. Add that before choosing this route.

## Local secret handoff

Create `ads/.env` locally:

```sh
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_CUSTOMER_ID=
GOOGLE_ADS_LOGIN_CUSTOMER_ID=
```

`ads/.env` is ignored by `ads/.gitignore`.

Then ask Codex to run:

```sh
set -a
source ads/.env
set +a
python3 ads/google_ads_clone_state_campaigns.py --source-campaign-name Illinois
```

That command validates the planned Ohio and Indiana campaign clone without creating campaigns.

## Official references

- Developer token: https://developers.google.com/google-ads/api/docs/get-started/dev-token
- Service account workflow: https://developers.google.com/google-ads/api/docs/oauth/service-accounts
- Single-user OAuth workflow: https://developers.google.com/google-ads/api/docs/oauth/single-user-authentication
- Generate user credentials: https://developers.google.com/google-ads/api/samples/generate-user-credentials
