from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from .db import Base, engine, get_session
from .models import (
    AuthorProfile,
    BlogPost,
    Campaign,
    CampaignStatus,
    ContentPackage,
    ContentStatus,
    InboxItem,
    PackageStatus,
    Platform,
    QuestionInputType,
    QuestionSeed,
    QuestionSeedStatus,
    SocialPost,
)
from .services.generator import assess_blog_readiness, extract_blog_insights, generate_bundle, generate_social_drafts
from .services.media import build_asset_url_for_point
from .services.scheduler import (
    mark_item_requeued,
    next_queue_position,
    process_daily_dispatch,
    process_retry_queue,
)
from .services.source_fetcher import SourceFetchError, fetch_source_snapshot
from .settings import enabled_surface_values, media_card_surface_values, media_cards_enabled, scheduler_enabled

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Los_Angeles")
DISPATCH_TIME_LOCAL = os.getenv("DAILY_DISPATCH_LOCAL_TIME", "09:00")

app = FastAPI(title="Troff Queue Content Ops")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
worker_scheduler = BackgroundScheduler(timezone=ZoneInfo(APP_TIMEZONE))


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)

    with get_session() as session:
        has_author = session.scalar(select(AuthorProfile.id).limit(1))
        if not has_author:
            session.add(
                AuthorProfile(
                    name="Bomi Team",
                    tone_summary="Practical, concise, operator-first voice.",
                    dos_json=json.dumps(["Use plain language", "Give concrete steps", "Tie every post to one core insight"]),
                    donts_json=json.dumps(["Avoid hype", "Avoid vague advice", "Avoid jargon without explanation"]),
                    cta_style="Invite reader to apply one action this week.",
                    writing_samples_json=json.dumps(["Start with the problem, then the playbook."]),
                    default_subreddits_json=json.dumps(["billwithbomi"]),
                )
            )

    if scheduler_enabled() and not worker_scheduler.running:
        hour, minute = (9, 0)
        try:
            pieces = DISPATCH_TIME_LOCAL.split(":", 1)
            hour = int(pieces[0])
            minute = int(pieces[1])
        except Exception:
            hour, minute = 9, 0

        worker_scheduler.add_job(
            process_daily_dispatch,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=ZoneInfo(APP_TIMEZONE)),
            id="daily_dispatch",
            replace_existing=True,
        )
        worker_scheduler.add_job(
            process_retry_queue,
            "interval",
            minutes=1,
            id="retry_queue",
            replace_existing=True,
        )
        worker_scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    if worker_scheduler.running:
        worker_scheduler.shutdown(wait=False)


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _safe_list(raw: str) -> list[str]:
    try:
        values = json.loads(raw or "[]")
        if isinstance(values, list):
            return [str(v).strip() for v in values if str(v).strip()]
    except Exception:
        pass
    return []


def _safe_json_items(raw: str) -> list[dict]:
    try:
        values = json.loads(raw or "[]")
        if isinstance(values, list):
            return [value for value in values if isinstance(value, dict)]
    except Exception:
        pass
    return []


def _author_prompt_dict(author: AuthorProfile) -> dict:
    return {
        "name": author.name,
        "tone_summary": author.tone_summary,
        "dos": _safe_list(author.dos_json),
        "donts": _safe_list(author.donts_json),
        "cta_style": author.cta_style,
        "writing_samples": _safe_list(author.writing_samples_json),
        "voice_prompt": getattr(author, "voice_prompt", ""),
        "default_subreddits": _safe_list(author.default_subreddits_json) or ["billwithbomi"],
    }


def _surface_values(include_blog: bool = True) -> list[str]:
    return enabled_surface_values(include_blog=include_blog)


def _seed_display(seed: QuestionSeed) -> str:
    if seed.input_type == QuestionInputType.url:
        return seed.source_url or seed.source_title or "URL seed"
    return seed.question_text


def _points_text(raw: str) -> str:
    return "\n".join(_safe_list(raw))


def _next_unique_slug(session, base_slug: str) -> str:
    root = (base_slug or "post").strip() or "post"
    candidate = root
    suffix = 1
    while session.scalar(select(BlogPost.id).where(BlogPost.slug == candidate)) is not None:
        candidate = f"{root}-{suffix}"
        suffix += 1
    return candidate


