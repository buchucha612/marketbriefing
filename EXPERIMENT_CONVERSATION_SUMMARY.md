# Conversation Summary for LLM/Coding-Agent Analysis

Date: 2026-07-19  
Project path: `D:\PYTHON\news-dashboard`  
Experiment purpose: Compare codebases produced by similar prompts across different LLM/coding-agent sessions.

## 1. Initial user goal

The user wanted to build a webpage that summarizes domestic Korean stock market conditions and overseas stock market conditions every day.

The user explicitly asked for codebase references, not data references.

Initial framing:

- Daily webpage.
- Domestic and overseas stock market status.
- Need suitable implementation references.
- User was interested in structure, but concerned about over-engineering.

## 2. Reference research outcome

The assistant searched for codebase references and recommended several categories:

### Larger architecture references

- `ZhuLinsen/daily_stock_analysis`
  - Multi-market stock analysis system.
  - Python backend, React/TypeScript frontend, FastAPI API, report history, scheduler, LLM analysis.
  - Considered useful as an architecture reference but too large for the initial MVP.

- `Benboerba620/daily-watchlist`
  - Daily watchlist/report workflow.
  - Better fit for a lightweight MVP.

- `lihor-hub/news-dashboard`
  - FastAPI + React + PostgreSQL news dashboard with AI briefing.
  - Useful later for search/history/briefing UX.

### UI/dashboard references

- `mohsinds/market-dashboard`
- `Spaghetih/lumina-invest`
- `codeperfectplus/Stock-Dashboard`
- `paduel/streamlit_finance_chart`

### Korean market adapter references

- `sharebook-kr/pykrx`
- `sharebook-kr/pykrx-mcp`
- `unohee/kis-agent`

## 3. Over-engineering discussion

The user asked whether the initial recommendation was over-engineered.

The assistant concluded:

- Yes, the initial architecture was closer to a final research platform.
- For MVP, avoid:
  - FastAPI + React + PostgreSQL + Scheduler + Auth from the start.
  - Complex provider fallbacks.
  - LLM agents and trading strategies.
  - Notifications and real-time features.

Recommended MVP shape at that point:

```text
1 daily script
  -> collect domestic/overseas market data
  -> collect headlines
  -> generate JSON/Markdown
  -> render webpage
```

## 4. User requirement shift: autonomous AI workflow

The user wanted the AI to work autonomously without losing context, following a staged plan.

The assistant recommended writing operating documents into the repository:

- `PROJECT_PLAN.md`
- `TASKS.md`
- `DECISIONS.md`
- `IMPLEMENTATION_LOG.md`

Core operating rule:

- At the start of each work session, the AI should read plan/task/decision docs.
- After making changes, the AI should update task/log docs.
- Important technical decisions should be recorded.

## 5. First implementation

The assistant created a minimal file-based static MVP.

Files created:

- `PROJECT_PLAN.md`
- `TASKS.md`
- `DECISIONS.md`
- `IMPLEMENTATION_LOG.md`
- `README.md`
- `.gitignore`
- `scripts/generate_report.py`
- `config/market_snapshot.example.json`
- `data/reports/.gitkeep`
- `public/.gitkeep`

Initial architecture:

```text
config/market_snapshot.json
  -> scripts/generate_report.py
  -> data/reports/YYYY-MM-DD.json
  -> public/index.html
```

Initial behavior:

- If `config/market_snapshot.json` exists, read it.
- Otherwise generate fallback report.
- Render `public/index.html`.
- No database, no server, no auth, no LLM.

Validation performed:

```powershell
python -m py_compile scripts/generate_report.py
python scripts/generate_report.py --date 2026-07-19
```

Observed output:

- `data/reports/2026-07-19.json`
- `public/index.html`
- `status=needs_data`

Issue encountered:

- PowerShell output displayed Korean text incorrectly.
- Python UTF-8 parsing later confirmed JSON content was readable, but subsequent file-writing through PowerShell stdin did corrupt some Korean literals into `?`.

## 6. User clarification: no LLM summary needed

The user clarified:

- Summary is not needed.
- The page only needs to dynamically display major headlines.
- LLM does not need to be attached.

The assistant explained that current code was still report/summary-oriented and used placeholders.

Current placeholder/fallback behavior at that point:

- `config/market_snapshot.example.json` contained dummy sample market/index/headline data.
- `fallback_snapshot()` in `scripts/generate_report.py` generated missing-data placeholder content.

The user then asked how to plan so that every step remains runnable.

## 7. Runnable-invariant planning

The assistant proposed a runnable-invariant workflow.

Main invariant:

```powershell
python scripts/generate_report.py
```

Every completed step must produce:

