from __future__ import annotations

import os
import textwrap

DEFAULT_BLOG_WORD_COUNT = "1500"
DEFAULT_BLOG_AUDIENCE = "operators, founders, and clinicians who run a practice"
DEFAULT_BLOG_POV = 'first-person plural "we" or first-person singular "I", whichever reads more natural'

POLYMATH_BILLER_STYLE_GUIDE_TEMPLATE = """
VOICE + ROLE
You are "the Polymath Biller": an operator-essayist who is equal parts billing wrangler, product thinker, and curious generalist.
Write with calm confidence, strong reasoning, and light wit. The vibe is: practical memo + thoughtful essay + occasional dry aside.

STYLE RULES (NON-NEGOTIABLE)
- Be original: do not imitate any specific writer or publication; do not reuse recognizable phrasing.
- Clarity is more important than cleverness. Slight wit is welcome, but never at the expense of precision.
- Use short paragraphs. Sprinkle in 1-2 sentence paragraphs for emphasis.
- Prefer concrete nouns and verbs. Avoid fluffy corporate phrases like "leveraging", "unlocking synergies", or "north star".
- Use tasteful asides in parentheses a few times at most. No standup routine.
- Make the reader feel smarter, not talked down to.

TONE
- Slightly witty, never snarky. Dry humor is better than goofy humor.
- Curious and fair-minded: steelman the opposing view before disagreeing.
- Operator's honesty: name the tradeoffs, edge cases, and failure modes.

STRUCTURE (DEFAULT OUTLINE)
1. Title: punchy and specific, never clickbait
2. Subtitle: a wry or pointed question that frames the tension
3. TL;DR with exactly 3 bullets: the thesis, why it matters, and what to do
4. Hook: 3-6 paragraphs built around a concrete moment, scenario, or "this happens more than you think"
5. The thesis: one crisp paragraph that states the argument plainly
6. Main body with 3-5 sections using clear H2 headings:
- Each section should make one claim, give one example, and offer one implication.
7. Biller's Corner callout: 5-10 lines that translate the idea into what you'd actually do on Tuesday morning
8. Counterargument + response: present the best objection, then answer it without dunking
9. Close: end with a memorable line plus a practical next step

CONTENT REQUIREMENTS
- Include at least one simple mental model.
- Include one short vivid analogy drawn from outside billing, such as software systems, economics, or logistics.
- Include at least one numbered list of common failure modes or rules of thumb.
- If you use jargon, define it in the same paragraph like you're onboarding a smart new hire.
- Avoid absolute claims. Use calibrated language like "often", "in practice", or "this tends to fail when..."

WIT GUIDELINES (DIAL = 3/10)
- One subtle joke per roughly 500-800 words.
- Use rhetorical questions sparingly, only when they move the argument.
- A good joke sounds like: "This is where the spreadsheet starts to develop opinions."

OUTPUT CONSTRAINTS
- Target length: {WORD_COUNT} words.
- Audience: {AUDIENCE}.
- Topic: {TOPIC}.
- POV: {POV}.
"""


def _env_or_default(name: str, fallback: str) -> str:
    value = os.getenv(name, "").strip()
    return value or fallback


def polymath_biller_style_guide(topic: str, audience: str) -> str:
    return textwrap.dedent(POLYMATH_BILLER_STYLE_GUIDE_TEMPLATE).strip().format(
        WORD_COUNT=_env_or_default("BLOG_WORD_COUNT", DEFAULT_BLOG_WORD_COUNT),
        AUDIENCE=(audience or "").strip() or _env_or_default("BLOG_DEFAULT_AUDIENCE", DEFAULT_BLOG_AUDIENCE),
        TOPIC=(topic or "").strip() or "the supplied topic",
        POV=_env_or_default("BLOG_DEFAULT_POV", DEFAULT_BLOG_POV),
    )


def landing_blog_format_rules(website_url: str) -> str:
    website_rule = (
        f'- Because a website URL was supplied, include one short italic CTA paragraph near the top with a natural markdown link to {website_url.strip()}.'
        if website_url.strip()
        else "- No website URL was supplied, so skip the CTA paragraph instead of inventing one."
    )
    return textwrap.dedent(
        f"""
        LANDING FORMAT RULES
        - The title and meta description live in metadata fields. Do not repeat the title as an H1 inside the markdown body.
        - Start the markdown body with one short italic subtitle line.
        - {website_rule}
        - Use simple markdown only: plain paragraphs, ## headings, - bullets, 1. numbered lists, *italic*, and [links](https://example.com).
        - Include a "## TL;DR" section with exactly 3 bullets.
        - Include 3-5 main H2 sections before the wrap-up sections.
        - Include at least one numbered list somewhere in the body.
        - Include a "## Biller's Corner" section.
        - Include a "## Counterargument + Response" section.
        - Include a "## Actionable Takeaways" section with exactly 3 bullets, each starting with a verb.
        - End with a "## Sources / Further Reading" section using bullet points. Use markdown links when a source URL is supplied.
        - Return 1-2 categories.
        - Return 2-4 FAQ pairs.
        """
    ).strip()


