# Market Briefing Runbook

## Manual Update

Run this from the project root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\update_market_briefing.ps1
```

This updates:

- `storage/raw/news_dynamic.json`
- `storage/raw/prices_dynamic.json`
- `storage/daily/daily_market_briefing.json`
- `serving/daily_market_briefing.json`
- `serving/briefing-data.js`
- `outputs/market-briefing-mvp/*`

Logs are written to:

```text
logs\market_briefing_update.log
```

## Register 30-Minute Windows Schedule

Run this once:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_30min_task.ps1
```

This creates a Windows Task Scheduler task named:

```text
MarketBriefingUpdateEvery30Min
```

The task runs `scripts/update_market_briefing.ps1` every 30 minutes.

## Remove The Schedule

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\unregister_task.ps1
```

## View The Page

Open:

```text
outputs\market-briefing-mvp\index.html
```
