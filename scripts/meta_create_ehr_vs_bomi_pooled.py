#!/usr/bin/env python3
"""
Create a paused Meta/Facebook Feed ad for the pooled EHR-vs-Bomi test.

The script creates new objects only and leaves campaign, ad set, and ad paused.
It writes a per-ad INFO.md with object IDs and readback details.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

from ad_tracking_urls import build_meta_feed_url


GRAPH_VERSION = "v22.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
SOURCE_ENV = Path("/Users/dax/bomi/bomi-ads/.env")
OUTPUT_DIR = Path("assets/ehr_vs_bomi_tax_software_2026-05-14")
SQUARE_IMAGE = OUTPUT_DIR / "ehr-vs-bomi-square-1080x1080.png"
INFO_PATH = OUTPUT_DIR / "INFO.md"

AD_ACCOUNT_ID = "act_302351874007793"
PAGE_ID = "588675787671641"

CAMPAIGN_NAME = "Bomi EHR vs Expert Billing Team - Leads - 2026-05-14"
AD_SET_NAME = "Pooled IL OH IN NM therapist operators - Facebook Feed - 2026-05-14"
CREATIVE_NAME = "Bomi EHR vs Expert Billing Team - Facebook Feed - 2026-05-14"
AD_NAME = "Bomi EHR vs Expert Billing Team - Facebook Feed - 2026-05-14"
DAILY_BUDGET_CENTS = 2000
FINAL_URL = (
    build_meta_feed_url(
        "https://www.billwithbomi.com/",
        campaign="ehr_vs_bomi_pooled_states",
        audience="pooled_states_therapist_operators",
    )
)

AD_MESSAGE = (
    "Your EHR gives you the tools. Bomi gives you the expert billing team. "
    "Billing + credentialing for therapists, flat 4% of collections, and no new EHR."
)
AD_HEADLINE = "Stop DIY-ing Insurance Billing"
AD_DESCRIPTION = "Book a free consultation."


class MetaError(RuntimeError):
    pass


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_env() -> None:
    load_env_file(Path.cwd() / ".env")
    load_env_file(SOURCE_ENV)


def access_token() -> str:
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        raise MetaError("Missing required environment variable: META_ACCESS_TOKEN")
    return token


def graph_get(node: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"access_token": access_token(), **(params or {})}
    response = requests.get(f"{GRAPH_BASE}/{node}", params=payload, timeout=60)
    if response.status_code >= 400:
        raise MetaError(f"Meta GET {node} failed: {response.text}")
    return response.json()


def graph_post(
    node: str,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {"access_token": access_token(), **(data or {})}
    response = requests.post(f"{GRAPH_BASE}/{node}", data=payload, files=files, timeout=120)
    if response.status_code >= 400:
        raise MetaError(f"Meta POST {node} failed: {response.text}")
    return response.json()


def ensure_no_existing_campaign() -> None:
    response = graph_get(
        f"{AD_ACCOUNT_ID}/campaigns",
        {
            "fields": "id,name,status,effective_status",
            "limit": 100,
        },
    )
    existing = [
        item
        for item in response.get("data", [])
        if item.get("name") == CAMPAIGN_NAME and item.get("status") != "DELETED"
    ]
    if existing:
        raise MetaError(f"Refusing to create duplicate Meta campaign: {existing}")


def image_hash(path: Path) -> str:
    with path.open("rb") as handle:
        response = graph_post(
            f"{AD_ACCOUNT_ID}/adimages",
            files={"filename": (path.name, handle, "image/png")},
        )
    images = response.get("images", {})
    if not images:
        raise MetaError(f"Could not read image upload response: {response}")
    return next(iter(images.values()))["hash"]


def targeting() -> dict[str, Any]:
    work_positions = [
        ("108163765872304", "Mental health counselor"),
        ("722313654550739", "Licensed Clinical Mental Health Counselor"),
        ("330966250435806", "Licensed Professional Counselor (LPC)"),
        ("334533013408721", "Licensed Clinical Social Worker (LCSW)"),
        ("125071804208180", "Licensed Clinical Social Worker/Therapist"),
        ("723240677773091", "Licensed Marriage and Family Therapist (LMFT)"),
        ("1554307254818982", "Clinical Psychologist"),
        ("335586239976066", "Licensed Clinical Psychologist"),
        ("407489252757668", "Counseling Psychologist"),
        ("1461653794055392", "Psychotherapist-Counselor"),
        ("593422084126001", "Behavioral Therapist"),
        ("108359589220684", "Owner/Psychotherapist"),
        ("718196931629654", "Psychologist, Private Practice"),
        ("911356208895948", "Practice Manager"),
        ("1569299249954237", "Medical Practice Manager"),
        ("893771870644160", "Medical Office Manager"),
        ("668500706594423", "Billing Manager"),
        ("768293416579944", "Medical Biller"),
        ("884216444934879", "Medical Insurance Biller"),
        ("786660018082739", "Billing Specialist"),
        ("342225789309645", "Medical Billing Specialist"),
        ("432841263549002", "Medical Billing and Coding Specialist"),
        ("331557573704439", "Credentialing Specialist"),
        ("544823505660174", "Clinical Director"),
        ("1581181608766724", "Clinic Director"),
        ("1568941850012049", "Director of Clinical Services"),
        ("105563979478424", "Executive director"),
        ("134988453211643", "Executive Director/CEO"),
    ]
    industries = [
        ("6012903159383", "Healthcare and Medical Services"),
        ("6012903168383", "Community and Social Services"),
        ("6008888954983", "Administrative Services"),
        ("6009003311983", "Management"),
        ("6262428231783", "Business Decision Makers"),
        ("6262428209783", "Business decision maker titles and interests"),
        ("6377169550583", "Company size: 1-10 employees"),
        ("6377134779583", "Company size: 11-100 employees"),
    ]
    behaviors = [("6002714898572", "Small business owners")]
    interests = [("6002921291555", "Blue Cross Blue Shield Association")]
    return {
        "geo_locations": {
            "regions": [
                {"key": "3856", "name": "Illinois"},
                {"key": "3878", "name": "Ohio"},
                {"key": "3857", "name": "Indiana"},
                {"key": "3874", "name": "New Mexico"},
            ],
        },
        "age_min": 25,
        "age_max": 65,
        "publisher_platforms": ["facebook"],
        "facebook_positions": ["feed"],
        "flexible_spec": [
            {
                "work_positions": [{"id": item_id, "name": name} for item_id, name in work_positions],
                "industries": [{"id": item_id, "name": name} for item_id, name in industries],
                "behaviors": [{"id": item_id, "name": name} for item_id, name in behaviors],
                "interests": [{"id": item_id, "name": name} for item_id, name in interests],
            }
        ],
        "targeting_automation": {"advantage_audience": 1},
    }


def create_objects() -> dict[str, str]:
    ensure_no_existing_campaign()
    uploaded_hash = image_hash(SQUARE_IMAGE)
    campaign = graph_post(
        f"{AD_ACCOUNT_ID}/campaigns",
        {
            "name": CAMPAIGN_NAME,
            "objective": "OUTCOME_TRAFFIC",
            "buying_type": "AUCTION",
            "special_ad_categories": json.dumps([]),
            "is_adset_budget_sharing_enabled": "false",
            "status": "PAUSED",
        },
    )
    campaign_id = campaign["id"]
    ad_set = graph_post(
        f"{AD_ACCOUNT_ID}/adsets",
        {
            "name": AD_SET_NAME,
            "campaign_id": campaign_id,
            "daily_budget": str(DAILY_BUDGET_CENTS),
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "LINK_CLICKS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "destination_type": "WEBSITE",
            "targeting": json.dumps(targeting()),
            "status": "PAUSED",
        },
    )
    ad_set_id = ad_set["id"]
    creative = graph_post(
        f"{AD_ACCOUNT_ID}/adcreatives",
        {
            "name": CREATIVE_NAME,
            "object_story_spec": json.dumps(
                {
                    "page_id": PAGE_ID,
                    "link_data": {
                        "image_hash": uploaded_hash,
                        "link": FINAL_URL,
                        "message": AD_MESSAGE,
                        "name": AD_HEADLINE,
                        "description": AD_DESCRIPTION,
                        "call_to_action": {
                            "type": "BOOK_NOW",
                            "value": {"link": FINAL_URL},
                        },
                    },
                }
            ),
        },
    )
    creative_id = creative["id"]
    ad = graph_post(
        f"{AD_ACCOUNT_ID}/ads",
        {
            "name": AD_NAME,
            "adset_id": ad_set_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": "PAUSED",
        },
    )
    return {
        "image_hash": uploaded_hash,
        "campaign_id": campaign_id,
        "ad_set_id": ad_set_id,
        "creative_id": creative_id,
        "ad_id": ad["id"],
    }


def readback(ids: dict[str, str]) -> dict[str, Any]:
    return {
        "campaign": graph_get(
            ids["campaign_id"],
            {"fields": "id,name,status,effective_status,objective,special_ad_categories"},
        ),
        "ad_set": graph_get(
            ids["ad_set_id"],
            {"fields": "id,name,status,effective_status,daily_budget,targeting"},
        ),
        "creative": graph_get(
            ids["creative_id"],
            {"fields": "id,name,status,object_story_spec,thumbnail_url"},
        ),
        "ad": graph_get(
            ids["ad_id"],
            {"fields": "id,name,status,effective_status,configured_status,creative"},
        ),
        "preview": graph_get(
            f"{ids['creative_id']}/previews",
            {"ad_format": "DESKTOP_FEED_STANDARD"},
        ),
    }


def write_info(ids: dict[str, str], readback_data: dict[str, Any]) -> None:
    asset_sha = hashlib.sha256(SQUARE_IMAGE.read_bytes()).hexdigest()
    info = f"""# Bomi EHR vs Expert Billing Team Facebook Feed Ad

