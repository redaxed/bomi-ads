# Agent Notes For Bomi Ads

This repo contains ad automation and live ad handoff context. Treat any Meta, Google Ads, or Slack publishing operation as production-adjacent work.

## Meta Ads

- Start with `META_ADS_INFO.md` for current Meta context.
- For any specific live ad, read that ad's `INFO.md` before making changes.
- Current per-ad folders live under `assets/bomi_bcbs_scammas/`.
- Never print, commit, or store `META_ACCESS_TOKEN` or other secrets.
- Use `#` comments in `.env` files, not `//`.
- Use `/Users/dax/.cache/bomi-ads-venv/bin/python` for Meta API scripts unless the environment has been intentionally changed.
- Create Meta campaigns/ad sets/ads paused first; activate only after all objects exist and the user has requested activation/spend.
- After every Meta ad creation, create a sibling per-ad folder with an `INFO.md`, then update `META_ADS_INFO.md`.
- Read back `status`, `effective_status`, budget, targeting, and creative/ad IDs after any spend-affecting change.

## Moda Social Asset Generation

Use Moda when the user wants generated social/ad visuals, creative variants, feed/story/carousel assets, or a polished asset from Bomi copy.

- Credentials live only in local `.env`. Current local names are `MODI_APP_KEY` for the Moda REST API key and `MODA_WEBHOOK` for webhook signature verification. Do not print, commit, or copy these values. If a tool or helper expects `MODA_API_KEY`, map it from `MODI_APP_KEY` in the process environment instead of editing `.env` into another committed file.
- Official REST base URL: `https://api.moda.app/v1`.
- Always send `Authorization: Bearer $MODI_APP_KEY` and pin `Moda-Version: 2026-05-01`.
- If API behavior is unclear, read the official docs first: `https://docs.moda.app/llms.txt`, then the relevant API reference pages for authentication, uploads, tasks, canvases/exports, brand kits, and webhooks.
- Do a small read-only preflight before generation: `GET /credits` to confirm credits and `GET /brand-kits?limit=20` to see whether Bomi has a default brand kit. If no brand kit exists, attach Bomi logo/site assets and include brand guidance in the prompt.
- Upload usable source assets before the task. Use `POST /uploads/from-url` for public URLs; use multipart `POST /uploads` for local files when needed. Pass uploaded files to tasks with explicit roles:
  - `asset` for logos, product screenshots, or images that should be used directly.
  - `reference` for images/canvases that should influence style or layout.
  - `source` for briefs, PDFs, or docs that Moda should extract content from.
- Start generation with `POST /tasks`. For social media, include `format: {"category": "social", "width": 1080, "height": 1080}` for square feed assets, `1080x1350` for 4:5 feed assets, and `1080x1920` for stories/reels. For multi-page posts, use `category: "carousel"` with `dimensions` and `page_count` instead of hand-rolling separate canvases.
- Include a stable `idempotency_key` such as `bomi-social:<campaign-or-topic>:<format>:<date-or-version>` so retries do not accidentally spend twice.
- Use `model_tier: "lite"` for quick drafts and smoke tests. Use `standard` or `pro` when the user is asking for a final production-quality asset or multiple nuanced variants.
- Prompt like a creative brief, not a vague image prompt. Include audience, platform, objective, offer, headline, supporting copy, CTA, required/forbidden claims, brand tone, visual constraints, and exact text that must appear. For Bomi, keep healthcare claims conservative and avoid fake guarantees.
- Poll `GET /tasks/{task_id}` until `status` is terminal. On success, read `result.canvas_id` and `result.canvas_url`.
- Export with `POST /canvases/{canvas_id}/export?format=png&page_number=1&pixel_ratio=2`. If the response is `in_progress`, poll `/canvases/{canvas_id}/export-status?task_id=...`.
- Download the signed export URL immediately; it expires. Save generated repo-local previews under ignored generated asset paths such as `troff/app/static/generated/cards/` unless the user asks for a committed asset.
- Verify the downloaded file with `file` and visual inspection. Moda may return JPEG bytes for an image export; name the local file to match actual content.
- For webhook-driven production flows, `MODA_WEBHOOK` is a signing secret, not the API key. Verify `X-Webhook-Signature` using HMAC-SHA256 over `{timestamp}.{raw_request_body}` with `X-Webhook-Timestamp`; reject stale timestamps and handle duplicate event IDs idempotently.
- Do not publish or spend ad budget just because an asset was generated. Treat Moda output as creative material that still needs review before live ad creation or activation.

## Standing Safety Posture

- Prefer read-only audits before writes.
- Validate or stage paused where the platform supports it.
- Do not increase budgets, broaden targeting, pause active ads, or create new spend without a clear user request.
- Keep `.env` local and ignored.
