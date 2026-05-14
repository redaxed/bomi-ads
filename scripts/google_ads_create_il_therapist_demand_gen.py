#!/usr/bin/env python3
"""
Create paused/active Google Demand Gen campaigns from the current Bomi Meta assets.

This script uses the Google Ads REST API directly, matching the repo's existing
Google Ads scripts. It validates by default; use --apply to create objects and
--enable to enable the created campaigns after readback.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
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

ASSET_DIR = Path("assets/bomi_bcbs_scammas")
LANDSCAPE_IMAGE = ASSET_DIR / "Bomi Health Digital Ad - LinkedIn Ad - 1200x628.png"
SQUARE_IMAGE = ASSET_DIR / "Bomi Health Digital Ad - Meta Facebook Ad - 1080x1080.png"
STORY_IMAGE = ASSET_DIR / "Bomi Health Digital Ad - Instagram Story Ad - 1080x1920.png"

CAMPAIGN_DATE = "2026-05-12"
FINAL_URL_BASE = "https://www.billwithbomi.com/illinois"
DAILY_BUDGET_MICROS = 20_000_000
ILLINOIS_GEO_TARGET = "geoTargetConstants/21147"
ENGLISH_LANGUAGE = "languageConstants/1000"

EXACT_CAMPAIGN_NAME = (
    f"IL Therapist Reimbursement Review - Exact Titles - Demand Gen - {CAMPAIGN_DATE}"
)
BROAD_CAMPAIGN_NAME = (
    f"IL Therapist Reimbursement Review - Operators - Demand Gen - {CAMPAIGN_DATE}"
)

EXACT_TERMS = [
    "therapist billing Illinois",
    "BCBSIL therapist billing",
    "Medicaid therapist billing",
    "therapy practice billing",
    "LCSW billing",
    "LMFT billing",
    "mental health billing",
    "behavioral health billing",
    "therapist reimbursement review",
    "claim reimbursement review",
]

BROAD_TERMS = [
    "practice manager",
    "medical practice manager",
    "medical office manager",
    "billing manager",
    "medical biller",
    "medical billing specialist",
    "credentialing specialist",
    "behavioral health billing service",
    "therapy practice insurance billing",
    "healthcare revenue cycle management",
    "small therapy practice owner",
    "Blue Cross Blue Shield billing",
]

COMMON_HEADLINES = [
    "Therapist Claim Review",
    "Find Underpayments",
    "Illinois Therapists",
    "Free Billing Review",
    "Review Claim Issues",
]

COMMON_DESCRIPTIONS = [
    "Bomi reviews reimbursements and claim issues for Illinois therapy practices.",
    "Find potential underpayments, denials, and billing setup issues.",
    "Book a free billing review with Bomi Health.",
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
        with urllib.request.urlopen(request, timeout=90) as response:
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


def mutate(
    credentials: Credentials, operations: list[dict[str, Any]], validate_only: bool
) -> dict[str, Any]:
    return post_json(
        f"{GOOGLE_ADS_BASE}/customers/{credentials.customer_id}/googleAds:mutate",
        headers(credentials),
        {
            "mutateOperations": operations,
            "partialFailure": False,
            "validateOnly": validate_only,
        },
    )


def mutate_custom_audiences(
    credentials: Credentials, operations: list[dict[str, Any]], validate_only: bool
) -> dict[str, Any]:
    return post_json(
        f"{GOOGLE_ADS_BASE}/customers/{credentials.customer_id}/customAudiences:mutate",
        headers(credentials),
        {
            "operations": operations,
            "validateOnly": validate_only,
        },
    )


def mutate_audiences(
    credentials: Credentials, operations: list[dict[str, Any]], validate_only: bool
) -> dict[str, Any]:
    return post_json(
        f"{GOOGLE_ADS_BASE}/customers/{credentials.customer_id}/audiences:mutate",
        headers(credentials),
        {
            "operations": operations,
            "validateOnly": validate_only,
        },
    )


def image_asset_operation(
    credentials: Credentials, temp_id: int, name: str, path: Path
) -> dict[str, Any]:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "assetOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/assets/{temp_id}",
                "name": name,
                "type": "IMAGE",
                "imageAsset": {"data": data},
            }
        }
    }


def text_assets(values: list[str]) -> list[dict[str, str]]:
    return [{"text": value} for value in values]


def custom_audience_operation(
    name: str, terms: list[str], stamp: int
) -> dict[str, Any]:
    return {
        "create": {
            "name": f"{name} {stamp}",
            "description": "Bomi Google port of current Meta therapist audience signals.",
            "type": "AUTO",
            "members": [
                {"memberType": "KEYWORD", "keyword": term}
                for term in terms
            ],
        }
    }


def budget_operation(
    credentials: Credentials, temp_id: int, name: str, stamp: int
) -> dict[str, Any]:
    return {
        "campaignBudgetOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/campaignBudgets/{temp_id}",
                "name": f"{name} Budget {stamp}",
                "amountMicros": str(DAILY_BUDGET_MICROS),
                "deliveryMethod": "STANDARD",
                "explicitlyShared": False,
            }
        }
    }


def campaign_operation(
    credentials: Credentials, temp_id: int, budget_temp_id: int, name: str
) -> dict[str, Any]:
    return {
        "campaignOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/campaigns/{temp_id}",
                "name": name,
                "status": "PAUSED",
                "advertisingChannelType": "DEMAND_GEN",
                "campaignBudget": (
                    f"customers/{credentials.customer_id}/campaignBudgets/{budget_temp_id}"
                ),
                "maximizeConversions": {},
                "containsEuPoliticalAdvertising": (
                    "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"
                ),
                "geoTargetTypeSetting": {
                    "positiveGeoTargetType": "PRESENCE",
                    "negativeGeoTargetType": "PRESENCE",
                },
            }
        }
    }


def ad_group_operation(
    credentials: Credentials,
    temp_id: int,
    campaign_temp_id: int,
    name: str,
    optimized_targeting_enabled: bool,
) -> dict[str, Any]:
    return {
        "adGroupOperation": {
            "create": {
                "resourceName": f"customers/{credentials.customer_id}/adGroups/{temp_id}",
                "campaign": f"customers/{credentials.customer_id}/campaigns/{campaign_temp_id}",
                "name": name,
                "status": "PAUSED",
                "audienceSetting": {"useAudienceGrouped": True},
                "optimizedTargetingEnabled": optimized_targeting_enabled,
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


def criterion_operation(
    credentials: Credentials,
    ad_group_temp_id: int,
    criterion: dict[str, Any],
    negative: bool = False,
) -> dict[str, Any]:
    create: dict[str, Any] = {
        "adGroup": f"customers/{credentials.customer_id}/adGroups/{ad_group_temp_id}",
        "negative": negative,
        **criterion,
    }
    return {"adGroupCriterionOperation": {"create": create}}


def ad_operation(
    credentials: Credentials,
    temp_id: int,
    ad_group_temp_id: int,
    name: str,
    final_url: str,
    landscape_asset: str,
    square_asset: str,
    story_asset: str,
    logo_asset: str,
) -> dict[str, Any]:
    return {
        "adGroupAdOperation": {
            "create": {
                "adGroup": f"customers/{credentials.customer_id}/adGroups/{ad_group_temp_id}",
                "status": "PAUSED",
                "ad": {
                    "name": name,
                    "finalUrls": [final_url],
                    "demandGenMultiAssetAd": {
                        "businessName": "Bomi Health",
                        "callToActionText": "Book now",
                        "marketingImages": [{"asset": landscape_asset}],
                        "squareMarketingImages": [{"asset": square_asset}],
                        "tallPortraitMarketingImages": [{"asset": story_asset}],
                        "logoImages": [{"asset": logo_asset}],
                        "headlines": text_assets(COMMON_HEADLINES),
                        "descriptions": text_assets(COMMON_DESCRIPTIONS),
                    },
                },
            }
        }
    }


def find_logo_asset(credentials: Credentials) -> str:
    rows = search(
        credentials,
        """
        SELECT
          asset.resource_name,
          asset.id,
          asset.name,
          asset.type,
          asset.image_asset.full_size.width_pixels,
          asset.image_asset.full_size.height_pixels
        FROM asset
        WHERE asset.name = 'logo_1:1.png'
          AND asset.type = 'IMAGE'
        ORDER BY asset.id DESC
        LIMIT 1
        """,
    )
    if not rows:
        raise GoogleAdsError("Could not find an existing square Bomi logo asset.")
    asset = rows[0]["asset"]
    return asset["resourceName"]


def ensure_no_existing_campaigns(credentials: Credentials) -> None:
    names = [EXACT_CAMPAIGN_NAME, BROAD_CAMPAIGN_NAME]
    quoted = ", ".join(quote_gaql(name) for name in names)
    rows = search(
        credentials,
        f"""
        SELECT campaign.id, campaign.name, campaign.status
        FROM campaign
        WHERE campaign.name IN ({quoted})
          AND campaign.status != 'REMOVED'
        """,
    )
    if rows:
        existing = ", ".join(
            f"{row['campaign']['id']} ({row['campaign']['name']})" for row in rows
        )
        raise GoogleAdsError(f"Refusing to create duplicates. Existing campaigns: {existing}")


def build_custom_audience_operations() -> list[dict[str, Any]]:
    stamp = int(time.time())
    return [
        custom_audience_operation("Bomi IL Therapist Exact Signals", EXACT_TERMS, stamp),
        custom_audience_operation("Bomi IL Operator Billing Signals", BROAD_TERMS, stamp),
    ]


def custom_audience_resource_names(response: dict[str, Any]) -> list[str]:
    return [
        result["resourceName"]
        for result in response.get("results", [])
        if result.get("resourceName")
    ]


def audience_operation(
    name: str, custom_audience_resource: str, stamp: int
) -> dict[str, Any]:
    return {
        "create": {
            "name": f"{name} {stamp}",
            "description": "Bomi Google port of current Meta therapist targeting.",
            "dimensions": [
                {
                    "audienceSegments": {
                        "segments": [
                            {
                                "customAudience": {
                                    "customAudience": custom_audience_resource
                                }
                            }
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


def build_audience_operations(
    exact_custom_audience: str, broad_custom_audience: str
) -> list[dict[str, Any]]:
    stamp = int(time.time())
    return [
        audience_operation(
            "Bomi IL Therapist Exact Audience", exact_custom_audience, stamp
        ),
        audience_operation(
            "Bomi IL Operator Billing Audience", broad_custom_audience, stamp
        ),
    ]


def audience_resource_names(response: dict[str, Any]) -> list[str]:
    return [
        result["resourceName"]
        for result in response.get("results", [])
        if result.get("resourceName")
    ]


def build_operations(
    credentials: Credentials,
    logo_asset: str,
    exact_audience: str | None = None,
    broad_audience: str | None = None,
) -> list[dict[str, Any]]:
    stamp = int(time.time())
    landscape_asset = f"customers/{credentials.customer_id}/assets/-10"
    square_asset = f"customers/{credentials.customer_id}/assets/-11"
    story_asset = f"customers/{credentials.customer_id}/assets/-12"

    operations: list[dict[str, Any]] = [
        image_asset_operation(
            credentials,
            -10,
            f"Bomi IL reimbursement landscape 1200x628 {CAMPAIGN_DATE}",
            LANDSCAPE_IMAGE,
        ),
        image_asset_operation(
            credentials,
            -11,
            f"Bomi IL reimbursement square 1080x1080 {CAMPAIGN_DATE}",
            SQUARE_IMAGE,
        ),
        image_asset_operation(
            credentials,
            -12,
            f"Bomi IL reimbursement story 1080x1920 {CAMPAIGN_DATE}",
            STORY_IMAGE,
        ),
        budget_operation(credentials, -100, EXACT_CAMPAIGN_NAME, stamp),
        campaign_operation(credentials, -101, -100, EXACT_CAMPAIGN_NAME),
        budget_operation(credentials, -200, BROAD_CAMPAIGN_NAME, stamp),
        campaign_operation(credentials, -201, -200, BROAD_CAMPAIGN_NAME),
        ad_group_operation(
            credentials,
            -102,
            -101,
            "Exact therapist title signals",
            optimized_targeting_enabled=False,
        ),
        ad_group_operation(
            credentials,
            -202,
            -201,
            "Therapist operator and billing signals",
            optimized_targeting_enabled=True,
        ),
    ]

    for ad_group_temp_id, audience_resource in [
        (-102, exact_audience),
        (-202, broad_audience),
    ]:
        operations.extend(
            [
                criterion_operation(
                    credentials,
                    ad_group_temp_id,
                    {"location": {"geoTargetConstant": ILLINOIS_GEO_TARGET}},
                ),
                criterion_operation(
                    credentials,
                    ad_group_temp_id,
                    {"language": {"languageConstant": ENGLISH_LANGUAGE}},
                ),
            ]
        )
        if audience_resource:
            operations.append(
                criterion_operation(
                    credentials,
                    ad_group_temp_id,
                    {"audience": {"audience": audience_resource}},
                )
            )

    operations.extend(
        [
            ad_operation(
                credentials,
                -103,
                -102,
                "IL therapist reimbursement review - exact title signals",
                FINAL_URL_BASE
                + "?utm_source=google&utm_medium=paid_demandgen"
                + "&utm_campaign=il_therapist_reimbursement_review"
                + "&utm_content=exact_titles",
                landscape_asset,
                square_asset,
                story_asset,
                logo_asset,
            ),
            ad_operation(
                credentials,
                -203,
                -202,
                "IL therapist reimbursement review - operator signals",
                FINAL_URL_BASE
                + "?utm_source=google&utm_medium=paid_demandgen"
                + "&utm_campaign=il_therapist_reimbursement_review"
                + "&utm_content=operator_broad",
                landscape_asset,
                square_asset,
                story_asset,
                logo_asset,
            ),
        ]
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


def enable_operations(credentials: Credentials, campaign_ids: list[str]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for campaign_id in campaign_ids:
        operations.append(
            {
                "campaignOperation": {
                    "update": {
                        "resourceName": (
                            f"customers/{credentials.customer_id}/campaigns/{campaign_id}"
                        ),
                        "status": "ENABLED",
                    },
                    "updateMask": "status",
                }
            }
        )

    campaign_filter = ", ".join(campaign_ids)
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group.resource_name,
          ad_group_ad.resource_name
        FROM ad_group_ad
        WHERE campaign.id IN ({campaign_filter})
          AND ad_group.status != 'REMOVED'
          AND ad_group_ad.status != 'REMOVED'
        """,
    )
    ad_groups: set[str] = set()
    ad_group_ads: set[str] = set()
    for row in rows:
        ad_groups.add(row["adGroup"]["resourceName"])
        ad_group_ads.add(row["adGroupAd"]["resourceName"])

    for ad_group_resource in sorted(ad_groups):
        operations.append(
            {
                "adGroupOperation": {
                    "update": {
                        "resourceName": ad_group_resource,
                        "status": "ENABLED",
                    },
                    "updateMask": "status",
                }
            }
        )
    for ad_group_ad_resource in sorted(ad_group_ads):
        operations.append(
            {
                "adGroupAdOperation": {
                    "update": {
                        "resourceName": ad_group_ad_resource,
                        "status": "ENABLED",
                    },
                    "updateMask": "status",
                }
            }
        )
    return operations


