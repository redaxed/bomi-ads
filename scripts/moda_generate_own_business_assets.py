#!/usr/bin/env python3
"""
Generate Bomi "Own your business" ad assets through Moda.

This reuses the EHR asset generator helpers, but keeps this campaign's prompt,
folder, filenames, and idempotency keys separate. By default it creates one
lite square master in Moda and derives the other platform sizes locally.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


BASE_PATH = Path(__file__).with_name("moda_generate_ehr_vs_bomi_assets.py")
spec = importlib.util.spec_from_file_location("bomi_moda_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
assert spec.loader is not None
spec.loader.exec_module(base)


base.OUTPUT_DIR = Path("assets/own_business_handle_insurance_2026-05-14")
base.CAMPAIGN_SLUG = "own_business_handle_insurance_pooled_states"
base.SQUARE_SPEC = base.AssetSpec(
    "square",
    "Square Feed 1:1",
    1080,
    1080,
    "own-business-handle-insurance-square-1080x1080.png",
)
base.LANDSCAPE_SPEC = base.AssetSpec(
    "landscape",
    "Landscape Demand Gen 1.91:1",
    1200,
    628,
    "own-business-handle-insurance-landscape-1200x628.png",
)
base.PORTRAIT_SPEC = base.AssetSpec(
    "portrait",
    "Portrait Demand Gen Padded",
    1080,
    1920,
    "own-business-handle-insurance-portrait-padded-1080x1920.png",
)
base.ALL_SPECS = [base.SQUARE_SPEC, base.LANDSCAPE_SPEC, base.PORTRAIT_SPEC]


def creative_prompt(spec: Any) -> str:
    return f"""
Create a polished static digital ad for Bomi Health / BillWithBomi, a billing
and credentialing service for therapists and private practices.

Ad format: {spec.label}, exact canvas size {spec.width}x{spec.height}. Make it
feel warm, calm, trustworthy, premium, and highly readable on mobile.

Core visual idea: show a confident therapist/private practice owner standing in
their own welcoming modern therapy office with natural light, plants, a desk,
soft seating, and calming decor. The therapist should look relaxed, relieved,
and empowered, representing ownership and independence. Use realistic people
and realistic photography style, not cartoons or generic corporate stock.

In the background or side of the composition, show abstract insurance admin
work being neatly handled by Bomi: claim forms, credentialing checklists,
eligibility verification, EOBs, and payer paperwork flowing into a clean digital
dashboard or being organized by a friendly support team. The admin side should
feel organized and handled, not chaotic or scary. Avoid hospital settings,
scary medical imagery, clutter, exaggerated stress, fake guarantees, and
insurance-carrier logos.

Visible text must be exactly:
Headline: "Own your business. Let us handle insurance."
Subheadline: "Billing & credentialing for therapists"
Small badge: "Flat 4% of collections"
CTA button: "Schedule a free consultation"

Brand direction: clean modern healthcare startup aesthetic with soft neutral
backgrounds, calming green/blue accents, deep navy text, subtle shadows, and
clear negative space for the text. Use the attached Bomi logo as subtle
branding. Keep all text crisp, correctly spelled, and within safe margins.
""".strip()


def start_task(
    spec: Any,
    logo_file_id: str,
    model_tier: str,
    brand_kit_id: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": creative_prompt(spec),
        "canvas_name": f"Bomi Own Your Business - {spec.label} - 2026-05-14",
        "idempotency_key": (
            f"bomi-social:{base.CAMPAIGN_SLUG}:{spec.key}:2026-05-14:{model_tier}:v1"
        ),
        "attachments": [
            {
                "file_id": logo_file_id,
                "role": "asset",
                "label": "Bomi Health logo",
            }
        ],
        "format": {
            "category": "social",
            "width": spec.width,
            "height": spec.height,
            "label": spec.label,
        },
        "model_tier": model_tier,
    }
    if brand_kit_id:
        payload["brand_kit_id"] = brand_kit_id
    else:
        payload["skip_brand_kit"] = True
    return base.api_json("POST", "/tasks", payload)


base.creative_prompt = creative_prompt
base.start_task = start_task


if __name__ == "__main__":
    raise SystemExit(base.main())
