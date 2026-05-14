#!/usr/bin/env python3
"""
Generate Bomi EHR-vs-expert-team ad assets through the Moda REST API.

By default this creates one square feed master through Moda, then derives the
landscape and portrait platform variants locally to conserve Moda credits. It
does not create or activate ads.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODA_BASE = "https://api.moda.app/v1"
MODA_VERSION = "2026-05-01"
SOURCE_ENV = Path("/Users/dax/bomi/bomi-ads/.env")
OUTPUT_DIR = Path("assets/ehr_vs_bomi_tax_software_2026-05-14")
LOGO_PATH = Path("/Users/dax/bomi/landing/public/logo-with-name.png")
CAMPAIGN_SLUG = "ehr_vs_bomi_pooled_states"


class ModaError(RuntimeError):
    pass


@dataclass(frozen=True)
class AssetSpec:
    key: str
    label: str
    width: int
    height: int
    filename: str


SQUARE_SPEC = AssetSpec("square", "Square Feed 1:1", 1080, 1080, "ehr-vs-bomi-square-1080x1080.png")
LANDSCAPE_SPEC = AssetSpec(
    "landscape",
    "Landscape Demand Gen 1.91:1",
    1200,
    628,
    "ehr-vs-bomi-landscape-1200x628.png",
)
PORTRAIT_SPEC = AssetSpec(
    "portrait",
    "Portrait Demand Gen Padded",
    1080,
    1920,
    "ehr-vs-bomi-portrait-padded-1080x1920.png",
)
ALL_SPECS = [SQUARE_SPEC, LANDSCAPE_SPEC, PORTRAIT_SPEC]


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
    modi_key = os.getenv("MODI_APP_KEY")
    if modi_key and not os.getenv("MODA_API_KEY"):
        os.environ["MODA_API_KEY"] = modi_key


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ModaError(f"Missing required environment variable: {name}")
    return value.strip()


def headers(content_type: str | None = "application/json") -> dict[str, str]:
    result = {
        "Authorization": f"Bearer {env('MODA_API_KEY')}",
        "Moda-Version": MODA_VERSION,
    }
    if content_type:
        result["Content-Type"] = content_type
    return result


def api_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    content_type: str | None = "application/json",
    raw_data: bytes | None = None,
) -> Any:
    data = raw_data
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{MODA_BASE}{path}",
        data=data,
        headers=headers(content_type),
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ModaError(f"Moda API error {exc.code} for {path}:\n{body}") from exc


def multipart_upload(path: Path) -> dict[str, Any]:
    boundary = f"----bomi-moda-{int(time.time() * 1000)}"
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        (
            'Content-Disposition: form-data; name="file"; '
            f'filename="{path.name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode()
    )
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    return api_json(
        "POST",
        "/uploads",
        content_type=f"multipart/form-data; boundary={boundary}",
        raw_data=bytes(body),
    )


def creative_prompt(spec: AssetSpec) -> str:
    return f"""
Create a polished static image ad for Bomi Health / BillWithBomi, a billing and
credentialing service for therapists.

Ad format: {spec.label}, exact canvas size {spec.width}x{spec.height}. Make it
feel modern, trustworthy, calming, premium, and highly readable on mobile.

Core creative idea: split-screen comparison.

Left side: "Your EHR is like DIY tax software." Show a solo therapist at a desk
trying to manage insurance billing inside a generic EHR-style software screen.
The screen should feel like generic DIY tax software: checkboxes, forms,
progress bars, and confusing claim tasks. Add subtle visual stress: claim
denial icons, "missing info", "payer follow-up", "eligibility check",
"denied claim", "unpaid balance". Do not use the TurboTax name, logo, colors,
branding, UI, or trade dress.

Right side: "BillWithBomi is like having a CPA." Show the same therapist looking
relieved while a friendly expert billing partner handles the complexity. Visual
cues: clean claims dashboard, green checkmarks, paid claims, credentialing
status complete, revenue collected, benefits verified.

Primary headline, large and centered across the top exactly:
"Your EHR is like DIY tax software.
BillWithBomi is like having a CPA."

Secondary copy below exactly:
"Your EHR gives you the tools. Bomi gives you the expert billing team."

Small proof/positioning chips near the bottom exactly:
"Billing + Credentialing for Therapists"
"Flat 4% of collections"
"No new EHR. No learning curve."