def _normalize_subreddit(value: str) -> str:
    normalized = (value or "").strip()
    if normalized.lower().startswith("r/"):
        normalized = normalized[2:]
    return normalized


def _normalize_points_input(points: list[str], topic: str) -> list[str]:
    normalized = [point.strip() for point in points if point and point.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for point in normalized:
        key = point.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(point)
    while len(deduped) < 3:
        deduped.append(f"{topic}: practical insight {len(deduped) + 1} with a concrete next step.")
    return deduped[:5]


def _insight_for_sequence(blog: BlogPost, sequence: int, fallback: str) -> str:
    insights = _safe_list(blog.interesting_points_json)
    if sequence > 0 and len(insights) >= sequence:
        return insights[sequence - 1]
    return fallback.strip() or blog.title


def _media_asset_for_draft(blog: BlogPost, draft) -> str:
    if not media_cards_enabled() or draft.platform not in set(media_card_surface_values()):
        return ""
    point = _insight_for_sequence(blog, draft.sequence, draft.body)
    try:
        return build_asset_url_for_point(point)
    except Exception:
        return ""


def _assign_missing_media_assets(package: ContentPackage, *, force: bool = False) -> int:
    blog = package.blog_post
    if not blog or (not force and not media_cards_enabled()):
        return 0

    media_surfaces = set(media_card_surface_values())
    generated = 0
    for post in package.social_posts:
        if post.asset_url or post.platform.value not in media_surfaces:
            continue
        point = _insight_for_sequence(blog, post.sequence, post.body)
        try:
            asset_url = build_asset_url_for_point(point)
        except Exception:
            asset_url = ""
        if asset_url:
            post.asset_url = asset_url
            generated += 1
    return generated


def _set_item_status(item, status: ContentStatus) -> None:
    item.status = status
    item.error_message = ""
    if status == ContentStatus.approved:
        item.approved_at = _now_utc_naive()
        item.blocked_reason = ""
        item.next_retry_at = None
    elif status == ContentStatus.blocked:
        item.blocked_reason = item.blocked_reason or "Blocked manually"
        item.next_retry_at = None
    elif status == ContentStatus.ignored:
        item.blocked_reason = ""
        item.next_retry_at = None
    elif status == ContentStatus.draft:
        item.blocked_reason = ""
        item.next_retry_at = None


def _sync_social_posts(session, package: ContentPackage, blog: BlogPost, author: AuthorProfile, drafts) -> None:
    default_subreddit = (_safe_list(author.default_subreddits_json) or [os.getenv("REDDIT_DEFAULT_SUBREDDIT", "billwithbomi")])[0]
    existing_by_key = {(post.platform.value, post.sequence): post for post in package.social_posts}
    generated_keys: set[tuple[str, int]] = set()

    for draft in drafts:
        key = (draft.platform, draft.sequence)
        generated_keys.add(key)
        try:
            platform = Platform(draft.platform)
        except Exception:
            continue
        if platform == Platform.blog:
            continue

        existing = existing_by_key.get(key)
        if existing:
            if existing.status == ContentStatus.draft:
                asset_url = _media_asset_for_draft(blog, draft)
                existing.body = draft.body
                existing.reddit_title = (draft.reddit_title or existing.reddit_title or f"{blog.title} - insight {draft.sequence}")[:300]
                existing.reddit_subreddit = existing.reddit_subreddit or default_subreddit
                existing.kind = draft.kind
                existing.requires_blog_live = True
                existing.blog_post_id = blog.id
                existing.error_message = ""
                if asset_url and not existing.asset_url:
                    existing.asset_url = asset_url
            continue

        asset_url = _media_asset_for_draft(blog, draft)
        session.add(
            SocialPost(
                package_id=package.id,
                campaign_id=package.campaign_id,
                question_seed_id=package.question_seed_id,
                blog_post_id=blog.id,
                platform=platform,
                body=draft.body,
                asset_url=asset_url,
                reddit_subreddit=default_subreddit,
                reddit_title=(draft.reddit_title or f"{blog.title} - insight {draft.sequence}")[:300],
                kind=draft.kind,
                sequence=draft.sequence,
                requires_blog_live=True,
                status=ContentStatus.draft,
                queue_position=next_queue_position(session, platform),
            )
        )

    for post in package.social_posts:
        key = (post.platform.value, post.sequence)
        if key in generated_keys:
            continue
        if post.status == ContentStatus.draft:
            post.status = ContentStatus.ignored
            post.blocked_reason = "Superseded by refreshed blog insights."


def _sync_package_status(package: ContentPackage) -> None:
    statuses: list[ContentStatus] = []
    if package.blog_post:
        statuses.append(package.blog_post.status)
    statuses.extend([p.status for p in package.social_posts])
    if not statuses:
        return
    if all(s == ContentStatus.published for s in statuses):
        package.status = PackageStatus.published
        if package.campaign:
            package.campaign.status = CampaignStatus.complete
    elif any(s == ContentStatus.failed for s in statuses):
        package.status = PackageStatus.failed
        if package.campaign:
            package.campaign.status = CampaignStatus.failed
    elif all(s in {ContentStatus.draft, ContentStatus.ignored} for s in statuses):
        package.status = PackageStatus.draft
        if package.campaign:
            package.campaign.status = CampaignStatus.draft
    else:
        package.status = PackageStatus.ready
        if package.campaign:
            package.campaign.status = CampaignStatus.active


def _apply_item_action(item, action: str) -> None:
    if action == "approve":
        _set_item_status(item, ContentStatus.approved)
    elif action == "block":
        _set_item_status(item, ContentStatus.blocked)
        item.blocked_reason = "Blocked manually"
    elif action == "unblock":
        _set_item_status(item, ContentStatus.approved)
    elif action == "requeue":
        mark_item_requeued(item)
    elif action == "ignore":
        _set_item_status(item, ContentStatus.ignored)
    item.next_retry_at = None


@app.get("/")
def dashboard(request: Request):
    with get_session() as session:
        queued_questions = session.scalar(
            select(func.count(QuestionSeed.id)).where(QuestionSeed.status == QuestionSeedStatus.queued)
        )
        pending_inbox = session.scalar(select(func.count(InboxItem.id)).where(InboxItem.is_read.is_(False)))
        published_blogs = session.scalar(select(func.count(BlogPost.id)).where(BlogPost.status == ContentStatus.published))
        failed_items = (
            (session.scalar(select(func.count(BlogPost.id)).where(BlogPost.dead_lettered_at.is_not(None))) or 0)
            + (session.scalar(select(func.count(SocialPost.id)).where(SocialPost.dead_lettered_at.is_not(None))) or 0)
        )
        recent_packages = session.scalars(select(ContentPackage).order_by(ContentPackage.created_at.desc()).limit(10)).all()

        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "queued_questions": queued_questions or 0,
                "pending_inbox": pending_inbox or 0,
                "published_blogs": published_blogs or 0,
                "failed_items": failed_items,
                "recent_packages": recent_packages,
                "dispatch_time": DISPATCH_TIME_LOCAL,
                "scheduler_enabled": scheduler_enabled(),
                "tz": APP_TIMEZONE,
            },
        )


