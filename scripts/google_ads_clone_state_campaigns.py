#!/usr/bin/env python3
"""
Clone a state-specific Google Search campaign into Ohio and Indiana.

The script uses the Google Ads REST API directly so it can run without a
generated client library. It defaults to validateOnly mode. Use --apply to
create paused campaigns.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from ad_tracking_urls import build_google_search_url, slugify


API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v24")
GOOGLE_ADS_BASE = f"https://googleads.googleapis.com/{API_VERSION}"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

DEFAULT_TARGETS = {
    "Ohio": "https://billwithbomi.com/ohio",
    "Indiana": "https://billwithbomi.com/indiana",
}

KEYWORD_POLICY_EXEMPTIONS = {
    "SimplePractice billing help": [
        {
            "policyName": "THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT",
            "violatingText": "SimplePractice billing help",
        }
    ],
    "TherapyNotes billing service": [
        {
            "policyName": "THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT",
            "violatingText": "TherapyNotes billing service",
        }
    ],
    "Therapy Notes billing help": [
        {
            "policyName": "THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT",
            "violatingText": "Therapy Notes billing help",
        }
    ],
}

EXCLUDED_SOURCE_KEYWORD_PATTERNS = [
    r"\bharmonic office solutions\b",
]

STATE_KEYWORD_REPLACEMENTS = {
    "illinois medicaid": {
        "Ohio": [
            "ohio medicaid therapist billing",
            "ohio medicaid credentialing",
            "ohio medicaid provider enrollment",
        ],
        "Indiana": [
            "indiana medicaid therapist billing",
            "indiana medicaid credentialing",
            "indiana medicaid provider enrollment",
        ],
    }
}

STATE_CLONE_NEGATIVE_KEYWORDS = [
    "pregnant",
    "apply",
    "office",
    "phone number",
    "eligibility",
    "portal",
    "gov",
]


class GoogleAdsError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    developer_token: str
    customer_id: str
    login_customer_id: str | None
    access_token: str


def env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if value:
        return value.strip()
    if required:
        raise GoogleAdsError(f"Missing required environment variable: {name}")
    return None


def customer_id(value: str) -> str:
    return re.sub(r"\D", "", value)


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> Any:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
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
            body = json.loads(response.read().decode("utf-8"))
            return body["access_token"]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GoogleAdsError(f"OAuth token refresh failed:\n{body}") from exc


def load_credentials() -> Credentials:
    login_customer = env("GOOGLE_ADS_LOGIN_CUSTOMER_ID", required=False)
    return Credentials(
        developer_token=env("GOOGLE_ADS_DEVELOPER_TOKEN") or "",
        customer_id=customer_id(env("GOOGLE_ADS_CUSTOMER_ID") or ""),
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


def compact_gaql(query: str) -> str:
    return " ".join(line.strip() for line in query.strip().splitlines() if line.strip())


def quote_gaql(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def find_source_campaign(
    credentials: Credentials, campaign_id: str | None, name_match: str
) -> dict[str, Any]:
    where = (
        f"campaign.id = {int(campaign_id)}"
        if campaign_id
        else f"campaign.name LIKE {quote_gaql('%' + name_match + '%')}"
    )
    rows = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          campaign.resource_name,
          campaign.advertising_channel_type,
          campaign.advertising_channel_sub_type,
          campaign.campaign_budget,
          campaign.bidding_strategy,
          campaign.bidding_strategy_type,
          campaign.manual_cpc.enhanced_cpc_enabled,
          campaign.maximize_conversions.target_cpa_micros,
          campaign.maximize_conversion_value.target_roas,
          campaign.target_spend.cpc_bid_ceiling_micros,
          campaign.network_settings.target_google_search,
          campaign.network_settings.target_search_network,
          campaign.network_settings.target_content_network,
          campaign.network_settings.target_partner_search_network,
          campaign.geo_target_type_setting.positive_geo_target_type,
          campaign.geo_target_type_setting.negative_geo_target_type,
          campaign.tracking_url_template,
          campaign.final_url_suffix
        FROM campaign
        WHERE {where}
          AND campaign.status != 'REMOVED'
        ORDER BY campaign.id
        """,
    )
    if not rows:
        raise GoogleAdsError("No source campaign matched.")
    if len(rows) > 1:
        choices = "\n".join(
            f"  {row['campaign']['id']}: {row['campaign']['name']}" for row in rows
        )
        raise GoogleAdsError(
            "Source campaign name matched more than one campaign. "
            f"Rerun with --source-campaign-id.\n{choices}"
        )
    campaign = rows[0]["campaign"]
    if campaign.get("advertisingChannelType") != "SEARCH":
        raise GoogleAdsError(
            "This first-pass cloner only supports Search campaigns. "
            f"Matched campaign is {campaign.get('advertisingChannelType')}."
        )
    return campaign