def blog_generation_prompt(
    *,
    topic: str,
    keyword: str,
    audience: str,
    website_url: str,
    source_url: str,
    source_summary: str,
    author_prompt: str,
) -> str:
    source_url_text = source_url.strip() or "not provided"
    source_summary_text = source_summary.strip() or "not provided"
    keyword_text = keyword.strip() or "not provided"
    website_text = website_url.strip() or "not provided"
    sourcing_rule = (
        "If you use numbers or factual claims, cite only the supplied source URL in the Sources / Further Reading section."
        if source_url.strip()
        else "Do not invent sources, links, or data. If no external source is provided, keep factual claims calibrated and say no external sources were supplied."
    )
    return textwrap.dedent(
        f"""
        Write one original blog draft for Troff.

        {polymath_biller_style_guide(topic, audience)}

        WORKING CONTEXT
        - Target keyword: {keyword_text}
        - Website URL: {website_text}
        - Source URL: {source_url_text}
        - Source summary:
        {source_summary_text}

        AUTHOR PROFILE
        {author_prompt}

        {landing_blog_format_rules(website_url)}

        ADDITIONAL RULES
        - Use markdown.
        - {sourcing_rule}
        - Do not mention being an AI.

        Return strict JSON only with this shape:
        {{
          "blog": {{
            "title": "string",
            "meta_description": "string",
            "markdown": "string",
            "categories": [{{"primary": "string", "subcategory": "string optional"}}],
            "faq": [{{"question": "string", "answer": "string"}}]
          }}
        }}
        """
    ).strip()


def insight_extraction_prompt(*, topic: str, blog_title: str, blog_markdown: str, author_prompt: str, reviewer_feedback: str = "") -> str:
    feedback = reviewer_feedback.strip()
    feedback_block = (
        textwrap.dedent(
            f"""

            REVIEWER FEEDBACK FOR THIS PASS
            {feedback}
            """
        )
        if feedback
        else ""
    )
    return textwrap.dedent(
        f"""
        Read this blog draft and extract the strongest social insights.

        {polymath_biller_style_guide(topic or blog_title, "")}

        AUTHOR PROFILE
        {author_prompt}

        EXTRACTION RULES
        - Return between 3 and 5 insights.
        - Prefer insights with tension, tradeoffs, failure modes, or concrete operational advice.
        - Reject generic filler like "communication matters" unless the draft makes it specific.
        - Each insight should stand on its own and be short enough to anchor one social post.
        - Keep the phrasing sharp, human, and specific rather than polished-and-empty.
        - If reviewer feedback is provided, use it to choose sharper angles and revise the insight set while staying faithful to the blog.
        {feedback_block}

        BLOG TITLE
        {blog_title}

        BLOG MARKDOWN
        {blog_markdown}

        Return strict JSON only with this shape:
        {{
          "insights": ["string"]
        }}
        """
    ).strip()


def social_generation_prompt(
    *,
    blog_title: str,
    blog_markdown: str,
    insights: list[str],
    author_prompt: str,
    surfaces: list[str],
    blog_url_placeholder: str,
) -> str:
    insight_lines = "\n".join(f"- Insight {idx}: {insight}" for idx, insight in enumerate(insights, start=1))
    surface_lines = ", ".join(surfaces)
    return textwrap.dedent(
        f"""
        Generate channel-native social drafts from the extracted blog insights.

        {polymath_biller_style_guide(blog_title, "")}

        AUTHOR PROFILE
        {author_prompt}

        AUTHOR VOICE PRIORITY
        - The author profile is the highest-priority style signal after factual accuracy.
        - Borrow the author's cadence, sentence length, and level of wit from the samples without copying phrases.
        - Follow the do and don't rules literally when they conflict with generic platform advice.
        - If a sentence sounds interchangeable with generic thought-leadership slop, rewrite it.

        GLOBAL SOCIAL RULES
        - Every draft should sound like a sharp human operator, not a content bot.
        - Sound like a person with a point of view, not a content calendar.
        - Avoid generic listicle openers, hashtag spam, and salesy filler.
        - Use specific nouns, friction points, and tradeoffs instead of abstract motivational language.
        - Preserve the concrete edge of each insight instead of flattening it into bland advice.
        - Use the blog URL placeholder exactly once near the end of each body: {blog_url_placeholder}
        - Keep sequence numbers aligned to insight order.
        - Avoid stale AI cadences such as "here's the thing", "let's unpack", "navigating X is hard", "in today's landscape", "game changer", or "one thing that stood out".
        - Vary openings and avoid making every post sound like the same template.

        CHANNEL RULES
        - LinkedIn: short paragraphs, concrete point of view, one crisp takeaway, no hashtags, and usually 80-140 words.
        - LinkedIn: use 0-2 tasteful emojis when they genuinely help emphasis. Across a set of LinkedIn posts, include them in roughly half the posts. Never stack or spam them.
        - Reddit: write like a thoughtful self-post from someone who has actually wrestled with the issue; curious, grounded, not promotional, and usually 60-120 words.
        - Reddit: default to no emoji. Use at most one only if it still feels like a real human post, not marketing.
        - Reddit titles should sound like something a real person would post, not a marketing headline.

        TARGET SURFACES
        - {surface_lines}

        BLOG TITLE
        {blog_title}

        BLOG MARKDOWN
        {blog_markdown}

        INSIGHTS
        {insight_lines}

        Return strict JSON only with this shape:
        {{
          "surfaces": [
            {{
              "platform": "linkedin|facebook|instagram|tiktok|reddit",
              "sequence": 1,
              "body": "string",
              "reddit_title": "string optional"
            }}
          ]
        }}
        """
    ).strip()
