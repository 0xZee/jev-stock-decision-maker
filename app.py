"""
JEV DECISION TERMINAL — 0xZee
Run:  streamlit run app.py
"""

import os
import pandas as pd
import streamlit as st

from data_fetcher import get_ticker_snapshot, get_market_context, build_state_document
from jev_client import (run_decision_scoring, run_quick_answer,
                        format_api_error, SCORE_MAX)
from typesafe_sdk import TypeSafeAPIError

# --------------------------------------------------------------------------- #
# Page config + BLUE NEON DARK CSS
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="JEV STOCK DECISION",
    layout="wide",
    initial_sidebar_state="collapsed"
)

NEON      = "#00B4FF"
NEON_DIM  = "#0090CC"
RED       = "#C94444"
AMBER     = "#C9A144"
DIM       = "#555555"
GREY      = "#8A8A8A"
BG        = "#050505"
CARD_BG   = "#070C13"

if "JEV_API_KEY" in st.secrets:
    os.environ["TYPESAFE_API_KEY"] = st.secrets["JEV_API_KEY"]

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&display=swap');

  :root {{
      --neon: {NEON};
      --neon-dim: {NEON_DIM};
      --red: {RED};
      --amber: {AMBER};
  }}

  .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
      background: {BG} !important;
  }}

  html, body, [data-testid="stAppViewContainer"] *:not(button):not(input):not(svg) {{
      font-family: 'Roboto Mono', 'Courier New', monospace !important;
      color: #D0D0D0;
  }}

  [data-testid="stMetric"] {{
      background: {CARD_BG};
      border: 1px solid #1A1A1A;
      border-radius: 4px;
      padding: 10px 14px;
  }}
  [data-testid="stMetricLabel"] p {{
      color: {NEON} !important;
      font-size: 11px !important;
      letter-spacing: 1.2px;
      text-transform: uppercase;
  }}
  [data-testid="stMetricValue"] {{
      color: #E8E8E8 !important;
      font-size: 22px !important;
  }}
  [data-testid="stMetricDelta"] svg {{ display: none; }}

  [data-testid="stContainer"] {{
      border-color: #1F1F1F !important;
      background: {CARD_BG};
  }}

  .term-sub {{
      color: {DIM};
      font-size: 11px;
      letter-spacing: 0.5px;
  }}
  .term-verdict {{
      font-size: 34px;
      font-weight: 700;
      letter-spacing: 5px;
      text-align: center;
      text-shadow: 0 0 14px currentColor;
  }}

  input, textarea {{
      background: #0E0E0E !important;
      color: {NEON} !important;
      border: 1px solid #2A2A2A !important;
      font-family: 'Roboto Mono', monospace !important;
      border-radius: 3px !important;
  }}

  button[kind="primary"] {{
      background: transparent !important;
      color: {NEON} !important;
      font-family: 'Roboto Mono', monospace !important;
      font-weight: 600 !important;
      border: 1px solid {NEON} !important;
      box-shadow: 0 0 8px rgba(0,180,255,0.3);
      border-radius: 3px !important;
  }}
  button[kind="primary"]:hover {{
      background: rgba(0,180,255,0.12) !important;
      box-shadow: 0 0 16px rgba(0,180,255,0.5);
  }}

  .stProgress > div > div > div > div {{
      background: {NEON} !important;
      box-shadow: 0 0 6px rgba(0,180,255,0.55);
  }}

  [data-testid="stExpander"] {{
      border: 1px solid #1A1A1A !important;
      background: {CARD_BG};
  }}



  [data-testid="stChatInput"] {{
      background: #0A0A0A !important;
      border: 1px solid #222 !important;
  }}

  .stDataFrame {{
      border: 1px solid #1A1A1A !important;
  }}
