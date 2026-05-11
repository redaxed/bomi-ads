# Meta Ads Handoff

Last updated: 2026-05-11, America/Los_Angeles

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

## Active Ads

### Instagram Story - BCCHP Illinois Therapists

- Folder: `assets/bomi_bcbs_scammas/meta-instagram-story-2026-05-11-bcchp-il-therapists/`
- Campaign: `120247752438820170`
- Ad set: `120247752439090170`
- Creative: `1668331050960382`
- Ad: `120247752442290170`
- Budget: `$20/day`
- Placement: Instagram Story only
- Asset: `Bomi Health Digital Ad - Instagram Story Ad - 1080x1920.png`
- Image hash: `180cb7cfa5905f28cf4792dc108d6bcc`
- Latest status checked on 2026-05-11: campaign/ad set/ad `ACTIVE`; ad effective status `ACTIVE`

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
- Latest status checked on 2026-05-11: campaign/ad set/ad `ACTIVE`; ad effective status `ACTIVE`

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

## Known Meta API Gotchas

- Campaigns using ad-set-level budgets required `is_adset_budget_sharing_enabled=false`.
- Do not explicitly send `geo_locations.location_types=["home"]`. Meta returned error `#1870194` saying the location targeting option had been removed. The repair that worked was to send Illinois region targeting while omitting `location_types`; Meta then read back the accepted default `["home","recent"]`.
- Direct `instagram_actor_id` creative creation failed for both `17841477913804164` and `897453543441565`; the working path was a Page-backed creative attached to an Instagram-only ad set.
- If the Meta app is in development mode, Page-backed creative creation can fail with an app-mode error. The app needed to be live/public.
- If the token user lacks ad-account tasks, image/ad creation fails even when read access works.

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
