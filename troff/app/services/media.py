from __future__ import annotations

import os
import textwrap
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from google.cloud import storage
except Exception:  # pragma: no cover
    storage = None


class MediaError(RuntimeError):
    pass


def _card_style() -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    bg_hex = os.getenv("CARD_BG_HEX", "#0F172A")
    fg_hex = os.getenv("CARD_FG_HEX", "#F8FAFC")

    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        if len(value) != 6:
            return (15, 23, 42)
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    return _hex_to_rgb(bg_hex), _hex_to_rgb(fg_hex)


def render_text_card(text: str, output_dir: str = "/data/generated/cards") -> Path:
    bg_color, fg_color = _card_style()
    width = int(os.getenv("CARD_WIDTH", "1080"))
    height = int(os.getenv("CARD_HEIGHT", "1080"))

    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    wrapped = textwrap.fill(text.strip(), width=34)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = max(40, (width - text_width) // 2)
    y = max(40, (height - text_height) // 2)
    draw.multiline_text((x, y), wrapped, fill=fg_color, font=font, spacing=10, align="left")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"card-{uuid.uuid4().hex}.png"
    image.save(path, format="PNG")
    return path


def upload_to_gcs(path: Path, object_prefix: str = "troff/cards") -> str:
    provider = os.getenv("MEDIA_PROVIDER", "gcs").strip().lower()
    if provider != "gcs":
        return ""

    if storage is None:
        raise MediaError("google-cloud-storage is not installed.")

    bucket_name = os.getenv("GCS_BUCKET", "").strip()
    if not bucket_name:
        raise MediaError("GCS_BUCKET is not configured.")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    key = f"{object_prefix.rstrip('/')}/{path.name}"
    blob = bucket.blob(key)
    blob.upload_from_filename(str(path), content_type="image/png")

    base = os.getenv("GCS_PUBLIC_BASE_URL", "https://storage.googleapis.com").rstrip("/")
    return f"{base}/{bucket_name}/{key}"


def build_asset_url_for_point(point_text: str) -> str:
    card = render_text_card(point_text)
    url = upload_to_gcs(card)
    if url:
        return url

    public_media_base = os.getenv("PUBLIC_MEDIA_BASE_URL", "").rstrip("/")
    if public_media_base:
        return f"{public_media_base}/{card.name}"
    return ""
