"""src.funnel のテスト: ファネル集計・変換率・空データ。"""

from __future__ import annotations

import pandas as pd

from src.data import generate_synthetic_data
from src.funnel import FUNNEL_STAGES, compute_conversion_rate, compute_funnel, compute_funnel_table


def test_compute_funnel_empty():
    f = compute_funnel(pd.DataFrame())
    assert f["month"] is None
    assert f["overall_rate"] == 0.0
    assert f["stages"] == {s: 0 for s in ["Leads", "MQL", "SQL", "Won"]}


def test_compute_funnel_latest_month_default():
    df = generate_synthetic_data(months=10, seed=1)
    f = compute_funnel(df)
    assert f["month"] == df.sort_values("month").iloc[-1]["month"]
    assert f["total_leads"] == int(df.iloc[-1]["leads"])
    assert 0.0 <= f["overall_rate"] <= 1.0


def test_compute_funnel_specific_month():
    df = generate_synthetic_data(months=12, seed=1)
    target = df.sort_values("month").iloc[3]["month"]
    f = compute_funnel(df, month=target)
    assert f["month"] == target


def test_compute_funnel_unknown_month_returns_empty():
    df = generate_synthetic_data(months=6, seed=1)
    f = compute_funnel(df, month="1999-01")
    assert f["month"] is None


def test_compute_funnel_step_rates_keys():
    df = generate_synthetic_data(months=6, seed=1)
    f = compute_funnel(df)
    assert set(f["step_rates"]) == {"Leads->MQL", "MQL->SQL", "SQL->Won"}
    for v in f["step_rates"].values():
        assert 0.0 <= v <= 1.0


def test_compute_funnel_table_columns():
    df = generate_synthetic_data(months=8, seed=1)
    t = compute_funnel_table(df)
    assert "lead_to_won" in t.columns
    assert len(t) == 8
    assert (t["lead_to_won"] >= 0).all()


def test_compute_funnel_table_empty():
    t = compute_funnel_table(pd.DataFrame())
    assert t.empty


def test_compute_conversion_rate_basic():
    df = generate_synthetic_data(months=6, seed=1)
    cr = compute_conversion_rate(df, "leads", "won_deals")
    assert list(cr.columns) == ["month", "conversion_rate"]
    assert (cr["conversion_rate"] >= 0).all()
    assert (cr["conversion_rate"] <= 1).all()


def test_compute_conversion_rate_unknown_stage():
    df = generate_synthetic_data(months=4, seed=1)
    cr = compute_conversion_rate(df, "leads", "ghost_stage")
    assert cr.empty


def test_funnel_stages_order():
    assert FUNNEL_STAGES == ("leads", "qualified_leads", "opportunities", "won_deals")


def test_compute_funnel_zero_leads():
    df = pd.DataFrame(
        [{"month": "2024-01", "mrr": 0.0, "customers": 0, "new_customers": 0,
          "churned_customers": 0, "leads": 0, "qualified_leads": 0,
          "opportunities": 0, "won_deals": 0}]
    )
    f = compute_funnel(df)
    assert f["overall_rate"] == 0.0
    assert f["total_leads"] == 0
