import os
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.main import _apply_package_intent, _save_package_form_values, _sync_package_status, _sync_social_posts
from app.models import (
    AuthorProfile,
    BlogPost,
    Campaign,
    CampaignStatus,
    ContentPackage,
    ContentStatus,
    PackageStatus,
    Platform,
    SocialPost,
)
from app.services.generator import SurfaceDraft


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_sync_social_posts_updates_drafts_and_preserves_non_drafts() -> None:
    session = _session()

    author = AuthorProfile(name="Bomi Team")
    session.add(author)
    session.flush()

    campaign = Campaign(question_seed_id=1, author_profile_id=author.id, status=CampaignStatus.draft)
    session.add(campaign)
    session.flush()

    package = ContentPackage(campaign_id=campaign.id, author_profile_id=author.id, question="Topic")
    session.add(package)
    session.flush()

    blog = BlogPost(
        package_id=package.id,
        campaign_id=campaign.id,
        author_profile_id=author.id,
        title="Sample Blog",
        slug="sample-blog",
        markdown="# Sample",
    )
    session.add(blog)
    session.flush()

    draft_post = SocialPost(
        package_id=package.id,
        campaign_id=campaign.id,
        blog_post_id=blog.id,
        platform=Platform.linkedin,
        body="old linkedin",
        sequence=1,
        status=ContentStatus.draft,
        queue_position=1,
    )
    approved_post = SocialPost(
        package_id=package.id,
        campaign_id=campaign.id,
        blog_post_id=blog.id,
        platform=Platform.reddit,
        body="keep me",
        reddit_title="Keep me",
        reddit_subreddit="billwithbomi",
        sequence=2,
        status=ContentStatus.approved,
        queue_position=1,
    )
    stale_draft = SocialPost(
        package_id=package.id,
        campaign_id=campaign.id,
        blog_post_id=blog.id,
        platform=Platform.reddit,
        body="stale",
        reddit_title="Stale",
        reddit_subreddit="billwithbomi",
        sequence=3,
        status=ContentStatus.draft,
        queue_position=2,
    )
    session.add_all([draft_post, approved_post, stale_draft])
    session.flush()

    package = session.get(ContentPackage, package.id)
    assert package is not None

    _sync_social_posts(
        session,
        package,
        blog,
        author,
        [
            SurfaceDraft(platform="linkedin", body="new linkedin", sequence=1),
            SurfaceDraft(platform="reddit", body="new reddit", sequence=4, reddit_title="New reddit"),
        ],
    )
    session.flush()

    posts = session.query(SocialPost).order_by(SocialPost.platform, SocialPost.sequence).all()
    posts_by_key = {(post.platform.value, post.sequence): post for post in posts}

    assert posts_by_key[("linkedin", 1)].body == "new linkedin"
    assert posts_by_key[("reddit", 2)].body == "keep me"
    assert posts_by_key[("reddit", 2)].status == ContentStatus.approved
    assert posts_by_key[("reddit", 3)].status == ContentStatus.ignored
    assert posts_by_key[("reddit", 4)].body == "new reddit"
    assert posts_by_key[("reddit", 4)].status == ContentStatus.draft

    session.close()


def test_sync_social_posts_can_attach_generated_media_cards() -> None:
    session = _session()

    author = AuthorProfile(name="Bomi Team")
    session.add(author)
    session.flush()

    package = ContentPackage(author_profile_id=author.id, question="Topic")
    session.add(package)
    session.flush()

    blog = BlogPost(
        package_id=package.id,
        author_profile_id=author.id,
        title="Sample Blog",
        slug="sample-blog",
        markdown="# Sample",
        interesting_points_json='["First insight", "Second insight"]',
    )
    session.add(blog)
    session.flush()

    package = session.get(ContentPackage, package.id)
    assert package is not None

    with patch.dict(os.environ, {"ENABLE_MEDIA_CARDS": "true", "MEDIA_CARD_SURFACES": "linkedin"}, clear=False):
        with patch("app.main.build_asset_url_for_point", return_value="https://cdn.example/card.png") as build_card:
            _sync_social_posts(
                session,
                package,
                blog,
                author,
                [SurfaceDraft(platform="linkedin", body="new linkedin", sequence=1)],
            )
    session.flush()

    post = session.query(SocialPost).one()
    assert post.asset_url == "https://cdn.example/card.png"
    build_card.assert_called_once_with("First insight")

    session.close()


def test_save_package_values_and_inline_action_preserve_current_edits() -> None:
    session = _session()

    author = AuthorProfile(name="Bomi Team")
    session.add(author)
    session.flush()

    package = ContentPackage(author_profile_id=author.id, question="Old topic")
    session.add(package)
    session.flush()

    blog = BlogPost(
        package_id=package.id,
        author_profile_id=author.id,
        title="Old title",
        slug="old-title",
        markdown="Old markdown",
        meta_description="Old meta",
        interesting_points_json='["Old point"]',
    )
    session.add(blog)
    session.flush()

    social = SocialPost(
        package_id=package.id,
        blog_post_id=blog.id,
        platform=Platform.linkedin,
        body="old social",
        sequence=1,
        status=ContentStatus.draft,
    )
    session.add(social)
    session.flush()

    package = session.get(ContentPackage, package.id)
    assert package is not None

    form = {
        "question": "New topic",
        "target_keyword": "new keyword",
        "audience": "new audience",
        "website_url": "https://www.billwithbomi.com/illinois",
        "blog_title": "New title",
        "blog_slug": "new-title",
        "blog_meta_description": "New meta",
        "blog_markdown": "New markdown",
        "interesting_points": "New point one\nNew point two\nNew point three",
        f"social_{social.id}_body": "new social",
        f"social_{social.id}_asset_url": "https://cdn.example/card.png",
        "intent": f"social:{social.id}:approve",
    }

    _save_package_form_values(package, form)
    _apply_package_intent(session, package, form["intent"])
    _sync_package_status(package)

    assert package.question == "New topic"
    assert blog.title == "New title"
    assert blog.markdown == "New markdown"
    assert social.body == "new social"
    assert social.asset_url == "https://cdn.example/card.png"
    assert social.status == ContentStatus.approved
    assert package.status == PackageStatus.ready

    session.close()
