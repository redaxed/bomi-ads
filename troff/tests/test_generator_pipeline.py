import os
from unittest.mock import patch

from app.services.generator import (
    BLOG_URL_PLACEHOLDER,
    SurfaceDraft,
    assess_blog_readiness,
    extract_blog_insights,
    generate_blog_draft,
    generate_social_drafts,
)
from app.services.prompting import blog_generation_prompt, polymath_biller_style_guide, social_generation_prompt


AUTHOR = {
    "name": "Bomi Team",
    "tone_summary": "Practical and direct",
    "dos": ["Be concrete"],
    "donts": ["Be vague"],
    "cta_style": "Ask for one action",
    "writing_samples": ["Start with the pain point."],
}


def test_generate_blog_draft_fallback_returns_blog() -> None:
    with patch.dict(os.environ, {}, clear=True):
        blog = generate_blog_draft(
            topic="Credentialing workflow",
            keyword="credentialing workflow",
            audience="clinic owners",
            website_url="https://www.billwithbomi.com",
            source_url="",
            source_summary="",
            author_profile=AUTHOR,
        )

    assert blog.title
    assert blog.markdown.startswith("*")
    assert blog.slug
    readiness = assess_blog_readiness(
        title=blog.title,
        meta_description=blog.meta_description,
        markdown=blog.markdown,
        categories=blog.categories,
        faq=blog.faq,
    )
    assert readiness.passed_checks >= 10


def test_extract_blog_insights_fallback_is_bounded() -> None:
    markdown = "\n".join(
        [
            "# Sample",
            "## First idea",
            "## Second idea",
            "## Third idea",
            "## Fourth idea",
            "## Fifth idea",
            "## Sixth idea",
        ]
    )
    with patch.dict(os.environ, {}, clear=True):
        insights = extract_blog_insights("Topic", "Sample", markdown, AUTHOR)

    assert 3 <= len(insights) <= 5
    assert insights[0] == "First idea"
    assert "Sixth idea" not in insights


def test_generate_social_drafts_creates_one_per_insight_per_surface() -> None:
    insights = ["Insight one", "Insight two", "Insight three", "Insight four"]
    with patch.dict(os.environ, {}, clear=True):
        drafts = generate_social_drafts(
            blog_title="Sample Blog",
            blog_markdown="# Sample",
            insights=insights,
            author_profile=AUTHOR,
            surfaces=["linkedin", "reddit"],
        )

    assert len(drafts) == 8
    linkedin_sequences = [draft.sequence for draft in drafts if draft.platform == "linkedin"]
    reddit_sequences = [draft.sequence for draft in drafts if draft.platform == "reddit"]
    assert linkedin_sequences == [1, 2, 3, 4]
    assert reddit_sequences == [1, 2, 3, 4]
    assert all(BLOG_URL_PLACEHOLDER in draft.body for draft in drafts)
    assert all(not draft.body.startswith("Insight ") for draft in drafts)


def test_polymath_biller_style_guide_uses_defaults_and_topic() -> None:
    with patch.dict(os.environ, {}, clear=True):
        guide = polymath_biller_style_guide("Credentialing bottlenecks", "")

    assert 'You are "the Polymath Biller"' in guide
    assert "operators, founders, and clinicians who run a practice" in guide
    assert "Credentialing bottlenecks" in guide


def test_generation_prompts_include_voice_and_platform_rules() -> None:
    with patch.dict(os.environ, {}, clear=True):
        blog_prompt = blog_generation_prompt(
            topic="Credentialing bottlenecks",
            keyword="credentialing bottlenecks",
            audience="practice operators",
            website_url="https://www.billwithbomi.com",
            source_url="",
            source_summary="",
            author_prompt="Author: Bomi Team",
        )
        social_prompt = social_generation_prompt(
            blog_title="Credentialing bottlenecks",
            blog_markdown="# Sample",
            insights=["One concrete operational insight"],
            author_prompt="Author: Bomi Team",
            surfaces=["linkedin", "reddit"],
            blog_url_placeholder=BLOG_URL_PLACEHOLDER,
        )

    assert "TL;DR" in blog_prompt
    assert "Biller's Corner" in blog_prompt
    assert "Do not repeat the title as an H1 inside the markdown body" in blog_prompt
    assert "Use simple markdown only" in blog_prompt
    assert "Do not invent sources" in blog_prompt
    assert "sound like a sharp human operator" in social_prompt
    assert "0-2 tasteful emojis" in social_prompt
    assert "highest-priority style signal" in social_prompt
    assert BLOG_URL_PLACEHOLDER in social_prompt
    assert "LinkedIn" in social_prompt
    assert "Reddit" in social_prompt


