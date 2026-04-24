#!/usr/bin/env python3
"""
Generate a daily Bomi Google Ads report.

The script is intentionally dependency-free so Codex automations can run it from
temporary worktrees. It loads credentials from local .env first, then falls back
to the source-of-truth ignored env file in /Users/dax/bomi/bomi-ads/.env.
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
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v24")
GOOGLE_ADS_BASE = f"https://googleads.googleapis.com/{API_VERSION}"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
SOURCE_ENV = Path("/Users/dax/bomi/bomi-ads/.env")


@dataclass(frozen=True)
class Window:
    label: str
    start: date
    end: date


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_env() -> Path | None:
    candidates = [Path.cwd() / ".env", SOURCE_ENV]
    loaded = None
    for candidate in candidates:
        if candidate.exists():
            load_env_file(candidate)
            loaded = candidate
    return loaded


def customer_id(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def refresh_access_token() -> str:
    payload = urllib.parse.urlencode(
        {
            "client_id": required_env("GOOGLE_ADS_CLIENT_ID"),
            "client_secret": required_env("GOOGLE_ADS_CLIENT_SECRET"),
            "refresh_token": required_env("GOOGLE_ADS_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OAUTH_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))["access_token"]


def ads_headers(access_token: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": required_env("GOOGLE_ADS_DEVELOPER_TOKEN"),
    }
    login_customer_id = customer_id(os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""))
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id
    return headers


def search(access_token: str, query: str) -> list[dict[str, Any]]:
    customer = customer_id(required_env("GOOGLE_ADS_CUSTOMER_ID"))
    response = post_json(
        f"{GOOGLE_ADS_BASE}/customers/{customer}/googleAds:searchStream",
        ads_headers(access_token),
        {"query": " ".join(query.split())},
    )
    rows: list[dict[str, Any]] = []
    for batch in response:
        rows.extend(batch.get("results", []))
    return rows


def money(micros: str | int | None) -> float:
    return int(micros or 0) / 1_000_000


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def fmt_int(value: int) -> str:
    return f"{value:,}"


def get_customer(access_token: str) -> dict[str, Any]:
    rows = search(
        access_token,
        """
        SELECT
          customer.id,
          customer.descriptive_name,
          customer.currency_code,
          customer.time_zone,
          customer.status
        FROM customer
        LIMIT 1
        """,
    )
    if not rows:
        raise RuntimeError("No customer row returned.")
    return rows[0]["customer"]


def metrics_for_window(access_token: str, window: Window) -> list[dict[str, Any]]:
    return search(
        access_token,
        f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          campaign.advertising_channel_type,
          campaign_budget.amount_micros,
          metrics.cost_micros,
          metrics.impressions,
          metrics.clicks,
          metrics.conversions,
          metrics.conversions_value
        FROM campaign
        WHERE campaign.status != 'REMOVED'
          AND segments.date BETWEEN '{window.start.isoformat()}'
          AND '{window.end.isoformat()}'
        ORDER BY campaign.name
        """,
    )


def search_terms(access_token: str, window: Window) -> list[dict[str, Any]]:
    return search(
        access_token,
        f"""
        SELECT
          campaign.name,
          search_term_view.search_term,
          metrics.cost_micros,
          metrics.impressions,
          metrics.clicks,
          metrics.conversions
        FROM search_term_view
        WHERE campaign.status != 'REMOVED'
          AND segments.date BETWEEN '{window.start.isoformat()}'
          AND '{window.end.isoformat()}'
        ORDER BY metrics.cost_micros DESC
        LIMIT 50
        """,
    )


def campaign_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        campaign = row["campaign"]
        metrics = row["metrics"]
        budget = row.get("campaignBudget", {})
        clicks = int(metrics.get("clicks", 0))
        impressions = int(metrics.get("impressions", 0))
        conversions = float(metrics.get("conversions", 0))
        cost = money(metrics.get("costMicros", 0))
        result.append(
            {
                "name": campaign.get("name", ""),
                "status": campaign.get("status", ""),
                "budget": money(budget.get("amountMicros", 0)),
                "cost": cost,
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ratio(clicks, impressions),
                "cpc": ratio(cost, clicks),
                "conversions": conversions,
                "cpa": ratio(cost, conversions),
            }
        )
    return result


def totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cost = sum(row["cost"] for row in rows)
    impressions = sum(row["impressions"] for row in rows)
    clicks = sum(row["clicks"] for row in rows)
    conversions = sum(row["conversions"] for row in rows)
    return {
        "cost": cost,
        "impressions": impressions,
        "clicks": clicks,
        "ctr": ratio(clicks, impressions),
        "cpc": ratio(cost, clicks),
        "conversions": conversions,
        "cpa": ratio(cost, conversions),
    }


