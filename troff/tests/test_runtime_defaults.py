from pathlib import Path

from app.db import _ensure_sqlite_parent_dir
from app.services.media import STATIC_ROOT, build_asset_url_for_point


def test_sqlite_parent_directory_is_created(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "troff.db"

    _ensure_sqlite_parent_dir(f"sqlite:///{db_path}")

    assert db_path.parent.exists()


def test_local_media_cards_return_served_static_url(monkeypatch) -> None:
    output_dir = STATIC_ROOT / "generated" / "test-cards"
    monkeypatch.setenv("MEDIA_PROVIDER", "local")
    monkeypatch.delenv("PUBLIC_MEDIA_BASE_URL", raising=False)
    monkeypatch.setenv("MEDIA_CARD_OUTPUT_DIR", str(output_dir))

    asset_url = build_asset_url_for_point("Credentialing bottlenecks need a named owner.")

    assert asset_url.startswith("/static/generated/test-cards/card-")
    assert asset_url.endswith(".png")
    assert (STATIC_ROOT / asset_url.removeprefix("/static/")).exists()
