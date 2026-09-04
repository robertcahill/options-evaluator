# Options Evaluator — Quick Start

## Two ways to use it

- **GUI (easiest):** a point-and-click app that combines BOTH tools (the strategy
  evaluator and the vol scanner) in one window. Launch it with:

      uv run streamlit run app.py

  A browser tab opens. Fill in the fields, click the button, read the results,
  and download the Excel/PNG. Nothing to edit. Works the same on Windows and Mac.

- **Scripts (edit-and-run):** the original workflow, described below. You edit the
  numbers in `evaluate.py` and run it from the terminal.

## Your repeatable process (4 steps, ~2 minutes)

1. Open **thinkorswim** → Trade tab → pull up your ticker → look at the option chain.
2. Open **evaluate.py** in Cursor. Edit the CONFIG box at the top:
   - TICKER, STOCK_PRICE, STRIKE, BID, ASK, DTE, IV_PERCENT
   - Uncomment the STRATEGY you want (long_call / cash_secured_put / covered_call)
   - Optional: IV_PERCENTILE (0–100) and DIVIDEND_YIELD_PERCENT
3. Run it from this folder: `uv run python evaluate.py`
   (first time, also: `Ctrl+Shift+P` → Python: Select Interpreter → pick `.venv`)
4. Read the console summary; open the saved .xlsx and _payoff.png for the visual.

That's the whole loop. You only ever edit **evaluate.py**. You never touch
**options_evaluator.py** (that's the engine) unless you're adding a new strategy.

## The numbers, and where they are on the TOS chain

| Field | Where on thinkorswim |
|--------------|--------------------------------------------------------|
| STOCK_PRICE  | the underlying quote at the top                        |
| STRIKE       | the Strike column                                      |
| BID / ASK    | Bid/Ask columns on **that contract's row** (calls left, puts right) |
| DTE          | the (number) in parentheses next to the expiration row |
| IV_PERCENT   | **that contract's IV on the chain row** — not the blended "Implied Volatility" on Today's Options Statistics |
| IV_PERCENTILE (optional) | "Current IV Percentile" in Today's Options Statistics. Context only (buy vs sell lean). Not used in the math. |
| DIVIDEND_YIELD_PERCENT (optional) | annual yield, e.g. 1.2. Leave 0 if you don't want to model it. |

If typed IV and "IV from mid" in the console differ by more than ~3 vol points, the IV and the quote probably didn't come from the same row.

## The one number that decides buy vs. sell: IV Percentile
- **LOW percentile (options cheap)**  -> favor BUYING premium (long_call)
- **HIGH percentile (options rich)**  -> favor SELLING premium (CSP / covered call)

## How to read the new outputs
- **Max profit / max loss** are from the trade's shape (including stock-to-zero), not from the chart window. "Unlimited" means the expiration slope never caps.
- **Prob. of profit** is risk-neutral: lognormal at expiry, measured from the breakeven(s). Not `1 − delta`.
- **Capital / ROC** is cash to put the trade on (debit, cash-secured strike, or stock minus credit).
- **Model vs mid / IV from mid** should nearly match if IV and the quote are from the same row. A gap is an input warning, not a free lunch.
- **Chart:** solid line = expiration; dashed = T+0 mark with IV held constant; shaded band = 1σ expected move (`S × IV × √T`). The ±40% zoom is the picture only.

## Files
- **app.py**               <- the GUI (both tools in one window): `uv run streamlit run app.py`
- **evaluate.py**          <- you edit this daily (script workflow)
- **options_evaluator.py** <- the engine (leave alone; read to learn)
- **vol_scanner.py**       <- IV vs realized vol (rich/cheap)
- **pyproject.toml**       <- this folder's uv project (Python 3.14 + libraries)
- HOW_TO_USE.md            <- this file

Run any script the same way: `uv run python vol_scanner.py`

## Next steps (later)
- Learn: build a vertical spread yourself (see the note at the bottom of
  options_evaluator.py). It's the naked-call-vs-spread lesson, made real.
- Automate: Phase 2 wires in the Schwab API so the 5 numbers pull automatically
  instead of being typed. Do the manual version first so you know what it does.
