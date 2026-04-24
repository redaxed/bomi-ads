from __future__ import annotations

import os

from .models import Platform

DEFAULT_ENABLED_SURFACES = [Platform.blog, Platform.linkedin, Platform.reddit]
CANONICAL_SURFACE_ORDER = [
    Platform.blog,
    Platform.linkedin,
    Platform.facebook,
    Platform.instagram,
    Platform.tiktok,
    Platform.reddit,
]
DEFAULT_MEDIA_CARD_SURFACES = [Platform.linkedin, Platform.facebook, Platform.instagram, Platform.tiktok]


def enabled_surfaces(include_blog: bool = True) -> list[Platform]:
    raw = os.getenv("ENABLED_SURFACES", "blog,linkedin,reddit")
    requested = {part.strip().lower() for part in raw.split(",") if part.strip()}

    selected: list[Platform] = []
    for platform in CANONICAL_SURFACE_ORDER:
        if platform == Platform.blog:
            continue
        if platform.value in requested:
            selected.append(platform)

    if not selected:
        selected = [platform for platform in DEFAULT_ENABLED_SURFACES if platform != Platform.blog]

    if include_blog:
        return [Platform.blog, *selected]
    return selected


def enabled_surface_values(include_blog: bool = True) -> list[str]:
    return [platform.value for platform in enabled_surfaces(include_blog=include_blog)]


def scheduler_enabled() -> bool:
    return os.getenv("ENABLE_SCHEDULER", "false").strip().lower() in {"1", "true", "yes", "on"}


def media_cards_enabled() -> bool:
    return os.getenv("ENABLE_MEDIA_CARDS", "false").strip().lower() in {"1", "true", "yes", "on"}


def media_card_surfaces() -> list[Platform]:
    raw = os.getenv("MEDIA_CARD_SURFACES", "linkedin,facebook,instagram,tiktok")
    requested = {part.strip().lower() for part in raw.split(",") if part.strip()}

    selected: list[Platform] = []
    for platform in CANONICAL_SURFACE_ORDER:
        if platform == Platform.blog:
            continue
        if platform.value in requested:
            selected.append(platform)

    return selected or DEFAULT_MEDIA_CARD_SURFACES


def media_card_surface_values() -> list[str]:
    return [platform.value for platform in media_card_surfaces()]
