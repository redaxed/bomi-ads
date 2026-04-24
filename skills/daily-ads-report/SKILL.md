# Daily Ads Report

Use this skill to create Bomi's daily Google Ads report.

## Workflow

1. Run from the local `bomi-ads` checkout at `/Users/dax/bomi/bomi-ads`. Keep the Codex cron automation on `execution_environment = local`; worktree mode has failed DNS and GitHub push access on this machine.
2. Use the previous full calendar day in the Google Ads account timezone.
3. Generate a report comparing:
   - Primary day
   - Prior day
   - Same weekday last week
   - Last 7 full days ending on the primary day
4. Save the report as `reports/YYYY-MM-DD-daily-ads-report.md`.
5. Commit and push the report update to `main` in `redaxed/bomi-ads` when the report file changed.
6. Post a concise report summary to Slack `#gtm` (`C0AUU3KTJ6P`) as the connected Slack user.
7. If live API access fails, still save, commit, push, and post a transparent blocked report instead of presenting stale metrics as live.

## Command

```sh
python3 scripts/google_ads_daily_report.py
```

The script loads credentials from:

1. `.env` in the current checkout, if present.
2. `/Users/dax/bomi/bomi-ads/.env`, the local source-of-truth ignored env file.

Do not copy credentials into automation worktrees or commit `.env`.

## Commit

After generating the report, stage only the generated dated report file and commit it if it changed:

```sh
git add reports/YYYY-MM-DD-daily-ads-report.md
git diff --cached --quiet || git commit -m "Update ads report for YYYY-MM-DD"
git push origin HEAD:main
```

If there are no staged changes, skip the commit and push. If the push is rejected because `main` moved, fetch/rebase and retry without discarding the generated report.

## Slack

Post to `#gtm` (`C0AUU3KTJ6P`) with a short summary pulled from the report:

- report date
- spend, clicks, conversions, and CPA, or the live-data blocker if the pull failed
- campaign status note when Ohio/Indiana are present
- GitHub link to the committed report, when a commit was created or the report already exists on `main`

Keep the Slack message brief and do not include secrets, credential paths, or raw OAuth/API errors beyond the high-level blocker.
