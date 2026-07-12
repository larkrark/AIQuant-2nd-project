"""
viz_hsi_candidate_plotly.py 의 Streamlit 탭 버전.

원본 스크립트와 차이:
- fig.show() / write_html() 대신 st.plotly_chart() 로 렌더링
- CSV 경로를 docs/tab/ (이 파일과 같은 폴더) 기준으로 수정
  (원본은 존재하지 않는 docs/output/tables/..._dedup.csv 를 참조했음)
- dedup 파일 대신 원본 timeseries CSV + drop_duplicates 안전장치 사용
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent

TS_PATH = DATA_DIR / "23_main_final_report_candidate_timeseries_subset.csv"
LAMBDA_TABLE_PATH = DATA_DIR / "23_main_final_report_lambda_family_table.csv"
SHORTLIST_PATH = DATA_DIR / "23_main_final_report_candidate_shortlist.csv"
COST_PIVOT_PATH = DATA_DIR / "23_main_final_report_candidate_cost_pivot.csv"

DISPLAY_STRATEGIES = [
    "EW",
    "HSI_final_baseline_overlay",
    "lambda_0.1",
    "lambda_0.3",
    "lambda_0.5",
    "HSI_event_balance_filter_overlay",
]

LABEL_MAP = {
    "EW": "EW Benchmark",
    "HSI_final_baseline_overlay": "HSI Baseline",
    "HSI_event_balance_filter_overlay": "Event Filter",
    "lambda_0.1": "Lambda 0.1",
    "lambda_0.3": "Lambda 0.3",
    "lambda_0.5": "Lambda 0.5",
    "lambda_0.7": "Lambda 0.7",
    "lambda_1.0": "Lambda 1.0",
}


@st.cache_data
def load_data():
    ts = pd.read_csv(TS_PATH, encoding="utf-8-sig")
    lambda_table = pd.read_csv(LAMBDA_TABLE_PATH, encoding="utf-8-sig")
    shortlist = pd.read_csv(SHORTLIST_PATH, encoding="utf-8-sig")
    cost_pivot = pd.read_csv(COST_PIVOT_PATH, encoding="utf-8-sig")

    # 중복 제거 안전장치 (원본 스크립트의 dedup 로직 유지)
    ts = (
        ts.sort_values(["strategy_name", "year_month"])
        .drop_duplicates(subset=["strategy_name", "year_month"], keep="last")
        .reset_index(drop=True)
    )
    ts["year_month"] = pd.to_datetime(ts["year_month"])

    return ts, lambda_table, shortlist, cost_pivot


def build_cumulative_return_fig(plot_ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        plot_ts,
        x="year_month",
        y="cumulative_return",
        color="strategy_label",
        hover_data={
            "strategy_name": True,
            "year_month": "|%Y-%m",
            "cumulative_return": ":.3f",
            "strategy_return": ":.3%",
            "drawdown": ":.3%",
            "turnover": ":.3%",
        },
        title="HSI Overlay 후보 전략 누적수익률 비교",
        labels={
            "year_month": "월",
            "cumulative_return": "누적수익률 지수",
            "strategy_label": "전략",
        },
    )
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        legend_title_text="전략",
    )
    fig.update_xaxes(
        showspikes=True,
        spikecolor="blue",
        spikethickness=1,
        spikemode="across",
        spikesnap="cursor",
    )
    return fig


def build_drawdown_fig(plot_ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        plot_ts,
        x="year_month",
        y="drawdown",
        color="strategy_label",
        hover_data={
            "strategy_name": True,
            "year_month": "|%Y-%m",
            "drawdown": ":.3%",
            "cumulative_return": ":.3f",
            "strategy_return": ":.3%",
            "turnover": ":.3%",
        },
        title="HSI Overlay 후보 전략 Drawdown 비교",
        labels={
            "year_month": "월",
            "drawdown": "Drawdown",
            "strategy_label": "전략",
        },
    )
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        legend_title_text="전략",
    )
    fig.update_yaxes(tickformat=".0%")
    fig.update_xaxes(
        showspikes=True,
        spikecolor="blue",
        spikethickness=1,
        spikemode="across",
        spikesnap="cursor",
    )
    return fig


def build_lambda_family_fig(lambda_table: pd.DataFrame) -> go.Figure:
    lambda_plot = lambda_table[
        lambda_table["strategy_name"].isin(
            [
                "EW",
                "HSI_final_baseline_overlay",
                "lambda_0.1",
                "lambda_0.3",
                "lambda_0.5",
                "lambda_0.7",
            ]
        )
    ].copy()

    fig = go.Figure()
    for col, name in [
        ("CAGR_pct", "CAGR"),
        ("MDD_pct", "MDD"),
        ("avg_turnover_pct", "Avg Turnover"),
    ]:
        fig.add_trace(
            go.Bar(
                x=lambda_plot["strategy_label"],
                y=lambda_plot[col],
                name=name,
                text=lambda_plot[col].round(2).astype(str) + "%",
                textposition="outside",
            )
        )

    fig.update_layout(
        title="λ 부분조정 후보 성과 비교",
        xaxis_title="전략",
        yaxis_title="%",
        barmode="group",
        template="plotly_white",
        legend_title_text="지표",
    )
    return fig


def build_cost_sensitivity_fig(cost_pivot: pd.DataFrame) -> go.Figure:
    cost_selected = cost_pivot[
        cost_pivot["strategy_name"].isin(
            [
                "HSI_final_baseline_overlay",
                "lambda_0.1",
                "lambda_0.3",
                "lambda_0.5",
                "HSI_event_balance_filter_overlay",
            ]
        )
    ].copy()

    cost_selected["strategy_label"] = (
        cost_selected["strategy_name"].map(LABEL_MAP).fillna(cost_selected["strategy_name"])
    )

    fig = px.line(
        cost_selected,
        x="cost_bps",
        y="CAGR_pct_after_cost_est",
        color="strategy_label",
        markers=True,
        hover_data={
            "strategy_name": True,
            "cost_bps": True,
            "CAGR_pct_before_cost": ":.2f",
            "avg_turnover_pct": ":.2f",
            "annual_cost_drag_pct_est": ":.3f",
            "CAGR_pct_after_cost_est": ":.2f",
        },
        title="거래비용 가정별 추정 CAGR 비교",
        labels={
            "cost_bps": "거래비용 가정 (bps)",
            "CAGR_pct_after_cost_est": "비용 반영 후 추정 CAGR (%)",
            "strategy_label": "전략",
        },
    )
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        legend_title_text="전략",
    )
    return fig


def render_viz_hsi_candidate() -> None:
    st.header("HSI Overlay 후보 전략 시각화")
    st.caption(
        "23번 후보 선별 산출물 CSV 기준. 누적수익률, Drawdown, λ family 성과, "
        "거래비용 민감도를 비교합니다."
    )

    try:
        ts, lambda_table, shortlist, cost_pivot = load_data()
    except FileNotFoundError as e:
        st.error(f"CSV 파일을 찾을 수 없습니다: {e}")
        return

    available = ts["strategy_name"].unique().tolist()
    selected = [s for s in DISPLAY_STRATEGIES if s in available]

    plot_ts = ts[ts["strategy_name"].isin(selected)].copy()
    plot_ts["strategy_label"] = plot_ts["strategy_name"].map(LABEL_MAP).fillna(
        plot_ts["strategy_name"]
    )
    lambda_table = lambda_table.copy()
    lambda_table["strategy_label"] = lambda_table["strategy_name"].map(LABEL_MAP).fillna(
        lambda_table["strategy_name"]
    )

    st.plotly_chart(build_cumulative_return_fig(plot_ts), use_container_width=True)
    st.plotly_chart(build_drawdown_fig(plot_ts), use_container_width=True)
    st.plotly_chart(build_lambda_family_fig(lambda_table), use_container_width=True)
    st.plotly_chart(build_cost_sensitivity_fig(cost_pivot), use_container_width=True)

    st.subheader("최종 후보 shortlist")
    st.dataframe(shortlist, use_container_width=True, hide_index=True)
