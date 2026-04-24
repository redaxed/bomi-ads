from __future__ import annotations

import json
import os
import re
import textwrap
from dataclasses import dataclass

from slugify import slugify

from .prompting import blog_generation_prompt, insight_extraction_prompt, social_generation_prompt

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

MIN_INSIGHTS = 3
MAX_INSIGHTS = 5
BLOG_URL_PLACEHOLDER = "{{BLOG_URL}}"
LINKEDIN_EMOJI_ROTATION = ["🧾", "⚙️", "⏱️", "📌", "🛠️"]
LANDING_SPECIAL_HEADINGS = {
    "tl;dr",
    "the thesis",
    "biller's corner",
    "counterargument + response",
    "actionable takeaways",
    "sources / further reading",
}


@dataclass
class BlogDraft:
    title: str
    slug: str
    meta_description: str
    markdown: str
    seo_score: float
    interesting_points: list[str]
    categories: list[dict]
    faq: list[dict]


@dataclass
class BlogChecklistItem:
    label: str
    passed: bool
    detail: str


@dataclass
class BlogReadiness:
    score: float
    passed_checks: int
    total_checks: int
    is_publish_ready: bool
    items: list[BlogChecklistItem]
    failed_items: list[BlogChecklistItem]


@dataclass
class SurfaceDraft:
    platform: str
    body: str
    sequence: int
    kind: str = "insight"
    reddit_title: str = ""


@dataclass
class GeneratedBundle:
    blog: BlogDraft
    surfaces: list[SurfaceDraft]


def _has_emoji(text: str) -> bool:
    return any(ord(ch) > 10_000 for ch in text)


def _polish_social_draft(draft: SurfaceDraft) -> SurfaceDraft:
    if draft.platform == "linkedin" and draft.sequence % 2 == 1 and not _has_emoji(draft.body):
        emoji = LINKEDIN_EMOJI_ROTATION[(draft.sequence - 1) % len(LINKEDIN_EMOJI_ROTATION)]
        draft.body = f"{emoji} {draft.body}"
    return draft


def _seo_score(title: str, markdown: str, keyword: str) -> float:
    score = 50.0
    lower = markdown.lower()
    kw = (keyword or "").strip().lower()
    if kw:
        if kw in title.lower():
            score += 15
        if kw in lower[:600]:
            score += 15
        if f"## {kw}" in lower:
            score += 10
    if markdown.count("## ") >= 3:
        score += 5
    if markdown.count("?") >= 2:
        score += 5
    return min(100.0, score)


