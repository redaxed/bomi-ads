#!/usr/bin/env python3
"""Build Bomi ad landing URLs that satisfy landing attribution capture."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


LANDING_REQUIRED_UTM_PARAMS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_audience",
    "utm_id",
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"


def _query_string(params: dict[str, str]) -> str:
    return urlencode(params, safe="{}")


def _with_query_params(url: str, params: dict[str, str]) -> str:
    parsed = urlsplit(url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    existing.update({key: value for key, value in params.items() if value})
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            _query_string(existing),
            parsed.fragment,
        )
    )


def missing_landing_tracking_fields(url: str) -> list[str]:
    params = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    return [key for key in LANDING_REQUIRED_UTM_PARAMS if not params.get(key)]


def build_ad_tracking_url(
    base_url: str,
    *,
    source: str,
    medium: str,
    campaign: str,
    content: str,
    audience: str,
    utm_id: str | None = None,
    term: str | None = None,
) -> str:
    params = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": campaign,
        "utm_content": content,
        "utm_audience": audience,
        "utm_id": utm_id or campaign,
    }
    if term:
        params["utm_term"] = term

    url = _with_query_params(base_url, params)
    missing = missing_landing_tracking_fields(url)
    if missing:
        raise ValueError(f"Tracking URL is missing fields: {', '.join(missing)}")
    return url


def build_google_demand_gen_url(
    base_url: str,
    *,
    campaign: str,
    content: str,
    audience: str,
) -> str:
    return build_ad_tracking_url(
        base_url,
        source="google",
        medium="paid_demandgen",
        campaign=campaign,
        content=f"{slugify(content)}_ad_{{creative}}",
        audience=audience,
        utm_id="{campaignid}",
    )


def build_google_search_url(
    base_url: str,
    *,
    campaign: str,
    content: str,
    audience: str,
) -> str:
    return build_ad_tracking_url(
        base_url,
        source="google",
        medium="paid_search",
        campaign=campaign,
        content=f"{slugify(content)}_ad_{{creative}}",
        audience=audience,
        utm_id="{campaignid}",
        term="{keyword}",
    )


def build_meta_feed_url(
    base_url: str,
    *,
    campaign: str,
    audience: str,
) -> str:
    return build_ad_tracking_url(
        base_url,
        source="meta",
        medium="paid_social",
        campaign=campaign,
        content="facebook_feed",
        audience=audience,
        utm_id=campaign,
    )
