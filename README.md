# Options Toolkit

A small, learning-oriented toolkit for evaluating stock-option strategies and
gauging whether volatility is rich or cheap. It has a point-and-click **web GUI**
and the original **command-line scripts** — both share the same math engine, so
they always agree.

- **Options Evaluator** — Greeks, max profit/loss, breakevens, probability of
  profit, a payoff chart, and an Excel export for a single strategy
  (`long_call`, `cash_secured_put`, or `covered_call`).
- **Vol Scanner** — compares the option's implied volatility against the stock's
  realized volatility to flag "rich" (favor selling) vs. "cheap" (favor buying).

No brokerage account or API key is required: enter the numbers from any option
chain by hand, and (optionally) pull free daily price history from Stooq for the
vol scanner.

## Run it locally

This project uses [uv](https://docs.astral.sh/uv/) to manage Python and
dependencies. It works the same on Windows, macOS, and Linux.

```bash
# 1. Install uv once (see https://docs.astral.sh/uv/ for platform options)
#    macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
#    Windows:     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. From the project folder — installs Python 3.14 + all libraries
uv sync

# 3. Launch the GUI (opens in your browser)
uv run streamlit run app.py
```

Prefer the script workflow? Edit the CONFIG block in `evaluate.py` and run
`uv run python evaluate.py` (see `HOW_TO_USE.md`).

## Share it on the web (Streamlit Community Cloud)

You can host the GUI for free so others use it in a browser with nothing to
install.

1. Push this repo to GitHub (already done).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. Click **New app**, choose this repository, the branch, and set the main file
   to `app.py`.
4. Click **Deploy**. Community Cloud detects `uv.lock` and runs `uv sync` to
   install the exact pinned dependencies, then serves the app at a public
   `https://<your-app>.streamlit.app` URL. Every push to the branch
   auto-redeploys.

**Note on repo visibility:** the free Community Cloud tier only deploys **public**
repositories. This repo is currently private, so to share it for free you would
either make it public or invite collaborators (who then run it locally).
Deploying a private repo requires a paid Streamlit plan.

## Files

- `app.py` — the combined web GUI (both tools).
- `evaluate.py` — the edit-and-run script for a single strategy.
- `options_evaluator.py` — the pricing/Greeks engine (shared by the GUI and script).
- `vol_scanner.py` — implied-vs-realized volatility scanner.
- `HOW_TO_USE.md` — step-by-step usage guide.
- `pyproject.toml` / `uv.lock` — the uv project (Python 3.14 + libraries).
- `.streamlit/config.toml` — app theme and settings.
