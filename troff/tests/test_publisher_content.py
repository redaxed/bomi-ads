import subprocess

import pytest

from app.models import BlogPost, Platform, SocialPost
from app.services.publisher import PublishError, _ensure_clean_repo, _render_social_body, markdown_to_tiptap


def test_render_social_body_replaces_blog_url_placeholder() -> None:
    blog = BlogPost(
        package_id=1,
        title="Sample",
        slug="sample",
        markdown="# Sample",
        canonical_url="https://www.billwithbomi.com/blog/sample",
    )
    post = SocialPost(
        package_id=1,
        platform=Platform.linkedin,
        body="Read the full breakdown: {{BLOG_URL}}",
    )
    post.blog_post = blog

    rendered = _render_social_body(post)

    assert "{{BLOG_URL}}" not in rendered
    assert "https://www.billwithbomi.com/blog/sample" in rendered


def test_ensure_clean_repo_raises_for_dirty_repo(tmp_path) -> None:
    repo = tmp_path / "landing"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "troff@example.com"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Troff"], check=True, capture_output=True, text=True)
    tracked = repo / "tracked.txt"
    tracked.write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True, text=True)

    tracked.write_text("changed\n", encoding="utf-8")

    with pytest.raises(PublishError) as exc:
        _ensure_clean_repo(repo)

    assert exc.value.code == "landing_repo_dirty"


def test_markdown_to_tiptap_keeps_italics_links_and_numbered_lists() -> None:
    doc = markdown_to_tiptap(
        "\n".join(
            [
                "*Why this matters in practice*",
                "",
                "*Need help? [Bomi can help](https://www.billwithbomi.com).*",
                "",
                "## TL;DR",
                "- First point",
                "- Second point",
                "- Third point",
                "",
                "## Failure modes",
                "1. First miss",
                "2. Second miss",
            ]
        )
    )

    content = doc["content"]
    assert content[0]["type"] == "paragraph"
    assert content[0]["content"][0]["marks"][0]["type"] == "italic"
    assert content[2]["content"][1]["marks"][1]["type"] == "link"
    assert content[5]["type"] == "bulletList"
    assert content[8]["type"] == "orderedList"
