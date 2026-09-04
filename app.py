"""
================================================================================
  OPTIONS TOOLKIT — GUI (Streamlit)
================================================================================
  A point-and-click front end for the two command-line tools in this project,
  combined into one app because they serve the same end goal (decide whether an
  option trade is worth it, and whether volatility is rich or cheap):

    - Tab 1  "Options Evaluator"  wraps evaluate.py / options_evaluator.py
    - Tab 2  "Vol Scanner"        wraps vol_scanner.py

  Nothing here reimplements the math. It calls the exact same engine functions
  the scripts use, so the GUI and the scripts always agree.

  Run it (same on Windows, macOS, Linux):

      uv run streamlit run app.py

  A browser tab opens automatically. Edit the fields, click the button, read
  the results. No code editing required.
================================================================================
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from options_evaluator import (
    long_call, cash_secured_put, covered_call,
    make_payoff_chart, export_excel, _fmt_money,
)
import vol_scanner


st.set_page_config(page_title="Options Toolkit", page_icon="📈", layout="wide")


# ---------------------------------------------------------------------------
# Small input helpers (mirrors the parsing evaluate.py does).
# ---------------------------------------------------------------------------
def as_decimal_iv(value):
    """Accept 62.84 or 0.6284. Values > 1.5 are treated as percents."""
    if value < 0:
        raise ValueError(f"IV cannot be negative (got {value})")
    return value / 100.0 if value > 1.5 else float(value)


# ===========================================================================
# TAB 1 — OPTIONS EVALUATOR
# ===========================================================================
def render_evaluator():
    st.subheader("Evaluate a single option strategy")
    st.caption(
        "Read the numbers off the option chain row for the ONE contract you're "
        "looking at, pick a strategy, and get the Greeks, payoff, and downloads."
    )

    with st.form("evaluator"):
        c1, c2, c3 = st.columns(3)
        with c1:
            ticker = st.text_input("Ticker (label only)", value="MRVL")
            stock_price = st.number_input("Stock price ($)", min_value=0.01,
                                          value=216.0, step=1.0, format="%.2f")
            strategy = st.selectbox(
                "Strategy",
                ["long_call", "cash_secured_put", "covered_call"],
                format_func=lambda s: {
                    "long_call": "Long call (buy — directional/convexity)",
                    "cash_secured_put": "Cash-secured put (sell — income)",
                    "covered_call": "Covered call (own shares + sell call — income)",
                }[s],
            )
        with c2:
            strike = st.number_input("Strike ($)", min_value=0.01, value=220.0,
                                     step=1.0, format="%.2f")
            bid = st.number_input("Bid ($)", min_value=0.0, value=81.10,
                                  step=0.05, format="%.2f")
            ask = st.number_input("Ask ($)", min_value=0.0, value=83.20,
                                  step=0.05, format="%.2f")
        with c3:
            dte = st.number_input("Days to expiry (DTE)", min_value=1, value=658,
                                  step=1)
            iv_percent = st.number_input("IV for this contract (%)", min_value=0.0,
                                         value=62.84, step=0.5, format="%.2f")
            risk_free = st.number_input("Risk-free rate (%)", min_value=0.0,
                                        value=4.5, step=0.25, format="%.2f")

        c4, c5, c6 = st.columns(3)
        with c4:
            dividend_yield = st.number_input("Dividend yield (%)", min_value=0.0,
                                             value=0.0, step=0.1, format="%.2f")
        with c5:
            use_pct = st.checkbox("Provide IV percentile (context only)")
            iv_percentile = st.number_input("IV percentile (0-100)", min_value=0.0,
                                            max_value=100.0, value=72.0, step=1.0,
                                            disabled=not use_pct)
        with c6:
            stock_entry = st.number_input(
                "Covered call: share entry price ($)", min_value=0.0, value=216.0,
                step=1.0, format="%.2f",
                help="Only used by the covered_call strategy.",
            )

        submitted = st.form_submit_button("Evaluate", type="primary")

    if not submitted:
        return

    # --- Validate + normalise inputs (same rules as evaluate.py) ---
    b, a = (bid, ask)
    if b > a:
        st.warning(f"Bid {b} > ask {a} — swapping them.")
        b, a = a, b
    mid = (b + a) / 2.0
    iv = as_decimal_iv(iv_percent)
    q = dividend_yield / 100.0
    r = risk_free / 100.0
    pct = iv_percentile if use_pct else None
    kwargs = dict(r=r, q=q, iv_percentile=pct)

    try:
        if strategy == "long_call":
            strat = long_call(stock_price, strike, iv, mid, int(dte), **kwargs)
        elif strategy == "cash_secured_put":
            strat = cash_secured_put(stock_price, strike, iv, mid, int(dte), **kwargs)
        else:  # covered_call
            if stock_entry <= 0:
                st.error("Covered call needs a positive share entry price.")
                return
            strat = covered_call(stock_price, stock_entry, strike, iv, mid,
                                 int(dte), **kwargs)
    except Exception as exc:  # surface engine errors in the UI instead of crashing
        st.error(f"Could not build strategy: {exc}")
        return

    s = strat.summary()
    g = strat.net_greeks()
    pop = strat.probability_of_profit_estimate()

    st.markdown(f"### {strat.name}")

    credit_debit = "credit (you collect)" if s["net_cost_or_credit"] > 0 else "debit (you pay)"
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net to open", _fmt_money(abs(s["net_cost_or_credit"])), credit_debit)
    m2.metric("Max profit", _fmt_money(s["max_profit"]))
    m3.metric("Max loss", _fmt_money(s["max_loss"]))
    m4.metric("Prob. of profit", f"~{pop*100:.0f}%" if pop is not None else "n/a")

    m5, m6, m7 = st.columns(3)
    be = ", ".join(f"${b:.2f}" for b in s["breakevens"]) or "n/a"
    m5.metric("Breakeven(s)", be)
    m6.metric("Capital", _fmt_money(s["capital"]) if s["capital"] is not None
              else "n/a (margin)")
    roc = s["roc_at_max_profit"]
    m7.metric("ROC at max profit", f"{roc*100:.1f}%" if roc is not None else "n/a")

    left, right = st.columns([3, 2])

    with left:
        st.markdown("#### Payoff diagram")
        tmp_png = Path(tempfile.gettempdir()) / f"{ticker}_{strategy}_payoff.png"
        make_payoff_chart(strat, str(tmp_png))
        st.image(str(tmp_png), use_container_width=True)

    with right:
        st.markdown("#### Net Greeks (whole position)")
        greek_notes = {
            "delta": "directional bias (+ bullish)",
            "gamma": "convexity (+ own acceleration)",
            "theta": "per day (+ collect decay = income)",
            "vega": "per 1% IV (+ gain if IV rises)",
            "rho": "per 1% rate move",
        }
        greeks_df = pd.DataFrame(
            [(k.capitalize(), round(g[k], 3), greek_notes[k])
             for k in ["delta", "gamma", "theta", "vega", "rho"]],
            columns=["Greek", "Value", "Meaning"],
        )
        st.dataframe(greeks_df, hide_index=True, use_container_width=True)

        if g["theta"] > 0:
            st.info("Positive theta → time decay works FOR you (income profile).")
        else:
            st.info("Negative theta → you're paying time decay (long premium).")

    st.markdown("#### Legs (model vs mid is a consistency check)")
    rows = []
    for d in strat.per_leg_detail():
        leg = d["leg"]
        rows.append({
            "Type": leg.kind,
            "Strike": leg.strike if leg.kind != "stock" else None,
            "Qty": leg.quantity,
            "Mid": round(leg.premium, 2),
            "Model": round(d["model_price"], 2) if d["model_price"] is not None else None,
            "IV typed": f"{leg.iv*100:.1f}%" if leg.kind != "stock" else None,
            "IV from mid": (f"{d['implied_vol']*100:.1f}%"
                            if d["implied_vol"] is not None else None),
            "Delta $": round(d["greeks"]["delta"], 1),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    for d in strat.per_leg_detail():
        if (d["implied_vol"] is not None
                and abs(d["implied_vol"] - d["leg"].iv) > 0.03):
            st.warning(
                "Typed IV and mid-implied IV differ by >3 vol points — check you "
                "used the CONTRACT row's IV (not the blended chain IV)."
            )
            break

    # --- Downloads: the same Excel + PNG artifacts the script produces ---
    st.markdown("#### Downloads")
    tag = f"{ticker}_{int(strike)}_{strategy}"
    tmp_xlsx = Path(tempfile.gettempdir()) / f"{tag}.xlsx"
    export_excel(strat, str(tmp_xlsx))
    dc1, dc2 = st.columns(2)
    with dc1:
        st.download_button("Download Excel dashboard (.xlsx)",
                           data=tmp_xlsx.read_bytes(), file_name=f"{tag}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with dc2:
        st.download_button("Download payoff chart (.png)",
                           data=tmp_png.read_bytes(), file_name=f"{tag}_payoff.png",
                           mime="image/png")


# ===========================================================================
# TAB 2 — VOL SCANNER
# ===========================================================================
def render_scanner():
    st.subheader("Is volatility rich or cheap?")
    st.caption(
        "Compares the option's IMPLIED volatility (from the chain) against the "
        "stock's REALIZED volatility (how much it actually moved). A wide, "
        "positive gap = options rich (favor selling); a negative gap = cheap "
        "(favor buying)."
    )

    c1, c2 = st.columns(2)
    with c1:
        ticker = st.text_input("Ticker", value="MRVL", key="scan_ticker")
        iv_percent = st.number_input("Implied volatility from chain (%)",
                                     min_value=0.0, value=63.0, step=0.5,
                                     format="%.2f", key="scan_iv")
    with c2:
        windows = st.multiselect("Realized-vol lookback windows (days)",
                                 options=[10, 20, 30, 60, 90, 120, 180, 252],
                                 default=[20, 30, 60, 90])
        source = st.radio(
            "Price data source",
            ["Fetch live from Stooq (needs internet)",
             "Paste closing prices",
             "Sample data (offline demo)"],
        )

    closes = None
    pasted = None
    if source == "Paste closing prices":
        pasted = st.text_area(
            "Daily closing prices, oldest → newest (comma/space/newline separated)",
            height=120,
            placeholder="210.5, 212.1, 208.9, ...",
        )

    if not st.button("Scan", type="primary", key="scan_btn"):
        return

    iv = as_decimal_iv(iv_percent)

    if source == "Fetch live from Stooq (needs internet)":
        try:
            with st.spinner(f"Fetching {ticker.upper()} closes from Stooq..."):
                closes = vol_scanner.fetch_prices(ticker)
            if not closes:
                st.error("Stooq returned no rows for that ticker. Check the symbol.")
                return
            st.success(f"Fetched {len(closes)} daily closes for {ticker.upper()}.")
        except Exception as exc:
            st.error(
                f"Could not fetch prices ({exc}). If this machine is offline or "
                "the ticker is wrong, use 'Paste closing prices' or 'Sample data'."
            )
            return
    elif source == "Paste closing prices":
        if not pasted or not pasted.strip():
            st.error("Paste some closing prices, or choose another data source.")
            return
        try:
            raw = pasted.replace(",", " ").split()
            closes = [float(x) for x in raw]
        except ValueError:
            st.error("Could not parse those prices — use plain numbers only.")
            return
        if len(closes) < 3:
            st.error("Need at least a few closes to compute realized vol.")
            return
        st.success(f"Using {len(closes)} pasted closes.")
    else:  # sample data — same simulation as vol_scanner.__main__
        import numpy as np
        np.random.seed(42)
        true_daily_vol = 0.45 / np.sqrt(252)
        rets = np.random.normal(0, true_daily_vol, 120)
        closes = list(216 * np.exp(np.cumsum(rets)))
        ticker = f"{ticker} (sample)"
        st.info("Using built-in simulated price path (~45% real vol) — no network.")

    st.markdown(f"### Rich / cheap scan — {ticker.upper()}")
    st.metric("Implied volatility (from chain)", f"{iv*100:.1f}%")

    rows = []
    for w in sorted(windows):
        if len(closes) < w + 1:
            continue
        rv = vol_scanner.realized_vol(closes, window=w)
        gap = iv - rv
        if gap > 0.05:
            read = "RICH (favor selling)"
        elif gap < -0.05:
            read = "CHEAP (favor buying)"
        else:
            read = "~fair"
        rows.append({
            "Lookback": f"{w}d",
            "Realized vol": f"{rv*100:.1f}%",
            "IV − RV": f"{gap*100:+.1f}%",
            "Read": read,
        })

    if not rows:
        st.warning("Not enough price history for the selected windows.")
        return

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(
        "Positive IV − RV = market pricing MORE movement than the stock has "
        "delivered (rich). Negative = pricing less (cheap). Realized vol is "
        "backward-looking; a catalyst like earnings can change future vol."
    )


# ===========================================================================
# APP SHELL
# ===========================================================================
st.title("📈 Options Toolkit")
st.caption(
    "One place for both tools: evaluate a strategy's Greeks/payoff, and check "
    "whether volatility is rich or cheap. Same math as the command-line scripts."
)

tab_eval, tab_scan = st.tabs(["Options Evaluator", "Vol Scanner"])
with tab_eval:
    render_evaluator()
with tab_scan:
    render_scanner()
