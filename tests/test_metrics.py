"""src.metrics のテスト: サマリー・MRR推移・MoM・チャーン率。"""

from __future__ import annotations

import pandas as pd

from src.data import generate_synthetic_data
from src.metrics import (
    compute_churn_rate,
    compute_mom_change,
    compute_mrr_trend,
    compute_summary,
)


def test_compute_summary_empty_returns_zeros():
    s = compute_summary(pd.DataFrame())
    assert s["latest_month"] is None
    assert s["mrr"] == 0.0
    assert s["churn_rate"] == 0.0


def test_compute_summary_single_row():
    df = generate_synthetic_data(months=1, seed=1)
    s = compute_summary(df)
    assert s["latest_month"] == s["prev_month"]
    assert s["mrr_growth"] == 0.0  # 前月=当月なので差ゼロ


def test_compute_summary_keys_and_types():
    df = generate_synthetic_data(months=12, seed=3)
    s = compute_summary(df)
    for k in ["latest_month", "prev_month", "mrr", "mrr_delta", "mrr_growth",
              "customers", "new_customers", "churned_customers", "churn_rate",
              "conversion_rate", "net_new_customers"]:
        assert k in s
    assert isinstance(s["customers"], int)
    assert 0.0 <= s["churn_rate"]
    assert 0.0 <= s["conversion_rate"] <= 1.0


def test_compute_mrr_trend_columns_and_length():
    df = generate_synthetic_data(months=10, seed=4)
    t = compute_mrr_trend(df)
    assert list(t.columns) == ["month", "mrr", "mrr_delta", "mrr_growth"]
    assert len(t) == 10
    assert t["mrr_delta"].iloc[0] == 0.0  # 最初月は差ゼロ


def test_compute_mrr_trend_empty():
    t = compute_mrr_trend(pd.DataFrame())
    assert t.empty
    assert "mrr" in t.columns


def test_compute_mom_change_unknown_column_returns_empty():
    df = generate_synthetic_data(months=5, seed=1)
    out = compute_mom_change(df, "nope")
    assert out.empty


def test_compute_mom_change_basic():
    df = generate_synthetic_data(months=8, seed=1)
    out = compute_mom_change(df, "customers")
    assert "customers_mom" in out.columns
    assert out["customers_mom"].iloc[0] == 0.0
    # 0割が起きてもNaNにならない
    assert not out["customers_mom"].isna().any()


def test_compute_churn_rate_series_and_scalar():
    df = generate_synthetic_data(months=6, seed=1)
    rates = compute_churn_rate(df)
    assert (rates >= 0).all()
    scalar = compute_churn_rate(df.iloc[0])
    assert scalar >= 0.0


def test_compute_churn_rate_zero_customers_safe():
    row = pd.Series({"customers": 0, "churned_customers": 5})
    assert compute_churn_rate(row) == 0.0  # 分母をmax(0,1)=1で安全化


def test_compute_summary_conversion_rate_zero_leads():
    df = pd.DataFrame(
        [
            {"month": "2024-01", "mrr": 100.0, "customers": 10, "new_customers": 2,
             "churned_customers": 1, "leads": 0, "qualified_leads": 0,
             "opportunities": 0, "won_deals": 0},
            {"month": "2024-02", "mrr": 110.0, "customers": 11, "new_customers": 2,
             "churned_customers": 1, "leads": 0, "qualified_leads": 0,
             "opportunities": 0, "won_deals": 0},
        ]
    )
    s = compute_summary(df)
    assert s["conversion_rate"] == 0.0
    assert s["mrr_growth"] > 0.0
