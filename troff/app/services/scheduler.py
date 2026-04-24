from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ..db import get_session
from ..models import (
    BlogPost,
    CampaignStatus,
    ContentPackage,
    ContentStatus,
    DispatchRun,
    InboxItem,
    PackageStatus,
    Platform,
    PublishAttempt,
    SocialPost,
)
from ..settings import enabled_surfaces
from .publisher import PublishError, PublishResult, github_pr_merged, publish_blog, publish_social, url_is_live

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Los_Angeles")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAYS_SECONDS = [60, 600, 3600]


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(APP_TIMEZONE))


def _dispatch_time_local() -> str:
    return os.getenv("DAILY_DISPATCH_LOCAL_TIME", "09:00").strip()


def _create_inbox(session, *, package_id: int | None, campaign_id: int | None, code: str, message: str, level: str = "error") -> None:
    session.add(
        InboxItem(
            package_id=package_id,
            campaign_id=campaign_id,
            code=code,
            message=message,
            level=level,
            is_read=False,
        )
    )


def _attempt_number(item) -> int:
    return int(getattr(item, "retries", 0)) + 1


def _record_attempt(
    session,
    *,
    content_type: str,
    content_id: int,
    surface: Platform,
    attempt_number: int,
    result: str,
    error: PublishError | None = None,
) -> None:
    session.add(
        PublishAttempt(
            content_type=content_type,
            content_id=content_id,
            surface=surface,
            attempt_number=attempt_number,
            result=result,
            http_status=(error.http_status if error else None),
            error_code=(error.code if error else ""),
            error_message=(str(error) if error else ""),
            provider_response_snippet=(error.provider_response if error else ""),
        )
    )


def _record_dispatch_run(
    session,
    *,
    surface: Platform,
    result: str,
    selected_type: str = "",
    selected_id: int | None = None,
    notes: str = "",
) -> None:
    now_local = _local_now()
    session.add(
        DispatchRun(
            run_date_local=now_local.date(),
            run_time_local=now_local.strftime("%H:%M"),
            surface=surface,
            selected_content_type=selected_type,
            selected_content_id=selected_id,
            result=result,
            notes=notes[:900],
        )
    )


def next_queue_position(session, surface: Platform) -> int:
    if surface == Platform.blog:
        current = session.scalar(select(func.max(BlogPost.queue_position))) or 0
        return int(current) + 1
    current = session.scalar(select(func.max(SocialPost.queue_position)).where(SocialPost.platform == surface)) or 0
    return int(current) + 1


def _set_retry_or_dead_letter(session, item, *, content_type: str, surface: Platform, err: PublishError, now: datetime) -> None:
    item.retries = int(item.retries or 0) + 1
    item.status = ContentStatus.failed
    item.error_message = str(err)

    attempt = item.retries
    _record_attempt(
        session,
        content_type=content_type,
        content_id=item.id,
        surface=surface,
        attempt_number=attempt,
        result="failed",
        error=err,
    )

    if attempt >= MAX_RETRIES:
        item.dead_lettered_at = now
        item.next_retry_at = None
        _create_inbox(
            session,
            package_id=getattr(item, "package_id", None),
            campaign_id=getattr(item, "campaign_id", None),
            code="dead_letter",
            message=f"{surface.value} post {item.id} moved to dead-letter after {attempt} attempts: {err}",
        )
        return

    idx = min(attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)
    item.next_retry_at = now + timedelta(seconds=RETRY_DELAYS_SECONDS[idx])


def _blog_eligibility(blog: BlogPost) -> tuple[bool, str]:
    if blog.dead_lettered_at is not None:
        return False, "dead-lettered"
    if blog.status == ContentStatus.ignored:
        return False, "ignored"
    if blog.status == ContentStatus.blocked:
        return False, blog.blocked_reason or "blocked"
    if blog.status != ContentStatus.approved:
        return False, f"status={blog.status.value}"
    if blog.eligible_after and blog.eligible_after > _now_utc_naive():
        return False, "not eligible yet"
    return True, ""


