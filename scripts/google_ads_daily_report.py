#!/usr/bin/env python3
"""
Generate a daily Bomi Google Ads report.

The script is intentionally dependency-free so Codex automations can run it from
temporary worktrees. It loads credentials from local .env first, then falls back
to the source-of-truth ignored env file in /Users/dax/bomi/bomi-ads/.env.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
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
REPO_REPORT_BASE = "https://github.com/redaxed/bomi-ads/blob/main/reports"
RAW_REPORT_BASE = "https://raw.githubusercontent.com/redaxed/bomi-ads/main/reports"


@dataclass(frozen=True)
class Window:
    label: str
    start: date
    end: date


@dataclass(frozen=True)
class LiveReport:
    customer: dict[str, Any]
    report_date: date
    window_data: dict[str, list[dict[str, Any]]]
    search_terms: list[dict[str, Any]]


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


def fmt_float(value: float) -> str:
    return f"{value:,.2f}"


def fmt_cpa(cost: float, conversions: float) -> str:
    return "n/a" if conversions <= 0 else fmt_money(cost / conversions)


def fmt_signed(value: float, formatter: Any) -> str:
    if abs(value) < 0.005:
        return "flat"
    sign = "+" if value > 0 else "-"
    return f"{sign}{formatter(abs(value))}"


def fmt_signed_count(value: float) -> str:
    if abs(value) < 0.005:
        return "flat"
    sign = "+" if value > 0 else "-"
    if float(value).is_integer():
        return f"{sign}{fmt_int(int(abs(value)))}"
    return f"{sign}{fmt_float(abs(value))}"


def text_bar(value: float, maximum: float, width: int = 24) -> str:
    if maximum <= 0 or value <= 0:
        return ""
    filled = max(1, round((value / maximum) * width))
    return "#" * min(width, filled)


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
                    fmt_cpa(total["cost"], total["conversions"]),
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
                    fmt_cpa(row["cost"], row["conversions"]),
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
                    fmt_cpa(cost, conversions),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def report_urls(report_date: date) -> dict[str, str]:
    stem = report_date.isoformat()
    return {
        "report": f"{REPO_REPORT_BASE}/{stem}-daily-ads-report.md",
        "summary": f"{REPO_REPORT_BASE}/{stem}-daily-ads-slack.md",
        "chart": f"{RAW_REPORT_BASE}/{stem}-daily-ads-chart.svg",
    }


def collect_live_report(access_token: str, report_date: date) -> LiveReport:
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
    return LiveReport(
        customer=customer,
        report_date=report_date,
        window_data=window_data,
        search_terms=search_terms(access_token, primary),
    )


def svg_text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def build_chart_svg(live: LiveReport) -> str:
    labels = list(live.window_data.keys())
    totals_by_label = {label: totals(rows) for label, rows in live.window_data.items()}
    chart_width = 940
    chart_height = 640
    left = 235
    max_bar = 555
    y_start = 92
    row_gap = 38

    metric_specs = [
        ("Spend", "cost", "#2563eb", fmt_money),
        ("Clicks", "clicks", "#059669", lambda value: fmt_int(int(value))),
        ("Conversions", "conversions", "#d97706", fmt_float),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_width}" height="{chart_height}" viewBox="0 0 {chart_width} {chart_height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#111827}.muted{fill:#6b7280}.label{font-size:14px}.title{font-size:24px;font-weight:700}.section{font-size:16px;font-weight:700}</style>',
        f'<text x="32" y="42" class="title">Google Ads report - {live.report_date.isoformat()}</text>',
        '<text x="32" y="66" class="muted label">Comparison windows: primary, prior day, same weekday last week, and trailing 7 full days</text>',
    ]

    section_y = y_start
    for title, key, color, formatter in metric_specs:
        values = [float(totals_by_label[label][key]) for label in labels]
        maximum = max(values) if values else 0.0
        parts.append(f'<text x="32" y="{section_y}" class="section">{svg_text(title)}</text>')
        for index, label in enumerate(labels):
            y = section_y + 24 + index * row_gap
            value = values[index]
            width = 0 if maximum <= 0 or value <= 0 else max(2, (value / maximum) * max_bar)
            parts.extend(
                [
                    f'<text x="32" y="{y + 15}" class="label">{svg_text(label)}</text>',
                    f'<rect x="{left}" y="{y}" width="{max_bar}" height="22" rx="4" fill="#eef2ff"/>',
                    f'<rect x="{left}" y="{y}" width="{width:.1f}" height="22" rx="4" fill="{color}"/>',
                    f'<text x="{left + max_bar + 18}" y="{y + 16}" class="label">{svg_text(formatter(value))}</text>',
                ]
            )
        section_y += 176

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def blocked_chart_svg(report_date: date) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="940" height="220" viewBox="0 0 940 220">
<rect width="100%" height="100%" fill="#ffffff"/>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#111827}}.muted{{fill:#6b7280}}.title{{font-size:24px;font-weight:700}}.body{{font-size:16px}}</style>
<text x="32" y="48" class="title">Google Ads report - {report_date.isoformat()}</text>
<text x="32" y="88" class="body">Live Google Ads metrics were unavailable for this run.</text>
<text x="32" y="118" class="muted body">The report file records the data-access blocker and the intended comparison windows.</text>
</svg>
"""