@app.get("/authors")
def authors_page(request: Request):
    with get_session() as session:
        authors = session.scalars(select(AuthorProfile).order_by(AuthorProfile.active.desc(), AuthorProfile.name.asc())).all()
        return templates.TemplateResponse(request, "authors.html", {"authors": authors, "safe_list": _safe_list})


@app.post("/authors")
def create_author(
    name: str = Form(...),
    tone_summary: str = Form(""),
    dos: str = Form(""),
    donts: str = Form(""),
    cta_style: str = Form(""),
    writing_samples: str = Form(""),
    default_subreddits: str = Form("billwithbomi"),
):
    with get_session() as session:
        session.add(
            AuthorProfile(
                name=name.strip(),
                tone_summary=tone_summary.strip(),
                dos_json=json.dumps([line.strip() for line in dos.splitlines() if line.strip()]),
                donts_json=json.dumps([line.strip() for line in donts.splitlines() if line.strip()]),
                cta_style=cta_style.strip(),
                writing_samples_json=json.dumps([line.strip() for line in writing_samples.splitlines() if line.strip()]),
                default_subreddits_json=json.dumps([_normalize_subreddit(line) for line in default_subreddits.splitlines() if line.strip()]),
            )
        )
    return RedirectResponse(url="/authors", status_code=303)