def _extract_h2_sections(markdown: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current_heading = stripped[3:].strip()
            sections[current_heading] = []
            continue
        if current_heading is not None:
            sections[current_heading].append(raw_line.rstrip())
    return sections


def _section_list_count(lines: list[str], *, ordered: bool = False) -> int:
    count = 0
    for raw_line in lines:
        stripped = raw_line.strip()
        if ordered and re.match(r"^\d+\.\s+", stripped):
            count += 1
        elif not ordered and stripped.startswith("- "):
            count += 1
    return count


def assess_blog_readiness(
    *,
    title: str,
    meta_description: str,
    markdown: str,
    categories: list[dict],
    faq: list[dict],
    source_url: str = "",
) -> BlogReadiness:
    nonempty_lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    first_line = nonempty_lines[0] if nonempty_lines else ""
    sections = _extract_h2_sections(markdown)
    h2_headings = list(sections.keys())
    main_h2s = [heading for heading in h2_headings if heading.lower() not in LANDING_SPECIAL_HEADINGS]
    tldr_lines = sections.get("TL;DR", [])
    actionable_lines = sections.get("Actionable Takeaways", [])
    sources_lines = sections.get("Sources / Further Reading", [])
    has_sources_link = any("](" in line for line in sources_lines)
    has_numbered_list = bool(re.search(r"(?m)^\d+\.\s+", markdown))
    has_duplicate_h1 = bool(re.search(r"(?m)^\s*#\s+", markdown))

    checks = [
        BlogChecklistItem(
            label="Title lives in metadata, not the body",
            passed=bool(title.strip()) and not has_duplicate_h1,
            detail="Keep the title in the title field and start the markdown body directly with the subtitle.",
        ),
        BlogChecklistItem(
            label="Body opens with an italic subtitle",
            passed=bool(first_line) and (first_line.startswith("*") or first_line.startswith("_")) and (first_line.endswith("*") or first_line.endswith("_")),
            detail="The first non-empty markdown line should be a short italic subtitle.",
        ),
        BlogChecklistItem(
            label="Meta description is present and tight",
            passed=120 <= len(meta_description.strip()) <= 220,
            detail="Aim for roughly 120-220 characters so the landing excerpt reads cleanly.",
        ),
        BlogChecklistItem(
            label="TL;DR has exactly 3 bullets",
            passed=_section_list_count(tldr_lines) == 3,
            detail='Include a "## TL;DR" section with exactly 3 bullet points.',
        ),
        BlogChecklistItem(
            label="Main body has 3-5 H2 sections",
            passed=3 <= len(main_h2s) <= 6,
            detail="Use 3-6 main H2 sections before the wrap-up sections.",
        ),
        BlogChecklistItem(
            label="Biller's Corner is included",
            passed="Biller's Corner" in sections,
            detail='Include a "## Biller\'s Corner" section with practical Tuesday-morning guidance.',
        ),
        BlogChecklistItem(
            label="Counterargument section is included",
            passed="Counterargument + Response" in sections,
            detail='Include a "## Counterargument + Response" section.',
        ),
        BlogChecklistItem(
            label="Actionable takeaways has exactly 3 bullets",
            passed=_section_list_count(actionable_lines) == 3,
            detail='Include a "## Actionable Takeaways" section with exactly 3 bullets.',
        ),
        BlogChecklistItem(
            label="Sources section is present",
            passed=bool(sources_lines) and (has_sources_link if source_url.strip() else True),
            detail="Include a sources section with bullet points, and use markdown links when a source URL was supplied.",
        ),
        BlogChecklistItem(
            label="Categories are set",
            passed=1 <= len([item for item in categories if isinstance(item, dict) and str(item.get("primary", "")).strip()]) <= 2,
            detail="Set 1-2 categories so the landing repo metadata stays clean.",
        ),
        BlogChecklistItem(
            label="FAQ has 2-4 entries",
            passed=2 <= len([item for item in faq if isinstance(item, dict) and str(item.get("question", "")).strip() and str(item.get("answer", "")).strip()]) <= 4,
            detail="Provide 2-4 concise FAQ pairs in metadata.",
        ),
        BlogChecklistItem(
            label="Body includes one numbered list",
            passed=has_numbered_list,
            detail="Include one numbered list for failure modes, rules of thumb, or a process.",
        ),
    ]

    passed_checks = sum(1 for item in checks if item.passed)
    total_checks = len(checks)
    failed_items = [item for item in checks if not item.passed]
    return BlogReadiness(
        score=round((passed_checks / total_checks) * 100, 1) if total_checks else 0.0,
        passed_checks=passed_checks,
        total_checks=total_checks,
        is_publish_ready=not failed_items,
        items=checks,
        failed_items=failed_items,
    )


def _normalize_insights(points: list[str], topic: str, *, minimum: int = MIN_INSIGHTS, maximum: int = MAX_INSIGHTS) -> list[str]:
    cleaned = [p.strip() for p in points if p and p.strip()]
    unique: list[str] = []
    seen: set[str] = set()
    for point in cleaned:
        key = point.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    while len(unique) < minimum:
        idx = len(unique) + 1
        unique.append(f"{topic}: practical insight {idx} with a concrete next step.")
    return unique[:maximum]


def _author_prompt(author_profile: dict) -> str:
    name = author_profile.get("name", "Bomi Team")
    tone = author_profile.get("tone_summary", "clear and practical")
    dos = [item.strip() for item in author_profile.get("dos", []) if str(item).strip()]
    donts = [item.strip() for item in author_profile.get("donts", []) if str(item).strip()]
    cta = author_profile.get("cta_style", "friendly and concrete")
    voice_prompt = str(author_profile.get("voice_prompt", "")).strip()
    samples = [str(sample).strip() for sample in author_profile.get("writing_samples", []) if str(sample).strip()][:4]

    lines = [
        f"Author: {name}",
        "Treat this author profile as a high-priority style constraint.",
        f"Tone summary: {tone}",
        f"CTA style: {cta}",
    ]
    if voice_prompt:
        lines.extend(
            [
                "Dedicated voice prompt:",
                voice_prompt,
            ]
        )
    if dos:
        lines.append("Do rules:")
        lines.extend(f"- {item}" for item in dos)
    if donts:
        lines.append("Don't rules:")
        lines.extend(f"- {item}" for item in donts)
    if samples:
        lines.append("Writing samples to borrow rhythm from without copying phrases:")
        lines.extend(f"- {sample}" for sample in samples)
    else:
        lines.append("No writing samples were supplied, so keep the voice concrete, thoughtful, and human.")
    return "\n".join(lines)


def _openai_client() -> OpenAI | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _openai_json(prompt: str | dict, *, max_output_tokens: int = 2200) -> dict | None:
    client = _openai_client()
    if client is None:
        return None
    try:
        user_content = prompt if isinstance(prompt, str) else json.dumps(prompt)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a sharp editorial assistant. Follow the requested voice exactly. "
                        "Return strict JSON only with no markdown fences or extra commentary."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            max_output_tokens=max_output_tokens,
        )
        raw = getattr(response, "output_text", "")
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


