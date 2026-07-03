"""Sales KPI Command Center — calculation and alert logic."""

from src.alerts import Alert, evaluate_alerts
from src.data import generate_synthetic_data, load_csv, validate_dataframe
from src.funnel import compute_conversion_rate, compute_funnel, compute_funnel_table
from src.metrics import (
    compute_churn_rate,
    compute_mom_change,
    compute_mrr_trend,
    compute_summary,
)

__all__ = [
    "Alert",
    "compute_churn_rate",
    "compute_conversion_rate",
    "compute_funnel",
    "compute_funnel_table",
    "compute_mom_change",
    "compute_mrr_trend",
    "compute_summary",
    "evaluate_alerts",
    "generate_synthetic_data",
    "load_csv",
    "validate_dataframe",
]