def test_generate_social_drafts_uses_targeted_model_calls_for_missing_posts() -> None:
    from app.services.generator import _has_emoji

    insights = ["Insight one", "Insight two", "Insight three"]
    batch_drafts = [
        SurfaceDraft(platform="linkedin", sequence=1, body="batch linkedin 1"),
        SurfaceDraft(platform="reddit", sequence=1, body="batch reddit 1", reddit_title="batch reddit 1"),
    ]

    def _targeted(*, platform: str, sequence: int, **_: object) -> SurfaceDraft:
        return SurfaceDraft(
            platform=platform,
            sequence=sequence,
            body=f"targeted {platform} {sequence}",
            reddit_title=f"targeted reddit {sequence}" if platform == "reddit" else "",
        )

    with patch("app.services.generator._openai_social_drafts", return_value=batch_drafts), patch(
        "app.services.generator._openai_single_social_draft",
        side_effect=_targeted,
    ):
        drafts = generate_social_drafts(
            blog_title="Sample Blog",
            blog_markdown="# Sample",
            insights=insights,
            author_profile=AUTHOR,
            surfaces=["linkedin", "reddit"],
        )

    drafts_by_key = {(draft.platform, draft.sequence): draft for draft in drafts}
    assert drafts_by_key[("linkedin", 1)].body.endswith("batch linkedin 1")
    assert drafts_by_key[("reddit", 1)].body == "batch reddit 1"
    assert drafts_by_key[("linkedin", 2)].body == "targeted linkedin 2"
    assert drafts_by_key[("reddit", 2)].body == "targeted reddit 2"
    assert drafts_by_key[("linkedin", 3)].body.endswith("targeted linkedin 3")
    assert drafts_by_key[("reddit", 3)].body == "targeted reddit 3"
    assert _has_emoji(drafts_by_key[("linkedin", 1)].body)
    assert _has_emoji(drafts_by_key[("linkedin", 3)].body)


def test_author_prompt_prioritizes_voice_rules_and_samples() -> None:
    from app.services.generator import _author_prompt

    prompt = _author_prompt(
        {
            "name": "Bomi Team",
            "tone_summary": "Calm, sharp, and lightly witty",
            "dos": ["Use concrete verbs", "Name tradeoffs"],
            "donts": ["Sound like thought leadership slop"],
            "cta_style": "Give one clear next step",
            "writing_samples": ["We start with the bottleneck, not the brand story.", "This is where the spreadsheet starts to develop opinions."],
            "voice_prompt": "Write like an operator who has actually run the process.",
        }
    )

    assert "high-priority style constraint" in prompt
    assert "Dedicated voice prompt:" in prompt
    assert "Do rules:" in prompt
    assert "Don't rules:" in prompt
    assert "Writing samples to borrow rhythm from" in prompt


def test_assess_blog_readiness_flags_missing_landing_structure() -> None:
    readiness = assess_blog_readiness(
        title="Thin Draft",
        meta_description="Too short",
        markdown="# Thin Draft\n## TL;DR\n- One bullet only",
        categories=[],
        faq=[],
        source_url="https://example.com",
    )

    assert readiness.is_publish_ready is False
    assert readiness.passed_checks < readiness.total_checks
    failed_labels = {item.label for item in readiness.failed_items}
    assert "Title lives in metadata, not the body" in failed_labels
    assert "FAQ has 2-4 entries" in failed_labels
