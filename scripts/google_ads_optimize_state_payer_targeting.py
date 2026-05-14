#!/usr/bin/env python3
"""
Validate/apply the state Search targeting cleanup from the May 2026 targeting
feedback.

Defaults to validateOnly mode. Use --apply only when the planned Search changes
have been approved for the live account.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ad_tracking_urls import build_google_search_url, slugify


API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v24")
GOOGLE_ADS_BASE = f"https://googleads.googleapis.com/{API_VERSION}"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
SOURCE_ENV = Path("/Users/dax/bomi/bomi-ads/.env")

PAYER_AD_GROUP_NAME = "Payer/program phrase + exact"
GENERAL_SEARCH_CAMPAIGN_ID = "23591492785"


@dataclass(frozen=True)
class StateCampaignPlan:
    state: str
    campaign_id: str
    landing_page: str
    disable_content_network: bool
    payer_terms: tuple[str, ...]


STATE_CAMPAIGNS = (
    StateCampaignPlan(
        state="Illinois",
        campaign_id="23586656126",
        landing_page="https://billwithbomi.com/illinois",
        disable_content_network=True,
        payer_terms=(
            "bcchp therapist billing",
            "bcchp therapy billing",
            "bcchp claims help",
            "bcchp behavioral health billing",
            "blue cross community health plans billing",
            "blue cross community health plans therapist billing",
            "healthchoice illinois therapist billing",
            "illinois medicaid therapist billing",
            "illinois medicaid credentialing therapist",
            "impact provider enrollment help",
            "aetna better health illinois therapist billing",
            "meridian illinois therapist billing",
            "molina illinois therapist billing",
            "countycare therapist billing",
            "countycare behavioral health billing",
        ),
    ),
    StateCampaignPlan(
        state="Ohio",
        campaign_id="23783665086",
        landing_page="https://billwithbomi.com/ohio",
        disable_content_network=True,
        payer_terms=(
            "ohio medicaid therapist billing",
            "odm behavioral health billing",
            "ohio behavioral health billing help",
            "ohio medicaid credentialing therapist",
            "ohio pnm provider enrollment help",
            "caresource therapist billing",
            "caresource behavioral health billing",
            "buckeye therapist billing",
            "anthem ohio medicaid therapist billing",
            "molina ohio therapist billing",
            "unitedhealthcare community plan ohio billing",
            "amerihealth caritas ohio therapist billing",
            "humana healthy horizons ohio billing",
            "ohiorise behavioral health billing",
        ),
    ),
    StateCampaignPlan(
        state="Indiana",
        campaign_id="23793592462",
        landing_page="https://billwithbomi.com/indiana",
        disable_content_network=False,
        payer_terms=(
            "ihcp therapist billing",
            "ihcp behavioral health billing",
            "indiana medicaid therapist billing",
            "indiana medicaid credentialing therapist",
            "ihcp provider enrollment help",
            "ihcp billing provider enrollment",
            "ihcp group clinic enrollment",
            "hip therapist billing indiana",
            "hoosier healthwise behavioral health billing",
            "hoosier care connect therapist billing",
            "mhs indiana therapist billing",
            "anthem indiana medicaid billing",
            "caresource indiana therapist billing",
            "unitedhealthcare community plan indiana billing",
        ),
    ),
    StateCampaignPlan(
        state="New Mexico",
        campaign_id="23786543262",
        landing_page="https://billwithbomi.com/new-mexico",
        disable_content_network=True,
        payer_terms=(
            "turquoise care therapist billing",
            "turquoise care behavioral health billing",
            "new mexico medicaid therapist billing",
            "nm medicaid behavioral health billing",
            "turquoise claims billing help",
            "turquoise claims provider enrollment",
            "turquoise claims therapy billing",
            "bcbs new mexico medicaid billing",
            "blue cross blue shield new mexico medicaid billing",
            "presbyterian health plan medicaid billing",
            "molina new mexico therapist billing",
            "unitedhealthcare community plan new mexico billing",
            "new mexico medicaid credentialing therapist",
        ),
    ),
)

CAMPAIGN_NEGATIVES = (
    ("job", "BROAD"),
    ("jobs", "BROAD"),
    ("career", "BROAD"),
    ("careers", "BROAD"),
    ("salary", "BROAD"),
    ("hiring", "BROAD"),
    ("resume", "BROAD"),
    ("internship", "BROAD"),
    ("training", "BROAD"),
    ("course", "BROAD"),
    ("certification course", "PHRASE"),
    ("school", "BROAD"),
    ("degree", "BROAD"),
    ("free", "BROAD"),
    ("template", "BROAD"),
    ("sample", "BROAD"),
    ("pdf", "BROAD"),
    ("manual", "BROAD"),
    ("handbook", "BROAD"),
    ("form", "BROAD"),
    ("forms", "BROAD"),
    ("phone number", "PHRASE"),
    ("customer service", "PHRASE"),
    ("login", "BROAD"),
    ("sign in", "PHRASE"),
    ("portal", "BROAD"),
    ("member portal", "PHRASE"),
    ("patient portal", "PHRASE"),
    ("provider portal", "PHRASE"),
    ("apply", "BROAD"),
    ("application status", "PHRASE"),
    ("check eligibility", "PHRASE"),
    ("fee schedule", "PHRASE"),
    ("reimbursement rate", "PHRASE"),
    ("cpt", "BROAD"),
    ("cpt code", "PHRASE"),
    ("icd 10", "PHRASE"),
    ("modifier", "BROAD"),
    ("taxonomy code", "PHRASE"),
    ("npi lookup", "PHRASE"),
    ("place of service", "PHRASE"),
    ("timely filing limit", "PHRASE"),
    ("prior authorization form", "PHRASE"),
    ("appeal form", "PHRASE"),
    ("claim form", "PHRASE"),
    ("provider manual", "PHRASE"),
    ("billing manual", "PHRASE"),
    ("pricing", "BROAD"),
    ("price", "BROAD"),
    ("demo", "BROAD"),
    ("reviews", "BROAD"),
    ("tutorial", "BROAD"),
    ("how to use", "PHRASE"),
    ("support phone number", "PHRASE"),
    ("customer support", "PHRASE"),
    ("download", "BROAD"),
    ("app", "BROAD"),
    ("software comparison", "PHRASE"),
    ("alternative software", "PHRASE"),
)

PAYER_RSA_HEADLINES = (
    "Bomi Therapist Billing",
    "Medicaid Billing Help",
    "Therapy Practice Billing",
    "Payer Claims Support",
    "Claims + Denials Help",
    "Billing + Credentialing",
    "Schedule Free Consult",
    "Flat 4% Collections",
    "Keep Your Current EHR",
    "Insurance Billing Help",
)

PAYER_RSA_DESCRIPTIONS = (
    "Billing and credentialing support for therapy practices without changing your EHR.",
    "Get help with Medicaid, payer enrollment, claims, denials, and follow-up.",
    "Built for practices that need operator support, not a government portal.",
    "Book a free consult with Bomi.",
)


def keyword_policy_exemptions(text: str) -> list[dict[str, str]]:
    exemptions: list[dict[str, str]] = []
    lower = text.lower()
    if "behavioral health" in lower:
        exemptions.append(
            {
                "policyName": "HEALTH_IN_PERSONALIZED_ADS",
                "violatingText": text,
            }
        )
    if " help" in lower or lower.endswith("help"):
        exemptions.append(
            {
                "policyName": "THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT",
                "violatingText": text,
            }
        )
    return exemptions


class GoogleAdsError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    developer_token: str
    customer_id: str
    login_customer_id: str | None
    access_token: str


@dataclass
class BuildResult:
    operations: list[dict[str, Any]]
    planned: list[str]
    skipped: list[str]


class TempIds:
    def __init__(self, start: int = -1000) -> None:
        self.next_id = start

    def take(self) -> str:
        value = str(self.next_id)
        self.next_id -= 1
        return value


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


def micros_to_money(value: str | int | None) -> float:
    return int(value or 0) / 1_000_000


def keyword_key(text: str, match_type: str, negative: bool = False) -> tuple[str, str, bool]:
    return (text.strip().lower(), match_type.upper(), negative)


def load_campaigns(
    credentials: Credentials, campaign_ids: list[str]
) -> dict[str, dict[str, Any]]:
    ids = ", ".join(str(int(campaign_id)) for campaign_id in campaign_ids)
    rows = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.resource_name,
          campaign.status,
          campaign.primary_status,
          campaign.advertising_channel_type,
          campaign.campaign_budget,
          campaign.network_settings.target_google_search,
          campaign.network_settings.target_search_network,
          campaign.network_settings.target_content_network,
          campaign.network_settings.target_partner_search_network,
          campaign_budget.id,
          campaign_budget.name,
          campaign_budget.amount_micros
        FROM campaign
        WHERE campaign.id IN ({ids})
          AND campaign.status != 'REMOVED'
        ORDER BY campaign.id
        """,
    )
    found = {row["campaign"]["id"]: row for row in rows}
    missing = sorted(set(campaign_ids) - set(found))
    if missing:
        raise GoogleAdsError(f"Could not find non-removed campaigns: {', '.join(missing)}")
    return found