def campaign_status_note(rows: list[dict[str, Any]]) -> str:
    state_rows = [
        row
        for row in rows
        if " - Ohio " in row["name"] or " - Indiana " in row["name"]
    ]
    if not state_rows:
        return "Ohio/Indiana state clones were not present in this report window."
    enabled = [row for row in state_rows if row["status"] == "ENABLED"]
    spend = sum(row["cost"] for row in state_rows)
    if len(enabled) == len(state_rows):
        return f"Ohio/Indiana clones are ENABLED with {fmt_money(spend)} spend in this window."
    statuses = ", ".join(f"{row['name']}: {row['status']}" for row in state_rows)
    return f"State clone statuses: {statuses}."


def build_slack_summary(live: LiveReport) -> str:
    primary = totals(live.window_data["Primary day"])
    prior = totals(live.window_data["Prior day"])
    last_7 = totals(live.window_data["Last 7 full days"])
    urls = report_urls(live.report_date)
    spend_delta = fmt_signed(primary["cost"] - prior["cost"], fmt_money)
    clicks_delta = fmt_signed_count(primary["clicks"] - prior["clicks"])
    conversions_delta = fmt_signed_count(primary["conversions"] - prior["conversions"])
    cpa = fmt_cpa(primary["cost"], primary["conversions"])
    prior_cpa = fmt_cpa(prior["cost"], prior["conversions"])
    max_spend = max(totals(rows)["cost"] for rows in live.window_data.values())
    max_clicks = max(totals(rows)["clicks"] for rows in live.window_data.values())
    max_conversions = max(totals(rows)["conversions"] for rows in live.window_data.values())

    chart_lines = ["Window                  Spend       Clicks   Conv"]
    for label, rows in live.window_data.items():
        total = totals(rows)
        spend_bar = text_bar(total["cost"], max_spend, 12)
        click_bar = text_bar(total["clicks"], max_clicks, 8)
        conv_bar = text_bar(total["conversions"], max_conversions, 8)
        chart_lines.append(
            (
                f"{label[:22]:<22} {fmt_money(total['cost']):>9} {spend_bar:<12} "
                f"{fmt_int(total['clicks']):>5} {click_bar:<8} {fmt_float(total['conversions']):>5} {conv_bar}"
            ).rstrip()
        )

    return "\n".join(
        [
            f"*Google Ads report - {live.report_date.isoformat()}*",
            "",
            "*Topline*",
            f"- *Spend:* {fmt_money(primary['cost'])} ({spend_delta} vs prior day)",
            f"- *Clicks:* {fmt_int(primary['clicks'])} ({clicks_delta} vs prior day)",
            f"- *Conversions:* {fmt_float(primary['conversions'])} ({conversions_delta} vs prior day)",
            f"- *CPA:* {cpa} (prior day: {prior_cpa})",
            "",
            "*7-day view*",
            f"- {fmt_money(last_7['cost'])} spend, {fmt_int(last_7['clicks'])} clicks, {fmt_float(last_7['conversions'])} conversions, {fmt_cpa(last_7['cost'], last_7['conversions'])} CPA",
            "",
            "*Mini chart*",
            "```text",
            *chart_lines,
            "```",
            "",
            "*Campaign status*",
            f"- {campaign_status_note(live.window_data['Primary day'])}",
            "",
            "*Links*",
            f"- Report: {urls['report']}",
            f"- Chart: {urls['chart']}",
        ]
    )


