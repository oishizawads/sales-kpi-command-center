"""KPI閾値アラートロジック。純関数。

閾値はデフォルト値を持つが、UIから上書き可能。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.metrics import _safe_ratio, compute_churn_rate

SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_CRITICAL = "CRITICAL"

_SEVERITY_ORDER = {SEVERITY_INFO: 0, SEVERITY_WARNING: 1, SEVERITY_CRITICAL: 2}

DEFAULT_THRESHOLDS: dict[str, float] = {
    "churn_warning": 0.06,
    "churn_critical": 0.10,
    "mrr_drop_warning": -0.10,
    "mrr_drop_critical": -0.20,
    "conversion_warning": 0.015,
    "conversion_critical": 0.008,
    "negative_mrr_streak": 2,
}


@dataclass(frozen=True)
class Alert:
    """単一アラート。"""

    kpi: str
    severity: str
    month: str
    value: float
    threshold: float
    message: str

    @property
    def rank(self) -> int:
        return _SEVERITY_ORDER.get(self.severity, 0)


def evaluate_alerts(
    df: pd.DataFrame,
    thresholds: dict[str, float] | None = None,
) -> list[Alert]:
    """DataFrame全体を走査し、閾値超過のアラートを返す。

    Args:
        df: REQUIRED_COLUMNS を持つ月次DataFrame。
        thresholds: 閾値オーバーライド。未指定時はDEFAULT_THRESHOLDS。

    Returns:
        重大度高順、月降順でソートされたAlertのリスト。空データ時は空リスト。
    """
    if df is None or df.empty:
        return []

    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    d = df.sort_values("month").reset_index(drop=True)
    alerts: list[Alert] = []

    churn_rates = compute_churn_rate(d)
    for i, row in d.iterrows():
        month = str(row["month"])
        churn = float(churn_rates.iloc[i])
        if churn >= th["churn_critical"]:
            alerts.append(
                _alert("Churn", SEVERITY_CRITICAL, month, churn, th["churn_critical"],
                       f"Churn rate {churn:.1%} >= {th['churn_critical']:.1%}")
            )
        elif churn >= th["churn_warning"]:
            alerts.append(
                _alert("Churn", SEVERITY_WARNING, month, churn, th["churn_warning"],
                       f"Churn rate {churn:.1%} >= {th['churn_warning']:.1%}")
            )

    mrr = d["mrr"].astype(float).to_numpy()
    prev = np.concatenate([[np.nan], mrr[:-1]])
    with np.errstate(divide="ignore", invalid="ignore"):
        growth = np.where(prev > 0, (mrr - prev) / prev, 0.0)
    growth = np.nan_to_num(growth, nan=0.0, posinf=0.0, neginf=0.0)

    negative_streak = 0
    for i, row in enumerate(d.itertuples(index=False)):
        month = str(row.month)
        g = float(growth[i])
        if i == 0:
            continue
        if g <= th["mrr_drop_critical"]:
            alerts.append(
                _alert("MRR", SEVERITY_CRITICAL, month, g, th["mrr_drop_critical"],
                       f"MRR MoM {g:+.1%} <= {th['mrr_drop_critical']:+.1%}")
            )
        elif g <= th["mrr_drop_warning"]:
            alerts.append(
                _alert("MRR", SEVERITY_WARNING, month, g, th["mrr_drop_warning"],
                       f"MRR MoM {g:+.1%} <= {th['mrr_drop_warning']:+.1%}")
            )
        if g < 0:
            negative_streak += 1
            if negative_streak >= int(th["negative_mrr_streak"]):
                alerts.append(
                    _alert("MRR", SEVERITY_INFO, month, float(g), th["negative_mrr_streak"],
                           f"MRR decline for {negative_streak} consecutive months")
                )
        else:
            negative_streak = 0

    for _, row in d.iterrows():
        month = str(row["month"])
        conv = _safe_ratio(float(row["won_deals"]), float(row["leads"]))
        if conv <= th["conversion_critical"] and conv > 0:
            alerts.append(
                _alert("Conversion", SEVERITY_CRITICAL, month, conv, th["conversion_critical"],
                       f"Conversion {conv:.2%} <= {th['conversion_critical']:.2%}")
            )
        elif conv < th["conversion_warning"]:
            alerts.append(
                _alert("Conversion", SEVERITY_WARNING, month, conv, th["conversion_warning"],
                       f"Conversion {conv:.2%} < {th['conversion_warning']:.2%}")
            )

    return _dedupe(alerts)


def _alert(kpi: str, severity: str, month: str, value: float, threshold: float, message: str) -> Alert:
    return Alert(kpi=kpi, severity=severity, month=month, value=value, threshold=threshold, message=message)


def _dedupe(alerts: Iterable[Alert]) -> list[Alert]:
    """同一(kpi, severity, month)の重複を除去し、重大度高順・月降順で返す。"""
    seen: dict[tuple, Alert] = {}
    for a in alerts:
        key = (a.kpi, a.severity, a.month)
        if key not in seen or a.rank > seen[key].rank:
            seen[key] = a
    return sorted(seen.values(), key=lambda a: (-a.rank, a.month))


def sort_alerts(alerts: Iterable[Alert]) -> list[Alert]:
    """アラートを重大度高順、月降順でソートする。"""
    return sorted(list(alerts), key=lambda a: (-a.rank, a.month), reverse=False)