def _fallback_blog(topic: str, keyword: str, audience: str, website_url: str, source_url: str, author_profile: dict) -> BlogDraft:
    points = _normalize_insights(
        [
            f"Define the exact audience pain point for {topic} before writing.",
            "Turn each section into a checklist readers can execute in one sitting.",
            "Repurpose each key section into channel-native posts instead of copy-pasting.",
        ],
        topic,
    )

    author_name = author_profile.get("name", "Bomi Team")
    title = f"{topic}: A Practical Playbook for {audience or 'Growing Teams'}"
    website_cta = (
        f"*Need help turning this into an actual operating system? [Bomi can help]({website_url}) with credentialing, claims, and A/R follow-through.*\n\n"
        if website_url.strip()
        else ""
    )
    sources_line = (
        f"- [Source material]({source_url})"
        if source_url.strip()
        else "- No external source was supplied for this draft, so verify payer-specific details before publishing."
    )
    markdown = textwrap.dedent(
        f"""
        *Why does this keep turning into a Tuesday problem instead of a tidy policy question?*

        {website_cta}## TL;DR
        - {points[0]}
        - {points[1]}
        - {points[2]}

        ## The Tuesday this goes sideways
        The neat version of this topic fits in a checklist. The real version shows up when someone is between clients, a payer portal says one thing, and the bank account says another.

        This is usually where teams discover they were managing hope, not process.

        ## The thesis
        The useful move is to treat {topic} as an operating system, not a one-off task. That means naming the bottleneck, deciding who owns each step, and checking the failure modes before they get expensive.

        ## Where the workflow actually breaks
        Most teams do not fail because they forgot the whole idea. They fail because one piece quietly goes stale while everyone assumes someone else has it covered.

        1. Intake details are incomplete, so downstream work starts with bad assumptions.
        2. Ownership is fuzzy, so follow-up happens late or not at all.
        3. Exceptions pile up, and the spreadsheet starts to develop opinions.

        ## The operating rule
        A simple mental model helps here: incentives versus mechanics. Incentives tell you what the team wants. Mechanics tell you whether the system can actually deliver it. If the mechanics are weak, good intentions just produce cleaner excuses.

        ## Biller's Corner
        On Tuesday morning, we would pull the last few stuck items, tag the specific handoff that failed, and decide one rule that prevents the same miss next week.

        Then we would write that rule somewhere the team can actually see it. Not in a perfect SOP graveyard. In the place people already work.

        ## Counterargument + Response
        The fair objection is that this feels heavy for a small team. Sometimes that is true.

        The response is that a light process is still a process. The goal is not bureaucracy. It is fewer preventable surprises for {author_name} and everyone else doing the work.

        ## Actionable Takeaways
        - Audit the current handoffs before you change tools.
        - Assign one owner to each fragile step in the workflow.
        - Track one weekly metric that tells you whether the system is actually getting less noisy.

        ## Sources / Further Reading
        {sources_line}
        """
    ).strip()

    return BlogDraft(
        title=title,
        slug=slugify(title) or "generated-post",
        meta_description=(
            f"{topic} is less about one clever fix and more about owning the workflow, the handoffs, and the failure modes before they start costing the team time."
        )[:220],
        markdown=markdown,
        seo_score=_seo_score(title, markdown, keyword),
        interesting_points=points,
        categories=[{"primary": "Billing"}, {"primary": "Operations"}],
        faq=[
            {
                "question": f"What is the biggest failure mode around {topic}?",
                "answer": "In practice, the common failure mode is unclear ownership around the fragile step that everyone assumes is already covered.",
            },
            {
                "question": "How should a small team operationalize this without overbuilding process?",
                "answer": "Start with one owner, one weekly check, and one short feedback loop rather than a giant SOP nobody reads.",
            },
        ],
    )