def blocked_slack_summary(report_date: date) -> str:
    urls = report_urls(report_date)
    return "\n".join(
        [
            f"*Google Ads report - {report_date.isoformat()}*",
            "",
            "*Status:* Live Google Ads metrics were unavailable for this run.",
            "",
            "*What this means*",
            "- Spend, clicks, conversions, CPA, and campaign status were not refreshed.",
            "- The report records the data-access blocker and the intended comparison windows.",
            "",
            "*Links*",
            f"- Report: {urls['report']}",
            f"- Chart: {urls['chart']}",
        ]
    )


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


def build_report(live: LiveReport, env_path: Path | None) -> str:
    now = datetime.now().astimezone()
    urls = report_urls(live.report_date)
    primary_totals = totals(live.window_data["Primary day"])
    return f"""# Daily Ads Report - {live.report_date.isoformat()}

Source: Google Ads API REST via local `.env` credentials
Credential file: `{env_path or 'environment'}`
Generated: {now.isoformat(timespec='seconds')}
Account: {live.customer.get('descriptiveName')} / `{live.customer.get('id')}`
Timezone: {live.customer.get('timeZone')}
Primary window: {live.report_date.isoformat()}

## Executive Readout

Primary-day spend was {fmt_money(primary_totals['cost'])} on {fmt_int(primary_totals['clicks'])} clicks and {primary_totals['conversions']:.2f} conversions, for a blended CPA of {fmt_cpa(primary_totals['cost'], primary_totals['conversions'])}.

## Visual Summary

![Daily ads chart]({live.report_date.isoformat()}-daily-ads-chart.svg)

## Scorecard

{metric_table(live.window_data)}

## Campaigns

{campaign_table(live.window_data["Primary day"])}

## Search Terms

{search_term_table(live.search_terms)}

## Notes

- Campaign status in the table is the current API status; metrics are for the selected report window.
- Ohio and Indiana state clone campaigns were created paused, then enabled after review on 2026-04-24.
- Slack-ready summary: [{live.report_date.isoformat()} daily ads Slack summary]({live.report_date.isoformat()}-daily-ads-slack.md)
- Raw chart URL: {urls['chart']}
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
    report = ""
    slack_summary = ""
    chart_svg = ""
    try:
        access_token = refresh_access_token()
        customer = get_customer(access_token)
        report_date = date.fromisoformat(args.date) if args.date else previous_full_day(customer["timeZone"])
        live = collect_live_report(access_token, report_date)
        report = build_report(live, env_path)
        slack_summary = build_slack_summary(live)
        chart_svg = build_chart_svg(live)
    except Exception as exc:
        report_date = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
        report = blocked_report(report_date, exc, env_path)
        slack_summary = blocked_slack_summary(report_date)
        chart_svg = blocked_chart_svg(report_date)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{report_date.isoformat()}-daily-ads-report.md"
    summary_path = output_dir / f"{report_date.isoformat()}-daily-ads-slack.md"
    chart_path = output_dir / f"{report_date.isoformat()}-daily-ads-chart.svg"
    output_path.write_text(report)
    summary_path.write_text(slack_summary + "\n")
    chart_path.write_text(chart_svg)
    print(f"Saved {output_path}")
    print(f"Saved {summary_path}")
    print(f"Saved {chart_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
