#!/usr/bin/env python3
"""
Add IHCP intent coverage, cleanup negatives, and a sitelink copy fix to the live
Indiana Search campaign.

The script validates by default. Use --apply after validation to create missing
keywords in Google Ads.
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


API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v24")
GOOGLE_ADS_BASE = f"https://googleads.googleapis.com/{API_VERSION}"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
SOURCE_ENV = Path("/Users/dax/bomi/bomi-ads/.env")

DEFAULT_CAMPAIGN_ID = "23793592462"

IHCP_KEYWORDS = [
    ("ihcp therapist billing", "PHRASE"),
    ("indiana ihcp therapist billing", "PHRASE"),
    ("ihcp therapy billing", "PHRASE"),
    ("indiana health coverage programs billing", "PHRASE"),
    ("ihcp credentialing", "PHRASE"),
    ("ihcp billing", "EXACT"),
]

QUERY_CLEANUP_NEGATIVES = [
    ("cpt code", "PHRASE"),
    ("90832", "BROAD"),
    ("90837", "BROAD"),
    ("npi", "BROAD"),
    ("transportation provider", "PHRASE"),
    ("provider portal", "PHRASE"),
    ("interchange", "BROAD"),
    ("medical billing startups", "PHRASE"),
    ("add on codes", "PHRASE"),
    ("how to become a medicaid provider", "PHRASE"),
]

SITELINK_DESCRIPTION_FIXES = {
    "352641782552": "SimplePractice, TherapyNotes, etc.",
}


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


def find_live_ad_group(credentials: Credentials, campaign_id: str) -> dict[str, Any]:
    rows = search(
        credentials,
        f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          ad_group.id,
          ad_group.name,
          ad_group.resource_name,
          ad_group.status
        FROM ad_group
        WHERE campaign.id = {int(campaign_id)}
          AND ad_group.status != 'REMOVED'
        ORDER BY ad_group.id
        LIMIT 10
        """,
    )
    if not rows:
        raise GoogleAdsError(f"No non-removed ad groups found for campaign {campaign_id}.")
    enabled_rows = [row for row in rows if row["adGroup"].get("status") == "ENABLED"]
    return enabled_rows[0] if enabled_rows else rows[0]


def existing_keyword_keys(
    credentials: Credentials, ad_group_resource: str
) -> set[tuple[str, str, bool]]:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group_criterion.resource_name,
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
            (
                keyword.get("text", "").strip().lower(),
                keyword.get("matchType") or keyword.get("match_type") or "",
                bool(criterion.get("negative")),
            )
        )
    return keys


def criterion_operation(
    ad_group_resource: str, text: str, match_type: str, negative: bool
) -> dict[str, Any]:
    create: dict[str, Any] = {
        "adGroup": ad_group_resource,
        "status": "ENABLED",
        "negative": negative,
        "keyword": {
            "text": text,
            "matchType": match_type,
        },
    }
    return {"adGroupCriterionOperation": {"create": create}}


def existing_sitelink_descriptions(credentials: Credentials) -> dict[str, dict[str, Any]]:
    ids = ", ".join(SITELINK_DESCRIPTION_FIXES)
    rows = search(
        credentials,
        f"""
        SELECT
          asset.id,
          asset.resource_name,
          asset.sitelink_asset.link_text,
          asset.sitelink_asset.description1
        FROM asset
        WHERE asset.id IN ({ids})
        """,
    )
    return {row["asset"]["id"]: row["asset"] for row in rows}


def asset_update_operation(asset_resource: str, description1: str) -> dict[str, Any]:
    return {
        "assetOperation": {
            "update": {
                "resourceName": asset_resource,
                "sitelinkAsset": {
                    "description1": description1,
                },
            },
            "updateMask": "sitelink_asset.description1",
        }
    }