def readback(credentials: Credentials, campaign_ids: list[str]) -> dict[str, Any]:
    campaign_filter = ", ".join(campaign_ids)
    campaigns = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          campaign.primary_status,
          campaign.advertising_channel_type,
          campaign_budget.amount_micros,
          campaign.geo_target_type_setting.positive_geo_target_type
        FROM campaign
        WHERE campaign.id IN ({campaign_filter})
        ORDER BY campaign.id
        """,
    )
    ads = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          campaign.name,
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
        WHERE campaign.id IN ({campaign_filter})
        ORDER BY campaign.id, ad_group.id
        """,
    )
    criteria = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          ad_group.id,
          ad_group_criterion.type,
          ad_group_criterion.negative,
          ad_group_criterion.location.geo_target_constant,
          ad_group_criterion.language.language_constant,
          ad_group_criterion.audience.audience
        FROM ad_group_criterion
        WHERE campaign.id IN ({campaign_filter})
          AND ad_group_criterion.status != 'REMOVED'
        ORDER BY campaign.id, ad_group.id, ad_group_criterion.type
        """,
    )
    return {"campaigns": campaigns, "ads": ads, "criteria": criteria}


def validate_files() -> None:
    for path in [LANDSCAPE_IMAGE, SQUARE_IMAGE, STORY_IMAGE]:
        if not path.exists():
            raise GoogleAdsError(f"Missing required asset: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the paused Demand Gen campaigns. Without this, validate only.",
    )
    parser.add_argument(
        "--enable",
        action="store_true",
        help="After creation, enable campaigns, ad groups, and ads.",
    )
    args = parser.parse_args()

    if args.enable and not args.apply:
        raise GoogleAdsError("--enable requires --apply")

    load_env()
    validate_files()
    credentials = load_credentials()
    ensure_no_existing_campaigns(credentials)
    logo_asset = find_logo_asset(credentials)
    custom_audience_operations = build_custom_audience_operations()

    if not args.apply:
        mutate_custom_audiences(
            credentials, custom_audience_operations, validate_only=True
        )
        # A full audience-targeted validation needs real custom audience resource
        # names, so the no-apply path validates the spend-bearing campaign shell.
        operations = build_operations(credentials, logo_asset)
        mutate(credentials, operations, validate_only=True)
        print(
            "Validation passed for assets, campaign shell, ads, and custom audiences. "
            "No campaigns were created."
        )
        return 0

    mutate_custom_audiences(
        credentials, custom_audience_operations, validate_only=True
    )
    audience_response = mutate_custom_audiences(
        credentials, custom_audience_operations, validate_only=False
    )
    audience_resources = custom_audience_resource_names(audience_response)
    if len(audience_resources) != 2:
        print(json.dumps(audience_response, indent=2, sort_keys=True))
        raise GoogleAdsError(
            f"Expected 2 custom audiences, found {audience_resources}"
        )

    audience_operations = build_audience_operations(
        audience_resources[0], audience_resources[1]
    )
    mutate_audiences(credentials, audience_operations, validate_only=True)
    grouped_audience_response = mutate_audiences(
        credentials, audience_operations, validate_only=False
    )
    grouped_audience_resources = audience_resource_names(grouped_audience_response)
    if len(grouped_audience_resources) != 2:
        print(json.dumps(grouped_audience_response, indent=2, sort_keys=True))
        raise GoogleAdsError(
            f"Expected 2 audiences, found {grouped_audience_resources}"
        )

    operations = build_operations(
        credentials,
        logo_asset,
        exact_audience=grouped_audience_resources[0],
        broad_audience=grouped_audience_resources[1],
    )
    mutate(credentials, operations, validate_only=True)
    create_response = mutate(credentials, operations, validate_only=False)
    campaign_ids = resource_ids(create_response, "campaigns")
    if len(campaign_ids) != 2:
        print(json.dumps(create_response, indent=2, sort_keys=True))
        raise GoogleAdsError(f"Expected 2 campaigns, found {campaign_ids}")

    print("Created paused campaigns:")
    print(json.dumps(readback(credentials, campaign_ids), indent=2, sort_keys=True))

    if args.enable:
        mutate(credentials, enable_operations(credentials, campaign_ids), validate_only=False)
        print("Enabled campaigns, ad groups, and ads:")
        print(json.dumps(readback(credentials, campaign_ids), indent=2, sort_keys=True))
    else:
        print("Campaigns are paused. Rerun with --enable only after review.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GoogleAdsError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
