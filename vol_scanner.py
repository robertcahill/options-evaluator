"""
================================================================================
  IMPLIED vs REALIZED VOLATILITY SCANNER  —  the "rich or cheap?" tool
================================================================================
  THE QUESTION THIS ANSWERS:
    Is the market's IMPLIED volatility (what options are pricing in) higher or
    lower than the stock's REALIZED volatility (how much it actually moves)?
      - IV >> realized  -> options are RICH  -> favor SELLING premium
      - IV << realized  -> options are CHEAP -> favor BUYING premium
    The gap (IV - realized) is the "variance risk premium." On average IV runs
    a bit above realized (sellers demand a premium), so what you're hunting is
    an UNUSUALLY wide or narrow gap.

  WHY THIS AND NOT JUST THE GREEKS:
    The Greeks tell you the SHAPE of what you're buying. This tells you whether
    it's a GOOD DEAL — by comparing the market's vol forecast (IV) against an
    INDEPENDENT reference (what the stock actually did). You judge a forecast
    against reality, not against another forecast.

  STRUCTURE (so you can follow / edit it):
    1. fetch_prices()      -> gets daily closes  [RUN THIS ON YOUR MACHINE]
    2. realized_vol()      -> annualized vol from those closes  [PURE MATH]
    3. scan()              -> compares realized vs the IV you supply  [PURE MATH]
    4. __main__            -> a demo using built-in sample data so you can SEE
                             the math work without any network.
================================================================================
"""

import numpy as np


# =============================================================================
# 1. FETCH — the ONLY part that needs the internet. Run on your own machine.
# =============================================================================
def fetch_prices(ticker):
    """
    Pull daily closing prices for `ticker` (free, no API key) from Stooq.
    Returns a list of closes, oldest -> newest.

    NOTE: this needs a working internet connection. It will run fine on your
    computer; it's blocked in the sandbox where this was built, which is why
    the demo below uses sample data instead. To use it for real, just call
    fetch_prices("MRVL") on your machine.
    """
    import urllib.request
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
    raw = urllib.request.urlopen(url, timeout=20).read().decode()
    rows = raw.strip().split("\n")[1:]        # skip header
    closes = [float(r.split(",")[4]) for r in rows if len(r.split(",")) >= 5]
    return closes


# =============================================================================
# 2. REALIZED VOLATILITY — pure math. This is the independent reference.
# =============================================================================
def realized_vol(closes, window=None):
    """
    Annualized realized (historical) volatility from a list of daily closes.

    HOW IT'S COMPUTED (standard method):
      - daily returns = ln(price_today / price_yesterday)   (log returns)
      - take the standard deviation of those daily returns
      - annualize by multiplying by sqrt(252)  (252 trading days/year)
    This is the same volatility unit as IV, so they're directly comparable.

    `window` = how many recent days to use (e.g. 30 for 30-day realized vol).
    None uses all supplied data.
    """
    closes = np.asarray(closes, dtype=float)
    if window:
        closes = closes[-(window + 1):]        # need window+1 prices for window returns
    log_returns = np.log(closes[1:] / closes[:-1])   # daily log returns
    daily_std = np.std(log_returns, ddof=1)          # sample standard deviation
    return daily_std * np.sqrt(252)                  # annualize


# =============================================================================
# 3. SCAN — compare realized vs the implied vol you read off the chain.
# =============================================================================
def scan(ticker, implied_vol, closes, windows=(20, 30, 60, 90)):
    """
    The rich/cheap verdict. `implied_vol` is the CONTRACT's IV (decimal, e.g.
    0.63) that you read off the option chain. `closes` is the price history.

    Prints realized vol over several lookback windows and the gap vs. IV, so
    you can see whether the market is pricing MORE or LESS movement than the
    stock has actually been delivering — and over what horizon.
    """
    print("=" * 60)
    print(f"  RICH / CHEAP SCAN:  {ticker}")
    print("=" * 60)
    print(f"  Implied volatility (from chain):  {implied_vol*100:5.1f}%")
    print("-" * 60)
    print(f"  {'Lookback':>10}   {'Realized':>9}   {'IV - RV':>8}   Read")
    print("-" * 60)
    for w in windows:
        if len(closes) < w + 1:
            continue
        rv = realized_vol(closes, window=w)
        gap = implied_vol - rv
        # A positive gap means IV is ABOVE realized = options relatively rich.
        if gap > 0.05:
            read = "RICH (favor selling)"
        elif gap < -0.05:
            read = "CHEAP (favor buying)"
        else:
            read = "~fair"
        print(f"  {w:>7}d   {rv*100:8.1f}%   {gap*100:+7.1f}%   {read}")
    print("-" * 60)
    print("  Positive IV-RV = market pricing MORE movement than the stock")
    print("  has delivered (rich). Negative = pricing LESS (cheap).")
    print("  NOTE: a wide premium can persist or widen — this is an edge,")
    print("  not a certainty. Realized vol is backward-looking; if you expect")
    print("  a catalyst (earnings), future vol may differ from both.")
    print("=" * 60)


# =============================================================================
# 4. DEMO — runs with built-in sample data so the MATH is visible with no network.
# =============================================================================
if __name__ == "__main__":
    # ---- Sample price path (simulated) so you can see the engine work. ----
    # On your machine you'd replace this with:  closes = fetch_prices("MRVL")
    np.random.seed(42)
    # simulate ~120 days of a stock around $216 with ~45% annualized real vol
    true_daily_vol = 0.45 / np.sqrt(252)
    rets = np.random.normal(0, true_daily_vol, 120)
    sample_closes = list(216 * np.exp(np.cumsum(rets)))

    print("\n[DEMO using SAMPLE data — on your machine, call fetch_prices('MRVL')]\n")
    # Suppose the chain shows this contract's IV at 63%:
    scan("MRVL (sample)", implied_vol=0.63, closes=sample_closes)

    print("\nHOW TO USE FOR REAL (on your machine):")
    print("  closes = fetch_prices('MRVL')")
    print("  scan('MRVL', implied_vol=0.63, closes=closes)")
    print("  (replace 0.63 with the contract's IV from the chain)")