- `data/reports/YYYY-MM-DD.json`
- `public/index.html`

External source failures must not break the command.

Planning principle:

- Do not plan by horizontal layers such as data collector, renderer, UI, tests.
- Plan by thin vertical slices that are runnable after every step.

Good staged approach:

```text
1. Static fallback headline page runs.
2. Local JSON headline input runs.
3. RSS fetch failure still runs.
4. Domestic RSS source runs.
5. Overseas RSS source runs.
6. Multiple sources merge/dedupe while still running.
```

The user asked to proceed.

## 8. Conversion to headline-first implementation

The assistant converted the project from summary/report-first to headline-first.

Major changes:

- Rewrote `PROJECT_PLAN.md` around headline dashboard MVP.
- Rewrote `TASKS.md` with runnable invariant.
- Rewrote `DECISIONS.md` to record LLM exclusion.
- Rewrote `README.md`.
- Replaced summary-oriented model with headline-first schema.
- Added `config/headlines.example.json`.
- Removed obsolete `config/market_snapshot.example.json`.

Headline schema:

```json
{
  "title": "headline title",
  "url": "https://example.com/article",
  "source": "source name",
  "market": "domestic",
  "published_at": "2026-07-19T09:00:00+09:00"
}
```

Updated behavior:

- Read `config/headlines.json` if present.
- Otherwise render fallback headlines.
- Write JSON snapshot and static HTML page.

Important implementation correction:

- Some Korean literals were corrupted during PowerShell-to-Python stdin writing.
- The assistant recovered by storing most runtime strings in ASCII and using Python Unicode escapes for Korean section labels:
  - `?? ?? ????`
  - `?? ?? ????`

Validation after conversion:

```powershell
python -m py_compile scripts/generate_report.py
python scripts/generate_report.py --date 2026-07-19
```

Result:

- `status=needs_source`
- fallback headlines rendered successfully.

## 9. RSS fetcher implementation

The user asked to proceed with the next step.

The assistant implemented RSS/Atom fetching.

Files changed:

- `scripts/generate_report.py`
- `config/sources.example.json`
- `README.md`
- `PROJECT_PLAN.md`
- `TASKS.md`
- `IMPLEMENTATION_LOG.md`
- `.gitignore`

RSS source config shape:

```json
{
  "timeout_seconds": 5,
  "max_items_per_source": 8,
  "sources": [
    {
      "name": "Example Domestic RSS",
      "market": "domestic",
      "url": "https://example.com/domestic/rss.xml"
    },
    {
      "name": "Example Overseas RSS",
      "market": "overseas",
      "url": "https://example.com/overseas/rss.xml"
    }
  ]
}
```

Implemented features:

- `config/sources.json` support.
- RSS fetch using Python standard library:
  - `urllib.request`
  - `xml.etree.ElementTree`
- User-Agent header.
- Timeout.
- RSS item parsing.
- Atom entry parsing.
- Published date normalization via `email.utils.parsedate_to_datetime`.
- Local + RSS headline merge.
- Dedupe by URL, otherwise by market/title.
- Max item limit per source and per market.
- `--no-rss` option for deterministic runs.
- External fetch/parse failures are warnings, not fatal.

Validation:

```powershell
python -m py_compile scripts/generate_report.py
python scripts/generate_report.py --date 2026-07-19
python scripts/generate_report.py --date 2026-07-19 --no-rss
```

Also ran a network-free RSS XML fixture smoke test by importing `parse_feed()`.

Result:

- RSS parser smoke test passed.
- Representative command remained runnable.

## 10. Domestic RSS configuration

The user chose:

- Yonhap Economy
- Yonhap Market+

The assistant searched and confirmed RSS URLs from public sources:

- `https://www.yna.co.kr/rss/economy.xml`
- `https://www.yna.co.kr/rss/market.xml`

The assistant created local `config/sources.json` with these two domestic sources.

Config added:

```json
{
  "name": "Yonhap Economy",
  "market": "domestic",
  "url": "https://www.yna.co.kr/rss/economy.xml"
}
```

```json
{
  "name": "Yonhap Market+",
  "market": "domestic",
  "url": "https://www.yna.co.kr/rss/market.xml"
}
```

Validation:

```powershell
python scripts/generate_report.py --date 2026-07-19
```

Result:

- `status=ready`
- domestic headlines: 19
- overseas headlines: 0
- first source: `Yonhap Economy`

Then `--no-rss` was run and temporarily overwrote the same date file with fallback content, so the assistant reran the RSS-enabled command to restore final output.

## 11. Overseas RSS source recommendation

The user asked for overseas section source recommendations.

The assistant recommended these, with preference order:

1. Investing.com Stock Market News
   - `https://www.investing.com/rss/news_25.rss`
   - Main overseas stock-market headline source.

2. Investing.com Economy News
   - `https://www.investing.com/rss/news_14.rss`
   - Macro/economy context.

3. CNBC Market Insider
   - `https://www.cnbc.com/id/20409666/device/rss/rss.html?x=1`
   - Market/trading supplement.

4. CNBC Economy
   - `https://www.cnbc.com/id/20910258/device/rss/rss.html`
   - US economy supplement.

The assistant recommended starting with the two Investing.com feeds because they are more directly aligned with stock-market/macro headlines and fit the current RSS fetcher.

## 12. Overseas RSS configuration

The user approved proceeding.

The assistant added these sources to `config/sources.json`:

```json
{
  "name": "Investing.com Stock Market News",
  "market": "overseas",
  "url": "https://www.investing.com/rss/news_25.rss"
}
```

```json
{
  "name": "Investing.com Economy News",
  "market": "overseas",
  "url": "https://www.investing.com/rss/news_14.rss"
}
```

Validation:

```powershell
python scripts/generate_report.py --date 2026-07-19
python -m py_compile scripts/generate_report.py
```

Generated JSON verification:

- `status=ready`
- domestic headlines: 19
- overseas headlines: 20
- warnings: 0
- first overseas source: `Investing.com Stock Market News`

## 13. Current project state

Current project is not Streamlit.

It is a static HTML generation pipeline:

```text
RSS sources
  - Yonhap Economy
  - Yonhap Market+
  - Investing.com Stock Market News
  - Investing.com Economy News
      -> python scripts/generate_report.py
      -> data/reports/YYYY-MM-DD.json
      -> public/index.html
```

How to generate/update:

```powershell
python scripts/generate_report.py
```

How to view directly:

```powershell
Start-Process public\index.html
```

How to view through a local server:

```powershell
python -m http.server 8000 -d public
```

Then open:

```text
http://localhost:8000
```

## 14. Current source files of interest

Primary implementation:

- `scripts/generate_report.py`

Config:

- `config/sources.json`
- `config/sources.example.json`
- `config/headlines.example.json`

Generated output:

- `data/reports/2026-07-19.json`
- `public/index.html`

Operating docs:

- `PROJECT_PLAN.md`
- `TASKS.md`
- `DECISIONS.md`
- `IMPLEMENTATION_LOG.md`
- `README.md`

## 15. Current validation commands

Baseline runnable invariant:

```powershell
python scripts/generate_report.py
```

Date-pinned validation:

```powershell
python scripts/generate_report.py --date 2026-07-19
```

Syntax check:

```powershell
python -m py_compile scripts/generate_report.py
```

Deterministic no-network run:

```powershell
python scripts/generate_report.py --no-rss
```

## 16. Important engineering constraints and lessons

### Always-runnable strategy

The project intentionally uses one command as the invariant:

```powershell
python scripts/generate_report.py
```

All future tasks should preserve this command.

### External failures are non-fatal

RSS failures should produce warnings, not stop page generation.

### No LLM in MVP

The user explicitly stated LLM summarization is unnecessary.

### Static first

The project does not currently run as Streamlit/FastAPI/React. This is intentional to keep the MVP simple.

### Encoding caution on Windows

Some PowerShell heredoc/stdin writing paths corrupted Korean literals into question marks. Future agents should avoid writing Korean literal-heavy code through fragile shell stdin. Safer options:

- Use Unicode escapes in Python source for critical Korean UI labels.
- Keep source code mostly ASCII.
- Use proper UTF-8-aware file writing if editing manually.
- Validate with Python `repr()` or JSON reads rather than relying only on PowerShell `Get-Content` rendering.

## 17. Next likely tasks

Recommended next steps for a coding agent:

1. Add tests using local RSS/Atom fixtures.
2. Add archive page for past reports.
3. Add a small local preview command or script.
4. Optionally convert to Streamlit only if the user wants a live dashboard experience.
5. Add scheduled execution documentation.
6. Improve UI density and headline metadata display.

## 18. Comparison points for the experiment

When comparing with another LLM/coding-agent's project, evaluate:

- Did it over-engineer with DB/auth/frameworks too early?
- Does it maintain a single runnable invariant?
- Does it handle RSS/network failure gracefully?
- Does it use config files cleanly for sources?
- Does it separate local/manual headlines from RSS sources?
- Does it deduplicate headlines?
- Does it avoid LLM dependency when the user said LLM is unnecessary?
- Is the generated output easy to view?
- Are implementation decisions captured in repo docs?
- Are validation results recorded?
- Does it preserve user intent changes over time?