@app.post("/authors/{author_id}/toggle")
def toggle_author(author_id: int):
    with get_session() as session:
        author = session.get(AuthorProfile, author_id)
        if author:
            author.active = not author.active
    return RedirectResponse(url="/authors", status_code=303)


@app.get("/questions")
def questions_page(request: Request):
    with get_session() as session:
        authors = session.scalars(select(AuthorProfile).where(AuthorProfile.active.is_(True)).order_by(AuthorProfile.name.asc())).all()
        questions = session.scalars(select(QuestionSeed).order_by(QuestionSeed.created_at.desc())).all()
        packages = session.scalars(select(ContentPackage).where(ContentPackage.question_seed_id.is_not(None))).all()
        package_by_seed_id = {package.question_seed_id: package for package in packages if package.question_seed_id is not None}
        return templates.TemplateResponse(
            request,
            "questions.html",
            {
                "authors": authors,
                "questions": questions,
                "package_by_seed_id": package_by_seed_id,
                "seed_display": _seed_display,
                "input_types": [t.value for t in QuestionInputType],
            },
        )


@app.post("/questions")
def create_question_seed(
    input_type: str = Form("question"),
    question_text: str = Form(""),
    source_url: str = Form(""),
    target_keyword: str = Form(""),
    audience: str = Form(""),
    website_url: str = Form(""),
    author_profile_id: int = Form(...),
):
    resolved_input = QuestionInputType.url if input_type == QuestionInputType.url.value else QuestionInputType.question
    with get_session() as session:
        author = session.get(AuthorProfile, author_profile_id)
        if not author or not author.active:
            return RedirectResponse(url="/questions", status_code=303)

        seed = QuestionSeed(
            input_type=resolved_input,
            question_text=question_text.strip(),
            source_url=source_url.strip(),
            target_keyword=target_keyword.strip(),
            audience=audience.strip(),
            website_url=website_url.strip(),
            author_profile_id=author_profile_id,
            status=QuestionSeedStatus.queued,
        )
        session.add(seed)
    return RedirectResponse(url="/questions", status_code=303)


@app.post("/questions/{seed_id}/generate")
def generate_from_seed(seed_id: int):
    with get_session() as session:
        seed = session.get(QuestionSeed, seed_id)
        if not seed:
            return RedirectResponse(url="/questions", status_code=303)

        author = session.get(AuthorProfile, seed.author_profile_id)
        if not author or not author.active:
            seed.status = QuestionSeedStatus.failed
            seed.error_message = "Selected author is inactive or missing."
            return RedirectResponse(url="/questions", status_code=303)

        topic = seed.question_text.strip()
        source_summary = seed.source_summary.strip()

        if seed.input_type == QuestionInputType.url:
            if not seed.source_url.strip():
                seed.status = QuestionSeedStatus.failed
                seed.error_message = "URL input requires source_url."
                return RedirectResponse(url="/questions", status_code=303)
            try:
                snapshot = fetch_source_snapshot(seed.source_url.strip())
                seed.source_fetch_status = "ok"
                seed.source_title = snapshot.title
                seed.source_summary = snapshot.summary
                source_summary = snapshot.summary
                if not topic:
                    topic = snapshot.title
            except SourceFetchError as exc:
                seed.source_fetch_status = "failed"
                seed.status = QuestionSeedStatus.failed
                seed.error_message = str(exc)
                return RedirectResponse(url="/questions", status_code=303)

        if not topic:
            topic = "Generated content topic"

        surfaces = _surface_values(include_blog=False)
        author_profile = _author_prompt_dict(author)
        bundle = generate_bundle(
            topic=topic,
            keyword=seed.target_keyword,
            audience=seed.audience,
            website_url=seed.website_url,
            source_url=seed.source_url,
            source_summary=source_summary,
            author_profile=author_profile,
            surfaces=surfaces,
        )

        if len(bundle.blog.interesting_points) < 3:
            seed.status = QuestionSeedStatus.failed
            seed.error_message = "Generation failed validation: fewer than 3 interesting points."
            return RedirectResponse(url="/questions", status_code=303)

        campaign = Campaign(
            question_seed_id=seed.id,
            author_profile_id=author.id,
            status=CampaignStatus.draft,
        )
        session.add(campaign)
        session.flush()

        package = ContentPackage(
            campaign_id=campaign.id,
            question_seed_id=seed.id,
            author_profile_id=author.id,
            question=topic,
            target_keyword=seed.target_keyword,
            audience=seed.audience,
            website_url=seed.website_url,
            tone=author.tone_summary[:80] or "clear",
            status=PackageStatus.draft,
        )
        session.add(package)
        session.flush()

        blog = BlogPost(
            package_id=package.id,
            campaign_id=campaign.id,
            question_seed_id=seed.id,
            author_profile_id=author.id,
            title=bundle.blog.title,
            slug=_next_unique_slug(session, bundle.blog.slug),
            meta_description=bundle.blog.meta_description,
            markdown=bundle.blog.markdown,
            tiptap_json=json.dumps({}),
            interesting_points_json=json.dumps(bundle.blog.interesting_points),
            source_url=seed.source_url,
            author=author.name,
            categories_json=json.dumps(bundle.blog.categories),
            faq_json=json.dumps(bundle.blog.faq),
            seo_score=bundle.blog.seo_score,
            status=ContentStatus.draft,
            queue_position=next_queue_position(session, Platform.blog),
        )
        session.add(blog)
        session.flush()

        _sync_social_posts(session, package, blog, author, bundle.surfaces)

        seed.status = QuestionSeedStatus.generated
        seed.error_message = ""
        campaign.status = CampaignStatus.draft
        package.status = PackageStatus.draft

        return RedirectResponse(url=f"/packages/{package.id}", status_code=303)


