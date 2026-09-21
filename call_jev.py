"""Thin wrapper around typesafe-sdk for the 20-question decision model."""

from __future__ import annotations
import pandas as pd
from dataclasses import dataclass, field
from typing import Any

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient, TypeSafeAPIError

SCORE_MAX = 5


@dataclass
class DecisionResult:
    final_call: str = "HOLD"
    composite: float = 50.0
    avg_score: float = 2.5
    probability: int = 50
    request_id: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    choices: dict[str, str] = field(default_factory=dict)
    nouls: dict[str, str] = field(default_factory=dict)
    raw: Any = None

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for k, v in self.scores.items():
            rows.append({
                "type": "SCORE",
                "name": k,
                "value": v,
                "detail": f"{v}/{SCORE_MAX}"
            })
        for k, v in self.choices.items():
            rows.append({
                "type": "CHOICE",
                "name": k,
                "value": str(v),
                "detail": str(v)
            })
        for k, v in self.nouls.items():
            # Safe handling — never assume v is a string
            txt = str(v) if v is not None else ""
            detail = txt[:120] + ("…" if len(txt) > 120 else "")
            rows.append({
                "type": "NOUL",
                "name": k,
                "value": "",
                "detail": detail
            })
        return pd.DataFrame(rows)


# 20 questions
DECISION_QUESTIONS = {
    "overall_action": Choice(
        instructions="Given the full market state and fundamentals, what is the single best action for this ticker right now?",
        criteria={
            "BUY": "Strong risk/reward, attractive valuation or momentum",
            "HOLD": "Fair value / mixed signals",
            "SELL": "Overvalued, deteriorating fundamentals or adverse macro"
        },
    ),
    "conviction": Score(
        instructions="How high is your conviction in the overall_action recommendation?",
        criteria=["very low", "low", "moderate", "high", "very high"],
    ),
    "time_horizon": Choice(
        instructions="Preferred holding horizon for the recommended action?",
        criteria={"days": None, "weeks": None, "1-3 months": None, "3-12 months": None, "multi-year": None},
    ),
    "valuation_attractiveness": Score(
        instructions="How attractive is current valuation vs history and peers (P/E, Fwd P/E, PEG, EV/EBITDA, P/S)?",
        criteria=["expensive", "slightly rich", "fair", "attractive", "deep value"],
    ),
    "valuation_vs_growth": Noul(
        instructions="Briefly assess whether growth (revenue/earnings) justifies the current multiples. 1-2 sentences.",
    ),
    "relative_value": Score(
        instructions="Relative value vs the broader market (SPY/QQQ) and its sector ETF.",
        criteria=["much more expensive", "more expensive", "in line", "cheaper", "much cheaper"],
    ),
    "balance_sheet_strength": Score(
        instructions="Balance-sheet quality: debt/equity, cash, current/quick ratios, free cash flow.",
        criteria=["weak", "below average", "adequate", "strong", "fortress"],
    ),
    "profitability": Score(
        instructions="Profitability and margin quality (gross, operating, net, ROE, ROA).",
        criteria=["poor", "mediocre", "average", "good", "excellent"],
    ),
    "earnings_quality": Noul(
        instructions="Comment on earnings quality, any red flags in cash flow vs reported earnings, or one-time items. 1-2 sentences.",
    ),
    "price_momentum": Score(
        instructions="Short-to-medium term price momentum (1D, 3M, 6M, YTD) relative to market and sector.",
        criteria=["strong downtrend", "weak", "neutral", "positive", "strong uptrend"],
    ),
    "relative_strength": Score(
        instructions="Relative strength vs SPY and its sector ETF over 3M/6M.",
        criteria=["severe underperformance", "underperforming", "in line", "outperforming", "leading"],
    ),
    "macro_sensitivity": Score(
        instructions="Sensitivity to current macro regime (rates ^TNX, volatility ^VIX, oil, gold, risk appetite).",
        criteria=["highly vulnerable", "vulnerable", "neutral", "somewhat resilient", "defensive/beneficiary"],
    ),
    "volatility_risk": Score(
        instructions="Risk level from beta, implied options (put/call), short interest if available.",
        criteria=["very high risk", "elevated", "average", "low", "very low"],
    ),
    "downside_protection": Score(
        instructions="How much downside protection does the current setup offer (valuation cushion, balance sheet, sector defensive characteristics)?",
        criteria=["none", "limited", "moderate", "good", "strong"],
    ),
    "sector_tailwind": Score(
        instructions="Is the sector or thematic exposure currently enjoying tailwinds or headwinds?",
        criteria=["strong headwind", "mild headwind", "neutral", "mild tailwind", "strong tailwind"],
    ),
    "thematic_exposure": Noul(
        instructions="If the ticker has meaningful thematic exposure (AI, semiconductors, cloud, cybersecurity, clean energy, space, robotics…), briefly note the relevance and current narrative strength.",
    ),
    "upside_probability": Score(
        instructions="Subjective probability that the stock outperforms SPY over the next 3-6 months.",
        criteria=["<20%", "20-40%", "40-60%", "60-80%", ">80%"],
    ),
    "catalyst_proximity": Score(
        instructions="Near-term catalysts (earnings, product, macro, sector rotation) that could move the stock.",
        criteria=["none visible", "distant", "moderate", "near-term", "imminent & material"],
    ),
    "key_risk": Noul(
        instructions="Single most important risk that could invalidate the recommendation. One clear sentence.",
    ),
    "key_opportunity": Noul(
        instructions="Single most important opportunity or positive catalyst. One clear sentence.",
    ),
}


def run_decision_scoring(state_doc: str) -> DecisionResult:
    with TypeSafeClient() as client:
        response = client.system_one(
            state={"document": state_doc},
            questions=DECISION_QUESTIONS,
        )

    scores = {k: float(v.score) for k, v in response.scores.items()}
    choices = {k: v.choice for k, v in response.choices.items()}
    nouls = {k: v.noul for k, v in response.nouls.items()}

    if scores:
        avg = sum(scores.values()) / len(scores)
        composite = round((avg / SCORE_MAX) * 100, 1)
    else:
        avg, composite = 2.5, 50.0

    final = choices.get("overall_action", "HOLD").upper()
    up_map = {1: 15, 2: 30, 3: 50, 4: 70, 5: 85}
    prob = up_map.get(int(scores.get("upside_probability", 3)), 50)

    return DecisionResult(
        final_call=final,
        composite=composite,
        avg_score=round(avg, 2),
        probability=prob,
        request_id=getattr(response, "request_id", "") or "",
        scores=scores,
        choices=choices,
        nouls=nouls,
        raw=response,
    )


def run_quick_answer(state_doc: str, question: str) -> str:
    with TypeSafeClient() as client:
        response = client.system_one(
            state={"document": state_doc},
            questions={
                "answer": Noul(
                    instructions=(
                        "Answer the following question using only the provided market state "
                        "and fundamentals. Be concise, direct, and cite concrete numbers when possible.\n\n"
                        f"Question: {question}"
                    )
                )
            },
        )
    return response.nouls["answer"].noul


def format_api_error(e: TypeSafeAPIError) -> str:
    return f"TypeSafe API error: {getattr(e, 'message', str(e))} (status={getattr(e, 'status_code', '?')})"