def build_operations(
    credentials: Credentials,
    ad_group_resource: str, existing_keys: set[tuple[str, str, bool]]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    operations: list[dict[str, Any]] = []
    skipped: list[str] = []
    planned: list[str] = []

    for text, match_type in IHCP_KEYWORDS:
        key = (text.lower(), match_type, False)
        label = f"+ {match_type.lower()} {text}"
        if key in existing_keys:
            skipped.append(label)
            continue
        operations.append(criterion_operation(ad_group_resource, text, match_type, False))
        planned.append(label)

    for text, match_type in QUERY_CLEANUP_NEGATIVES:
        key = (text.lower(), match_type, True)
        label = f"- {match_type.lower()} {text}"
        if key in existing_keys:
            skipped.append(label)
            continue
        operations.append(criterion_operation(ad_group_resource, text, match_type, True))
        planned.append(label)

    sitelinks = existing_sitelink_descriptions(credentials)
    for asset_id, description1 in SITELINK_DESCRIPTION_FIXES.items():
        asset = sitelinks.get(asset_id)
        if not asset:
            skipped.append(f"asset {asset_id} not found for sitelink typo fix")
            continue
        current = asset.get("sitelinkAsset", {}).get("description1", "")
        label = (
            f"~ sitelink {asset_id} description1: "
            f"{current!r} -> {description1!r}"
        )
        if current == description1:
            skipped.append(label)
            continue
        operations.append(asset_update_operation(asset["resourceName"], description1))
        planned.append(label)

    return operations, planned, skipped


def readback(credentials: Credentials, ad_group_resource: str) -> None:
    rows = search(
        credentials,
        f"""
        SELECT
          ad_group_criterion.resource_name,
          ad_group_criterion.status,
          ad_group_criterion.negative,
          ad_group_criterion.keyword.text,
          ad_group_criterion.keyword.match_type
        FROM ad_group_criterion
        WHERE ad_group.resource_name = {quote_gaql(ad_group_resource)}
          AND ad_group_criterion.type = 'KEYWORD'
          AND ad_group_criterion.status != 'REMOVED'
        ORDER BY ad_group_criterion.keyword.text
        """,
    )
    keyword_texts = {text for text, _ in IHCP_KEYWORDS} | {
        text for text, _ in QUERY_CLEANUP_NEGATIVES
    }
    print("\nReadback:")
    for row in rows:
        criterion = row["adGroupCriterion"]
        keyword = criterion.get("keyword", {})
        text = keyword.get("text", "")
        if text.lower() not in keyword_texts:
            continue
        sign = "-" if criterion.get("negative") else "+"
        print(
            f"  {sign} {keyword.get('matchType')} {text} "
            f"[{criterion.get('status')}] {criterion.get('resourceName')}"
        )
    sitelinks = existing_sitelink_descriptions(credentials)
    for asset_id, description1 in SITELINK_DESCRIPTION_FIXES.items():
        asset = sitelinks.get(asset_id, {})
        sitelink = asset.get("sitelinkAsset", {})
        print(
            f"  ~ sitelink {asset_id} "
            f"{sitelink.get('linkText')}: {sitelink.get('description1')} "
            f"(expected: {description1})"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    load_env()
    credentials = load_credentials()
    ad_group_row = find_live_ad_group(credentials, args.campaign_id)
    campaign = ad_group_row["campaign"]
    ad_group = ad_group_row["adGroup"]
    ad_group_resource = ad_group["resourceName"]

    print(
        f"Campaign: {campaign['id']} / {campaign['name']} "
        f"[{campaign.get('status')}]"
    )
    print(
        f"Ad group: {ad_group['id']} / {ad_group['name']} "
        f"[{ad_group.get('status')}]"
    )

    existing_keys = existing_keyword_keys(credentials, ad_group_resource)
    operations, planned, skipped = build_operations(
        credentials, ad_group_resource, existing_keys
    )

    if planned:
        print("\nPlanned keyword changes:")
        for item in planned:
            print(f"  {item}")
    if skipped:
        print("\nAlready present, skipped:")
        for item in skipped:
            print(f"  {item}")

    if not operations:
        print("\nNo Google Ads changes needed.")
        readback(credentials, ad_group_resource)
        return 0

    validate_only = not args.apply
    response = mutate(credentials, operations, validate_only=validate_only)
    mode = "VALIDATE ONLY" if validate_only else "APPLIED"
    print(f"\n{mode}: {len(operations)} operations")
    print(json.dumps(response, indent=2))

    if args.apply:
        readback(credentials, ad_group_resource)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GoogleAdsError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
