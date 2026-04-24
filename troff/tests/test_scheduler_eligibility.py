from app.models import BlogPost, ContentStatus, Platform, SocialPost
from app.services.scheduler import _social_eligibility


def test_linkedin_is_not_blocked_by_legacy_blog_score() -> None:
    blog = BlogPost(
        package_id=1,
        title="Sample",
        slug="sample",
        markdown="*Subtitle*\n\n## TL;DR\n- One\n- Two\n- Three",
        seo_score=10,
        live_verified_at=None,
    )
    post = SocialPost(
        package_id=1,
        blog_post_id=1,
        platform=Platform.linkedin,
        body="LinkedIn body",
        status=ContentStatus.approved,
        requires_blog_live=False,
    )
    post.blog_post = blog

    eligible, reason = _social_eligibility(post)

    assert eligible is True
    assert reason == ""
