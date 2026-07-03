"""Synthetic SaaS KPI data generation, CSV loading, and validation.

合成データであり、実在企業の数値を模倣しない。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = (
    "month",
    "mrr",
    "customers",
    "new_customers",
    "churned_customers",
    "leads",
    "qualified_leads",
    "opportunities",
    "won_deals",
)

NUMERIC_COLUMNS: tuple[str, ...] = REQUIRED_COLUMNS[1:]

DEFAULT_MONTHS = 24
DEFAULT_SEED = 42


def generate_synthetic_data(months: int = DEFAULT_MONTHS, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """架空のSaaS月次KPIデータを生成する。

    Args:
        months: 生成する月数。
        seed: 乱数シード。

    Returns:
        REQUIRED_COLUMNS をすべて持つ月次DataFrame。実在企業とは無関係の合成値。
    """
    if months <= 0:
        return _empty_frame()

    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2023-01-01")
    month_labels = [
        (start + pd.offsets.MonthBegin(i)).strftime("%Y-%m") for i in range(months)
    ]

    customers = 200.0
    mrr = 50_000.0
    rows: list[dict] = []
    for label in month_labels:
        # 成長トレンド + ノイズ。実在企業の規模感を避けるため明示的に架空の数値。
        gross_adds = max(0.0, rng.normal(18.0, 5.0))
        churn_share = rng.normal(0.04, 0.01)
        churn_share = float(np.clip(churn_share, 0.005, 0.12))
        churned = max(0.0, round(customers * churn_share))
        new_customers = max(0.0, round(gross_adds))
        customers = max(0.0, customers + new_customers - churned)

        arpu = mrr / max(customers, 1.0)
        arpu_next = arpu * float(np.clip(rng.normal(1.005, 0.02), 0.9, 1.15))
        mrr = max(0.0, customers * arpu_next)

        leads = int(max(0.0, rng.normal(950.0, 120.0)))
        qualified_leads = int(max(0.0, round(leads * float(np.clip(rng.normal(0.42, 0.05), 0.2, 0.7)))))
        opportunities = int(max(0.0, round(qualified_leads * float(np.clip(rng.normal(0.38, 0.05), 0.2, 0.7)))))
        won_deals = int(max(0.0, round(opportunities * float(np.clip(rng.normal(0.20, 0.04), 0.05, 0.5)))))

        rows.append(
            {
                "month": label,
                "mrr": round(mrr, 2),
                "customers": int(customers),
                "new_customers": int(new_customers),
                "churned_customers": int(churned),
                "leads": leads,
                "qualified_leads": qualified_leads,
                "opportunities": opportunities,
                "won_deals": won_deals,
            }
        )

    df = pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))

    # アラート機能を示すため、意図的に異常月を2つ仕込む。
    if len(df) >= 12:
        anomaly_idx = len(df) // 2
        df.loc[anomaly_idx, "churned_customers"] = int(df.loc[anomaly_idx, "customers"] * 0.11)
        df.loc[anomaly_idx + 1, "mrr"] = df.loc[anomaly_idx + 1, "mrr"] * 0.82
        df.loc[anomaly_idx + 1, "won_deals"] = max(0, df.loc[anomaly_idx + 1, "won_deals"] // 3)

    return df


def load_csv(path: str | Path) -> pd.DataFrame:
    """CSVを読み込み、検証して正規化する。

    Args:
        path: CSVファイルのパス。

    Returns:
        REQUIRED_COLUMNS を持つDataFrame。空・不正な場合は空フレームを返す。
    """
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return _empty_frame()
    try:
        raw = pd.read_csv(p)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return _empty_frame()
    return validate_dataframe(raw)


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """入力DataFrameを検証し、型を整えて返す。

    欠損列は0/空で補完する。数値は非負にクリップする。月は文字列化。
    空DataFrameや全欠損の場合は空フレームを返す（例外は投げない）。
    """
    if df is None or len(df) == 0:
        return _empty_frame()

    out = pd.DataFrame(index=df.index)
    if "month" in df.columns:
        out["month"] = df["month"].astype(str).str.strip()
    else:
        out["month"] = ""

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            series = series.clip(lower=0.0)
        else:
            series = 0.0
        out[col] = series

    out = out[list(REQUIRED_COLUMNS)]
    out = out[out["month"].astype(str).str.len() > 0].reset_index(drop=True)
    if out.empty:
        return _empty_frame()
    return out


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in REQUIRED_COLUMNS})