def _openai_blog(topic: str, keyword: str, audience: str, website_url: str, source_url: str, source_summary: str, author_profile: dict) -> BlogDraft | None:
    prompt = blog_generation_prompt(
        topic=topic,
        keyword=keyword,
        audience=audience,
        website_url=website_url,
        source_url=source_url,
        source_summary=source_summary,
        author_prompt=_author_prompt(author_profile),
    )
    data = _openai_json(prompt, max_output_tokens=3600)
    if not data:
        return None
    blog_raw = data.get("blog", {})
    title = (blog_raw.get("title") or "").strip()
    markdown = (blog_raw.get("markdown") or "").strip()
    if not title or not markdown:
        return None
    return BlogDraft(
        title=title,
        slug=slugify(title) or "generated-post",
        meta_description=(blog_raw.get("meta_description") or "")[:340],
        markdown=markdown,
        seo_score=_seo_score(title, markdown, keyword),
        interesting_points=[],
        categories=blog_raw.get("categories") or [{"primary": "Marketing"}],
        faq=blog_raw.get("faq") or [],
    )


def generate_blog_draft(
    topic: str,
    keyword: str,
    audience: str,
    website_url: str,
    source_url: str,
    source_summary: str,
    author_profile: dict,
) -> BlogDraft:
    generated = _openai_blog(
        topic=topic,
        keyword=keyword,
        audience=audience,
        website_url=website_url,
        source_url=source_url,
        source_summary=source_summary,
        author_profile=author_profile,
    )
    return generated or _fallback_blog(topic, keyword, audience, website_url, source_url, author_profile)


def _fallback_extract_insights(topic: str, blog_title: str, blog_markdown: str) -> list[str]:
    headings = [
        line[3:].strip()
        for line in blog_markdown.splitlines()
        if line.strip().startswith("## ")
    ]
    candidates = headings[:MAX_INSIGHTS]
    if not candidates:
        paragraphs = [line.strip() for line in blog_markdown.splitlines() if line.strip() and not line.strip().startswith("#")]
        candidates = paragraphs[:MAX_INSIGHTS]
    return _normalize_insights(candidates, blog_title or topic)


def _openai_extract_insights(topic: str, blog_title: str, blog_markdown: str, author_profile: dict) -> list[str] | None:
    prompt = insight_extraction_prompt(
        topic=topic,
        blog_title=blog_title,
        blog_markdown=blog_markdown,
        author_prompt=_author_prompt(author_profile),
    )
    data = _openai_json(prompt, max_output_tokens=1400)
    if not data:
        return None
    insights = _normalize_insights(data.get("insights") or [], blog_title or topic)
    if len(insights) < MIN_INSIGHTS:
        return None
    return insights


def extract_blog_insights(topic: str, blog_title: str, blog_markdown: str, author_profile: dict) -> list[str]:
    extracted = _openai_extract_insights(topic, blog_title, blog_markdown, author_profile)
    return extracted or _fallback_extract_insights(topic, blog_title, blog_markdown)


def _fallback_social_draft(platform: str, sequence: int, insight: str, blog_title: str) -> SurfaceDraft | None:
    linkedin_openers = [
        "🧾 A pattern worth noticing:",
        "One tradeoff that gets missed:",
        "⚙️ The expensive mistake here:",
        "What tends to work in practice:",
        "📌 A decent operating rule:",
    ]
    reddit_openers = [
        "I keep seeing this come up in practice:",
        "One thing that feels true here:",
        "The part people usually underestimate:",
        "The failure mode I would watch first:",
        "The useful rule of thumb:",
    ]
    if platform == "linkedin":
        return SurfaceDraft(
            platform="linkedin",
            sequence=sequence,
            body=(
                f"{linkedin_openers[(sequence - 1) % len(linkedin_openers)]} {insight}\n\n"
                f"In practice, the move is to turn that into one clear operating rule before the process gets expensive.\n\n"
                f"Read the full breakdown: {BLOG_URL_PLACEHOLDER}"
            ),
        )
    if platform == "reddit":
        return SurfaceDraft(
            platform="reddit",
            sequence=sequence,
            body=(
                f"{reddit_openers[(sequence - 1) % len(reddit_openers)]}\n\n"
                f"{insight}\n\n"
                f"Curious how other teams handle this. Full post: {BLOG_URL_PLACEHOLDER}"
            ),
            reddit_title=f"What trips people up about {blog_title.rstrip('?') or 'this workflow'}?",
        )
    if platform == "facebook":
        return SurfaceDraft(
            platform="facebook",
            sequence=sequence,
            body=f"Insight {sequence}: {insight}\n\nFull post: {BLOG_URL_PLACEHOLDER}",
        )
    return None