def metric_table(window_data: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "| Window | Cost | Impressions | Clicks | CTR | Avg CPC | Conversions | CPA |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, rows in window_data.items():
        total = totals(rows)
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    fmt_money(total["cost"]),
                    fmt_int(total["impressions"]),
                    fmt_int(total["clicks"]),
                    f"{total['ctr'] * 100:.2f}%",
                    fmt_money(total["cpc"]),
                    f"{total['conversions']:.2f}",
                    fmt_money(total["cpa"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def campaign_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Campaign | Status | Budget | Cost | Clicks | Impressions | Conversions | CPA |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['name']}`",
                    row["status"],
                    fmt_money(row["budget"]),
                    fmt_money(row["cost"]),
                    fmt_int(row["clicks"]),
                    fmt_int(row["impressions"]),
                    f"{row['conversions']:.2f}",
                    fmt_money(row["cpa"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def search_term_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No search terms returned for the primary window."
    lines = [
        "| Campaign | Search term | Cost | Clicks | Impressions | Conversions | CPA |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows[:25]:
        campaign = row["campaign"]
        search_term = row["searchTermView"]
        metrics = row["metrics"]
        cost = money(metrics.get("costMicros", 0))
        clicks = int(metrics.get("clicks", 0))
        impressions = int(metrics.get("impressions", 0))
        conversions = float(metrics.get("conversions", 0))
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{campaign.get('name', '')}`",
                    f"`{search_term.get('searchTerm', '')}`",
                    fmt_money(cost),
                    fmt_int(clicks),
                    fmt_int(impressions),
                    f"{conversions:.2f}",
                    fmt_money(ratio(cost, conversions)),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def blocked_report(report_date: date, error: BaseException, env_path: Path | None) -> str:
    now = datetime.now().astimezone()
    return f"""# Daily Ads Report - {report_date.isoformat()}

Source: Google Ads API REST via local `.env` credentials
Credential file: `{env_path or 'not found'}`
Generated: {now.isoformat(timespec='seconds')}

## Executive Readout

No live performance readout is available. The Google Ads live pull failed before data retrieval:

```text
{type(error).__name__}: {error}
```

Treat this as a data-access blocker, not a performance assessment.

## Recommended Actions

1. Verify terminal DNS/network access for `oauth2.googleapis.com` and `googleads.googleapis.com`.
2. Verify the ignored `.env` exists at `/Users/dax/bomi/bomi-ads/.env`.
3. Rerun `python3 scripts/google_ads_daily_report.py`.
"""


def build_report(access_token: str, report_date: date, env_path: Path | None) -> str:
    customer = get_customer(access_token)
    primary = Window("Primary day", report_date, report_date)
    prior = Window("Prior day", report_date - timedelta(days=1), report_date - timedelta(days=1))
    same_weekday = Window(
        "Same weekday last week", report_date - timedelta(days=7), report_date - timedelta(days=7)
    )
    last_7 = Window("Last 7 full days", report_date - timedelta(days=6), report_date)
    windows = [primary, prior, same_weekday, last_7]

    window_data = {
        window.label: campaign_rows(metrics_for_window(access_token, window))
        for window in windows
    }
    terms = search_terms(access_token, primary)
    now = datetime.now().astimezone()

    primary_totals = totals(window_data[primary.label])
    return f"""# Daily Ads Report - {report_date.isoformat()}

Source: Google Ads API REST via local `.env` credentials
Credential file: `{env_path or 'environment'}`
Generated: {now.isoformat(timespec='seconds')}
Account: {customer.get('descriptiveName')} / `{customer.get('id')}`
Timezone: {customer.get('timeZone')}
Primary window: {report_date.isoformat()}

## Executive Readout

Primary-day spend was {fmt_money(primary_totals['cost'])} on {fmt_int(primary_totals['clicks'])} clicks and {primary_totals['conversions']:.2f} conversions, for a blended CPA of {fmt_money(primary_totals['cpa'])}.

## Scorecard

{metric_table(window_data)}

## Campaigns

{campaign_table(window_data[primary.label])}

## Search Terms

{search_term_table(terms)}

## Notes

- Campaign status in the table is the current API status; metrics are for the selected report window.
- Ohio and Indiana state clone campaigns were created paused, then enabled after review on 2026-04-24.
"""


def previous_full_day(account_timezone: str) -> date:
    now = datetime.now(ZoneInfo(account_timezone))
    return now.date() - timedelta(days=1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Report date in YYYY-MM-DD. Defaults to previous full account-local day.")
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()

    env_path = load_env()
    report_date = None
    try:
        access_token = refresh_access_token()
        customer = get_customer(access_token)
        report_date = date.fromisoformat(args.date) if args.date else previous_full_day(customer["timeZone"])
        report = build_report(access_token, report_date, env_path)
    except Exception as exc:
        report_date = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
        report = blocked_report(report_date, exc, env_path)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{report_date.isoformat()}-daily-ads-report.md"
    output_path.write_text(report)
    print(f"Saved {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