def load_ad_groups(credentials: Credentials, campaign_id: str) -> list[dict[str, Any]]:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group.id,
          ad_group.name,
          ad_group.resource_name,
          ad_group.status,
          ad_group.type,
          ad_group.cpc_bid_micros
        FROM ad_group
        WHERE campaign.id = {int(campaign_id)}
          AND ad_group.status != 'REMOVED'
        ORDER BY ad_group.id
        """,
    )
    return [row["adGroup"] for row in rows]


def load_ad_group_keywords(
    credentials: Credentials, ad_group_resource: str
) -> set[tuple[str, str, bool]]:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group_criterion.status,
          ad_group_criterion.negative,
          ad_group_criterion.keyword.text,
          ad_group_criterion.keyword.match_type
        FROM ad_group_criterion
        WHERE ad_group.resource_name = {quote_gaql(ad_group_resource)}
          AND ad_group_criterion.type = 'KEYWORD'
          AND ad_group_criterion.status != 'REMOVED'
        """,
    )
    keys: set[tuple[str, str, bool]] = set()
    for row in rows:
        criterion = row["adGroupCriterion"]
        keyword = criterion.get("keyword", {})
        keys.add(
            keyword_key(
                keyword.get("text", ""),
                keyword.get("matchType") or "",
                bool(criterion.get("negative")),
            )
        )
    return keys


