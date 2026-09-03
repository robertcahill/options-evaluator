"""
================================================================================
  OPTIONS EVALUATOR — YOUR CONTROL PANEL
================================================================================
  THE ONLY FILE YOU TOUCH DAY-TO-DAY.

  Your entire job: edit the numbers in the CONFIG box below (read them off the
  thinkorswim option chain), then run:

      uv run python evaluate.py

  Everything else is automatic.

  The five things to read off the TOS chain for any contract:
      1. STRIKE          -> the strike column
      2. BID and ASK     -> the model uses the midpoint automatically
      3. EXPIRATION days  -> the number in (parentheses) next to the expiry row
      4. STOCK price     -> the underlying quote at the top
      5. IV              -> the IV on THAT CONTRACT'S ROW, not the blended
                            "Implied Volatility" on Today's Options Statistics
================================================================================
"""

from options_evaluator import (long_call, cash_secured_put, covered_call,
                               print_summary, make_payoff_chart, export_excel)

# ==============================================================================
#  CONFIG  —  EDIT THESE, THEN RUN.  (This is the whole workflow.)
# ==============================================================================

TICKER      = "MRVL"     # just a label for the output files
STOCK_PRICE = 216.0      # underlying quote from TOS
RISK_FREE   = 0.045      # ~current risk-free rate (update occasionally)

# Optional. Dividend yield as a percent (e.g. 1.2 for 1.2%). 0 is fine.
DIVIDEND_YIELD_PERCENT = 0.0

# Optional. "Current IV Percentile" from Today's Options Statistics (0-100).
# Does not enter the math — it only prints a buy-vs-sell lean.
IV_PERCENTILE = None     # e.g. 72

# --- Read these off the chain ROW for the ONE contract you're evaluating ---
STRIKE      = 220        # strike price
BID         = 81.10      # bid  (calls on the left of the chain, puts on the right)
ASK         = 83.20      # ask
DTE         = 658        # days to expiry — the (number) in the TOS expiry row
IV_PERCENT  = 62.84      # THIS contract's IV, as the % on that row (62.84 = 62.84%)

# --- Which strategy? Uncomment ONE. -------------------------------------------
STRATEGY = "long_call"          # buy a call (directional / convexity)
# STRATEGY = "cash_secured_put"   # SELL a put for income
# STRATEGY = "covered_call"       # own shares + SELL a call for income

# --- Only needed for covered_call: what you paid / would pay for the shares ---
STOCK_ENTRY = 216.0

# ==============================================================================
#  Everything below is automatic — you don't need to edit it.
# ==============================================================================

def _as_decimal_iv(value):
    """Accept 62.84 or 0.6284. Values > 1.5 are treated as percents."""
    if value < 0:
        raise ValueError(f"IV cannot be negative (got {value})")
    return value / 100.0 if value > 1.5 else float(value)


def _as_percentile(value):
    if value is None:
        return None
    if 0 <= value <= 1:
        return value * 100.0
    if 0 <= value <= 100:
        return float(value)
    raise ValueError(f"IV_PERCENTILE should be 0-100 (got {value})")


if DTE <= 0:
    raise ValueError(f"DTE must be a positive number of days (got {DTE})")

bid, ask = BID, ASK
if bid > ask:
    print(f"WARNING: bid {bid} > ask {ask} - swapping them.")
    bid, ask = ask, bid

mid = (bid + ask) / 2
iv  = _as_decimal_iv(IV_PERCENT)
q   = float(DIVIDEND_YIELD_PERCENT) / 100.0
pct = _as_percentile(IV_PERCENTILE)

kwargs = dict(r=RISK_FREE, q=q, iv_percentile=pct)

if STRATEGY == "long_call":
    strat = long_call(STOCK_PRICE, STRIKE, iv, mid, DTE, **kwargs)
elif STRATEGY == "cash_secured_put":
    strat = cash_secured_put(STOCK_PRICE, STRIKE, iv, mid, DTE, **kwargs)
elif STRATEGY == "covered_call":
    if STOCK_ENTRY <= 0:
        raise ValueError("covered_call needs STOCK_ENTRY (what you pay for the shares).")
    strat = covered_call(STOCK_PRICE, STOCK_ENTRY, STRIKE, iv, mid, DTE, **kwargs)
else:
    raise ValueError(f"Unknown STRATEGY: {STRATEGY}")

print_summary(strat)

tag = f"{TICKER}_{STRIKE}_{STRATEGY}"
export_excel(strat, f"{tag}.xlsx")
make_payoff_chart(strat, f"{tag}_payoff.png")
print(f"Saved: {tag}.xlsx  and  {tag}_payoff.png")
