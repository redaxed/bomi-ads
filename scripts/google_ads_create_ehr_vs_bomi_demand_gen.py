#!/usr/bin/env python3
"""
Create a paused Google Demand Gen campaign for the pooled EHR-vs-Bomi test.

Validates by default. Use --apply to create paused Google Ads objects. This
script never enables campaigns, ad groups, or ads.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v24")
GOOGLE_ADS_BASE = f"https://googleads.googleapis.com/{API_VERSION}"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
SOURCE_ENV = Path("/Users/dax/bomi/bomi-ads/.env")
OUTPUT_DIR = Path("assets/ehr_vs_bomi_tax_software_2026-05-14")

SQUARE_IMAGE = OUTPUT_DIR / "ehr-vs-bomi-square-1080x1080.png"
LANDSCAPE_IMAGE = OUTPUT_DIR / "ehr-vs-bomi-landscape-1200x628.png"
PORTRAIT_IMAGE = OUTPUT_DIR / "ehr-vs-bomi-portrait-padded-1080x1920.png"
READBACK_PATH = OUTPUT_DIR / "google_ads_readback.json"

CAMPAIGN_DATE = "2026-05-14"
CAMPAIGN_NAME = f"Bomi EHR vs Expert Billing Team - Demand Gen - {CAMPAIGN_DATE}"
AD_GROUP_NAME = "Pooled state therapist operator audience"
AD_NAME = "Bomi EHR vs Expert Billing Team - pooled states"
FINAL_URL = (
    "https://www.billwithbomi.com/"
    "?utm_source=google&utm_medium=paid_demandgen"
    "&utm_campaign=ehr_vs_bomi_pooled_states&utm_content=square_landscape"
)
DAILY_BUDGET_MICROS = 20_000_000
ENGLISH_LANGUAGE = "languageConstants/1000"
STATE_GEOS = [
    "geoTargetConstants/21147",  # Illinois
    "geoTargetConstants/21168",  # Ohio
    "geoTargetConstants/21148",  # Indiana
    "geoTargetConstants/21165",  # New Mexico
]

CUSTOM_AUDIENCE_TERMS = [
    "therapist billing",
    "therapy practice billing",
    "insurance billing for therapists",
    "credentialing for therapists",
    "therapy practice insurance claims",
    "EHR billing help",
    "SimplePractice billing help",
    "TherapyNotes billing service",
    "Sessions Health billing",
    "practice manager",
    "medical practice manager",
    "medical office manager",
    "billing manager",
    "medical biller",
    "credentialing specialist",
    "therapy practice revenue cycle",
]

HEADLINES = [
    "Stop DIY Billing",
    "Expert Billing Team",
    "No New EHR",
    "Billing + Credentialing",
    "Book a Free Consult",
]

DESCRIPTIONS = [
    "Your EHR gives you tools. Bomi gives you the expert billing team.",
    "Billing and credentialing support for therapy practices.",
    "Flat 4% of collections. No new EHR and no learning curve.",
]


class GoogleAdsError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    developer_token: str
    customer_id: str
    login_customer_id: str | None
    access_token: str


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


def env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if value:
        return value.strip()
    if required:
        raise GoogleAdsError(f"Missing required environment variable: {name}")
    return None


def customer_id(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GoogleAdsError(f"Google Ads API error {exc.code} for {url}:\n{body}") from exc


def refresh_access_token() -> str:
    direct_token = env("GOOGLE_ADS_ACCESS_TOKEN", required=False)
    if direct_token:
        return direct_token
    payload = urllib.parse.urlencode(
        {
            "client_id": env("GOOGLE_ADS_CLIENT_ID"),
            "client_secret": env("GOOGLE_ADS_CLIENT_SECRET"),
            "refresh_token": env("GOOGLE_ADS_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OAUTH_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))["access_token"]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GoogleAdsError(f"OAuth token refresh failed:\n{body}") from exc


def load_credentials() -> Credentials:
    login_customer = env("GOOGLE_ADS_LOGIN_CUSTOMER_ID", required=False)
    return Credentials(
        developer_token=env("GOOGLE_ADS_DEVELOPER_TOKEN") or "",
        customer_id=customer_id(env("GOOGLE_ADS_CUSTOMER_ID")),
        login_customer_id=customer_id(login_customer) if login_customer else None,
        access_token=refresh_access_token(),
    )


def headers(credentials: Credentials) -> dict[str, str]:
    result = {
        "Authorization": f"Bearer {credentials.access_token}",
        "developer-token": credentials.developer_token,
    }
    if credentials.login_customer_id:
        result["login-customer-id"] = credentials.login_customer_id
    return result


def compact_gaql(query: str) -> str:
    return " ".join(line.strip() for line in query.strip().splitlines() if line.strip())


def quote_gaql(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def search(credentials: Credentials, query: str) -> list[dict[str, Any]]:
    response = post_json(
        f"{GOOGLE_ADS_BASE}/customers/{credentials.customer_id}/googleAds:searchStream",
        headers(credentials),
        {"query": compact_gaql(query)},
    )
    rows: list[dict[str, Any]] = []
    for batch in response:
        rows.extend(batch.get("results", []))
    return rows


def mutate(credentials: Credentials, operations: list[dict[str, Any]], validate_only: bool) -> dict[str, Any]:
    return post_json(
        f"{GOOGLE_ADS_BASE}/customers/{credentials.customer_id}/googleAds:mutate",
        headers(credentials),
        {
            "mutateOperations": operations,
            "partialFailure": False,
            "validateOnly": validate_only,
        },
    )


def mutate_custom_audiences(credentials: Credentials, operations: list[dict[str, Any]], validate_only: bool) -> dict[str, Any]:
    return post_json(
        f"{GOOGLE_ADS_BASE}/customers/{credentials.customer_id}/customAudiences:mutate",
        headers(credentials),
        {"operations": operations, "validateOnly": validate_only},
    )


def mutate_audiences(credentials: Credentials, operations: list[dict[str, Any]], validate_only: bool) -> dict[str, Any]:
    return post_json(
        f"{GOOGLE_ADS_BASE}/customers/{credentials.customer_id}/audiences:mutate",
        headers(credentials),
        {"operations": operations, "validateOnly": validate_only},
    )


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise GoogleAdsError(f"{path} is not a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def ensure_portrait_derivative() -> None:
    if PORTRAIT_IMAGE.exists() and png_size(PORTRAIT_IMAGE) == (1080, 1920):
        return
    subprocess.run(
        [
            "sips",
            "--padToHeightWidth",
            "1920",
            "1080",
            "--padColor",
            "f8f7f2",
            str(SQUARE_IMAGE),
            "--out",
            str(PORTRAIT_IMAGE),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if png_size(PORTRAIT_IMAGE) != (1080, 1920):
        raise GoogleAdsError(f"Could not create valid portrait derivative: {PORTRAIT_IMAGE}")


def validate_files() -> None:
    expected = [
        (SQUARE_IMAGE, (1080, 1080)),
        (LANDSCAPE_IMAGE, (1200, 628)),
    ]
    for path, size in expected:
        if not path.exists():
            raise GoogleAdsError(f"Missing required asset: {path}")
        actual = png_size(path)
        if actual != size:
            raise GoogleAdsError(f"{path} is {actual[0]}x{actual[1]}, expected {size[0]}x{size[1]}")
    ensure_portrait_derivative()


def image_asset_operation(credentials: Credentials, temp_id: int, name: str, path: Path) -> dict[str, Any]:
    return {
        "assetOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/assets/{temp_id}",
                "name": name,
                "type": "IMAGE",
                "imageAsset": {"data": base64.b64encode(path.read_bytes()).decode("ascii")},
            }
        }
    }


def text_assets(values: list[str]) -> list[dict[str, str]]:
    return [{"text": value} for value in values]


def budget_operation(credentials: Credentials, temp_id: int, stamp: int) -> dict[str, Any]:
    return {
        "campaignBudgetOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/campaignBudgets/{temp_id}",
                "name": f"{CAMPAIGN_NAME} Budget {stamp}",
                "amountMicros": str(DAILY_BUDGET_MICROS),
                "deliveryMethod": "STANDARD",
                "explicitlyShared": False,
            }
        }
    }


def campaign_operation(credentials: Credentials, temp_id: int, budget_temp_id: int) -> dict[str, Any]:
    return {
        "campaignOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/campaigns/{temp_id}",
                "name": CAMPAIGN_NAME,
                "status": "PAUSED",
                "advertisingChannelType": "DEMAND_GEN",
                "campaignBudget": f"customers/{credentials.customer_id}/campaignBudgets/{budget_temp_id}",
                "maximizeConversions": {},
                "containsEuPoliticalAdvertising": "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
                "geoTargetTypeSetting": {
                    "positiveGeoTargetType": "PRESENCE",
                    "negativeGeoTargetType": "PRESENCE",
                },
            }
        }
    }


def ad_group_operation(credentials: Credentials, temp_id: int, campaign_temp_id: int) -> dict[str, Any]:
    return {
        "adGroupOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/adGroups/{temp_id}",
                "campaign": f"customers/{credentials.customer_id}/campaigns/{campaign_temp_id}",
                "name": AD_GROUP_NAME,
                "status": "PAUSED",
                "audienceSetting": {"useAudienceGrouped": True},
                "optimizedTargetingEnabled": True,
                "targetingSetting": {
                    "targetRestrictions": [
                        {"targetingDimension": "AUDIENCE", "bidOnly": False}
                    ]
                },
                "demandGenAdGroupSettings": {
                    "channelControls": {
                        "selectedChannels": {
                            "gmail": True,
                            "discover": True,
                            "display": False,
                            "youtubeInFeed": True,
                            "youtubeInStream": False,
                            "youtubeShorts": True,
                        }
                    }
                },
            }
        }
    }


def criterion_operation(credentials: Credentials, ad_group_temp_id: int, criterion: dict[str, Any]) -> dict[str, Any]:
    return {
        "adGroupCriterionOperation": {
            "create": {
                "adGroup": f"customers/{credentials.customer_id}/adGroups/{ad_group_temp_id}",
                "negative": False,
                **criterion,
            }
        }
    }


def ad_operation(
    credentials: Credentials,
    temp_id: int,
    ad_group_temp_id: int,
    landscape_asset: str,
    square_asset: str,
    portrait_asset: str,
    logo_asset: str,
) -> dict[str, Any]:
    return {
        "adGroupAdOperation": {
            "create": {
                "adGroup": f"customers/{credentials.customer_id}/adGroups/{ad_group_temp_id}",
                "status": "PAUSED",
                "ad": {
                    "name": AD_NAME,
                    "finalUrls": [FINAL_URL],
                    "demandGenMultiAssetAd": {
                        "businessName": "Bomi Health",
                        "callToActionText": "Book now",
                        "marketingImages": [{"asset": landscape_asset}],
                        "squareMarketingImages": [{"asset": square_asset}],
                        "tallPortraitMarketingImages": [{"asset": portrait_asset}],
                        "logoImages": [{"asset": logo_asset}],
                        "headlines": text_assets(HEADLINES),
                        "descriptions": text_assets(DESCRIPTIONS),
                    },
                },
            }
        }
    }


def find_logo_asset(credentials: Credentials) -> str:
    rows = search(
        credentials,
        """
        SELECT asset.resource_name, asset.id, asset.name, asset.type
        FROM asset
        WHERE asset.name = 'logo_1:1.png'
          AND asset.type = 'IMAGE'
        ORDER BY asset.id DESC
        LIMIT 1
        """,
    )
    if not rows:
        raise GoogleAdsError("Could not find existing square Bomi logo asset.")
    return rows[0]["asset"]["resourceName"]


def ensure_no_existing_campaign(credentials: Credentials) -> None:
    rows = search(
        credentials,
        f"""
        SELECT campaign.id, campaign.name, campaign.status
        FROM campaign
        WHERE campaign.name = {quote_gaql(CAMPAIGN_NAME)}
          AND campaign.status != 'REMOVED'
        """,
    )
    if rows:
        existing = ", ".join(f"{row['campaign']['id']} ({row['campaign']['status']})" for row in rows)
        raise GoogleAdsError(f"Refusing to create duplicate Google campaign: {existing}")


def custom_audience_operation(stamp: int) -> dict[str, Any]:
    return {
        "create": {
            "name": f"Bomi EHR vs Expert Billing Signals {stamp}",
            "description": "Bomi pooled-state therapist billing and practice-operator signals.",
            "type": "AUTO",
            "members": [
                {"memberType": "KEYWORD", "keyword": term}
                for term in CUSTOM_AUDIENCE_TERMS
            ],
        }
    }


def audience_operation(custom_audience_resource: str, stamp: int) -> dict[str, Any]:
    return {
        "create": {
            "name": f"Bomi EHR vs Expert Billing Audience {stamp}",
            "description": "Pooled-state audience for the EHR-vs-Bomi Demand Gen test.",
            "dimensions": [
                {
                    "audienceSegments": {
                        "segments": [
                            {"customAudience": {"customAudience": custom_audience_resource}}
                        ]
                    }
                },
                {
                    "age": {
                        "ageRanges": [
                            {"minAge": 25, "maxAge": 34},
                            {"minAge": 35, "maxAge": 44},
                            {"minAge": 45, "maxAge": 54},
                            {"minAge": 55, "maxAge": 64},
                            {"minAge": 65},
                        ],
                        "includeUndetermined": False,
                    }
                },
            ],
        }
    }


def build_operations(credentials: Credentials, logo_asset: str, audience: str | None = None) -> list[dict[str, Any]]:
    stamp = int(time.time())
    landscape_asset = f"customers/{credentials.customer_id}/assets/-10"
    square_asset = f"customers/{credentials.customer_id}/assets/-11"
    portrait_asset = f"customers/{credentials.customer_id}/assets/-12"
    operations = [
        image_asset_operation(credentials, -10, f"Bomi EHR vs expert team landscape {CAMPAIGN_DATE}", LANDSCAPE_IMAGE),
        image_asset_operation(credentials, -11, f"Bomi EHR vs expert team square {CAMPAIGN_DATE}", SQUARE_IMAGE),
        image_asset_operation(credentials, -12, f"Bomi EHR vs expert team portrait padded {CAMPAIGN_DATE}", PORTRAIT_IMAGE),
        budget_operation(credentials, -100, stamp),
        campaign_operation(credentials, -101, -100),
        ad_group_operation(credentials, -102, -101),
    ]
    for geo in STATE_GEOS:
        operations.append(criterion_operation(credentials, -102, {"location": {"geoTargetConstant": geo}}))
    operations.append(
        criterion_operation(credentials, -102, {"language": {"languageConstant": ENGLISH_LANGUAGE}})
    )
    if audience:
        operations.append(criterion_operation(credentials, -102, {"audience": {"audience": audience}}))
    operations.append(
        ad_operation(
            credentials,
            -103,
            -102,
            landscape_asset,
            square_asset,
            portrait_asset,
            logo_asset,
        )
    )
    return operations


def resource_ids(response: dict[str, Any], resource_type: str) -> list[str]:
    needle = f"/{resource_type}/"
    ids: list[str] = []
    for item in response.get("mutateOperationResponses", []):
        result = next(iter(item.values()), {})
        resource = result.get("resourceName", "")
        if needle in resource:
            ids.append(resource.rsplit("/", 1)[-1])
    return ids


def readback(credentials: Credentials, campaign_id: str) -> dict[str, Any]:
    campaigns = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          campaign.primary_status,
          campaign.advertising_channel_type,
          campaign_budget.id,
          campaign_budget.amount_micros,
          campaign.geo_target_type_setting.positive_geo_target_type
        FROM campaign
        WHERE campaign.id = {int(campaign_id)}
        """,
    )
    ads = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          ad_group.id,
          ad_group.name,
          ad_group.status,
          ad_group.optimized_targeting_enabled,
          ad_group_ad.ad.id,
          ad_group_ad.ad.name,
          ad_group_ad.status,
          ad_group_ad.policy_summary.approval_status,
          ad_group_ad.policy_summary.review_status,
          ad_group_ad.ad.final_urls
        FROM ad_group_ad
        WHERE campaign.id = {int(campaign_id)}
        """,
    )
    criteria = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          ad_group.id,
          ad_group_criterion.type,
          ad_group_criterion.location.geo_target_constant,
          ad_group_criterion.language.language_constant,
          ad_group_criterion.audience.audience
        FROM ad_group_criterion
        WHERE campaign.id = {int(campaign_id)}
          AND ad_group_criterion.status != 'REMOVED'
        ORDER BY ad_group_criterion.type
        """,
    )
    return {"campaigns": campaigns, "ads": ads, "criteria": criteria}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Create paused Google objects.")
    args = parser.parse_args()

    load_env()
    validate_files()
    credentials = load_credentials()
    ensure_no_existing_campaign(credentials)
    logo_asset = find_logo_asset(credentials)
    custom_ops = [custom_audience_operation(int(time.time()))]

    if not args.apply:
        mutate_custom_audiences(credentials, custom_ops, validate_only=True)
        mutate(credentials, build_operations(credentials, logo_asset), validate_only=True)
        print("Validation passed for Google Demand Gen campaign shell and custom audience.")
        print("No Google Ads objects were created. Use --apply to create paused objects.")
        return 0

    mutate_custom_audiences(credentials, custom_ops, validate_only=True)
    custom_response = mutate_custom_audiences(credentials, custom_ops, validate_only=False)
    custom_audience = custom_response["results"][0]["resourceName"]
    audience_ops = [audience_operation(custom_audience, int(time.time()))]
    mutate_audiences(credentials, audience_ops, validate_only=True)
    audience_response = mutate_audiences(credentials, audience_ops, validate_only=False)
    audience = audience_response["results"][0]["resourceName"]
    operations = build_operations(credentials, logo_asset, audience=audience)
    mutate(credentials, operations, validate_only=True)
    response = mutate(credentials, operations, validate_only=False)
    campaign_ids = resource_ids(response, "campaigns")
    if len(campaign_ids) != 1:
        raise GoogleAdsError(f"Expected one campaign id in response, got {campaign_ids}")
    rb = readback(credentials, campaign_ids[0])
    READBACK_PATH.write_text(json.dumps({"response": response, "readback": rb}, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"campaign_id": campaign_ids[0], "readback": rb}, indent=2, sort_keys=True))
    print(f"Readback written: {READBACK_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GoogleAdsError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
