"""src.alerts のテスト: 閾値判定・重大度・空データ耐性・異常値。"""

from __future__ import annotations

import pandas as pd

from src.alerts import DEFAULT_THRESHOLDS, SEVERITY_CRITICAL, SEVERITY_WARNING, evaluate_alerts
from src.data import generate_synthetic_data


def test_evaluate_alerts_empty_returns_empty():
    assert evaluate_alerts(pd.DataFrame()) == []


def test_evaluate_alerts_none_returns_empty():
    assert evaluate_alerts(None) == []


def test_evaluate_alerts_detects_churn_spike():
    df = generate_synthetic_data(months=14, seed=5)
    # 異常チャーン月を作る
    df.loc[5, "churned_customers"] = int(df.loc[5, "customers"] * 0.15)
    alerts = evaluate_alerts(df)
    churn_alerts = [a for a in alerts if a.kpi == "Churn" and a.month == df.loc[5, "month"]]
    assert len(churn_alerts) >= 1
    assert churn_alerts[0].severity == SEVERITY_CRITICAL


def test_evaluate_alerts_detects_mrr_drop():
    df = generate_synthetic_data(months=12, seed=2)
    # 前月比で明確に -50% の下落を作る（異常月の干渉を避けるため前月基準）
    df.loc[8, "mrr"] = float(df.loc[7, "mrr"]) * 0.5
    alerts = evaluate_alerts(df)
    mrr_alerts = [a for a in alerts if a.kpi == "MRR" and a.month == df.loc[8, "month"]]
    assert any(a.severity == SEVERITY_CRITICAL for a in mrr_alerts)


def test_evaluate_alerts_threshold_override():
    df = generate_synthetic_data(months=12, seed=9)
    strict = {"churn_warning": 0.001, "churn_critical": 0.002,
              "mrr_drop_warning": -0.001, "mrr_drop_critical": -0.5,
              "conversion_warning": 0.999, "conversion_critical": 0.0,
              "negative_mrr_streak": 99}
    alerts = evaluate_alerts(df, thresholds=strict)
    # 閾値が極端に厳しいので多数のアラートが出るはず
    assert len(alerts) > 0


def test_evaluate_alerts_synthetic_has_at_least_some():
    # 合成データには意図的な異常月が仕込まれている
    df = generate_synthetic_data(months=24, seed=42)
    alerts = evaluate_alerts(df)
    assert len(alerts) > 0
    severities = {a.severity for a in alerts}
    assert severities & {SEVERITY_WARNING, SEVERITY_CRITICAL}


def test_evaluate_alerts_sorted_by_severity_then_month():
    df = generate_synthetic_data(months=24, seed=42)
    alerts = evaluate_alerts(df)
    ranks = [-a.rank for a in alerts]
    assert ranks == sorted(ranks)


def test_evaluate_alerts_handles_all_zero_dataframe():
    df = pd.DataFrame(
        [
            {"month": "2024-01", "mrr": 0.0, "customers": 0, "new_customers": 0,
             "churned_customers": 0, "leads": 0, "qualified_leads": 0,
             "opportunities": 0, "won_deals": 0},
            {"month": "2024-02", "mrr": 0.0, "customers": 0, "new_customers": 0,
             "churned_customers": 0, "leads": 0, "qualified_leads": 0,
             "opportunities": 0, "won_deals": 0},
        ]
    )
    # 0割やNaNで落ちないことだけ保証
    alerts = evaluate_alerts(df)
    assert isinstance(alerts, list)


def test_default_thresholds_sanity():
    assert DEFAULT_THRESHOLDS["churn_critical"] > DEFAULT_THRESHOLDS["churn_warning"]
    assert DEFAULT_THRESHOLDS["mrr_drop_critical"] < DEFAULT_THRESHOLDS["mrr_drop_warning"]
