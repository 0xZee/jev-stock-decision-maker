"""Market data layer — yfinance snapshots + market context."""

from __future__ import annotations
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import Any

# --------------------------------------------------------------------------- #
# Universe
# --------------------------------------------------------------------------- #
BROAD = ["SPY", "QQQ", "DIA", "IWM"]
MACRO = ["^TNX", "^VIX", "CL=F", "GC=F"]          # 10y, VIX, Oil, Gold
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]
THEMATIC = ["ARKX", "QTUM", "CLOU", "HACK", "ICLN", "BOTZ", "SMH", "SOXX", "AIQ", "ROBO"]
UNIVERSE = BROAD + MACRO + SECTORS + THEMATIC


def _to_billion(v):
    try:
        return round(float(v) / 1e9, 2) if v is not None else None
    except (TypeError, ValueError):
        return None


def _to_pct(v):
    """Always return float with exactly 2 decimals or None."""
    if v is None:
        return None
    try:
        return round(float(v) * 100, 2)
    except (TypeError, ValueError):
        return None


def _round2(v):
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Single-ticker rich snapshot
# --------------------------------------------------------------------------- #
def get_ticker_snapshot(ticker: str) -> dict[str, Any]:
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    news_raw = stock.news or []

    categories = {
        "main_info": {},
        "valuation": {},
        "financial": {},
        "growth": {},
        "margins": {},
        "earnings": {},
        "dividends": {},
        "price_perf": {},
        "returns": {},
        "shorts": {},
        "risk": {},
        "recommendations_pt": {},
        "debt": {},
        "options": {},
    }

    key_mappings = {
        "main_info": [
            "symbol", "shortName", "currentPrice", "regularMarketChange",
            "preMarketChangePercent", "marketCap", "exchange", "market",
            "quoteType", "currency", "sector", "industry", "fullTimeEmployees",
            "longBusinessSummary", "country", "website",
        ],
        "valuation": [
            "marketCap", "enterpriseValue", "trailingPE", "forwardPE", "pegRatio",
            "priceToSalesTrailing12Months", "priceToBook", "enterpriseToRevenue",
            "enterpriseToEbitda", "profitMargins", "trailingPegRatio",
        ],
        "financial": [
            "totalRevenue", "grossProfits", "ebitda", "totalDebt", "totalCash",
            "freeCashflow", "operatingCashflow",
        ],
        "growth": [
            "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth",
            "revenueQuarterlyGrowth", "fiveYearAvgDividendYield",
        ],
        "margins": [
            "grossMargins", "operatingMargins", "ebitdaMargins", "profitMargins",
            "pretaxProfitMargin", "netProfitMargin",
        ],
        "earnings": [
            "trailingEps", "forwardEps", "lastEps", "earningsQuarterlyGrowth",
            "netIncomeToCommon", "earningsTimestamp",
        ],
        "dividends": [
            "dividendRate", "dividendYield", "exDividendDate", "payoutRatio",
            "trailingAnnualDividendRate", "trailingAnnualDividendYield",
            "lastDividendValue", "lastDividendDate",
        ],
        "price_perf": [
            "marketState", "currentPrice", "previousClose", "regularMarketChangePercent",
            "preMarketChangePercent", "volume", "averageVolume10days",
            "averageDailyVolume3Month", "beta", "fiftyDayAverage",
            "twoHundredDayAverage", "twoHundredDayAverageChangePercent",
            "fiftyDayAverageChangePercent",
        ],
        "returns": ["returnOnAssets", "returnOnEquity"],
        "shorts": [
            "floatShares", "sharesOutstanding", "sharesShort", "sharesShortPriorMonth",
            "heldPercentInsiders", "heldPercentInstitutions", "shortRatio",
            "shortPercentOfFloat", "impliedSharesOutstanding", "bookValue",
            "lastFiscalYearEnd", "nextFiscalYearEnd",
        ],
        "risk": [
            "auditRisk", "boardRisk", "compensationRisk", "shareHolderRightsRisk",
            "overallRisk", "governanceEpochDate", "compensationAsOfEpochDate",
        ],
        "recommendations_pt": [
            "averageAnalystRating", "targetHighPrice", "targetLowPrice",
            "targetMeanPrice", "targetMedianPrice", "recommendationMean",
            "recommendationKey", "numberOfAnalystOpinions",
        ],
        "debt": ["currentRatio", "quickRatio", "debtToEquity", "returnOnAssets", "returnOnEquity"],
    }

    for cat, keys in key_mappings.items():
        for k in keys:
            if k not in info or info[k] is None:
                continue
            if k == "marketCap":
                categories[cat]["marketCap_B$"] = _to_billion(info[k])
            elif k in {
                "enterpriseValue", "totalRevenue", "grossProfits", "ebitda",
                "totalDebt", "totalCash", "freeCashflow", "operatingCashflow",
            }:
                categories[cat][k] = _to_billion(info[k])
            elif k in {
                "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth",
                "revenueQuarterlyGrowth", "fiveYearAvgDividendYield",
                "grossMargins", "operatingMargins", "ebitdaMargins", "profitMargins",
                "pretaxProfitMargin", "netProfitMargin", "returnOnAssets",
                "returnOnEquity", "dividendYield", "trailingAnnualDividendYield",
                "regularMarketChangePercent", "preMarketChangePercent",
                "twoHundredDayAverageChangePercent", "fiftyDayAverageChangePercent",
                "shortPercentOfFloat", "heldPercentInsiders", "heldPercentInstitutions",
            }:
                categories[cat][k] = _to_pct(info[k])
            elif k in {
                "trailingPE", "forwardPE", "pegRatio", "priceToSalesTrailing12Months",
                "priceToBook", "enterpriseToRevenue", "enterpriseToEbitda",
                "trailingPegRatio", "currentRatio", "quickRatio", "debtToEquity",
                "shortRatio", "payoutRatio", "regularMarketChange",
            }:
                categories[cat][k] = _round2(info[k])
            elif k in {"earningsTimestamp", "exDividendDate"}:
                try:
                    categories[cat][k] = datetime.fromtimestamp(info[k]).strftime("%Y-%m-%d")
                except Exception:
                    categories[cat][k] = "N/A"
            else:
                categories[cat][k] = info[k]

    # volume change %
    vol = categories["price_perf"].get("volume")
    avg = categories["price_perf"].get("averageVolume10days")
    if vol is not None and avg:
        try:
            categories["price_perf"]["volume_change_pct"] = _to_pct((vol - avg) / avg)
        except Exception:
            categories["price_perf"]["volume_change_pct"] = None

    # options (2nd expiration)
    try:
        expirations = stock.options or []
        if len(expirations) > 1:
            second_exp = sorted(expirations)[1]
            chain = stock.option_chain(second_exp)
            calls = chain.calls.fillna(0)
            puts = chain.puts.fillna(0)
            tcoi = int(calls["openInterest"].sum())
            tpoi = int(puts["openInterest"].sum())
            tcv = int(calls["volume"].sum())
            tpv = int(puts["volume"].sum())
            categories["options"] = {
                "second_expiration": second_exp,
                "total_call_oi": tcoi,
                "total_put_oi": tpoi,
                "put_call_oi_ratio": _round2(tpoi / tcoi) if tcoi else 0.0,
                "total_call_volume": tcv,
                "total_put_volume": tpv,
                "put_call_volume_ratio": _round2(tpv / tcv) if tcv else 0.0,
            }
    except Exception:
        pass

    # Process news the correct way
    news = stock.news
    processed_news = [
        {
            "provider": item.get("provider", {}).get("displayName", "N/A")
                        if isinstance(item.get("provider"), dict)
                        else item.get("publisher", "N/A"),
            "pubDate": item.get("pubDate", "N/A"),
            "title": item.get("title", "N/A"),
            "summary": item.get("summary", "N/A"),
        }
        for item in news
    ]

    return {"structured_info": categories, "news": processed_news}