@app.get("/packages/{package_id}")
def package_detail(request: Request, package_id: int):
    with get_session() as session:
        package = session.get(ContentPackage, package_id)
        if not package:
            return RedirectResponse(url="/", status_code=303)

        social_posts = sorted(package.social_posts, key=lambda p: (p.platform.value, p.sequence, p.id))
        blog_readiness = None
        if package.blog_post:
            blog_readiness = assess_blog_readiness(
                title=package.blog_post.title,
                meta_description=package.blog_post.meta_description,
                markdown=package.blog_post.markdown,
                categories=_safe_json_items(package.blog_post.categories_json),
                faq=_safe_json_items(package.blog_post.faq_json),
                source_url=package.blog_post.source_url,
            )
        return templates.TemplateResponse(
            request,
            "package.html",
            {
                "package": package,
                "blog": package.blog_post,
                "social_posts": social_posts,
                "blog_readiness": blog_readiness,
                "points_text": _points_text(package.blog_post.interesting_points_json if package.blog_post else "[]"),
                "queue_surfaces": _surface_values(),
            },
        )


def _save_package_form_values(package: ContentPackage, form) -> None:
    package.question = str(form.get("question", package.question)).strip()
    package.target_keyword = str(form.get("target_keyword", package.target_keyword)).strip()
    package.audience = str(form.get("audience", package.audience)).strip()
    package.website_url = str(form.get("website_url", package.website_url)).strip()

    blog = package.blog_post
    if not blog:
        return

    blog.title = str(form.get("blog_title", blog.title)).strip()
    blog.slug = str(form.get("blog_slug", blog.slug)).strip()
    blog.meta_description = str(form.get("blog_meta_description", blog.meta_description)).strip()
    blog.markdown = str(form.get("blog_markdown", blog.markdown))

    points = _normalize_points_input(
        [line.strip() for line in str(form.get("interesting_points", "")).splitlines() if line.strip()],
        package.question or blog.title,
    )
    blog.interesting_points_json = json.dumps(points)

    for social in package.social_posts:
        social.body = str(form.get(f"social_{social.id}_body", social.body))
        social.asset_url = str(form.get(f"social_{social.id}_asset_url", social.asset_url)).strip()
        social.reddit_title = str(form.get(f"social_{social.id}_reddit_title", social.reddit_title)).strip()
        social.reddit_subreddit = _normalize_subreddit(str(form.get(f"social_{social.id}_reddit_subreddit", social.reddit_subreddit)))


