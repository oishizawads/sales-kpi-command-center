"""Sales KPI Command Center — Streamlitエントリポイント。

UIは薄く保ち、集計・閾値判定は src/ に委譲する。
実行: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.alerts import DEFAULT_THRESHOLDS, evaluate_alerts
from src.data import REQUIRED_COLUMNS, generate_synthetic_data, validate_dataframe
from src.funnel import compute_funnel, compute_funnel_table
from src.metrics import compute_churn_rate, compute_mrr_trend, compute_summary

st.set_page_config(
    page_title="Sales KPI Command Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

SEVERITY_STYLE = {
    "CRITICAL": ("🔴", "critical"),
    "WARNING": ("🟠", "warning"),
    "INFO": ("🔵", "info"),
}


# ---------- データ読み込み ----------

@st.cache_data(show_spinner=False)
def _cached_synthetic(months: int, seed: int) -> pd.DataFrame:
    return generate_synthetic_data(months=months, seed=seed)


@st.cache_data(show_spinner=False)
def _cached_summary(df: pd.DataFrame) -> dict:
    return compute_summary(df)


@st.cache_data(show_spinner=False)
def _cached_mrr_trend(df: pd.DataFrame) -> pd.DataFrame:
    return compute_mrr_trend(df)


@st.cache_data(show_spinner=False)
def _cached_funnel(df: pd.DataFrame, month: str | None) -> dict:
    return compute_funnel(df, month=month)


@st.cache_data(show_spinner=False)
def _cached_funnel_table(df: pd.DataFrame) -> pd.DataFrame:
    return compute_funnel_table(df)


@st.cache_data(show_spinner=False)
def _cached_alerts(df: pd.DataFrame, thresholds_tuple: tuple) -> list:
    thresholds = dict(thresholds_tuple)
    return evaluate_alerts(df, thresholds=thresholds)


def _thresholds_to_tuple(th: dict) -> tuple:
    return tuple(sorted(th.items()))


# ---------- サイドバー ----------

with st.sidebar:
    st.header("⚙️ Data & Settings")
    data_mode = st.radio("Data source", ["Synthetic (sample)", "Upload CSV"], index=0)

    df: pd.DataFrame
    if data_mode == "Synthetic (sample)":
        col1, col2 = st.columns(2)
        with col1:
            months_n = st.number_input("Months", min_value=3, max_value=60, value=24, step=1)
        with col2:
            seed = st.number_input("Seed", min_value=0, max_value=10_000, value=42, step=1)
        if st.button("Regenerate", type="primary", width="stretch"):
            st.session_state["regen_counter"] = st.session_state.get("regen_counter", 0) + 1
        regen = st.session_state.get("regen_counter", 0)
        df = _cached_synthetic(int(months_n) + regen * 0, int(seed) + regen)
    else:
        uploaded = st.file_uploader(
            "Upload KPI CSV", type=["csv"],
            help=f"Required columns: {', '.join(REQUIRED_COLUMNS)}",
        )
        if uploaded is not None:
            try:
                raw = pd.read_csv(uploaded)
            except Exception as exc:
                st.error(f"Could not parse CSV: {exc}")
                df = pd.DataFrame()
            else:
                df = validate_dataframe(raw)
        else:
            df = pd.DataFrame()

    st.divider()
    st.subheader("Alert thresholds")
    th_churn_warn = st.slider("Churn warning", 0.01, 0.20, float(DEFAULT_THRESHOLDS["churn_warning"]), 0.005, format="%.3f")
    th_churn_crit = st.slider("Churn critical", 0.02, 0.30, float(DEFAULT_THRESHOLDS["churn_critical"]), 0.005, format="%.3f")
    th_mrr_warn = st.slider("MRR drop warning", -0.30, -0.01, float(DEFAULT_THRESHOLDS["mrr_drop_warning"]), 0.01, format="%.2f")
    th_mrr_crit = st.slider("MRR drop critical", -0.50, -0.02, float(DEFAULT_THRESHOLDS["mrr_drop_critical"]), 0.01, format="%.2f")
    th_conv_warn = st.slider("Conversion warning", 0.001, 0.10, float(DEFAULT_THRESHOLDS["conversion_warning"]), 0.001, format="%.3f")

    thresholds = {
        "churn_warning": th_churn_warn,
        "churn_critical": max(th_churn_crit, th_churn_warn + 0.005),
        "mrr_drop_warning": th_mrr_warn,
        "mrr_drop_critical": min(th_mrr_crit, th_mrr_warn - 0.01),
        "conversion_warning": th_conv_warn,
        "conversion_critical": float(DEFAULT_THRESHOLDS["conversion_critical"]),
        "negative_mrr_streak": int(DEFAULT_THRESHOLDS["negative_mrr_streak"]),
    }

    st.divider()
    with st.expander("Required CSV schema", expanded=False):
        st.code(", ".join(REQUIRED_COLUMNS), language="text")
        st.caption("Numeric columns must be non-negative. month = YYYY-MM string.")


# ---------- ヘルパー ----------

def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def _fmt_pct(x: float, sign: bool = False) -> str:
    return f"{x:+.1%}" if sign else f"{x:.1%}"


def _empty_state(msg: str) -> None:
    st.info(msg)


def _fig_base(fig: go.Figure, title: str, y_title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title=y_title,
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _chart(fig: go.Figure, key: str) -> None:
    """plotly_chartを一意キー付きで描画（重複要素IDエラーを回避）。"""
    st.plotly_chart(fig, width="stretch", key=key)


# ---------- メイン ----------

from src.brand import apply_brand, hero
apply_brand(st)
hero(st, "Analytics Dashboard", "Sales KPI Command Center", "SaaS の主要 KPI を一覧し、異常値と次の確認ポイントを表示します。")
st.caption("Synthetic SaaS KPI dashboard — data is generated, not from any real company.")

if df is None or df.empty:
    _empty_state(
        "No data to display yet. Choose **Synthetic (sample)** in the sidebar, "
        "or upload a CSV with the required columns."
    )
    st.stop()

valid_months = sorted(df["month"].astype(str).unique())
selected_month = st.selectbox("Focus month", valid_months, index=len(valid_months) - 1)

summary = _cached_summary(df)
mrr_trend = _cached_mrr_trend(df)
funnel = _cached_funnel(df, selected_month)
funnel_table = _cached_funnel_table(df)
alerts = _cached_alerts(df, _thresholds_to_tuple(thresholds))

tab_overview, tab_funnel, tab_revenue, tab_churn, tab_alerts = st.tabs(
    ["KPI Overview", "Funnel", "Revenue Trend", "Churn", "Alerts"]
)

with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("MRR", _fmt_money(summary["mrr"]), _fmt_pct(summary["mrr_growth"], sign=True))
    c2.metric("Customers", f"{summary['customers']:,}", f"{summary['net_new_customers']:+d}")
    c3.metric("Churn rate", _fmt_pct(summary["churn_rate"]))
    c4.metric("Conversion (won/leads)", _fmt_pct(summary["conversion_rate"]))

    st.markdown(f"**Latest month:** {summary['latest_month']}  •  **Previous:** {summary['prev_month']}")

    spark_c1, spark_c2 = st.columns(2)
    with spark_c1:
        fig = px.area(mrr_trend, x="month", y="mrr", labels={"mrr": "MRR (USD)", "month": "Month"})
        _fig_base(fig, "MRR trend", "MRR (USD)")
        _chart(fig, "overview_mrr")
    with spark_c2:
        churn_df = df.sort_values("month").copy()
        churn_df["churn_rate"] = compute_churn_rate(churn_df)
        fig = px.line(churn_df, x="month", y="churn_rate", labels={"churn_rate": "Churn rate", "month": "Month"})
        fig.update_yaxes(tickformat=".0%")
        _fig_base(fig, "Churn rate trend", "Churn rate")
        _chart(fig, "overview_churn")

with tab_funnel:
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader(f"Funnel — {funnel['month']}")
        if funnel["total_leads"] > 0:
            stage_names = list(funnel["stages"].keys())
            stage_vals = list(funnel["stages"].values())
            fig = go.Figure(go.Funnel(y=stage_names, x=stage_vals, textinfo="value+percent initial"))
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
            _chart(fig, "funnel_chart")
        else:
            st.info("No leads in the selected month.")
    with col_b:
        st.markdown("**Step conversion rates**")
        if funnel["step_rates"]:
            for step, rate in funnel["step_rates"].items():
                st.write(f"- {step}: **{_fmt_pct(rate)}**")
            st.write(f"- Overall (Lead→Won): **{_fmt_pct(funnel['overall_rate'])}**")
        else:
            st.write("—")

    st.markdown("---")
    st.subheader("Monthly funnel breakdown")
    st.dataframe(funnel_table, width="stretch", hide_index=True)

with tab_revenue:
    st.subheader("MRR trend & MoM growth")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        fig = px.line(mrr_trend, x="month", y="mrr", labels={"mrr": "MRR (USD)", "month": "Month"})
        _fig_base(fig, "Monthly MRR", "MRR (USD)")
        _chart(fig, "revenue_mrr")
    with col_r:
        fig = px.bar(mrr_trend, x="month", y="mrr_growth", labels={"mrr_growth": "MoM growth", "month": "Month"})
        fig.update_yaxes(tickformat=".0%")
        _fig_base(fig, "MRR MoM growth", "MoM growth")
        _chart(fig, "revenue_mom")

with tab_churn:
    st.subheader("Churn")
    churn_df = df.sort_values("month").copy()
    churn_df["churn_rate"] = compute_churn_rate(churn_df)
    col_l, col_r = st.columns(2)
    with col_l:
        fig = px.bar(churn_df, x="month", y="churned_customers", labels={"churned_customers": "Churned customers", "month": "Month"})
        _fig_base(fig, "Churned customers / month", "Customers")
        _chart(fig, "churn_bar")
    with col_r:
        fig = px.line(churn_df, x="month", y="churn_rate", labels={"churn_rate": "Churn rate", "month": "Month"})
        fig.update_yaxes(tickformat=".0%")
        _fig_base(fig, "Churn rate trend", "Churn rate")
        _chart(fig, "churn_rate")
    st.caption("Churn rate = churned_customers / customers. Customers is end-of-month count (0 のとき 0)。")

with tab_alerts:
    st.subheader(f"Alerts ({len(alerts)})")
    if not alerts:
        st.success("No alerts — all KPIs within thresholds.")
    else:
        for a in alerts:
            icon, kind = SEVERITY_STYLE.get(a.severity, ("⚪", "info"))
            if kind == "critical":
                st.error(f"{icon} **[{a.severity}] {a.kpi} — {a.month}**  \n{a.message}")
            elif kind == "warning":
                st.warning(f"{icon} **[{a.severity}] {a.kpi} — {a.month}**  \n{a.message}")
            else:
                st.info(f"{icon} **[{a.severity}] {a.kpi} — {a.month}**  \n{a.message}")

    st.markdown("---")
    st.subheader("Alert timeline")
    if alerts:
        al_df = pd.DataFrame(
            [{"month": a.month, "kpi": a.kpi, "severity": a.severity, "value": a.value} for a in alerts]
        )
        sev_order = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
        al_df["sev_rank"] = al_df["severity"].map(sev_order)
        fig = px.scatter(
            al_df, x="month", y="kpi", color="severity", size="sev_rank",
            category_orders={"severity": ["CRITICAL", "WARNING", "INFO"]},
            labels={"month": "Month", "kpi": "KPI"},
        )
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
        _chart(fig, "alert_timeline")
    else:
        st.write("—")

with st.expander("Data preview", expanded=False):
    st.dataframe(df.sort_values("month"), width="stretch", hide_index=True)