</style>
""", unsafe_allow_html=True)

# Header (pure markdown → icons work)
st.subheader("☰ :blue-background[JEV STOCKS DECISION] ☰", text_alignment='center', divider='gray')
# st.caption("[DEMO] :shimmer[Stock Financials | Market state > 20-Questions > Decision Model TypeSafe Jev > Stock scoring]", text_alignment='center',)

with st.container(border=True):
    st.caption("[DEMO] :shimmer[Stock Financials | Market state > 20-Questions > Decision Model TypeSafe Jev > Stock scoring] : JEV Decision is a live demo that turns market data into structured decisions. It pulls real-time prices, valuation ratios and sector context, then runs a 20-question against TypeSafe Jev model to score buy/sell conviction, financial health and risk")

# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
for k in ("snapshot", "context_df", "state_doc", "as_of", "result"):
    if k not in st.session_state:
        st.session_state[k] = None
if "qa_log" not in st.session_state:
    st.session_state.qa_log = []

# --------------------------------------------------------------------------- #
# Cached data
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=900, show_spinner=False)
def _snapshot(t):
    return get_ticker_snapshot(t)

@st.cache_data(ttl=900, show_spinner=False)
def _context():
    return get_market_context()

if st.session_state.context_df is None:
    with st.spinner(":shimmer[Loading market context] …"):
        try:
            st.session_state.context_df, st.session_state.as_of = _context()
        except Exception as e:
            st.error(f"Market context failed: {e}")

# --------------------------------------------------------------------------- #
# 1. RIBBON
# --------------------------------------------------------------------------- #
SECTORS = ["SOXX", "AIQ", "QTUM", "HACK", "CLOU", "ICLN", "ARKX"]

# --------------------------------------------------------------------------- #
# 1. RIBBON
# --------------------------------------------------------------------------- #
SECTORS = ["SOXX", "AIQ", "ROBO", "QTUM", "HACK", "CLOU", "ICLN", "ARKX"]

if st.session_state.context_df is not None:
    parts = []
    for s in SECTORS:
        if s in st.session_state.context_df.index:
            chg = st.session_state.context_df.loc[s, "1D %"]

            if pd.isna(chg):
                pair = f":grey-background[{s}] :grey-background[—]"
            elif chg > 0:
                pair = f":grey-background[{s}] :green-background[+{chg:.2f}%]"
            elif chg < 0:
                pair = f":grey-background[{s}] :red-background[{chg:.2f}%]"
            else:
                pair = f":grey-background[{s}] :grey-background[{chg:.2f}%]"

            parts.append(pair)

    rib = " | ".join(parts)
    st.markdown(f":small[{rib}]")

# --------------------------------------------------------------------------- #
# 2. Four top cards
# --------------------------------------------------------------------------- #
def _card_value(ticker):
    if st.session_state.context_df is None or ticker not in st.session_state.context_df.index:
        return "—", None
    row = st.session_state.context_df.loc[ticker]
    price = row.get("Price")
    chg = row.get("1D %")
    price_str = f"{price:.2f}" if pd.notna(price) else "—"
    return price_str, chg

c1, c2, c3, c4 = st.columns(4)
with c1:
    p, chg = _card_value("SPY")
    st.metric("SPY", p, f"{chg:+.2f} %" if pd.notna(chg) else None)
with c2:
    p, chg = _card_value("QQQ")
    st.metric("QQQ", p, f"{chg:+.2f} %" if pd.notna(chg) else None)
with c3:
    p, chg = _card_value("^TNX")
    st.metric("10Y", p, f"{chg:+.2f} %" if pd.notna(chg) else None)
with c4:
    p, chg = _card_value("^VIX")
    st.metric("VIX", p, f"{chg:+.2f} %" if pd.notna(chg) else None)

st.markdown("")

# --------------------------------------------------------------------------- #
# 3. Market dataframe
# --------------------------------------------------------------------------- #
if st.session_state.context_df is not None:
    with st.expander("", expanded=False):
        df = st.session_state.context_df.reset_index().copy()
        for col in ["Price", "1D %", "3M %", "6M %", "YTD %", "P/E", "Fwd P/E"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

        def _color(v):
            if pd.isna(v):
                return ""
            return f"color:{NEON}" if v > 0 else (f"color:{RED}" if v < 0 else "")

        sty = df.style.map(_color, subset=["1D %", "3M %", "6M %", "YTD %"])
        st.dataframe(sty, width="stretch", height=220, hide_index=True)

# --------------------------------------------------------------------------- #
# 4. Control line
# --------------------------------------------------------------------------- #
st.markdown("")
ctrl2, ctrl3 = st.columns([4, 2])
# with ctrl1:
#     st.markdown("⚖️")
with ctrl2:
    ticker = st.text_input(
        "TICKER",
        # value="NVDA",
        label_visibility="collapsed",
        placeholder="⚖️ Ask JEV to score your Stock on 20 Predefined Fields (e.g. NVDA)",
    ).upper().strip()
with ctrl3:
    score_btn = st.button(
        "🌀 SCORE DECISIONS",
        type="primary",
        use_container_width=True,
    )

# --------------------------------------------------------------------------- #
# Run scoring
# --------------------------------------------------------------------------- #
if score_btn:
    if "JEV_API_KEY" not in st.secrets:
        st.error("Add JEV_API_KEY to .streamlit/secrets.toml")
        st.stop()
    with st.spinner(f"Fetching {ticker} + running 20-question model …"):
        try:
            st.session_state.snapshot = _snapshot(ticker)
            if st.session_state.context_df is None:
                st.session_state.context_df, st.session_state.as_of = _context()
            st.session_state.state_doc = build_state_document(
                ticker, st.session_state.snapshot, st.session_state.context_df
            )
            st.session_state.result = run_decision_scoring(st.session_state.state_doc)
        except TypeSafeAPIError as e:
            st.error(format_api_error(e))
        except Exception as e:
            st.error(f"Error: {e}")

# --------------------------------------------------------------------------- #
# 5. Ticker metrics
# --------------------------------------------------------------------------- #
if st.session_state.snapshot:
    si = st.session_state.snapshot["structured_info"]
    mi = si.get("main_info", {})
    val = si.get("valuation", {})
    fin = si.get("financial", {})
    mrg = si.get("margins", {})
    grw = si.get("growth", {})
    ret = si.get("returns", {})

    st.markdown(
        f"🏛️ :blue-background[**{mi.get('shortName','')}**] | "
        f"{mi.get('sector','—')} | {mi.get('industry','—')} · "
        f":gray[{st.session_state.as_of}]"
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("PRICE", mi.get("currentPrice"), f'{mi.get("regularMarketChange","")} %')
    m2.metric("MKT CAP B$", val.get("marketCap_B$"), f'{mi.get("regularMarketChange","")} %')
    m3.metric("P/E → FWD", val.get("trailingPE"), f'Fwd PE {val.get("forwardPE")}')
    m4.metric("REV B$ / g%", fin.get("totalRevenue"), f'% Rev. {grw.get("revenueGrowth","")}%')
    m5.metric("NET MGN %", mrg.get("netProfitMargin") or mrg.get("profitMargins"),
              f'ROE {ret.get("returnOnEquity","")}%')

# --------------------------------------------------------------------------- #
# 6. Verdict + breakdown table
# --------------------------------------------------------------------------- #
res = st.session_state.get("result")
if res:
    vcol = {"BUY": NEON, "SELL": RED, "HOLD": AMBER}.get(res.final_call, "#DDD")

    with st.container(border=True, vertical_alignment='top'):
        v1, v2, v3, v4 = st.columns([1.6, 1.4, 1.4, 3])
        with v1:
            st.markdown(
                f'<div class="term-verdict" style="color:{vcol}; padding-top:10px;">'
                f'{res.final_call}</div>',
                unsafe_allow_html=True,
            )
        v2.metric("COMPOSITE", f"{res.composite:.1f}", f"avg {res.avg_score}/{SCORE_MAX}")
        v3.metric("PROBABILITY", f"{res.probability}%", border=True)
        with v4:
            st.caption("📶 Probability Score")
            st.progress(min(res.composite, 100) / 100)
            st.caption(f"Req_id: {res.request_id}")

    # ----- Breakdown table -----
    st.markdown("🧊 20-Questions Decision Scroring Breakdown")

    rows = []
    for k, v in res.scores.items():
        rows.append({"question": k, "type": "SCORE", "value": v, "detail": f"{v}/{SCORE_MAX}"})
    for k, v in res.choices.items():
        rows.append({"question": k, "type": "CHOICE", "value": str(v), "detail": str(v)})
    for k, v in res.nouls.items():
        txt = str(v) if v is not None else ""
        rows.append({
            "question": k,
            "type": "NOUL",
            "value": "",
            "detail": txt
        })

    rdf = pd.DataFrame(rows)

    html = [
        '<table style="width:100%; border-collapse:collapse; font-size:13px;">',
        '<thead><tr style="border-bottom:1px solid #222; color:#666;">',
        '<th style="width:20%; text-align:left; padding:7px;">QUESTION</th>',
        '<th style="width:9%; text-align:left; padding:7px;">TYPE</th>',
        '<th style="width:11%; text-align:center; padding:7px;">VALUE</th>',
        '<th style="width:60%; text-align:left; padding:7px;">DETAIL / PROGRESS / NARRATIVE</th>',
        '</tr></thead><tbody>'
    ]

    for _, r in rdf.iterrows():
        q, typ, val, detail = r["question"], r["type"], r["value"], r["detail"]

        if typ == "SCORE":
            try:
                score = float(val)
                if score >= 4:
                    color = NEON
                elif score <= 2:
                    color = RED
                else:
                    color = AMBER
                pct = score / SCORE_MAX
                bar = (
                    f'<div style="background:#1A1A1A; border-radius:2px; height:12px; width:100%;">'
                    f'<div style="background:{color}; width:{pct*100:.0f}%; height:12px; '
                    f'border-radius:2px; box-shadow:0 0 6px {color}55;"></div></div>'
                )
                val_html = f'<span style="color:{color}; font-weight:600;">{val}</span>'
                detail_html = bar
            except Exception:
                val_html = str(val)
                detail_html = detail
        elif typ == "CHOICE":
            v_up = str(val).upper()
            if "BUY" in v_up:
                color = NEON
            elif "SELL" in v_up:
                color = RED
            else:
                color = AMBER
            val_html = f'<span style="color:{color}; font-weight:700;">{val}</span>'
            detail_html = f'<span style="color:{color};">{detail}</span>'
        else:  # NOUL
            val_html = "—"
            detail_html = f'<span style="color:#B0B0B0;">{detail}</span>'

        html.append(
            f'<tr style="border-bottom:1px solid #111;">'
            f'<td style="padding:7px; color:#CCC;">{q}</td>'
            f'<td style="padding:7px; color:#666;">{typ}</td>'
            f'<td style="padding:7px; text-align:center;">{val_html}</td>'
            f'<td style="padding:7px;">{detail_html}</td>'
            f'</tr>'
        )

    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# 7. Chat + News (news under chat)
# --------------------------------------------------------------------------- #
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("🌐 QUICK CHAT Q&A")

        for qq, aa in st.session_state.qa_log[-8:]:
            st.markdown(
                f'<div style="margin:7px 0;">'
                f'<span style="color:{DIM};">Q ▸ {qq}</span><br>'
                f'<span style="color:{NEON};">A ▸ {aa}</span></div>',
                unsafe_allow_html=True,
            )

        user_q = st.chat_input("Ask about valuation, financial health, buy/sell …")
        if user_q and st.session_state.state_doc:
            with st.spinner("Jev answering …"):
                try:
                    ans = run_quick_answer(st.session_state.state_doc, user_q)
                    st.session_state.qa_log.append((user_q, ans))
                    st.rerun()
                except TypeSafeAPIError as e:
                    st.error(format_api_error(e))
                except Exception as e:
                    st.error(f"Error: {e}")
        elif user_q and not st.session_state.state_doc:
            st.warning("Run SCORE DECISION first so the model has context.")

# News under chat
# st.markdown("<br>", unsafe_allow_html=True)
# with st.container(border=True):
#     st.markdown("📉 NEWS FEED")
#     if st.session_state.snapshot and st.session_state.snapshot.get("news"):
#         news_df = pd.DataFrame(st.session_state.snapshot["news"])[
#             ["pubDate", "provider", "title"]
#         ]
#         st.dataframe(news_df, width="stretch", height=340, hide_index=True)
#     else:
#         st.caption("Run a ticker to load news.")

st.markdown("---")
st.caption("💻 [:shimmer[github.com/0xZee]] | Demo only | Not Financial/Investment Advice | Sept. 2026")