def _apply_package_intent(session, package: ContentPackage, intent: str) -> None:
    parts = [part.strip() for part in (intent or "").split(":")]
    if len(parts) != 3:
        return

    item_type, raw_id, action = parts
    if not raw_id.isdigit():
        return

    if item_type == "blog":
        item = session.get(BlogPost, int(raw_id))
        if item and item.package_id == package.id:
            _apply_item_action(item, action)
            return

    if item_type == "social":
        item = session.get(SocialPost, int(raw_id))
        if item and item.package_id == package.id:
            _apply_item_action(item, action)


def _mark_package_dirty(package: ContentPackage) -> None:
    package.status = PackageStatus.draft
    if package.campaign:
        package.campaign.status = CampaignStatus.draft


@app.post("/packages/{package_id}/save")
async def save_package(request: Request, package_id: int):
    form = await request.form()
    with get_session() as session:
        package = session.get(ContentPackage, package_id)
        if not package or not package.blog_post:
            return RedirectResponse(url="/", status_code=303)

        _save_package_form_values(package, form)
        _mark_package_dirty(package)

    return RedirectResponse(url=f"/packages/{package_id}", status_code=303)


@app.post("/packages/{package_id}/save-action")
async def save_package_action(request: Request, package_id: int):
    form = await request.form()
    with get_session() as session:
        package = session.get(ContentPackage, package_id)
        if not package or not package.blog_post:
            return RedirectResponse(url="/", status_code=303)

        _save_package_form_values(package, form)
        _apply_package_intent(session, package, str(form.get("intent", "")))
        _sync_package_status(package)

    return RedirectResponse(url=f"/packages/{package_id}", status_code=303)


@app.post("/packages/{package_id}/refresh-socials")
async def refresh_package_socials(request: Request, package_id: int):
    form = await request.form()
    with get_session() as session:
        package = session.get(ContentPackage, package_id)
        if not package or not package.blog_post:
            return RedirectResponse(url="/", status_code=303)

        if "blog_markdown" in form:
            _save_package_form_values(package, form)

        author = package.author_profile
        if not author:
            return RedirectResponse(url=f"/packages/{package_id}", status_code=303)

        blog = package.blog_post
        author_profile = _author_prompt_dict(author)
        insights = extract_blog_insights(package.question or blog.title, blog.title, blog.markdown, author_profile)
        blog.interesting_points_json = json.dumps(insights)
        drafts = generate_social_drafts(
            blog_title=blog.title,
            blog_markdown=blog.markdown,
            insights=insights,
            author_profile=author_profile,
            surfaces=_surface_values(include_blog=False),
        )
        _sync_social_posts(session, package, blog, author, drafts)
        _assign_missing_media_assets(package)

        package.status = PackageStatus.draft
        if package.campaign:
            package.campaign.status = CampaignStatus.draft

    return RedirectResponse(url=f"/packages/{package_id}", status_code=303)


@app.post("/packages/{package_id}/generate-media")
async def generate_package_media(request: Request, package_id: int):
    form = await request.form()
    with get_session() as session:
        package = session.get(ContentPackage, package_id)
        if package:
            if "blog_markdown" in form:
                _save_package_form_values(package, form)
            _assign_missing_media_assets(package, force=True)

    return RedirectResponse(url=f"/packages/{package_id}", status_code=303)


@app.post("/packages/{package_id}/approve")
def approve_package(package_id: int):
    return RedirectResponse(url="/queue/blog", status_code=303)


@app.post("/packages/{package_id}/blog/{item_id}/action")
def package_blog_action(package_id: int, item_id: int, action: str = Form(...)):
    with get_session() as session:
        package = session.get(ContentPackage, package_id)
        item = session.get(BlogPost, item_id)
        if package and item and item.package_id == package.id:
            _apply_item_action(item, action)
            _sync_package_status(package)
    return RedirectResponse(url=f"/packages/{package_id}", status_code=303)


@app.post("/packages/{package_id}/social/{item_id}/action")
def package_social_action(package_id: int, item_id: int, action: str = Form(...)):
    with get_session() as session:
        package = session.get(ContentPackage, package_id)
        item = session.get(SocialPost, item_id)
        if package and item and item.package_id == package.id:
            _apply_item_action(item, action)
            _sync_package_status(package)
    return RedirectResponse(url=f"/packages/{package_id}", status_code=303)


