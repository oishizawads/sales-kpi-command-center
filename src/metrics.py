"""KPI集計ロジック。UIから独立した純関数。

単位: mrr は USD、レートは割合(0.0-1.0)。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MRR_UNIT = "USD"
RATE_UNIT = "ratio"


def compute_summary(df: pd.DataFrame) -> dict:
    """最新月と前月をもとに主要KPIサマリーを返す。

    Args:
        df: REQUIRED_COLUMNS を持つ月次DataFrame。

    Returns:
        latest_month, prev_month, mrr, mrr_delta, mrr_growth,
        customers, new_customers, churned_customers, churn_rate,
        conversion_rate, net_new_customers を含むdict。
        空データの場合は値がNone/0の辞書を返す。
    """
    if df is None or df.empty:
        return _empty_summary()

    d = df.sort_values("month").reset_index(drop=True)
    latest = d.iloc[-1]
    prev = d.iloc[-2] if len(d) >= 2 else latest

    mrr = float(latest["mrr"])
    mrr_prev = float(prev["mrr"])
    mrr_delta = mrr - mrr_prev
    mrr_growth = _safe_ratio(mrr_delta, mrr_prev)

    customers = int(latest["customers"])
    new_customers = int(latest["new_customers"])
    churned = int(latest["churned_customers"])
    net_new = new_customers - churned

    churn_rate = float(compute_churn_rate(latest))
    conv_rate = _safe_ratio(float(latest["won_deals"]), float(latest["leads"]))

    return {
        "latest_month": str(latest["month"]),
        "prev_month": str(prev["month"]),
        "mrr": mrr,
        "mrr_delta": mrr_delta,
        "mrr_growth": mrr_growth,
        "customers": customers,
        "new_customers": new_customers,
        "churned_customers": churned,
        "churn_rate": churn_rate,
        "conversion_rate": conv_rate,
        "net_new_customers": net_new,
    }


def compute_mrr_trend(df: pd.DataFrame) -> pd.DataFrame:
    """月次MRR推移と前月差・成長率を返す。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=["month", "mrr", "mrr_delta", "mrr_growth"])
    d = df.sort_values("month").reset_index(drop=True).copy()
    d["mrr_delta"] = d["mrr"].diff().fillna(0.0)
    d["mrr_growth"] = _mom_ratios(d["mrr"])
    return d[["month", "mrr", "mrr_delta", "mrr_growth"]]


def compute_mom_change(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """任意の数値列の月次推移とMoM変化率を返す。"""
    empty_cols = ["month", column, f"{column}_mom"]
    if df is None or df.empty or column not in df.columns:
        return pd.DataFrame(columns=empty_cols)
    d = df.sort_values("month").reset_index(drop=True).copy()
    series = pd.to_numeric(d[column], errors="coerce").fillna(0.0)
    d[column] = series
    d[f"{column}_mom"] = _mom_ratios(series)
    return d[["month", column, f"{column}_mom"]]


def compute_churn_rate(row: pd.Series | pd.DataFrame) -> float | pd.Series:
    """チャーンレート = churned_customers / customers。

    customersは月末残。customers <= 0 のときは 0.0 を返す（0割回避）。
    """
    if isinstance(row, pd.DataFrame):
        cust = row["customers"].astype(float).to_numpy()
        churned = row["churned_customers"].astype(float).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            rates = np.where(cust > 0, churned / cust, 0.0)
        return pd.Series(np.clip(rates, 0.0, None), index=row.index)
    customers = float(row["customers"])
    churned = float(row["churned_customers"])
    if customers <= 0:
        return 0.0
    return churned / customers


def _mom_ratios(series: pd.Series) -> pd.Series:
    """前月比変化率を計算する。前月0のときは0を返す（0割回避）。"""
    prev = series.shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = np.where(prev > 0, (series - prev) / prev, 0.0)
    return pd.Series(ratios, index=series.index)


def _safe_ratio(num: float, denom: float) -> float:
    if denom <= 0:
        return 0.0
    return num / denom


def _empty_summary() -> dict:
    return {
        "latest_month": None,
        "prev_month": None,
        "mrr": 0.0,
        "mrr_delta": 0.0,
        "mrr_growth": 0.0,
        "customers": 0,
        "new_customers": 0,
        "churned_customers": 0,
        "churn_rate": 0.0,
        "conversion_rate": 0.0,
        "net_new_customers": 0,
    }