# --------------------------------------------------------------------------- #
# Market context table
# --------------------------------------------------------------------------- #
def _horizon_return(hist: pd.DataFrame, days: int) -> float | None:
    if hist is None or hist.empty or len(hist) < 2:
        return None
    try:
        end = float(hist["Close"].iloc[-1])
        start = float(hist["Close"].iloc[max(0, len(hist) - days - 1)])
        return _to_pct((end - start) / start)
    except Exception:
        return None


def get_market_context() -> tuple[pd.DataFrame, str]:
    rows = []
    as_of = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    for t in UNIVERSE:
        try:
            tk = yf.Ticker(t)
            info = tk.info or {}
            hist = tk.history(period="1y", auto_adjust=True)

            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if price is None and not hist.empty:
                price = float(hist["Close"].iloc[-1])

            chg_1d = info.get("regularMarketChangePercent")
            if chg_1d is not None:
                chg_1d = _round2(chg_1d)          # already in %
            else:
                chg_1d = _horizon_return(hist, 1)

            row = {
                "Ticker": t,
                "Price": _round2(price),
                "1D %": chg_1d,
                "3M %": _horizon_return(hist, 63),
                "6M %": _horizon_return(hist, 126),
                "YTD %": _horizon_return(
                    hist,
                    max(1, (datetime.now() - datetime(datetime.now().year, 1, 1)).days)
                ),
                "P/E": _round2(info.get("trailingPE")),
                "Fwd P/E": _round2(info.get("forwardPE")),
            }
            rows.append(row)
        except Exception:
            rows.append({
                "Ticker": t, "Price": None, "1D %": None, "3M %": None,
                "6M %": None, "YTD %": None, "P/E": None, "Fwd P/E": None
            })

    df = pd.DataFrame(rows).set_index("Ticker")
    return df, as_of