def load_budget(credentials: Credentials, budget_resource_name: str) -> dict[str, Any]:
    rows = search(
        credentials,
        f"""
        SELECT
          campaign_budget.id,
          campaign_budget.name,
          campaign_budget.amount_micros,
          campaign_budget.delivery_method
        FROM campaign_budget
        WHERE campaign_budget.resource_name = {quote_gaql(budget_resource_name)}
        """,
    )
    if not rows:
        raise GoogleAdsError(f"Could not read budget {budget_resource_name}")
    return rows[0]["campaignBudget"]


def load_ad_groups(credentials: Credentials, source_campaign_id: str) -> list[dict[str, Any]]:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group.id,
          ad_group.name,
          ad_group.status,
          ad_group.type,
          ad_group.cpc_bid_micros
        FROM ad_group
        WHERE campaign.id = {int(source_campaign_id)}
          AND ad_group.status != 'REMOVED'
        ORDER BY ad_group.id
        """,
    )
    return [row["adGroup"] for row in rows]


def load_keywords(credentials: Credentials, source_campaign_id: str) -> list[dict[str, Any]]:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group.id,
          ad_group_criterion.status,
          ad_group_criterion.negative,
          ad_group_criterion.keyword.text,
          ad_group_criterion.keyword.match_type,
          ad_group_criterion.cpc_bid_micros
        FROM ad_group_criterion
        WHERE campaign.id = {int(source_campaign_id)}
          AND ad_group_criterion.status != 'REMOVED'
          AND ad_group_criterion.type = 'KEYWORD'
        ORDER BY ad_group.id, ad_group_criterion.criterion_id
        """,
    )
    return rows


def load_responsive_search_ads(
    credentials: Credentials, source_campaign_id: str
) -> list[dict[str, Any]]:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group.id,
          ad_group_ad.status,
          ad_group_ad.ad.final_urls,
          ad_group_ad.ad.responsive_search_ad.path1,
          ad_group_ad.ad.responsive_search_ad.path2,
          ad_group_ad.ad.responsive_search_ad.headlines,
          ad_group_ad.ad.responsive_search_ad.descriptions
        FROM ad_group_ad
        WHERE campaign.id = {int(source_campaign_id)}
          AND ad_group_ad.status != 'REMOVED'
          AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
        ORDER BY ad_group.id, ad_group_ad.ad.id
        """,
    )
    return rows


def load_campaign_assets(
    credentials: Credentials, source_campaign_id: str
) -> list[dict[str, Any]]:
    rows = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          campaign_asset.field_type,
          campaign_asset.status,
          asset.resource_name,
          asset.id,
          asset.name,
          asset.type,
          asset.final_urls,
          asset.sitelink_asset.link_text,
          asset.sitelink_asset.description1,
          asset.sitelink_asset.description2,
          asset.callout_asset.callout_text
        FROM campaign_asset
        WHERE campaign.id = {int(source_campaign_id)}
          AND campaign_asset.status != 'REMOVED'
        ORDER BY campaign_asset.field_type, asset.id
        """,
    )
    seen: set[str] = set()
    unique_rows: list[dict[str, Any]] = []
    for row in rows:
        asset = row.get("asset", {})
        campaign_asset = row.get("campaignAsset", {})
        key = json.dumps(
            {
                "fieldType": campaign_asset.get("fieldType"),
                "assetType": asset.get("type"),
                "finalUrls": asset.get("finalUrls", []),
                "sitelinkAsset": asset.get("sitelinkAsset", {}),
                "calloutAsset": asset.get("calloutAsset", {}),
                "resourceName": (
                    asset.get("resourceName")
                    if asset.get("type") not in {"SITELINK", "CALLOUT"}
                    else None
                ),
            },
            sort_keys=True,
        )
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)
    return unique_rows


