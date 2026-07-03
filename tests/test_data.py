"""src.data のテスト: 合成データ生成・CSV読込・検証。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data import REQUIRED_COLUMNS, generate_synthetic_data, load_csv, validate_dataframe


def test_generate_synthetic_data_has_required_columns():
    df = generate_synthetic_data(months=12, seed=1)
    assert list(df.columns) == list(REQUIRED_COLUMNS)
    assert len(df) == 12


def test_generate_synthetic_data_non_negative():
    df = generate_synthetic_data(months=18, seed=7)
    for col in REQUIRED_COLUMNS[1:]:
        assert (df[col] >= 0).all(), f"negative values in {col}"


def test_generate_synthetic_data_months_zero_returns_empty():
    df = generate_synthetic_data(months=0, seed=1)
    assert df.empty
    assert list(df.columns) == list(REQUIRED_COLUMNS)


def test_generate_synthetic_data_reproducible():
    a = generate_synthetic_data(months=10, seed=42)
    b = generate_synthetic_data(months=10, seed=42)
    pd.testing.assert_frame_equal(a, b)


def test_validate_dataframe_fills_missing_columns(tmp_path: Path):
    raw = pd.DataFrame({"month": ["2024-01", "2024-02"], "mrr": [100.0, 120.0]})
    out = validate_dataframe(raw)
    assert list(out.columns) == list(REQUIRED_COLUMNS)
    assert len(out) == 2
    assert (out["customers"] == 0).all()


def test_validate_dataframe_clips_negative_and_coerces():
    raw = pd.DataFrame(
        {
            "month": ["2024-01", "2024-02"],
            "mrr": [100.0, -50.0],
            "customers": [10, 20],
            "new_customers": [3, "oops"],
            "churned_customers": [1, 2],
            "leads": [100, 200],
            "qualified_leads": [40, 80],
            "opportunities": [15, 30],
            "won_deals": [3, 6],
        }
    )
    out = validate_dataframe(raw)
    assert (out["mrr"] >= 0).all()
    assert out.loc[1, "new_customers"] == 0.0  # "oops" -> coerce to NaN -> fill 0


def test_validate_dataframe_empty_returns_empty_frame():
    out = validate_dataframe(pd.DataFrame())
    assert out.empty
    assert list(out.columns) == list(REQUIRED_COLUMNS)


def test_validate_dataframe_none_returns_empty():
    out = validate_dataframe(None)
    assert out.empty


def test_validate_dataframe_drops_blank_months():
    raw = pd.DataFrame(
        {
            "month": ["2024-01", "", "2024-03"],
            "mrr": [1, 2, 3],
            "customers": [1, 1, 1],
            "new_customers": [0, 0, 0],
            "churned_customers": [0, 0, 0],
            "leads": [1, 1, 1],
            "qualified_leads": [1, 1, 1],
            "opportunities": [1, 1, 1],
            "won_deals": [1, 1, 1],
        }
    )
    out = validate_dataframe(raw)
    assert len(out) == 2
    assert list(out["month"]) == ["2024-01", "2024-03"]


def test_load_csv_missing_file_returns_empty(tmp_path: Path):
    out = load_csv(tmp_path / "does_not_exist.csv")
    assert out.empty
    assert list(out.columns) == list(REQUIRED_COLUMNS)


def test_load_csv_empty_file_returns_empty(tmp_path: Path):
    p = tmp_path / "empty.csv"
    p.write_text("")
    out = load_csv(p)
    assert out.empty


def test_load_csv_roundtrip(tmp_path: Path):
    df = generate_synthetic_data(months=6, seed=2)
    p = tmp_path / "kpi.csv"
    df.to_csv(p, index=False)
    out = load_csv(p)
    assert len(out) == 6
    assert list(out.columns) == list(REQUIRED_COLUMNS)
    assert out["mrr"].iloc[-1] == df["mrr"].iloc[-1]
