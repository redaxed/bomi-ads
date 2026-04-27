# Daily Ads Report

Use this skill to create Bomi's daily Google Ads report.

## Workflow

1. For the scheduled Codex cron, keep `execution_environment = local` and run `/Users/dax/.codex/automations/ads-report/run.sh`. The publisher script uses an automation-owned local clone so the run is isolated from whatever branch is checked out at `/Users/dax/bomi/bomi-ads`.
2. Use the previous full calendar day in the Google Ads account timezone.
3. Generate a report comparing:
   - Primary day
   - Prior day
   - Same weekday last week
   - Last 7 full days ending on the primary day
   - Primary-day performance grouped by inferred state
4. Save the report, Slack summary, and chart artifacts:
   - `reports/YYYY-MM-DD-daily-ads-report.md`
   - `reports/YYYY-MM-DD-daily-ads-slack.md`
   - `reports/YYYY-MM-DD-daily-ads-chart.svg`
5. Commit and push the generated artifacts to `main` in `bomi-ai/bomi-ads` when any of them changed.
6. Post the generated Slack summary to Slack `#gtm` (`C0AUU3KTJ6P`) as the connected Slack user.
7. If live API access fails, still save, commit, push, and post a transparent blocked report instead of presenting stale metrics as live.

## Command

For automation, run:

```sh
/Users/dax/.codex/automations/ads-report/run.sh
```

For a manual local-only report generation check, run:

```sh
python3 scripts/google_ads_daily_report.py
```

The script loads credentials from:

1. `.env` in the current checkout, if present.
2. `/Users/dax/bomi/bomi-ads/.env`, the local source-of-truth ignored env file.

Do not copy credentials into automation clones or commit `.env`.

## Commit

The automation publisher script handles this step. If publishing manually, stage only the generated dated report artifacts and commit them if they changed:

```sh
git add reports/YYYY-MM-DD-daily-ads-report.md reports/YYYY-MM-DD-daily-ads-slack.md reports/YYYY-MM-DD-daily-ads-chart.svg
git diff --cached --quiet || git commit -m "Update ads report for YYYY-MM-DD"
git push origin HEAD:main
```

If there are no staged changes, skip the commit and push. If the push is rejected because `main` moved, fetch/rebase and retry without discarding the generated report.

Use local shell/git for publishing. Do not use the GitHub app, GitHub connector, MCP GitHub tools, the GitHub contents API, or create-blob/update-file flows for this automation.

## Slack

Post the exact contents of `reports/YYYY-MM-DD-daily-ads-slack.md` to `#gtm` (`C0AUU3KTJ6P`). The generated summary uses Slack mrkdwn, including:

- bold section labels with single asterisks
- spend, clicks, conversions, CPA, and prior-day deltas
- a monospace mini chart that renders reliably in Slack
- a primary-day state breakdown grouped from campaign names
- links to the committed report and SVG chart

Keep the Slack message brief and do not include secrets, credential paths, or raw OAuth/API errors beyond the high-level blocker.