# --------------------------------------------------------------------------- #
# Compact state document for the LLM
# --------------------------------------------------------------------------- #
def build_state_document(ticker: str, snapshot: dict, context_df: pd.DataFrame) -> str:
    si = snapshot["structured_info"]
    mi = si.get("main_info", {})
    val = si.get("valuation", {})
    fin = si.get("financial", {})
    mrg = si.get("margins", {})
    grw = si.get("growth", {})
    ret = si.get("returns", {})
    debt = si.get("debt", {})
    rec = si.get("recommendations_pt", {})
    pp = si.get("price_perf", {})

    lines = [
        f"FOCUS TICKER: {ticker} — {mi.get('shortName', '')}",
        f"Sector/Industry: {mi.get('sector', '—')} / {mi.get('industry', '—')}",
        f"Price: {mi.get('currentPrice')} | 1D Δ: {mi.get('regularMarketChange')} "
        f"({pp.get('regularMarketChangePercent')}%)",
        f"Market Cap B$: {val.get('marketCap_B$')} | Beta: {pp.get('beta')}",
        f"Valuation → P/E {val.get('trailingPE')} | Fwd P/E {val.get('forwardPE')} | "
        f"PEG {val.get('pegRatio')} | P/S {val.get('priceToSalesTrailing12Months')} | "
        f"P/B {val.get('priceToBook')} | EV/EBITDA {val.get('enterpriseToEbitda')}",
        f"Financials → Rev B$ {fin.get('totalRevenue')} (g {grw.get('revenueGrowth')}%) | "
        f"EBITDA B$ {fin.get('ebitda')} | Net Margin {mrg.get('netProfitMargin') or mrg.get('profitMargins')}% | "
        f"ROE {ret.get('returnOnEquity')}% | Debt/Eq {debt.get('debtToEquity')}",
        f"Analyst → {rec.get('recommendationKey')} | mean rating {rec.get('averageAnalystRating')} | "
        f"target mean {rec.get('targetMeanPrice')}",
        "",
        "MARKET CONTEXT (price / multi-horizon % / PE):",
    ]
    for t, r in context_df.iterrows():
        lines.append(
            f"  {t}: {r['Price']} | 1D {r['1D %']}% | 3M {r['3M %']}% | "
            f"6M {r['6M %']}% | YTD {r['YTD %']}% | PE {r['P/E']} | FwdPE {r['Fwd P/E']}"
        )

    if snapshot.get("news"):
        lines.append("\nRECENT NEWS HEADLINES:")
        for n in snapshot["news"][:6]:
            lines.append(f"  • [{n.get('provider')}] {n.get('title')}")

    return "\n".join(lines)