Created on 2026-05-14 as a paused pooled-state Meta/Facebook Feed test.

## IDs

- Campaign: `{ids['campaign_id']}`
- Ad set: `{ids['ad_set_id']}`
- Creative: `{ids['creative_id']}`
- Ad: `{ids['ad_id']}`
- Image hash: `{ids['image_hash']}`

## Budget And Status

- Daily budget: `2000` cents = `$20/day`
- Creation status: paused only; no activation performed
- Latest readback campaign status: `{readback_data['campaign'].get('status')}` / effective `{readback_data['campaign'].get('effective_status')}`
- Latest readback ad set status: `{readback_data['ad_set'].get('status')}` / effective `{readback_data['ad_set'].get('effective_status')}`
- Latest readback ad status: `{readback_data['ad'].get('status')}` / effective `{readback_data['ad'].get('effective_status')}`

## Asset

- Square image: `{SQUARE_IMAGE}`
- SHA256: `{asset_sha}`

## Copy

Primary text:

```text
{AD_MESSAGE}
```

Headline:

```text
{AD_HEADLINE}
```

Description:

```text
{AD_DESCRIPTION}
```

CTA: `BOOK_NOW`

Final URL:

```text
{FINAL_URL}
```

## Targeting

- Placement: Facebook Feed only
- Regions: Illinois, Ohio, Indiana, New Mexico
- Age: `25-65+`
- Audience: broad therapist/practice-operator flexible spec, Advantage audience expansion enabled

## Readback

```json
{json.dumps(readback_data, indent=2, sort_keys=True)}
```

## Safety Notes

- Objects were created paused first and were not activated.
- Do not activate without explicit user approval.
- Never commit or print `META_ACCESS_TOKEN`.
"""
    INFO_PATH.write_text(info)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Create paused Meta objects.")
    args = parser.parse_args()

    load_env()
    if not SQUARE_IMAGE.exists():
        raise MetaError(f"Missing required square image: {SQUARE_IMAGE}")
    if not args.apply:
        ensure_no_existing_campaign()
        print("Validation passed: no duplicate Meta campaign found and square image exists.")
        print("No Meta objects were created. Use --apply to create paused objects.")
        return 0

    ids = create_objects()
    # Give Meta a moment to settle before status/preview readback.
    time.sleep(2)
    readback_data = readback(ids)
    write_info(ids, readback_data)
    print(json.dumps({"ids": ids, "readback": readback_data}, indent=2, sort_keys=True))
    print(f"INFO written: {INFO_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MetaError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