def _social_eligibility(post: SocialPost) -> tuple[bool, str]:
    if post.dead_lettered_at is not None:
        return False, "dead-lettered"
    if post.status == ContentStatus.ignored:
        return False, "ignored"
    if post.status == ContentStatus.blocked:
        return False, post.blocked_reason or "blocked"
    if post.status != ContentStatus.approved:
        return False, f"status={post.status.value}"
    if post.eligible_after and post.eligible_after > _now_utc_naive():
        return False, "not eligible yet"

    blog = post.blog_post
    if post.requires_blog_live:
        if not blog:
            return False, "blocked: missing blog link"
        if not blog.live_verified_at:
            return False, "blocked: waiting for blog live verification"

    if post.platform in {Platform.instagram, Platform.tiktok} and not post.asset_url.strip():
        return False, "blocked: asset_url required"

    if post.platform == Platform.reddit:
        if not post.reddit_subreddit.strip():
            return False, "blocked: subreddit required"
        if not (post.reddit_title.strip() or post.body.strip()):
            return False, "blocked: reddit title/body required"

    return True, ""


def _publish_blog_item(session, blog: BlogPost, now: datetime) -> bool:
    try:
        result: PublishResult = publish_blog(blog)
        blog.status = ContentStatus.published
        blog.published_at = now
        blog.external_id = result.external_id
        blog.canonical_url = result.canonical_url
        blog.landing_pr_url = result.landing_pr_url
        blog.landing_pr_number = result.landing_pr_number
        blog.landing_branch = result.landing_branch
        blog.landing_commit_sha = result.landing_commit_sha
        blog.landing_state = result.landing_state
        blog.error_message = ""
        blog.blocked_reason = ""
        blog.next_retry_at = None

        _record_attempt(
            session,
            content_type="blog",
            content_id=blog.id,
            surface=Platform.blog,
            attempt_number=_attempt_number(blog),
            result="success",
        )
        return True
    except PublishError as err:
        _set_retry_or_dead_letter(session, blog, content_type="blog", surface=Platform.blog, err=err, now=now)
        return False


def _publish_social_item(session, post: SocialPost, now: datetime) -> bool:
    try:
        external_id = publish_social(post)
        post.status = ContentStatus.published
        post.published_at = now
        post.external_id = external_id
        post.error_message = ""
        post.blocked_reason = ""
        post.next_retry_at = None

        _record_attempt(
            session,
            content_type="social",
            content_id=post.id,
            surface=post.platform,
            attempt_number=_attempt_number(post),
            result="success",
        )
        return True
    except PublishError as err:
        _set_retry_or_dead_letter(session, post, content_type="social", surface=post.platform, err=err, now=now)
        return False


def _refresh_blog_live_states(session, now: datetime) -> None:
    blogs = session.scalars(
        select(BlogPost).where(
            BlogPost.status == ContentStatus.published,
            BlogPost.live_verified_at.is_(None),
        )
    ).all()

    for blog in blogs:
        merged_ok = True
        if blog.landing_pr_number:
            merged_ok = github_pr_merged(blog.landing_pr_number)
            if merged_ok:
                blog.landing_state = "merged"

        if not merged_ok:
            continue

        if url_is_live(blog.canonical_url):
            blog.live_verified_at = now
            blocked_social = session.scalars(
                select(SocialPost).where(
                    SocialPost.blog_post_id == blog.id,
                    SocialPost.status == ContentStatus.blocked,
                    SocialPost.blocked_reason.like("blocked: waiting for blog live verification%"),
                )
            ).all()
            for social in blocked_social:
                social.status = ContentStatus.approved
                social.blocked_reason = ""