def _fallback_social_drafts(insights: list[str], surfaces: list[str], blog_title: str) -> list[SurfaceDraft]:
    drafts: list[SurfaceDraft] = []
    for idx, insight in enumerate(insights, start=1):
        for platform in surfaces:
            draft = _fallback_social_draft(platform, idx, insight, blog_title)
            if draft is not None:
                drafts.append(draft)
    return drafts


def _openai_social_drafts(blog_title: str, blog_markdown: str, insights: list[str], author_profile: dict, surfaces: list[str]) -> list[SurfaceDraft] | None:
    drafts: list[SurfaceDraft] = []
    author_prompt = _author_prompt(author_profile)
    for surface in surfaces:
        prompt = social_generation_prompt(
            blog_title=blog_title,
            blog_markdown=blog_markdown,
            insights=insights,
            author_prompt=author_prompt,
            surfaces=[surface],
            blog_url_placeholder=BLOG_URL_PLACEHOLDER,
        )
        data = _openai_json(prompt, max_output_tokens=2400)
        if not data:
            continue

        for item in data.get("surfaces", []):
            platform = (item.get("platform") or "").lower().strip()
            body = (item.get("body") or "").strip()
            sequence = int(item.get("sequence") or 0)
            if platform != surface or not body or sequence < 1 or sequence > len(insights):
                continue
            drafts.append(
                SurfaceDraft(
                    platform=platform,
                    sequence=sequence,
                    body=body,
                    reddit_title=(item.get("reddit_title") or "").strip(),
                )
            )
    return drafts or None


def _openai_single_social_draft(
    *,
    blog_title: str,
    blog_markdown: str,
    insight: str,
    author_profile: dict,
    platform: str,
    sequence: int,
) -> SurfaceDraft | None:
    prompt = social_generation_prompt(
        blog_title=blog_title,
        blog_markdown=blog_markdown,
        insights=[insight],
        author_prompt=_author_prompt(author_profile),
        surfaces=[platform],
        blog_url_placeholder=BLOG_URL_PLACEHOLDER,
    )
    data = _openai_json(prompt, max_output_tokens=1200)
    if not data:
        return None

    for item in data.get("surfaces", []):
        item_platform = (item.get("platform") or "").lower().strip()
        body = (item.get("body") or "").strip()
        if item_platform != platform or not body:
            continue
        return SurfaceDraft(
            platform=platform,
            sequence=sequence,
            body=body,
            reddit_title=(item.get("reddit_title") or "").strip(),
        )
    return None


def generate_social_drafts(
    *,
    blog_title: str,
    blog_markdown: str,
    insights: list[str],
    author_profile: dict,
    surfaces: list[str],
) -> list[SurfaceDraft]:
    chosen = [s for s in surfaces if s in {"linkedin", "facebook", "instagram", "tiktok", "reddit"}]
    if not chosen:
        chosen = ["linkedin", "reddit"]

    generated = _openai_social_drafts(
        blog_title=blog_title,
        blog_markdown=blog_markdown,
        insights=insights,
        author_profile=author_profile,
        surfaces=chosen,
    )
    drafts = generated or _fallback_social_drafts(insights, chosen, blog_title)

    existing = {(draft.platform, draft.sequence) for draft in drafts}
    for idx, insight in enumerate(insights, start=1):
        for platform in chosen:
            if (platform, idx) in existing:
                continue
            targeted = _openai_single_social_draft(
                blog_title=blog_title,
                blog_markdown=blog_markdown,
                insight=insight,
                author_profile=author_profile,
                platform=platform,
                sequence=idx,
            )
            if targeted is not None:
                drafts.append(targeted)
                existing.add((platform, idx))
                continue
            fallback = _fallback_social_draft(platform, idx, insight, blog_title)
            if fallback is not None:
                drafts.append(fallback)
    return [_polish_social_draft(draft) for draft in drafts]


def generate_bundle(
    topic: str,
    keyword: str,
    audience: str,
    website_url: str,
    source_url: str,
    source_summary: str,
    author_profile: dict,
    surfaces: list[str],
) -> GeneratedBundle:
    blog = generate_blog_draft(
        topic=topic,
        keyword=keyword,
        audience=audience,
        website_url=website_url,
        source_url=source_url,
        source_summary=source_summary,
        author_profile=author_profile,
    )
    insights = extract_blog_insights(topic, blog.title, blog.markdown, author_profile)
    blog.interesting_points = _normalize_insights(insights, topic or blog.title)
    surfaces_drafts = generate_social_drafts(
        blog_title=blog.title,
        blog_markdown=blog.markdown,
        insights=blog.interesting_points,
        author_profile=author_profile,
        surfaces=surfaces,
    )
    return GeneratedBundle(blog=blog, surfaces=surfaces_drafts)