def resolve_state_geo_targets(
    credentials: Credentials, states: list[str]
) -> dict[str, str]:
    names = ", ".join(quote_gaql(state) for state in states)
    rows = search(
        credentials,
        f"""
        SELECT
          geo_target_constant.id,
          geo_target_constant.name,
          geo_target_constant.resource_name,
          geo_target_constant.country_code,
          geo_target_constant.target_type,
          geo_target_constant.status
        FROM geo_target_constant
        WHERE geo_target_constant.country_code = 'US'
          AND geo_target_constant.target_type = 'State'
          AND geo_target_constant.name IN ({names})
          AND geo_target_constant.status = 'ENABLED'
        """,
    )
    found = {
        row["geoTargetConstant"]["name"]: row["geoTargetConstant"]["resourceName"]
        for row in rows
    }
    missing = sorted(set(states) - set(found))
    if missing:
        raise GoogleAdsError(f"Could not resolve geo target constants for: {missing}")
    return found


def replace_state_text(value: str, state: str) -> str:
    value = re.sub(
        r"\bServing Illinois and Indiana practices\b",
        f"Serving {state} practices",
        value,
    )
    replacements = [
        (r"\bIllinois\b", state),
        (r"\billinois\b", state.lower()),
        (r"\bIL\b", state_to_abbrev(state)),
    ]
    result = value
    for pattern, repl in replacements:
        result = re.sub(pattern, repl, result)
    return result


def state_to_abbrev(state: str) -> str:
    return {"Ohio": "OH", "Indiana": "IN"}.get(state, state[:2].upper())


def maybe_copy(source: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: source[key] for key in keys if key in source}


def campaign_bidding_payload(source_campaign: dict[str, Any]) -> dict[str, Any]:
    strategy_type = source_campaign.get("biddingStrategyType")

    if strategy_type == "MANUAL_CPC":
        manual = source_campaign.get("manualCpc", {})
        payload: dict[str, Any] = {"manualCpc": {}}
        if "enhancedCpcEnabled" in manual:
            payload["manualCpc"]["enhancedCpcEnabled"] = manual["enhancedCpcEnabled"]
        return payload

    if strategy_type == "MAXIMIZE_CONVERSIONS":
        source = source_campaign.get("maximizeConversions", {})
        payload = {"maximizeConversions": {}}
        if "targetCpaMicros" in source:
            payload["maximizeConversions"]["targetCpaMicros"] = source["targetCpaMicros"]
        return payload

    if strategy_type == "MAXIMIZE_CONVERSION_VALUE":
        source = source_campaign.get("maximizeConversionValue", {})
        payload = {"maximizeConversionValue": {}}
        if "targetRoas" in source:
            payload["maximizeConversionValue"]["targetRoas"] = source["targetRoas"]
        return payload

    if strategy_type == "TARGET_SPEND":
        source = source_campaign.get("targetSpend", {})
        payload = {"targetSpend": {}}
        if "cpcBidCeilingMicros" in source:
            payload["targetSpend"]["cpcBidCeilingMicros"] = source[
                "cpcBidCeilingMicros"
            ]
        return payload

    if source_campaign.get("biddingStrategy"):
        return {"biddingStrategy": source_campaign["biddingStrategy"]}

    raise GoogleAdsError(
        "Unsupported or unreadable source campaign bidding strategy: "
        f"{strategy_type}. Add a mapping before applying."
    )