def load_campaign_negative_keywords(
    credentials: Credentials, campaign_id: str
) -> set[tuple[str, str, bool]]:
    rows = search(
        credentials,
        f"""
        SELECT
          campaign_criterion.status,
          campaign_criterion.negative,
          campaign_criterion.keyword.text,
          campaign_criterion.keyword.match_type
        FROM campaign_criterion
        WHERE campaign.id = {int(campaign_id)}
          AND campaign_criterion.type = 'KEYWORD'
          AND campaign_criterion.negative = TRUE
          AND campaign_criterion.status != 'REMOVED'
        """,
    )
    keys: set[tuple[str, str, bool]] = set()
    for row in rows:
        criterion = row["campaignCriterion"]
        keyword = criterion.get("keyword", {})
        keys.add(
            keyword_key(
                keyword.get("text", ""),
                keyword.get("matchType") or "",
                True,
            )
        )
    return keys


def load_responsive_search_ads(
    credentials: Credentials, ad_group_resource: str
) -> list[dict[str, Any]]:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group_ad.resource_name,
          ad_group_ad.status,
          ad_group_ad.ad.id,
          ad_group_ad.ad.final_urls,
          ad_group_ad.ad.type,
          ad_group_ad.policy_summary.approval_status,
          ad_group_ad.policy_summary.review_status
        FROM ad_group_ad
        WHERE ad_group.resource_name = {quote_gaql(ad_group_resource)}
          AND ad_group_ad.status != 'REMOVED'
          AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
        """,
    )
    return rows


def campaign_update_content_network_operation(
    campaign_resource: str,
) -> dict[str, Any]:
    return {
        "campaignOperation": {
            "update": {
                "resourceName": campaign_resource,
                "networkSettings": {"targetContentNetwork": False},
            },
            "updateMask": "network_settings.target_content_network",
        }
    }


def ad_group_create_operation(
    credentials: Credentials,
    campaign_resource: str,
    source_ad_group: dict[str, Any],
    temp_id: str,
) -> tuple[dict[str, Any], str]:
    ad_group_resource = f"customers/{credentials.customer_id}/adGroups/{temp_id}"
    create: dict[str, Any] = {
        "resourceName": ad_group_resource,
        "campaign": campaign_resource,
        "name": PAYER_AD_GROUP_NAME,
        "status": "ENABLED",
        "type": source_ad_group.get("type", "SEARCH_STANDARD"),
    }
    if "cpcBidMicros" in source_ad_group:
        create["cpcBidMicros"] = source_ad_group["cpcBidMicros"]
    return {"adGroupOperation": {"create": create}}, ad_group_resource


def rsa_text_assets(values: tuple[str, ...]) -> list[dict[str, str]]:
    return [{"text": value} for value in values]


def final_url_for_plan(plan: StateCampaignPlan, campaign_name: str) -> str:
    return build_google_search_url(
        plan.landing_page,
        campaign=slugify(campaign_name),
        content=PAYER_AD_GROUP_NAME,
        audience=f"{slugify(plan.state)}_payer_program_search",
    )


def ad_create_operation(
    ad_group_resource: str, plan: StateCampaignPlan, campaign_name: str
) -> dict[str, Any]:
    return {
        "adGroupAdOperation": {
            "create": {
                "adGroup": ad_group_resource,
                "status": "ENABLED",
                "ad": {
                    "finalUrls": [final_url_for_plan(plan, campaign_name)],
                    "responsiveSearchAd": {
                        "path1": "billing",
                        "path2": "medicaid",
                        "headlines": rsa_text_assets(PAYER_RSA_HEADLINES),
                        "descriptions": rsa_text_assets(PAYER_RSA_DESCRIPTIONS),
                    },
                },
            }
        }
    }


def ad_group_keyword_operation(
    ad_group_resource: str, text: str, match_type: str
) -> dict[str, Any]:
    create = {
        "adGroup": ad_group_resource,
        "status": "ENABLED",
        "negative": False,
        "keyword": {
            "text": text,
            "matchType": match_type,
        },
    }
    operation: dict[str, Any] = {"create": create}
    exemptions = keyword_policy_exemptions(text)
    if exemptions:
        operation["exemptPolicyViolationKeys"] = exemptions
    return {
        "adGroupCriterionOperation": operation
    }


def campaign_negative_operation(
    campaign_resource: str, text: str, match_type: str
) -> dict[str, Any]:
    return {
        "campaignCriterionOperation": {
            "create": {
                "campaign": campaign_resource,
                "negative": True,
                "keyword": {
                    "text": text,
                    "matchType": match_type,
                },
            }
        }
    }


def find_source_ad_group(ad_groups: list[dict[str, Any]]) -> dict[str, Any]:
    enabled = [ad_group for ad_group in ad_groups if ad_group.get("status") == "ENABLED"]
    if enabled:
        return enabled[0]
    if ad_groups:
        return ad_groups[0]
    raise GoogleAdsError("No non-removed ad groups found for campaign.")


def build_operations(credentials: Credentials) -> BuildResult:
    state_campaign_ids = [plan.campaign_id for plan in STATE_CAMPAIGNS]
    negative_campaign_ids = [GENERAL_SEARCH_CAMPAIGN_ID, *state_campaign_ids]
    campaigns = load_campaigns(credentials, sorted(set(negative_campaign_ids)))
    temp_ids = TempIds()
    result = BuildResult(operations=[], planned=[], skipped=[])

    for plan in STATE_CAMPAIGNS:
        row = campaigns[plan.campaign_id]
        campaign = row["campaign"]
        budget = row.get("campaignBudget", {})
        if campaign.get("advertisingChannelType") != "SEARCH":
            raise GoogleAdsError(
                f"{campaign['id']} / {campaign['name']} is not a Search campaign."
            )

        network = campaign.get("networkSettings", {})
        content_enabled = bool(network.get("targetContentNetwork"))
        if plan.disable_content_network and content_enabled:
            result.operations.append(
                campaign_update_content_network_operation(campaign["resourceName"])
            )
            result.planned.append(
                f"~ {plan.state}: disable Content network on {campaign['id']} / {campaign['name']}"
            )
        elif plan.disable_content_network:
            result.skipped.append(f"{plan.state}: Content network already disabled")
        else:
            result.skipped.append(f"{plan.state}: Content network left as-is by plan")

        ad_groups = load_ad_groups(credentials, plan.campaign_id)
        source_ad_group = find_source_ad_group(ad_groups)
        payer_ad_group = next(
            (ad_group for ad_group in ad_groups if ad_group.get("name") == PAYER_AD_GROUP_NAME),
            None,
        )
        if payer_ad_group:
            ad_group_resource = payer_ad_group["resourceName"]
            result.skipped.append(
                f"{plan.state}: ad group already exists: {payer_ad_group['id']} / {PAYER_AD_GROUP_NAME}"
            )
            existing_keyword_keys = load_ad_group_keywords(credentials, ad_group_resource)
            if load_responsive_search_ads(credentials, ad_group_resource):
                result.skipped.append(f"{plan.state}: payer ad group already has an RSA")
            else:
                result.operations.append(ad_create_operation(ad_group_resource, plan, campaign["name"]))
                result.planned.append(f"+ {plan.state}: create RSA in existing payer ad group")
        else:
            ad_group_operation, ad_group_resource = ad_group_create_operation(
                credentials,
                campaign["resourceName"],
                source_ad_group,
                temp_ids.take(),
            )
            result.operations.append(ad_group_operation)
            result.operations.append(ad_create_operation(ad_group_resource, plan, campaign["name"]))
            result.planned.append(
                f"+ {plan.state}: create ad group {PAYER_AD_GROUP_NAME!r} under {campaign['id']}"
            )
            result.planned.append(f"+ {plan.state}: create payer-program RSA")
            existing_keyword_keys = set()

        for text in plan.payer_terms:
            for match_type in ("PHRASE", "EXACT"):
                key = keyword_key(text, match_type, False)
                label = f"+ {plan.state}: {match_type.lower()} {text}"
                if key in existing_keyword_keys:
                    result.skipped.append(label)
                    continue
                result.operations.append(ad_group_keyword_operation(ad_group_resource, text, match_type))
                result.planned.append(label)

        result.skipped.append(
            f"{plan.state}: budget preserved at ${micros_to_money(budget.get('amountMicros')):.2f}/day"
        )

    for campaign_id in negative_campaign_ids:
        row = campaigns[campaign_id]
        campaign = row["campaign"]
        existing_negative_keys = load_campaign_negative_keywords(credentials, campaign_id)
        for text, match_type in CAMPAIGN_NEGATIVES:
            key = keyword_key(text, match_type, True)
            label = f"- {campaign['name']}: {match_type.lower()} {text}"
            if key in existing_negative_keys:
                result.skipped.append(label)
                continue
            result.operations.append(
                campaign_negative_operation(campaign["resourceName"], text, match_type)
            )
            result.planned.append(label)

    return result


def readback_campaign_settings(credentials: Credentials) -> None:
    campaign_ids = [
        GENERAL_SEARCH_CAMPAIGN_ID,
        *(plan.campaign_id for plan in STATE_CAMPAIGNS),
    ]
    campaigns = load_campaigns(credentials, sorted(set(campaign_ids)))
    print("\nCampaign readback:")
    for campaign_id in campaign_ids:
        row = campaigns[campaign_id]
        campaign = row["campaign"]
        budget = row.get("campaignBudget", {})
        network = campaign.get("networkSettings", {})
        print(
            "  "
            f"{campaign['id']} / {campaign['name']} "
            f"[status={campaign.get('status')}, primary={campaign.get('primaryStatus')}, "
            f"budget=${micros_to_money(budget.get('amountMicros')):.2f}/day, "
            f"google_search={network.get('targetGoogleSearch')}, "
            f"search_network={network.get('targetSearchNetwork')}, "
            f"content={network.get('targetContentNetwork')}, "
            f"partners={network.get('targetPartnerSearchNetwork')}]"
        )


def readback_payer_ad_groups(credentials: Credentials) -> None:
    print("\nPayer ad group readback:")
    for plan in STATE_CAMPAIGNS:
        rows = search(
            credentials,
            f"""
            SELECT
              campaign.id,
              campaign.name,
              ad_group.id,
              ad_group.name,
              ad_group.resource_name,
              ad_group.status
            FROM ad_group
            WHERE campaign.id = {int(plan.campaign_id)}
              AND ad_group.name = {quote_gaql(PAYER_AD_GROUP_NAME)}
              AND ad_group.status != 'REMOVED'
            """,
        )
        if not rows:
            print(f"  {plan.state}: missing ad group {PAYER_AD_GROUP_NAME!r}")
            continue
        ad_group = rows[0]["adGroup"]
        ad_group_resource = ad_group["resourceName"]
        rsa_rows = load_responsive_search_ads(credentials, ad_group_resource)
        keyword_rows = search(
            credentials,
            f"""
            SELECT
              ad_group_criterion.status,
              ad_group_criterion.negative,
              ad_group_criterion.keyword.text,
              ad_group_criterion.keyword.match_type
            FROM ad_group_criterion
            WHERE ad_group.resource_name = {quote_gaql(ad_group_resource)}
              AND ad_group_criterion.type = 'KEYWORD'
              AND ad_group_criterion.status != 'REMOVED'
            ORDER BY ad_group_criterion.keyword.text,
              ad_group_criterion.keyword.match_type
            """,
        )
        matching_keyword_count = 0
        term_set = {term.lower() for term in plan.payer_terms}
        for row in keyword_rows:
            criterion = row["adGroupCriterion"]
            keyword = criterion.get("keyword", {})
            if keyword.get("text", "").lower() in term_set and not criterion.get("negative"):
                matching_keyword_count += 1
        print(
            f"  {plan.state}: {ad_group['id']} / {ad_group['name']} "
            f"[{ad_group.get('status')}], rsa_count={len(rsa_rows)}, "
            f"payer_keywords={matching_keyword_count}/{len(plan.payer_terms) * 2}"
        )
        for row in rsa_rows:
            ad_group_ad = row.get("adGroupAd", {})
            ad = ad_group_ad.get("ad", {})
            policy = ad_group_ad.get("policySummary", {})
            print(
                f"    RSA ad {ad.get('id')} "
                f"[status={ad_group_ad.get('status')}, "
                f"approval={policy.get('approvalStatus')}, "
                f"review={policy.get('reviewStatus')}]"
            )


def readback_negative_counts(credentials: Credentials) -> None:
    print("\nCampaign negative readback:")
    campaigns = load_campaigns(
        credentials,
        sorted({GENERAL_SEARCH_CAMPAIGN_ID, *(plan.campaign_id for plan in STATE_CAMPAIGNS)}),
    )
    for campaign_id, row in sorted(campaigns.items()):
        campaign = row["campaign"]
        keys = load_campaign_negative_keywords(credentials, campaign_id)
        planned_keys = {keyword_key(text, match_type, True) for text, match_type in CAMPAIGN_NEGATIVES}
        print(
            f"  {campaign['id']} / {campaign['name']}: "
            f"{len(keys & planned_keys)}/{len(planned_keys)} planned negatives present"
        )


def readback(credentials: Credentials) -> None:
    readback_campaign_settings(credentials)
    readback_payer_ad_groups(credentials)
    readback_negative_counts(credentials)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply live Google Ads mutations.")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Only print readback; do not build or validate mutations.",
    )
    args = parser.parse_args()

    load_env()
    credentials = load_credentials()

    if args.read_only:
        readback(credentials)
        return 0

    result = build_operations(credentials)

    if result.planned:
        print("Planned changes:")
        for item in result.planned:
            print(f"  {item}")
    if result.skipped:
        print("\nAlready present / skipped:")
        for item in result.skipped:
            print(f"  {item}")

    if not result.operations:
        print("\nNo Google Ads changes needed.")
        readback(credentials)
        return 0

    validate_only = not args.apply
    response = mutate(credentials, result.operations, validate_only=validate_only)
    mode = "VALIDATE ONLY" if validate_only else "APPLIED"
    print(f"\n{mode}: {len(result.operations)} operations")
    print(json.dumps(response, indent=2))
    readback(credentials)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GoogleAdsError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
