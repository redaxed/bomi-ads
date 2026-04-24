# Daily Ads Report

Use this skill to create Bomi's daily Google Ads report.

## Workflow

1. Run from the `bomi-ads` checkout or a Codex automation worktree for `bomi-ads`.
2. Use the previous full calendar day in the Google Ads account timezone.
3. Generate a report comparing:
   - Primary day
   - Prior day
   - Same weekday last week
   - Last 7 full days ending on the primary day
4. Save the report as `reports/YYYY-MM-DD-daily-ads-report.md`.
5. If live API access fails, save a transparent blocked report instead of presenting stale metrics as live.

## Command

```sh
python3 scripts/google_ads_daily_report.py
```

The script loads credentials from:

1. `.env` in the current checkout, if present.
2. `/Users/dax/bomi/bomi-ads/.env`, the local source-of-truth ignored env file.

Do not copy credentials into automation worktrees or commit `.env`.