@app.get("/queue/{surface}")
def queue_surface(request: Request, surface: str):
    if surface not in _surface_values():
        return RedirectResponse(url="/", status_code=303)

    platform = Platform(surface)
    with get_session() as session:
        if platform == Platform.blog:
            items = session.scalars(
                select(BlogPost)
                .where(BlogPost.status.in_([ContentStatus.draft, ContentStatus.approved, ContentStatus.blocked, ContentStatus.failed]))
                .order_by(BlogPost.queue_position.asc(), BlogPost.id.asc())
            ).all()
        else:
            items = session.scalars(
                select(SocialPost)
                .where(
                    SocialPost.platform == platform,
                    SocialPost.status.in_([ContentStatus.draft, ContentStatus.approved, ContentStatus.blocked, ContentStatus.failed]),
                )
                .order_by(SocialPost.queue_position.asc(), SocialPost.id.asc())
            ).all()

        return templates.TemplateResponse(
            request,
            "queue.html",
            {
                "surface": surface,
                "platform": platform,
                "items": items,
                "is_blog": platform == Platform.blog,
                "queue_surfaces": _surface_values(),
            },
        )


@app.post("/queue/{surface}/reorder")
def reorder_queue(surface: str, ordered_ids: str = Form("")):
    if surface not in _surface_values():
        return RedirectResponse(url="/", status_code=303)
    ids = [int(x) for x in ordered_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return RedirectResponse(url=f"/queue/{surface}", status_code=303)

    platform = Platform(surface)
    with get_session() as session:
        if platform == Platform.blog:
            rows = session.scalars(select(BlogPost).where(BlogPost.id.in_(ids))).all()
            by_id = {row.id: row for row in rows}
        else:
            rows = session.scalars(select(SocialPost).where(SocialPost.id.in_(ids), SocialPost.platform == platform)).all()
            by_id = {row.id: row for row in rows}

        pos = 1
        for row_id in ids:
            row = by_id.get(row_id)
            if not row:
                continue
            row.queue_position = pos
            pos += 1
    return RedirectResponse(url=f"/queue/{surface}", status_code=303)


@app.post("/queue/{surface}/blog/{item_id}/update")
def update_blog_queue_item(
    surface: str,
    item_id: int,
    title: str = Form(""),
    markdown: str = Form(""),
    meta_description: str = Form(""),
    status: str = Form(""),
):
    if surface != Platform.blog.value:
        return RedirectResponse(url="/", status_code=303)

    with get_session() as session:
        item = session.get(BlogPost, item_id)
        if item:
            item.title = title.strip() or item.title
            item.markdown = markdown or item.markdown
            item.meta_description = meta_description.strip() or item.meta_description
            if status in {s.value for s in ContentStatus}:
                _set_item_status(item, ContentStatus(status))
            item.error_message = ""
            if item.package:
                _sync_package_status(item.package)
    return RedirectResponse(url=f"/queue/{surface}", status_code=303)


@app.post("/queue/{surface}/social/{item_id}/update")
def update_social_queue_item(
    surface: str,
    item_id: int,
    body: str = Form(""),
    asset_url: str = Form(""),
    reddit_title: str = Form(""),
    reddit_subreddit: str = Form(""),
    status: str = Form(""),
):
    if surface not in _surface_values(include_blog=False):
        return RedirectResponse(url="/", status_code=303)

    with get_session() as session:
        item = session.get(SocialPost, item_id)
        if item and item.platform.value == surface:
            item.body = body or item.body
            item.asset_url = asset_url.strip()
            item.reddit_title = reddit_title.strip()
            item.reddit_subreddit = _normalize_subreddit(reddit_subreddit)
            if status in {s.value for s in ContentStatus}:
                _set_item_status(item, ContentStatus(status))
            item.error_message = ""
            if item.package:
                _sync_package_status(item.package)
    return RedirectResponse(url=f"/queue/{surface}", status_code=303)


@app.post("/queue/{surface}/blog/{item_id}/action")
def blog_queue_action(surface: str, item_id: int, action: str = Form(...)):
    if surface != Platform.blog.value:
        return RedirectResponse(url="/", status_code=303)

    with get_session() as session:
        item = session.get(BlogPost, item_id)
        if item:
            _apply_item_action(item, action)
            if item.package:
                _sync_package_status(item.package)
    return RedirectResponse(url=f"/queue/{surface}", status_code=303)


@app.post("/queue/{surface}/social/{item_id}/action")
def social_queue_action(surface: str, item_id: int, action: str = Form(...)):
    if surface not in _surface_values(include_blog=False):
        return RedirectResponse(url="/", status_code=303)

    with get_session() as session:
        item = session.get(SocialPost, item_id)
        if item and item.platform.value == surface:
            _apply_item_action(item, action)
            if item.package:
                _sync_package_status(item.package)
    return RedirectResponse(url=f"/queue/{surface}", status_code=303)


@app.get("/pipeline")
def pipeline_map(request: Request):
    with get_session() as session:
        campaigns = session.scalars(select(Campaign).order_by(Campaign.created_at.desc())).all()
        rows = []
        for campaign in campaigns:
            package = session.scalars(select(ContentPackage).where(ContentPackage.campaign_id == campaign.id)).first()
            if not package:
                continue
            blog = package.blog_post
            social = package.social_posts
            by_surface: dict[str, dict] = {}
            for surface in _surface_values(include_blog=False):
                posts = [p for p in social if p.platform.value == surface]
                if not posts:
                    by_surface[surface] = {"count": 0, "published": 0, "failed": 0, "blocked": 0}
                    continue
                by_surface[surface] = {
                    "count": len(posts),
                    "published": sum(1 for p in posts if p.status == ContentStatus.published),
                    "failed": sum(1 for p in posts if p.status == ContentStatus.failed),
                    "blocked": sum(1 for p in posts if p.status == ContentStatus.blocked),
                }

            rows.append(
                {
                    "campaign": campaign,
                    "package": package,
                    "seed": package.question_seed,
                    "blog": blog,
                    "by_surface": by_surface,
                }
            )

        return templates.TemplateResponse(request, "pipeline.html", {"rows": rows, "surfaces": _surface_values(include_blog=False)})


@app.get("/failures")
def failures_page(request: Request):
    with get_session() as session:
        blog_failures = session.scalars(
            select(BlogPost)
            .where((BlogPost.dead_lettered_at.is_not(None)) | (BlogPost.status == ContentStatus.failed))
            .order_by(BlogPost.updated_at.desc())
        ).all()
        social_failures = session.scalars(
            select(SocialPost)
            .where((SocialPost.dead_lettered_at.is_not(None)) | (SocialPost.status == ContentStatus.failed))
            .order_by(SocialPost.updated_at.desc())
        ).all()
        inbox = session.scalars(select(InboxItem).order_by(InboxItem.created_at.desc()).limit(100)).all()
        return templates.TemplateResponse(
            request,
            "failures.html",
            {
                "blog_failures": blog_failures,
                "social_failures": social_failures,
                "inbox": inbox,
            },
        )


@app.post("/failures/blog/{item_id}/requeue")
def requeue_failed_blog(item_id: int):
    with get_session() as session:
        item = session.get(BlogPost, item_id)
        if item:
            mark_item_requeued(item)
    return RedirectResponse(url="/failures", status_code=303)


@app.post("/failures/social/{item_id}/requeue")
def requeue_failed_social(item_id: int):
    with get_session() as session:
        item = session.get(SocialPost, item_id)
        if item:
            mark_item_requeued(item)
    return RedirectResponse(url="/failures", status_code=303)


@app.post("/inbox/{item_id}/read")
def mark_inbox_read(item_id: int):
    with get_session() as session:
        item = session.get(InboxItem, item_id)
        if item:
            item.is_read = True
    return RedirectResponse(url="/failures", status_code=303)


@app.post("/run-dispatch")
def run_dispatch():
    process_daily_dispatch(force=True)
    process_retry_queue()
    return RedirectResponse(url="/", status_code=303)


@app.post("/run-worker")
def run_worker_compat():
    process_daily_dispatch(force=True)
    process_retry_queue()
    return RedirectResponse(url="/", status_code=303)
