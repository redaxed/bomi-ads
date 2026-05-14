#!/usr/bin/env python3
"""
Create a paused Meta/Facebook Feed ad for the pooled "Own your business" test.

This imports the existing pooled Meta helper so the targeting, paused-first
creation, and readback behavior stay consistent with the prior test.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


BASE_PATH = Path(__file__).with_name("meta_create_ehr_vs_bomi_pooled.py")
spec = importlib.util.spec_from_file_location("bomi_meta_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
assert spec.loader is not None
spec.loader.exec_module(base)


base.OUTPUT_DIR = Path("assets/own_business_handle_insurance_2026-05-14")
base.SQUARE_IMAGE = base.OUTPUT_DIR / "own-business-handle-insurance-square-1080x1080.png"
base.INFO_PATH = base.OUTPUT_DIR / "INFO.md"

base.CAMPAIGN_NAME = "Bomi Own Your Business - Leads - 2026-05-14"
base.AD_SET_NAME = "Pooled IL OH IN NM therapist operators - Own Business - Facebook Feed - 2026-05-14"
base.CREATIVE_NAME = "Bomi Own Your Business - Facebook Feed - 2026-05-14"
base.AD_NAME = "Bomi Own Your Business - Facebook Feed - 2026-05-14"
base.FINAL_URL = (
    "https://www.billwithbomi.com/"
    "?utm_source=meta&utm_medium=paid_social"
    "&utm_campaign=own_business_handle_insurance_pooled_states&utm_content=facebook_feed"
)
base.AD_MESSAGE = (
    "Own your business. Let Bomi handle insurance billing and credentialing for "
    "your therapy practice. Flat 4% of collections."
)
base.AD_HEADLINE = "Own Your Business"
base.AD_DESCRIPTION = "Schedule a free consultation."


def write_info(ids: dict[str, str], readback_data: dict[str, Any]) -> None:
    asset_sha = hashlib.sha256(base.SQUARE_IMAGE.read_bytes()).hexdigest()
    info = f"""# Bomi Own Your Business Facebook Feed Ad

Created on 2026-05-14 as a paused pooled-state Meta/Facebook Feed test.

## IDs

- Campaign: `{ids['campaign_id']}`
- Ad set: `{ids['ad_set_id']}`
- Creative: `{ids['creative_id']}`
- Ad: `{ids['ad_id']}`
- Image hash: `{ids['image_hash']}`

## Budget And Status

- Daily budget: `2000` cents = `$20/day`
- Creation status: paused only; no activation performed
- Latest readback campaign status: `{readback_data['campaign'].get('status')}` / effective `{readback_data['campaign'].get('effective_status')}`
- Latest readback ad set status: `{readback_data['ad_set'].get('status')}` / effective `{readback_data['ad_set'].get('effective_status')}`
- Latest readback ad status: `{readback_data['ad'].get('status')}` / effective `{readback_data['ad'].get('effective_status')}`

## Asset

- Square image: `{base.SQUARE_IMAGE}`
- SHA256: `{asset_sha}`

## Copy

Primary text:

```text
{base.AD_MESSAGE}
```

Headline:

```text
{base.AD_HEADLINE}
```

Description:

```text
{base.AD_DESCRIPTION}
```

CTA: `BOOK_NOW`

Final URL:

```text
{base.FINAL_URL}
```

## Targeting

- Placement: Facebook Feed only
- Regions: Illinois, Ohio, Indiana, New Mexico
- Age: `25-65+`
- Audience: broad therapist/practice-operator flexible spec, Advantage audience expansion enabled

## Readback

```json
{json.dumps(readback_data, indent=2, sort_keys=True)}
```

## Safety Notes

- Objects were created paused first and were not activated.
- Do not activate without explicit user approval.
- Never commit or print Meta, Google Ads, or Moda credentials.
"""
    base.INFO_PATH.write_text(info)


base.write_info = write_info


if __name__ == "__main__":
    raise SystemExit(base.main())