def _dispatch_surface(session, surface: Platform, now: datetime, force: bool) -> None:
    local_now = _local_now()
    already_succeeded = session.scalar(
        select(func.count(DispatchRun.id)).where(
            DispatchRun.run_date_local == local_now.date(),
            DispatchRun.surface == surface,
            DispatchRun.result == "success",
        )
    )
    if already_succeeded and not force:
        return

    if surface == Platform.blog:
        items = session.scalars(
            select(BlogPost)
            .where(BlogPost.status.in_([ContentStatus.approved, ContentStatus.blocked]))
            .order_by(BlogPost.queue_position.asc(), BlogPost.approved_at.asc(), BlogPost.id.asc())
        ).all()

        for blog in items:
            eligible, reason = _blog_eligibility(blog)
            if not eligible:
                _record_attempt(
                    session,
                    content_type="blog",
                    content_id=blog.id,
                    surface=surface,
                    attempt_number=_attempt_number(blog),
                    result="blocked",
                    error=PublishError(reason, code="blocked"),
                )
                continue

            success = _publish_blog_item(session, blog, now)
            _record_dispatch_run(
                session,
                surface=surface,
                result="success" if success else "failed",
                selected_type="blog",
                selected_id=blog.id,
                notes=(blog.error_message if not success else ""),
            )
            return

        _record_dispatch_run(session, surface=surface, result="no_eligible")
        return

    items = session.scalars(
        select(SocialPost)
        .where(
            SocialPost.platform == surface,
            SocialPost.status.in_([ContentStatus.approved, ContentStatus.blocked]),
        )
        .order_by(SocialPost.queue_position.asc(), SocialPost.approved_at.asc(), SocialPost.id.asc())
    ).all()

    for post in items:
        eligible, reason = _social_eligibility(post)
        if not eligible:
            if post.status == ContentStatus.approved and reason.startswith("blocked:"):
                post.status = ContentStatus.blocked
                post.blocked_reason = reason
            _record_attempt(
                session,
                content_type="social",
                content_id=post.id,
                surface=surface,
                attempt_number=_attempt_number(post),
                result="blocked",
                error=PublishError(reason, code="blocked"),
            )
            continue

        success = _publish_social_item(session, post, now)
        _record_dispatch_run(
            session,
            surface=surface,
            result="success" if success else "failed",
            selected_type="social",
            selected_id=post.id,
            notes=(post.error_message if not success else ""),
        )
        return

    _record_dispatch_run(session, surface=surface, result="no_eligible")


def _recompute_package_state(session) -> None:
    packages = session.scalars(select(ContentPackage)).all()
    for package in packages:
        statuses: list[ContentStatus] = []
        if package.blog_post:
            statuses.append(package.blog_post.status)
        statuses.extend([s.status for s in package.social_posts])
        if not statuses:
            continue

        if all(status == ContentStatus.published for status in statuses):
            package.status = PackageStatus.published
            if package.campaign:
                package.campaign.status = CampaignStatus.complete
            continue

        dead_letter_exists = bool(package.blog_post and package.blog_post.dead_lettered_at) or any(s.dead_lettered_at for s in package.social_posts)
        if dead_letter_exists:
            package.status = PackageStatus.failed
            if package.campaign:
                package.campaign.status = CampaignStatus.failed
            continue

        if all(status in {ContentStatus.draft, ContentStatus.ignored} for status in statuses):
            package.status = PackageStatus.draft
            if package.campaign:
                package.campaign.status = CampaignStatus.draft
            continue

        package.status = PackageStatus.ready
        if package.campaign and package.campaign.status == CampaignStatus.draft:
            package.campaign.status = CampaignStatus.active


def process_daily_dispatch(force: bool = False) -> None:
    now = _now_utc_naive()
    with get_session() as session:
        _refresh_blog_live_states(session, now)
        for surface in enabled_surfaces():
            _dispatch_surface(session, surface, now, force)
        _recompute_package_state(session)


def process_retry_queue() -> None:
    now = _now_utc_naive()
    with get_session() as session:
        due_blogs = session.scalars(
            select(BlogPost).where(
                BlogPost.status == ContentStatus.failed,
                BlogPost.dead_lettered_at.is_(None),
                BlogPost.next_retry_at.is_not(None),
                BlogPost.next_retry_at <= now,
                BlogPost.retries < MAX_RETRIES,
            )
        ).all()
        for blog in due_blogs:
            _publish_blog_item(session, blog, now)

        due_social = session.scalars(
            select(SocialPost).where(
                SocialPost.status == ContentStatus.failed,
                SocialPost.dead_lettered_at.is_(None),
                SocialPost.next_retry_at.is_not(None),
                SocialPost.next_retry_at <= now,
                SocialPost.retries < MAX_RETRIES,
            )
        ).all()
        for post in due_social:
            eligible, reason = _social_eligibility(post)
            if not eligible:
                if reason.startswith("blocked:"):
                    post.status = ContentStatus.blocked
                    post.blocked_reason = reason
                _record_attempt(
                    session,
                    content_type="social",
                    content_id=post.id,
                    surface=post.platform,
                    attempt_number=_attempt_number(post),
                    result="blocked",
                    error=PublishError(reason, code="blocked"),
                )
                continue
            _publish_social_item(session, post, now)

        _refresh_blog_live_states(session, now)
        _recompute_package_state(session)


def mark_item_requeued(item) -> None:
    item.status = ContentStatus.approved
    item.retries = 0
    item.next_retry_at = None
    item.dead_lettered_at = None
    item.error_message = ""
    item.blocked_reason = ""
