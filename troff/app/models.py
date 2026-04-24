from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class PackageStatus(str, enum.Enum):
    draft = "draft"
    ready = "ready"
    published = "published"
    failed = "failed"


class ContentStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    blocked = "blocked"
    published = "published"
    failed = "failed"
    ignored = "ignored"


class Platform(str, enum.Enum):
    blog = "blog"
    linkedin = "linkedin"
    facebook = "facebook"
    instagram = "instagram"
    tiktok = "tiktok"
    reddit = "reddit"


class QuestionInputType(str, enum.Enum):
    question = "question"
    url = "url"


class QuestionSeedStatus(str, enum.Enum):
    queued = "queued"
    generated = "generated"
    archived = "archived"
    failed = "failed"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    ready = "ready"
    active = "active"
    failed = "failed"
    complete = "complete"


class AuthorProfile(Base):
    __tablename__ = "author_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    tone_summary: Mapped[str] = mapped_column(Text, default="")
    dos_json: Mapped[str] = mapped_column(Text, default="[]")
    donts_json: Mapped[str] = mapped_column(Text, default="[]")
    cta_style: Mapped[str] = mapped_column(Text, default="")
    writing_samples_json: Mapped[str] = mapped_column(Text, default="[]")
    default_subreddits_json: Mapped[str] = mapped_column(Text, default='["billwithbomi"]')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuestionSeed(Base):
    __tablename__ = "question_seeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    input_type: Mapped[QuestionInputType] = mapped_column(Enum(QuestionInputType), default=QuestionInputType.question, index=True)
    question_text: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    source_fetch_status: Mapped[str] = mapped_column(String(50), default="pending")
    source_title: Mapped[str] = mapped_column(String(500), default="")
    source_summary: Mapped[str] = mapped_column(Text, default="")
    target_keyword: Mapped[str] = mapped_column(String(200), default="")
    audience: Mapped[str] = mapped_column(String(200), default="")
    website_url: Mapped[str] = mapped_column(String(500), default="")
    author_profile_id: Mapped[int] = mapped_column(ForeignKey("author_profiles.id", ondelete="RESTRICT"), index=True)
    status: Mapped[QuestionSeedStatus] = mapped_column(Enum(QuestionSeedStatus), default=QuestionSeedStatus.queued, index=True)
    error_message: Mapped[str] = mapped_column(String(800), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author_profile: Mapped[AuthorProfile] = relationship()


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_seed_id: Mapped[int] = mapped_column(ForeignKey("question_seeds.id", ondelete="CASCADE"), index=True)
    author_profile_id: Mapped[int] = mapped_column(ForeignKey("author_profiles.id", ondelete="RESTRICT"), index=True)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.draft, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    question_seed: Mapped[QuestionSeed] = relationship()
    author_profile: Mapped[AuthorProfile] = relationship()


class ContentPackage(Base):
    __tablename__ = "content_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True, nullable=True)
    question_seed_id: Mapped[Optional[int]] = mapped_column(ForeignKey("question_seeds.id", ondelete="SET NULL"), index=True, nullable=True)
    author_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("author_profiles.id", ondelete="SET NULL"), index=True, nullable=True)
    question: Mapped[str] = mapped_column(String(1000), default="")
    target_keyword: Mapped[str] = mapped_column(String(200), default="")
    audience: Mapped[str] = mapped_column(String(200), default="")
    website_url: Mapped[str] = mapped_column(String(500), default="")
    tone: Mapped[str] = mapped_column(String(100), default="clear")
    status: Mapped[PackageStatus] = mapped_column(Enum(PackageStatus), default=PackageStatus.draft)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign: Mapped[Optional[Campaign]] = relationship()
    question_seed: Mapped[Optional[QuestionSeed]] = relationship()
    author_profile: Mapped[Optional[AuthorProfile]] = relationship()
    blog_post: Mapped[Optional[BlogPost]] = relationship(back_populates="package", uselist=False, cascade="all, delete-orphan")
    social_posts: Mapped[list[SocialPost]] = relationship(back_populates="package", cascade="all, delete-orphan")


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("content_packages.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True, nullable=True)
    question_seed_id: Mapped[Optional[int]] = mapped_column(ForeignKey("question_seeds.id", ondelete="SET NULL"), index=True, nullable=True)
    author_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("author_profiles.id", ondelete="SET NULL"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    meta_description: Mapped[str] = mapped_column(String(350), default="")
    markdown: Mapped[str] = mapped_column(Text)
    tiptap_json: Mapped[str] = mapped_column(Text, default="")
    interesting_points_json: Mapped[str] = mapped_column(Text, default="[]")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    author: Mapped[str] = mapped_column(String(200), default="Bomi Team")
    categories_json: Mapped[str] = mapped_column(Text, default='[{"primary":"Billing"}]')
    faq_json: Mapped[str] = mapped_column(Text, default="[]")
    canonical_url: Mapped[str] = mapped_column(String(1000), default="")
    landing_pr_url: Mapped[str] = mapped_column(String(1000), default="")
    landing_pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    landing_branch: Mapped[str] = mapped_column(String(300), default="")
    landing_commit_sha: Mapped[str] = mapped_column(String(200), default="")
    landing_state: Mapped[str] = mapped_column(String(50), default="none")
    seo_score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status: Mapped[ContentStatus] = mapped_column(Enum(ContentStatus), default=ContentStatus.draft, index=True)
    queue_position: Mapped[int] = mapped_column(Integer, default=0, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    eligible_after: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    live_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    external_id: Mapped[str] = mapped_column(String(300), default="")
    retries: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    dead_lettered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    blocked_reason: Mapped[str] = mapped_column(String(500), default="")
    error_message: Mapped[str] = mapped_column(String(1000), default="")

    package: Mapped[ContentPackage] = relationship(back_populates="blog_post")
    campaign: Mapped[Optional[Campaign]] = relationship()
    question_seed: Mapped[Optional[QuestionSeed]] = relationship()
    author_profile: Mapped[Optional[AuthorProfile]] = relationship()
    social_posts: Mapped[list[SocialPost]] = relationship(back_populates="blog_post")


class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("content_packages.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True, nullable=True)
    question_seed_id: Mapped[Optional[int]] = mapped_column(ForeignKey("question_seeds.id", ondelete="SET NULL"), index=True, nullable=True)
    blog_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blog_posts.id", ondelete="SET NULL"), index=True, nullable=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), index=True)
    body: Mapped[str] = mapped_column(Text)
    asset_url: Mapped[str] = mapped_column(String(1000), default="")
    reddit_subreddit: Mapped[str] = mapped_column(String(200), default="billwithbomi")
    reddit_title: Mapped[str] = mapped_column(String(300), default="")
    kind: Mapped[str] = mapped_column(String(50), default="point")
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    requires_blog_live: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status: Mapped[ContentStatus] = mapped_column(Enum(ContentStatus), default=ContentStatus.draft, index=True)
    queue_position: Mapped[int] = mapped_column(Integer, default=0, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    eligible_after: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    external_id: Mapped[str] = mapped_column(String(300), default="")
    retries: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    dead_lettered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    blocked_reason: Mapped[str] = mapped_column(String(500), default="")
    error_message: Mapped[str] = mapped_column(String(1000), default="")

    package: Mapped[ContentPackage] = relationship(back_populates="social_posts")
    campaign: Mapped[Optional[Campaign]] = relationship()
    question_seed: Mapped[Optional[QuestionSeed]] = relationship()
    blog_post: Mapped[Optional[BlogPost]] = relationship(back_populates="social_posts")


class PublishAttempt(Base):
    __tablename__ = "publish_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content_type: Mapped[str] = mapped_column(String(50), index=True)
    content_id: Mapped[int] = mapped_column(Integer, index=True)
    surface: Mapped[Platform] = mapped_column(Enum(Platform), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    result: Mapped[str] = mapped_column(String(50), index=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str] = mapped_column(String(100), default="")
    error_message: Mapped[str] = mapped_column(String(1000), default="")
    provider_response_snippet: Mapped[str] = mapped_column(String(1000), default="")


class DispatchRun(Base):
    __tablename__ = "dispatch_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_date_local: Mapped[date] = mapped_column(Date, index=True)
    run_time_local: Mapped[str] = mapped_column(String(20), default="")
    surface: Mapped[Platform] = mapped_column(Enum(Platform), index=True)
    selected_content_type: Mapped[str] = mapped_column(String(50), default="")
    selected_content_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    result: Mapped[str] = mapped_column(String(50), index=True)
    notes: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InboxItem(Base):
    __tablename__ = "inbox_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    package_id: Mapped[Optional[int]] = mapped_column(ForeignKey("content_packages.id", ondelete="SET NULL"), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(20), default="error", index=True)
    code: Mapped[str] = mapped_column(String(100), default="general_error", index=True)
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped[Optional[Campaign]] = relationship()
    package: Mapped[Optional[ContentPackage]] = relationship()
