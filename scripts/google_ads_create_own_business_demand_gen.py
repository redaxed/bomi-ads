#!/usr/bin/env python3
"""
Create a paused Google Demand Gen campaign for the pooled "Own your business" test.

Validates by default. Use --apply to create paused Google Ads objects. This
wrapper reuses the existing Demand Gen helper and only swaps campaign-specific
assets, copy, audience signals, and naming.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


BASE_PATH = Path(__file__).with_name("google_ads_create_ehr_vs_bomi_demand_gen.py")
spec = importlib.util.spec_from_file_location("bomi_google_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
assert spec.loader is not None
spec.loader.exec_module(base)


base.OUTPUT_DIR = Path("assets/own_business_handle_insurance_2026-05-14")
base.SQUARE_IMAGE = base.OUTPUT_DIR / "own-business-handle-insurance-square-1080x1080.png"
base.LANDSCAPE_IMAGE = base.OUTPUT_DIR / "own-business-handle-insurance-landscape-1200x628.png"
base.PORTRAIT_IMAGE = base.OUTPUT_DIR / "own-business-handle-insurance-portrait-padded-1080x1920.png"
base.READBACK_PATH = base.OUTPUT_DIR / "google_ads_readback.json"

base.CAMPAIGN_NAME = "Bomi Own Your Business - Demand Gen - 2026-05-14"
base.AD_GROUP_NAME = "Pooled state therapist practice-owner audience"
base.AD_NAME = "Bomi Own Your Business - pooled states"
base.FINAL_URL = (
    "https://www.billwithbomi.com/"
    "?utm_source=google&utm_medium=paid_demandgen"
    "&utm_campaign=own_business_handle_insurance_pooled_states&utm_content=square_landscape"
)

base.CUSTOM_AUDIENCE_TERMS = [
    "therapy private practice",
    "start a therapy practice",
    "therapist business owner",
    "private practice therapist billing",
    "insurance billing for therapists",
    "credentialing for therapists",
    "therapy practice credentialing",
    "therapy practice insurance claims",
    "eligibility verification therapy",
    "EOB therapist billing",
    "payer paperwork therapy practice",
    "SimplePractice billing help",
    "TherapyNotes billing service",
    "practice manager",
    "medical office manager",
    "billing manager",
    "credentialing specialist",
]

base.HEADLINES = [
    "Own Your Business",
    "Let Us Handle Insurance",
    "Billing + Credentialing",
    "Flat 4% Collections",
    "Schedule Free Consult",
]

base.DESCRIPTIONS = [
    "Own and grow your practice while Bomi handles insurance complexity.",
    "Billing and credentialing for therapists at flat 4% of collections.",
    "Claims, eligibility, payer paperwork, and credentialing support.",
]


def custom_audience_operation(stamp: int) -> dict:
    return {
        "create": {
            "name": f"Bomi Own Your Business Signals {stamp}",
            "description": "Bomi pooled-state therapist practice-owner and insurance admin signals.",
            "type": "AUTO",
            "members": [
                {"memberType": "KEYWORD", "keyword": term}
                for term in base.CUSTOM_AUDIENCE_TERMS
            ],
        }
    }


def audience_operation(custom_audience_resource: str, stamp: int) -> dict:
    return {
        "create": {
            "name": f"Bomi Own Your Business Audience {stamp}",
            "description": "Pooled-state audience for the Own Your Business Demand Gen test.",
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


base.custom_audience_operation = custom_audience_operation
base.audience_operation = audience_operation


if __name__ == "__main__":
    raise SystemExit(base.main())
