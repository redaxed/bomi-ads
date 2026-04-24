# Troff

Troff is a self-hosted content queue for one operator or one team. In `bomi-ads`, it is the Bomi content workflow for moving one SEO question into a landing blog post and a set of social posts.

The main idea is simple:

1. Start with a `question` or a `source URL`.
2. Generate one landing-ready blog draft.
3. Extract 3-5 key insights from the blog.
4. Generate channel-native social drafts from those insights.
5. Review and edit the package by hand.
6. Queue each piece for the right channel.
7. Publish on a steady schedule.

Instead of trying to be a full content operating system, Troff is best understood as:

- a draft machine
- a review screen
- a per-channel queue
- a lightweight publishing worker

## Core loop

Troff turns one idea into one reusable package:

`question or URL -> blog draft -> 3-5 insights -> social drafts -> review -> queue -> publish`

MVP packages include:

- 1 blog post
- 3-5 LinkedIn drafts
- 3-5 Reddit drafts
- optional generated media cards for selected social surfaces

The human stays in control of approval and editing. The app handles the queue, retries, and publishing attempts.

AI voice is shaped by the Polymath Biller prompt in `app/services/prompting.py`, with optional env overrides for default word count, audience, and POV.

## What belongs in v1

- Single-user or single-team workflow
- Author profile / voice settings
- Manual review before publish
- One item per surface per day
- Retry and dead-letter handling
- Traceability from idea to published outputs

## What this is not

- A multi-user CMS
- A social analytics suite
- A complex campaign planner
- A fully autonomous content bot

## Pages

- `/` dashboard
- `/questions` idea backlog and generate-now flow
- `/authors` author profiles
- `/packages/{id}` package review and editing
- `/queue/{surface}` per-surface queue management
- `/pipeline` lineage view
- `/failures` failed jobs and inbox

## Integrations

- Postiz for LinkedIn, Facebook, Instagram, and TikTok
- Postiz for Reddit publishing
- Optional media card generation and GCS or public URL hosting
- Optional blog publish flow into a landing repo

## Quick start

1. Copy the env file:

```bash
cp .env.example .env
```

2. Set the MVP env values you actually need:

- `ENABLED_SURFACES=blog,linkedin,reddit`
- `ENABLE_SCHEDULER=false`
- `LANDING_REPO_PATH=/Users/dax/bomi/landing`
- `OPENAI_API_KEY`
- `POSTIZ_API_KEY`
- `POSTIZ_INTEGRATION_LINKEDIN`
- `POSTIZ_INTEGRATION_REDDIT`
- Optional: `ENABLE_MEDIA_CARDS=true`
- Optional: `MEDIA_CARD_SURFACES=linkedin,facebook,instagram,tiktok`
- Optional: `MEDIA_PROVIDER=gcs`, `GCS_BUCKET`, and `GCS_PUBLIC_BASE_URL`
- Optional: `MEDIA_CARD_OUTPUT_DIR=app/static/generated/cards` for locally served card previews
- Optional: `BLOG_WORD_COUNT`, `BLOG_DEFAULT_AUDIENCE`, `BLOG_DEFAULT_POV`

3. Create a local venv and install dependencies:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
```

4. Start the app locally:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8080
```

5. Open [http://localhost:8080](http://localhost:8080)

## Local testing

Run tests from the project root with:

```bash
.venv/bin/pytest -q
```

## Scheduling and retries

- Use `/run-dispatch` for manual-first MVP testing
- Scheduler can be enabled later with `ENABLE_SCHEDULER=true`
- Queue order is FIFO unless you reorder it in the UI
- Blocked items can be skipped
- Retry backoff is `1m`, `10m`, `60m`
- Terminal failures move to the dead-letter view

## Media cards

Troff can generate square text cards from each extracted insight and attach those card URLs to social posts. Keep `ENABLE_MEDIA_CARDS=false` for text-only drafts. Turn it on after configuring either:

- GCS upload with `MEDIA_PROVIDER=gcs`, `GCS_BUCKET`, and Google credentials.
- Existing public hosting with `PUBLIC_MEDIA_BASE_URL`, where generated files are served from the configured base URL.
- Local static previews with `MEDIA_PROVIDER=local` and `MEDIA_CARD_OUTPUT_DIR=app/static/generated/cards`.

The package review page also has a `Generate Missing Media Cards` action, so you can turn media on later and backfill assets for an already-generated package.