CTA button exactly:
"Book a Free Consultation"

Brand direction: clean medical-fintech look with soft off-white background,
deep navy text, teal/blue accents, rounded cards, subtle shadows, lots of
whitespace. Use the attached Bomi logo as an asset. Avoid clutter. Avoid
stock-photo cheesiness. Keep all visible text crisp, correctly spelled, and
within safe margins.
""".strip()


def start_task(
    spec: AssetSpec,
    logo_file_id: str,
    model_tier: str,
    brand_kit_id: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": creative_prompt(spec),
        "canvas_name": f"Bomi EHR vs Expert Billing Team - {spec.label} - 2026-05-14",
        "idempotency_key": f"bomi-social:{CAMPAIGN_SLUG}:{spec.key}:2026-05-14:{model_tier}:v2",
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
    return api_json(
        "POST",
        "/tasks",
        payload,
    )


def poll_task(task_id: str) -> dict[str, Any]:
    while True:
        task = api_json("GET", f"/tasks/{task_id}")
        status = task.get("status")
        print(f"Moda task {task_id}: {status}")
        if status in {"succeeded", "failed", "cancelled"}:
            return task
        retry_ms = task.get("retry_after_ms") or 5000
        time.sleep(max(2, min(20, retry_ms / 1000)))


def export_canvas(canvas_id: str, spec: AssetSpec) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "format": "png",
            "page_number": 1,
            "pixel_ratio": 1,
            "wait": "true",
        }
    )
    result = api_json("POST", f"/canvases/{canvas_id}/export?{query}")
    while result.get("status") == "in_progress":
        retry_seconds = result.get("retry_after_seconds") or 5
        time.sleep(max(2, min(20, int(retry_seconds))))
        status_query = urllib.parse.urlencode({"task_id": result["task_id"]})
        result = api_json("GET", f"/canvases/{canvas_id}/export-status?{status_query}")
    if result.get("status") not in {"completed", "succeeded"} or not result.get("url"):
        raise ModaError(f"Export failed for {canvas_id}: {json.dumps(result, indent=2)}")
    return result


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ModaError(f"{path} is not a PNG file")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def ensure_png(path: Path) -> None:
    data = path.read_bytes()
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return
    temp_path = path.with_suffix(".converted.png")
    subprocess.run(
        ["sips", "-s", "format", "png", str(path), "--out", str(temp_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    temp_path.replace(path)


def verify_png(path: Path, spec: AssetSpec) -> dict[str, Any]:
    ensure_png(path)
    width, height = png_size(path)
    if (width, height) != (spec.width, spec.height):
        raise ModaError(f"{path} has dimensions {width}x{height}, expected {spec.width}x{spec.height}")
    file_output = subprocess.check_output(["file", str(path)], text=True).strip()
    return {"path": str(path), "width": width, "height": height, "file": file_output}


def derive_from_square(square_path: Path) -> dict[str, Any]:
    landscape_path = OUTPUT_DIR / LANDSCAPE_SPEC.filename
    portrait_path = OUTPUT_DIR / PORTRAIT_SPEC.filename
    temp_scaled = OUTPUT_DIR / "_square-628-temp.png"
    subprocess.run(
        [
            "sips",
            "-z",
            "628",
            "628",
            str(square_path),
            "--out",
            str(temp_scaled),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    subprocess.run(
        [
            "sips",
            "--padToHeightWidth",
            "628",
            "1200",
            "--padColor",
            "f8f7f2",
            str(temp_scaled),
            "--out",
            str(landscape_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    subprocess.run(
        [
            "sips",
            "--padToHeightWidth",
            "1920",
            "1080",
            "--padColor",
            "f8f7f2",
            str(square_path),
            "--out",
            str(portrait_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    temp_scaled.unlink(missing_ok=True)
    return {
        "landscape": verify_png(landscape_path, LANDSCAPE_SPEC),
        "portrait": verify_png(portrait_path, PORTRAIT_SPEC),
    }


def scrub_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task.get("id"),
        "kind": task.get("kind"),
        "status": task.get("status"),
        "created_at": task.get("created_at"),
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "result": task.get("result"),
        "credits": task.get("credits"),
        "error": task.get("error"),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-tier",
        choices=["lite", "standard", "pro"],
        default="lite",
        help="Moda model tier. Defaults to lite to conserve credits.",
    )
    parser.add_argument(
        "--full-moda-variants",
        action="store_true",
        help="Generate square and landscape separately in Moda instead of deriving variants locally.",
    )
    args = parser.parse_args()

    load_env()
    if not LOGO_PATH.exists():
        raise ModaError(f"Missing Bomi logo asset: {LOGO_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    credits = api_json("GET", "/credits")
    brand_kits = api_json("GET", "/brand-kits?limit=20")
    remaining = int(credits.get("credits_remaining") or 0)
    generation_specs = [SQUARE_SPEC, LANDSCAPE_SPEC] if args.full_moda_variants else [SQUARE_SPEC]
    if remaining < len(generation_specs):
        raise ModaError(f"Moda credits remaining ({remaining}) are below required Moda generations ({len(generation_specs)})")
    default_brand_kit = next(
        (item for item in brand_kits.get("data", []) if item.get("is_default")),
        None,
    )
    print(f"Moda credits remaining: {remaining}")
    print(f"Moda brand kits available: {len(brand_kits.get('data', []))}")
    if default_brand_kit:
        print(f"Using Moda brand kit: {default_brand_kit.get('title')} ({default_brand_kit.get('id')})")

    logo_upload = multipart_upload(LOGO_PATH)
    print(f"Uploaded logo file: {logo_upload.get('id')} duplicate={logo_upload.get('was_duplicate')}")

    metadata: dict[str, Any] = {
        "campaign_slug": CAMPAIGN_SLUG,
        "model_tier": args.model_tier,
        "generation_mode": "full_moda_variants" if args.full_moda_variants else "single_moda_square_with_local_derivatives",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "credits_preflight": credits,
        "brand_kits_count": len(brand_kits.get("data", [])),
        "brand_kit_id": default_brand_kit.get("id") if default_brand_kit else None,
        "logo_upload": {
            "id": logo_upload.get("id"),
            "filename": logo_upload.get("filename"),
            "mime_type": logo_upload.get("mime_type"),
            "size_bytes": logo_upload.get("size_bytes"),
            "was_duplicate": logo_upload.get("was_duplicate"),
        },
        "assets": {},
    }

    for spec in generation_specs:
        task = start_task(
            spec,
            logo_upload["id"],
            args.model_tier,
            default_brand_kit.get("id") if default_brand_kit else None,
        )
        completed = poll_task(task["id"])
        if completed.get("status") != "succeeded":
            raise ModaError(f"Moda task failed for {spec.key}: {json.dumps(completed.get('error'), indent=2)}")
        canvas_id = completed["result"]["canvas_id"]
        try:
            pages = api_json("GET", f"/canvases/{canvas_id}/pages")
        except ModaError as exc:
            pages = {"warning": "Moda pages read failed; continuing with export", "error": str(exc)}
        export = export_canvas(canvas_id, spec)
        output_path = OUTPUT_DIR / spec.filename
        download(export["url"], output_path)
        verification = verify_png(output_path, spec)
        metadata["assets"][spec.key] = {
            "spec": spec.__dict__,
            "task": scrub_task(completed),
            "pages": pages,
            "export": {
                "status": export.get("status"),
                "canvas_id": export.get("canvas_id"),
                "canvas_url": export.get("canvas_url"),
                "format": export.get("format"),
                "total_pages": export.get("total_pages"),
            },
            "verification": verification,
        }
        print(f"Saved {spec.key}: {output_path} ({spec.width}x{spec.height})")

    if not args.full_moda_variants:
        derived = derive_from_square(OUTPUT_DIR / SQUARE_SPEC.filename)
        metadata["assets"]["landscape"] = {
            "spec": LANDSCAPE_SPEC.__dict__,
            "derived_from": SQUARE_SPEC.filename,
            "verification": derived["landscape"],
        }
        metadata["assets"]["portrait"] = {
            "spec": PORTRAIT_SPEC.__dict__,
            "derived_from": SQUARE_SPEC.filename,
            "verification": derived["portrait"],
        }
        print(f"Derived landscape: {OUTPUT_DIR / LANDSCAPE_SPEC.filename}")
        print(f"Derived portrait: {OUTPUT_DIR / PORTRAIT_SPEC.filename}")

    (OUTPUT_DIR / "moda_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    print(f"Metadata written: {OUTPUT_DIR / 'moda_metadata.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ModaError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
