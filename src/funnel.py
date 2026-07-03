"""ファネル計算ロジック。純関数。

リード -> MQL(qualified) -> SQL(opportunities) -> Won の段階変換を扱う。
"""

from __future__ import annotations

import pandas as pd

from src.metrics import _safe_ratio

FUNNEL_STAGES: tuple[str, ...] = ("leads", "qualified_leads", "opportunities", "won_deals")
FUNNEL_LABELS: dict[str, str] = {
    "leads": "Leads",
    "qualified_leads": "MQL",
    "opportunities": "SQL",
    "won_deals": "Won",
}


def compute_funnel(df: pd.DataFrame, month: str | None = None) -> dict:
    """指定月（未指定時は最新月）のファネル段階別件数と段階間変換率を返す。

    Returns:
        month, stages(ラベル→件数のdict), step_rates(段階間レートのdict),
        overall_rate(won/leads), total_leads, won を含むdict。
    """
    if df is None or df.empty:
        return _empty_funnel()
    d = df.sort_values("month").reset_index(drop=True)
    if month is not None:
        match = d[d["month"].astype(str) == str(month)]
        if match.empty:
            return _empty_funnel()
        row = match.iloc[-1]
    else:
        row = d.iloc[-1]

    stages = {FUNNEL_LABELS[s]: int(row[s]) for s in FUNNEL_STAGES}
    step_rates = {
        f"{FUNNEL_LABELS[FUNNEL_STAGES[i]]}->{FUNNEL_LABELS[FUNNEL_STAGES[i + 1]]}": _safe_ratio(
            float(row[FUNNEL_STAGES[i + 1]]), float(row[FUNNEL_STAGES[i]])
        )
        for i in range(len(FUNNEL_STAGES) - 1)
    }
    overall = _safe_ratio(float(row["won_deals"]), float(row["leads"]))
    return {
        "month": str(row["month"]),
        "stages": stages,
        "step_rates": step_rates,
        "overall_rate": overall,
        "total_leads": int(row["leads"]),
        "won": int(row["won_deals"]),
    }


def compute_funnel_table(df: pd.DataFrame) -> pd.DataFrame:
    """全月のファネル段階と主要変換率を表形式で返す。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=["month", *FUNNEL_STAGES, "lead_to_mql", "mql_to_sql", "sql_to_won", "lead_to_won"])
    d = df.sort_values("month").reset_index(drop=True).copy()
    d["lead_to_mql"] = d.apply(lambda r: _safe_ratio(r["qualified_leads"], r["leads"]), axis=1)
    d["mql_to_sql"] = d.apply(lambda r: _safe_ratio(r["opportunities"], r["qualified_leads"]), axis=1)
    d["sql_to_won"] = d.apply(lambda r: _safe_ratio(r["won_deals"], r["opportunities"]), axis=1)
    d["lead_to_won"] = d.apply(lambda r: _safe_ratio(r["won_deals"], r["leads"]), axis=1)
    cols = ["month", *FUNNEL_STAGES, "lead_to_mql", "mql_to_sql", "sql_to_won", "lead_to_won"]
    return d[cols]


def compute_conversion_rate(df: pd.DataFrame, from_stage: str = "leads", to_stage: str = "won_deals") -> pd.DataFrame:
    """2段階間の月次変換率を返す。"""
    if df is None or df.empty or from_stage not in df.columns or to_stage not in df.columns:
        return pd.DataFrame(columns=["month", "conversion_rate"])
    d = df.sort_values("month").reset_index(drop=True).copy()
    d["conversion_rate"] = d.apply(lambda r: _safe_ratio(r[to_stage], r[from_stage]), axis=1)
    return d[["month", "conversion_rate"]]


def _empty_funnel() -> dict:
    return {
        "month": None,
        "stages": {FUNNEL_LABELS[s]: 0 for s in FUNNEL_STAGES},
        "step_rates": {},
        "overall_rate": 0.0,
        "total_leads": 0,
        "won": 0,
    }