def text_asset_list(assets: list[dict[str, Any]], state: str) -> list[dict[str, Any]]:
    result = []
    for asset in assets:
        copied = maybe_copy(asset, ["pinnedField"])
        copied["text"] = replace_state_text(asset["text"], state)
        result.append(copied)
    return result


def should_skip_source_keyword(text: str) -> bool:
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in EXCLUDED_SOURCE_KEYWORD_PATTERNS
    )


def target_keyword_texts(source_text: str, state: str) -> list[str]:
    replacement = STATE_KEYWORD_REPLACEMENTS.get(source_text.lower())
    if replacement:
        return replacement.get(state, [replace_state_text(source_text, state)])
    return [replace_state_text(source_text, state)]


def landing_page_variant(url: str, landing_page: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    target = urllib.parse.urlsplit(landing_page)
    return urllib.parse.urlunsplit(
        (
            target.scheme,
            target.netloc,
            target.path.rstrip("/"),
            parsed.query,
            parsed.fragment,
        )
    )


def tracked_search_landing_page(
    landing_page: str,
    *,
    state: str,
    campaign_name: str,
    content: str,
) -> str:
    return build_google_search_url(
        landing_page,
        campaign=slugify(campaign_name),
        content=replace_state_text(content, state),
        audience=f"{slugify(state)}_state_search",
    )


def create_operations_for_state(
    credentials: Credentials,
    state: str,
    landing_page: str,
    geo_target: str,
    source_campaign: dict[str, Any],
    source_budget: dict[str, Any],
    ad_groups: list[dict[str, Any]],
    keywords: list[dict[str, Any]],
    ads: list[dict[str, Any]],
    campaign_assets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    millis = int(time.time() * 1000)
    campaign_temp_id = "-2"
    budget_temp_id = "-1"
    temp_id_by_ad_group_id = {
        ad_group["id"]: str(-1000 - index) for index, ad_group in enumerate(ad_groups)
    }

    campaign_name = replace_state_text(source_campaign["name"], state)
    if campaign_name == source_campaign["name"]:
        campaign_name = f"{source_campaign['name']} - {state}"

    operations: list[dict[str, Any]] = [
        {
            "campaignBudgetOperation": {
                "create": {
                    "resourceName": (
                        f"customers/{credentials.customer_id}/campaignBudgets/{budget_temp_id}"
                    ),
                    "name": f"{campaign_name} Budget {millis}",
                    "amountMicros": source_budget["amountMicros"],
                    "deliveryMethod": source_budget.get("deliveryMethod", "STANDARD"),
                    "explicitlyShared": False,
                }
            }
        }
    ]

    campaign_create: dict[str, Any] = {
        "resourceName": f"customers/{credentials.customer_id}/campaigns/{campaign_temp_id}",
        "name": f"{campaign_name} {millis}",
        "status": "PAUSED",
        "advertisingChannelType": "SEARCH",
        "containsEuPoliticalAdvertising": "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
        "campaignBudget": f"customers/{credentials.customer_id}/campaignBudgets/{budget_temp_id}",
        "networkSettings": maybe_copy(
            source_campaign.get("networkSettings", {}),
            [
                "targetGoogleSearch",
                "targetSearchNetwork",
                "targetContentNetwork",
                "targetPartnerSearchNetwork",
            ],
        ),
        "geoTargetTypeSetting": maybe_copy(
            source_campaign.get("geoTargetTypeSetting", {}),
            ["positiveGeoTargetType", "negativeGeoTargetType"],
        ),
    }
    campaign_create.update(campaign_bidding_payload(source_campaign))
    for key in ["trackingUrlTemplate", "finalUrlSuffix"]:
        if key in source_campaign:
            campaign_create[key] = source_campaign[key]

    operations.append({"campaignOperation": {"create": campaign_create}})
    operations.append(
        {
            "campaignCriterionOperation": {
                "create": {
                    "campaign": f"customers/{credentials.customer_id}/campaigns/{campaign_temp_id}",
                    "location": {"geoTargetConstant": geo_target},
                }
            }
        }
    )

    for ad_group in ad_groups:
        ad_group_temp_id = temp_id_by_ad_group_id[ad_group["id"]]
        create = {
            "resourceName": f"customers/{credentials.customer_id}/adGroups/{ad_group_temp_id}",
            "campaign": f"customers/{credentials.customer_id}/campaigns/{campaign_temp_id}",
            "name": replace_state_text(ad_group["name"], state),
            "status": ad_group.get("status", "ENABLED"),
            "type": ad_group.get("type", "SEARCH_STANDARD"),
        }
        if "cpcBidMicros" in ad_group:
            create["cpcBidMicros"] = ad_group["cpcBidMicros"]
        operations.append({"adGroupOperation": {"create": create}})

    for row in keywords:
        criterion = row["adGroupCriterion"]
        ad_group_id = row["adGroup"]["id"]
        keyword = criterion.get("keyword", {})
        source_keyword_text = keyword["text"]
        if should_skip_source_keyword(source_keyword_text):
            continue
        for target_keyword_text in target_keyword_texts(source_keyword_text, state):
            create = {
                "adGroup": (
                    f"customers/{credentials.customer_id}/adGroups/"
                    f"{temp_id_by_ad_group_id[ad_group_id]}"
                ),
                "status": criterion.get("status", "ENABLED"),
                "negative": criterion.get("negative", False),
                "keyword": {
                    "text": target_keyword_text,
                    "matchType": keyword.get("matchType", "PHRASE"),
                },
            }
            if "cpcBidMicros" in criterion:
                create["cpcBidMicros"] = criterion["cpcBidMicros"]
            operation: dict[str, Any] = {"create": create}
            exemptions = KEYWORD_POLICY_EXEMPTIONS.get(source_keyword_text)
            if exemptions:
                operation["exemptPolicyViolationKeys"] = exemptions
            operations.append({"adGroupCriterionOperation": operation})

    for ad_group in ad_groups:
        ad_group_temp_id = temp_id_by_ad_group_id[ad_group["id"]]
        for negative_text in STATE_CLONE_NEGATIVE_KEYWORDS:
            operations.append(
                {
                    "adGroupCriterionOperation": {
                        "create": {
                            "adGroup": f"customers/{credentials.customer_id}/adGroups/{ad_group_temp_id}",
                            "negative": True,
                            "keyword": {
                                "text": negative_text,
                                "matchType": "BROAD",
                            },
                        }
                    }
                }
            )

    for row in ads:
        ad_group_id = row["adGroup"]["id"]
        ad_group_ad = row["adGroupAd"]
        ad = ad_group_ad["ad"]
        rsa = ad["responsiveSearchAd"]
        create = {
            "adGroup": (
                f"customers/{credentials.customer_id}/adGroups/"
                f"{temp_id_by_ad_group_id[ad_group_id]}"
            ),
            "status": "PAUSED",
            "ad": {
                "finalUrls": [
                    tracked_search_landing_page(
                        landing_page,
                        state=state,
                        campaign_name=campaign_name,
                        content=row["adGroup"].get("name", "responsive_search_ad"),
                    )
                ],
                "responsiveSearchAd": {
                    "headlines": text_asset_list(rsa.get("headlines", []), state),
                    "descriptions": text_asset_list(rsa.get("descriptions", []), state),
                },
            },
        }
        for path_key in ["path1", "path2"]:
            if path_key in rsa:
                create["ad"]["responsiveSearchAd"][path_key] = replace_state_text(
                    rsa[path_key], state
                )
        operations.append({"adGroupAdOperation": {"create": create}})

    for index, row in enumerate(campaign_assets):
        asset = row.get("asset", {})
        campaign_asset = row.get("campaignAsset", {})
        field_type = campaign_asset.get("fieldType")
        asset_type = asset.get("type")

        if asset_type in {"SITELINK", "CALLOUT"}:
            asset_temp_id = str(-2000 - index)
            asset_create: dict[str, Any] = {
                "resourceName": f"customers/{credentials.customer_id}/assets/{asset_temp_id}",
            }
            if asset_type == "SITELINK":
                sitelink = asset.get("sitelinkAsset", {})
                asset_create["sitelinkAsset"] = {
                    "linkText": replace_state_text(sitelink["linkText"], state),
                }
                for description_key in ["description1", "description2"]:
                    if description_key in sitelink:
                        asset_create["sitelinkAsset"][description_key] = replace_state_text(
                            sitelink[description_key], state
                        )
                asset_create["finalUrls"] = [
                    tracked_search_landing_page(
                        landing_page_variant(url, landing_page),
                        state=state,
                        campaign_name=campaign_name,
                        content=f"sitelink_{sitelink.get('linkText', 'asset')}",
                    )
                    for url in asset.get("finalUrls", [])
                ]
            elif asset_type == "CALLOUT":
                callout = asset.get("calloutAsset", {})
                asset_create["calloutAsset"] = {
                    "calloutText": replace_state_text(callout["calloutText"], state)
                }

            operations.append({"assetOperation": {"create": asset_create}})
            asset_resource_name = f"customers/{credentials.customer_id}/assets/{asset_temp_id}"
        else:
            asset_resource_name = asset.get("resourceName")

        if not asset_resource_name or not field_type:
            continue
        operations.append(
            {
                "campaignAssetOperation": {
                    "create": {
                        "campaign": f"customers/{credentials.customer_id}/campaigns/{campaign_temp_id}",
                        "asset": asset_resource_name,
                        "fieldType": field_type,
                    }
                }
            }
        )

    return operations


def parse_targets(values: list[str]) -> dict[str, str]:
    if not values:
        return DEFAULT_TARGETS
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise GoogleAdsError(
                "--target-state values must look like 'Ohio=https://example.com/ohio'"
            )
        state, url = value.split("=", 1)
        parsed[state.strip()] = url.strip()
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--source-campaign-id")
    source.add_argument("--source-campaign-name", default="Illinois")
    parser.add_argument(
        "--target-state",
        action="append",
        default=[],
        help="Repeatable. Example: Ohio=https://billwithbomi.com/ohio",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create paused campaigns. Without this, Google validates only.",
    )
    args = parser.parse_args()

    targets = parse_targets(args.target_state)
    credentials = load_credentials()

    source_campaign = find_source_campaign(
        credentials, args.source_campaign_id, args.source_campaign_name
    )
    source_budget = load_budget(credentials, source_campaign["campaignBudget"])
    ad_groups = load_ad_groups(credentials, source_campaign["id"])
    keywords = load_keywords(credentials, source_campaign["id"])
    ads = load_responsive_search_ads(credentials, source_campaign["id"])
    campaign_assets = load_campaign_assets(credentials, source_campaign["id"])
    geo_targets = resolve_state_geo_targets(credentials, list(targets))

    print("Source campaign:")
    print(f"  {source_campaign['id']}: {source_campaign['name']}")
    print(f"  budget micros: {source_budget['amountMicros']}")
    print(f"  ad groups: {len(ad_groups)}")
    print(f"  keywords: {len(keywords)}")
    print(f"  responsive search ads: {len(ads)}")
    print(f"  unique campaign assets: {len(campaign_assets)}")
    print()

    validate_only = not args.apply
    for state, landing_page in targets.items():
        operations = create_operations_for_state(
            credentials=credentials,
            state=state,
            landing_page=landing_page,
            geo_target=geo_targets[state],
            source_campaign=source_campaign,
            source_budget=source_budget,
            ad_groups=ad_groups,
            keywords=keywords,
            ads=ads,
            campaign_assets=campaign_assets,
        )
        mode = "VALIDATE ONLY" if validate_only else "APPLY"
        print(f"{mode}: {state}")
        print(f"  landing page: {landing_page}")
        print(f"  geo target: {geo_targets[state]}")
        print(f"  operations: {len(operations)}")
        response = mutate(credentials, operations, validate_only=validate_only)
        print(json.dumps(response, indent=2, sort_keys=True))
        print()

    if validate_only:
        print("No campaigns were created. Rerun with --apply to create paused campaigns.")
    else:
        print("Created paused campaigns. Review in Google Ads before enabling.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GoogleAdsError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
